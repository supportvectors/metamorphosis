# =============================================================================
#  Filename: self_reviewer.py
#
#  Short Description: Self-reviewer agent(s) for the periodic employee self-review process.
#
#  Creation date: 2025-09-01
#  Author: Chandar L
# =============================================================================
from langchain_mcp_adapters.client import MultiServerMCPClient
from langgraph.graph import StateGraph, START, END
from typing_extensions import TypedDict
from typing import Annotated, Optional
from langchain_core.messages import AnyMessage
from langgraph.graph.message import add_messages
import asyncio
import json
from rich import print as rprint

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
    """
    original_text: str
    copy_edited_text: Optional[str]
    summary: Optional[str]
    word_cloud_path: Optional[str]
    messages: Annotated[list[AnyMessage], add_messages]

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

# Global variable to store tools
tools = []

async def initialize_components():
    global tools
    tools = await client.get_tools()  
    # Log available tools for debugging
    print(f"🔧 Available tools: {[tool.name for tool in tools]}")

async def copy_editor_node(state: GraphState) -> GraphState:
    """Copy editor node."""
    original_text = state["messages"][-1].content
    
    # Find the copy_edit tool from the available tools
    copy_edit_tool = next((tool for tool in tools if tool.name == "copy_edit"), None)
    if not copy_edit_tool:
        raise ValueError("copy_edit tool not found")
    
    # Call the tool using LangChain's ainvoke method
    result = await copy_edit_tool.ainvoke({"text": original_text})
    
    # Parse the JSON result
    result_data = json.loads(result)
    copy_edited_text = result_data["copy_edited_text"]
    return {"original_text": original_text, "copy_edited_text": copy_edited_text}

async def summarizer_node(state: GraphState) -> GraphState:
    """Summarizer node."""
    # Find the abstractive_summarize tool from the available tools
    summarizer_tool = next((tool for tool in tools if tool.name == "abstractive_summarize"), None)
    if not summarizer_tool:
        raise ValueError("abstractive_summarize tool not found")
    
    # Call the tool using LangChain's ainvoke method
    result = await summarizer_tool.ainvoke({"text": state["copy_edited_text"]})
    
    # Parse the JSON result
    result_data = json.loads(result)
    summary = result_data["summarized_text"]
    return {"summary": summary}

async def wordcloud_node(state: GraphState) -> GraphState:
    """Wordcloud node."""
    # Find the word_cloud tool from the available tools
    wordcloud_tool = next((tool for tool in tools if tool.name == "word_cloud"), None)
    if not wordcloud_tool:
        raise ValueError("word_cloud tool not found")
    
    # Call the tool using LangChain's ainvoke method
    result = await wordcloud_tool.ainvoke({"text": state["copy_edited_text"]})
    
    # The word_cloud tool returns a string path directly, not JSON
    wordcloud_path = result
    
    return {"word_cloud_path": wordcloud_path}

async def build_graph():
    # Initialize components first
    await initialize_components()
    
    # Build the graph following the original pattern
    builder = StateGraph(GraphState)

    # add the nodes to the graph
    builder.add_node("copy_editor", copy_editor_node)
    builder.add_node("summarizer", summarizer_node)
    builder.add_node("wordcloud", wordcloud_node)

    # add the edges to the graph
    builder.add_edge(START, "copy_editor")
    builder.add_edge("copy_editor", "summarizer")
    builder.add_edge("copy_editor", "wordcloud")
    builder.add_edge("summarizer", END)
    builder.add_edge("wordcloud", END)  

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
