# =============================================================================
#  Filename: self_reviewer.py
#
#  Short Description: Self-reviewer agent(s) for the periodic employee self-review process.
#
#  Creation date: 2025-09-01
#  Author: Chandar L
# =============================================================================
from langchain_mcp_adapters.client import MultiServerMCPClient
from langchain.chat_models import init_chat_model
from langgraph.graph import StateGraph, START, END
from langgraph.prebuilt import ToolNode
from typing_extensions import TypedDict
from typing import Annotated, Optional, Literal
from langchain_core.messages import AnyMessage
from langgraph.graph.message import add_messages
from pydantic import BaseModel, Field
import asyncio
from rich import print as rprint
from dotenv import load_dotenv

load_dotenv()

class LLMResponse(BaseModel):
    """
    Structured response model for LLM outputs.
    
    This Pydantic model ensures that the LLM returns the response in a consistent format.
    """
    original_text: str = Field(..., description="The original self-review input text")
    copy_edited_text: Optional[str] = Field(None, description="The copy-edited text")
    summary: Optional[str] = Field(None, description="The abstractive summary of the text")
    word_cloud_path: Optional[str] = Field(None, description="Path to the generated word cloud image file")

class GraphState(TypedDict):
    """
    State definition for the LangGraph workflow.
    
    This TypedDict defines the structure of the state that flows through the LangGraph,
    containing all the data needed at each step of the workflow.
    
    The state is passed between nodes and updated as the workflow progresses.
    
    Attributes:
        original_text (str): The original self-review input text
        copy_edited_text (Optional[str]): The copy-edited text
        summary (Optional[str]): The abstractive summary of the text
        word_cloud_path (Optional[str]): Path to the generated word cloud image file
        messages (Annotated[list, add_messages]): Conversation messages that get appended to the state
        tools_completed (list): List of completed tool names to track progress
    """
    original_text: str
    copy_edited_text: Optional[str]
    summary: Optional[str]
    word_cloud_path: Optional[str]
    messages: Annotated[list[AnyMessage], add_messages]
    tools_completed: list[str]

# Initialize the model
model = init_chat_model("openai:gpt-4o")

self_reviewer_system_prompt = """
You are an intelligent assistant that helps users with self-review. You MUST use the tools provided to you to complete the task.

DO NOT USE YOUR OWN KNOWLEDGE TO COMPLETE THE TASK. ONLY USE THE TOOLS PROVIDED TO YOU.

Here's your workflow:

1. First, call the copy_edit tool to fix any grammatical or spelling mistakes in the input text.
2. Then call the abstractive_summarize tool to provide a summary of the corrected text.
3. Finally, call the word_cloud tool to generate a word cloud of the corrected text.

IMPORTANT: 
- You can call all three tools in a single response if you want
- After all three tools complete, you MUST return the final response as a JSON object
- Do NOT ask if there's anything else - just return the JSON response
- Do NOT continue chatting - return the JSON and stop

The final response should be a JSON object with the following EXACT format:
{
  "original_text": "The original self-review input text",
  "copy_edited_text": "The corrected text from copy_edit tool",
  "summary": "The abstractive summary from abstractive_summarize tool",
  "word_cloud_path": "Path to the generated word cloud image file from word_cloud tool"
}

CRITICAL: After calling all three tools, return ONLY the JSON response in the exact format above. Do not ask questions or offer additional help. Do not add any other text before or after the JSON.
"""

# Set up MCP client
client = MultiServerMCPClient(
    {
        "text_modifier_mcp_server": {
            # make sure you start your text_modifier_mcp_server on port 3333
            "url": "http://localhost:3333/mcp",
            "transport": "streamable_http",
        }
    }
)

async def initialize_components():
    global tools, model_with_tools, tool_node
    tools = await client.get_tools()
    
    # Log available tools for debugging
    print(f"🔧 Available tools: {[tool.name for tool in tools]}")
    
    model_with_tools = model.bind_tools(tools)
    tool_node = ToolNode(tools)

async def execute_tools(state: GraphState) -> GraphState:
    """Execute all tools in the last message and return results."""
    messages = state["messages"]
    last_message = messages[-1]
    
    if not last_message.tool_calls:
        return state
    
    # Execute all tools
    tool_results = []
    for tool_call in last_message.tool_calls:
        tool_name = tool_call.get('name', '')
        tool_args = tool_call.get('args', {})
        
        # Find the tool
        tool = next((t for t in tools if t.name == tool_name), None)
        if tool:
            try:
                result = await tool.ainvoke(tool_args)
                tool_results.append(result)
                print(f"✅ Tool {tool_name} executed successfully")
            except Exception as e:
                print(f"❌ Error executing tool {tool_name}: {e}")
                tool_results.append(f"Error: {e}")
    
    # Create a new message with tool results
    from langchain_core.messages import ToolMessage
    
    tool_messages = []
    for i, (tool_call, result) in enumerate(zip(last_message.tool_calls, tool_results)):
        tool_message = ToolMessage(
            content=str(result),
            tool_call_id=tool_call.get('id', f"call_{i}"),
            name=tool_call.get('name', '')
        )
        tool_messages.append(tool_message)
    
    return {
        "messages": tool_messages
    }

# Define reviewer function with enhanced prompt for relevance checking
async def reviewer(state: GraphState) -> GraphState:
    messages = state["messages"]
    tools_completed = state.get("tools_completed", [])
    
    # If this is the first call (no previous tool calls), add a system prompt for self-reviewer
    if len(messages) == 1:
        system_prompt = self_reviewer_system_prompt        
        # Add the system prompt to the beginning
        enhanced_messages = [{"role": "system", "content": system_prompt}] + messages
    else:
        # Add context about what tools have been completed
        progress_context = f"\n\nProgress: You have completed these tools: {tools_completed}"
        if tools_completed:
            if "copy_edit" not in tools_completed:
                progress_context += "\nNext: Call the copy_edit tool first."
            elif "abstractive_summarize" not in tools_completed:
                progress_context += "\nNext: Call the abstractive_summarize tool with the copy_edited_text."
            elif "word_cloud" not in tools_completed:
                progress_context += "\nNext: Call the word_cloud tool with the copy_edited_text."
            else:
                progress_context += "\nAll tools completed! Now return the final JSON response."
        else:
            progress_context += "\nNext: Call the copy_edit tool first."
        
        enhanced_messages = [{"role": "system", "content": progress_context}] + messages
    
    response = await model_with_tools.ainvoke(enhanced_messages)
    rprint(response)
    return {
        "messages": [response],
        "tools_completed": tools_completed  # Preserve tools_completed state
    }

def should_continue(state: GraphState) -> Literal["tools", "parse"]:
    messages = state["messages"]
    tools_completed = state.get("tools_completed", [])
    last_message = messages[-1]
    
    # If there are tool calls, continue to tools
    if last_message.tool_calls:
        return "tools"
    
    # If no tool calls and all tools are completed, parse the final result
    if len(tools_completed) >= 3:
        return "parse"
    
    # If no tool calls but not all tools completed, continue to reviewer
    return "reviewer"

def track_tool_completion(state: GraphState) -> GraphState:
    """Track which tools have been completed and update the state."""
    messages = state["messages"]
    tools_completed = state.get("tools_completed", [])
    
    # Check the last message for tool calls
    if messages and hasattr(messages[-1], 'tool_calls') and messages[-1].tool_calls:
        # Process all tool calls in the message
        for tool_call in messages[-1].tool_calls:
            tool_name = tool_call.get('name', '')
            
            # Add the completed tool to the list if not already there
            if tool_name and tool_name not in tools_completed:
                tools_completed.append(tool_name)
                print(f"✅ Tool completed: {tool_name}")
        
        print(f"📊 Progress: {tools_completed}")
    
    return {
        "tools_completed": tools_completed,
        "messages": messages  # Preserve messages in state
    }

def parse(state: GraphState) -> GraphState:
    messages = state["messages"]
    last_message = messages[-1]
    print("Last message:")
    rprint(last_message)
    # parse the response to the LLMResponse model
    llm_response = LLMResponse.model_validate(last_message)
    return {
        "original_text": llm_response.original_text,
        "copy_edited_text": llm_response.copy_edited_text,
        "summary": llm_response.summary,
        "word_cloud_path": llm_response.word_cloud_path
    }

async def build_graph():
    # Initialize components first
    await initialize_components()
    
    # Build the graph following the original pattern
    builder = StateGraph(GraphState)
    builder.add_node("reviewer", reviewer)
    builder.add_node("tools", execute_tools)
    builder.add_node("track_completion", track_tool_completion)
    builder.add_node("parse", parse)

    builder.add_edge(START, "reviewer")
    builder.add_conditional_edges(
        "reviewer",
        should_continue,
        {
            "tools": "tools",
            "parse": "parse",
            "reviewer": "reviewer"
        }
    )
    builder.add_edge("tools", "track_completion")
    builder.add_edge("track_completion", "reviewer")
    builder.add_edge("parse", END)

    # Compile the graph
    graph = builder.compile()
    
    # save the graph to a file
    graph.get_graph().draw_mermaid_png(output_file_path="self_reviewer_graph.png")
    
    return graph

async def test_graph():
    # Build the graph (which initializes components)
    graph = await build_graph()
    
    # Test the graph with different types of queries
    self_review_response = await graph.ainvoke(
        {
            "messages": [{"role": "user", "content": 
            '''I had an eventful cycle this summer.  Learnt agentic workflows and implemented a self-reviewer agent
            for the periodic employee self-review process.  It significantly improved employee productivity for the organization.'''}],
            "tools_completed": []
        }
    )
    return self_review_response

# test the graph and print the results
if __name__ == "__main__":
    self_review_response = asyncio.run(test_graph())
    rprint("=== Self-Reviewer Response ===")
    rprint(self_review_response)
