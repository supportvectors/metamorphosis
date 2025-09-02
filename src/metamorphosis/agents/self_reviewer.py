# =============================================================================
#  Filename: self_reviewer.py
#
#  Short Description: Self-reviewer agent(s) for the periodic employee self-review process.
#
#  Creation date: 2025-09-01
#  Author: Chandar L
# =============================================================================

"""
Self-Reviewer Agent Implementation

This module implements an intelligent self-review processing system using LangGraph
for workflow orchestration and MCP (Model Context Protocol) for tool integration.

The system processes employee self-review text through three main stages:
1. Copy editing for grammar and clarity improvements
2. Abstractive summarization for key insights extraction
3. Word cloud generation for visual representation of key themes

Architecture:
- Uses LangGraph StateGraph for workflow management
- Integrates with MCP servers for text processing tools
- Implements async/await pattern for concurrent processing
- Supports state persistence through checkpointing
"""

# Core dependencies for workflow orchestration and async processing
from langchain_mcp_adapters.client import MultiServerMCPClient  # MCP client for tool integration
from langgraph.graph import StateGraph, START, END  # Graph workflow framework
from typing_extensions import TypedDict  # Type hints for state structure
from typing import Optional  # Optional type annotations
from langgraph.checkpoint.memory import InMemorySaver  # State persistence
import asyncio  # Async/await support
import json  # JSON parsing for tool responses
from rich import print as rprint  # Enhanced console output

class GraphState(TypedDict):
    """
    State definition for the LangGraph workflow.
    
    This TypedDict defines the structure of the state that flows through the LangGraph,
    containing all the data needed at each step of the workflow. The state acts as a
    shared data container that gets passed between nodes and updated as the workflow
    progresses through each processing stage.
    
    The state follows a pipeline pattern where:
    - original_text is the input to the entire workflow
    - copy_edited_text is produced by the copy_editor_node
    - summary is produced by the summarizer_node (using copy_edited_text)
    - word_cloud_path is produced by the wordcloud_node (using copy_edited_text)
    
    Attributes:
        original_text (str): The original self-review input text from the employee
        copy_edited_text (Optional[str]): The grammar and clarity improved version
        summary (Optional[str]): The abstractive summary of the key insights
        word_cloud_path (Optional[str]): Path to the generated word cloud image file
    """
    original_text: str
    copy_edited_text: Optional[str]
    summary: Optional[str]
    word_cloud_path: Optional[str]

# =============================================================================
# MCP CLIENT CONFIGURATION
# =============================================================================

# Set up MCP (Model Context Protocol) client for tool integration
# This client connects to external MCP servers that provide text processing tools
client = MultiServerMCPClient(
    {
        "text_modifier_mcp_server": {
            # Connection to the text processing MCP server
            # Note: Ensure the text_modifier_mcp_server is running on port 3333
            "url": "http://localhost:3333/mcp",
            "transport": "streamable_http",  # HTTP-based streaming transport
        }
    }
)

# Global variable to store available tools from MCP servers
# This gets populated during initialization and used throughout the workflow
tools = []

# =============================================================================
# INITIALIZATION FUNCTIONS
# =============================================================================

async def initialize_components():
    """
    Initialize MCP components and retrieve available tools.
    
    This function establishes the connection to MCP servers and retrieves
    the list of available tools that can be used in the workflow. It must
    be called before any workflow execution to ensure tools are available.
    
    The function updates the global 'tools' variable with the retrieved tools
    and logs them for debugging purposes.
    
    Raises:
        ConnectionError: If unable to connect to MCP servers
        Exception: If tool retrieval fails
    """
    global tools
    
    # Retrieve all available tools from connected MCP servers
    tools = await client.get_tools()  
    
    # Log available tools for debugging and verification
    print(f"🔧 Available tools: {[tool.name for tool in tools]}")

# =============================================================================
# WORKFLOW NODE FUNCTIONS
# =============================================================================

async def copy_editor_node(state: GraphState) -> GraphState:
    """
    Copy editor node for grammar and clarity improvements.
    
    This node processes the original self-review text to improve grammar,
    spelling, punctuation, and overall clarity. It uses the MCP copy_edit
    tool to perform the text enhancement.
    
    The node is the first processing step in the workflow and its output
    is used by both the summarizer and wordcloud nodes.
    
    Args:
        state (GraphState): Current workflow state containing original_text
        
    Returns:
        GraphState: Updated state with copy_edited_text field populated
        
    Raises:
        ValueError: If copy_edit tool is not available
        json.JSONDecodeError: If tool response is not valid JSON
        Exception: If tool execution fails
    """
    # Extract the original text from the current state
    original_text = state["original_text"]
    
    # Find the copy_edit tool from the available tools list
    # Uses generator expression for efficient search
    copy_edit_tool = next((tool for tool in tools if tool.name == "copy_edit"), None)
    if not copy_edit_tool:
        raise ValueError("copy_edit tool not found - ensure MCP server is running")
    
    # Call the copy_edit tool asynchronously with the original text
    # The tool expects a dictionary with 'text' key
    result = await copy_edit_tool.ainvoke({"text": original_text})
    
    # Parse the JSON response from the tool
    # The tool returns a JSON string that needs to be parsed
    result_data = json.loads(result)
    copy_edited_text = result_data["copy_edited_text"]
    
    # Return updated state with the copy-edited text
    return {"copy_edited_text": copy_edited_text}

async def summarizer_node(state: GraphState) -> GraphState:
    """
    Summarizer node for abstractive text summarization.
    
    This node creates a concise, abstractive summary of the copy-edited text,
    extracting key insights and main points. It uses the MCP abstractive_summarize
    tool to generate a high-level overview of the self-review content.
    
    The node processes the copy_edited_text (not the original) to ensure
    the summary is based on the improved version of the text.
    
    Args:
        state (GraphState): Current workflow state containing copy_edited_text
        
    Returns:
        GraphState: Updated state with summary field populated
        
    Raises:
        ValueError: If abstractive_summarize tool is not available
        json.JSONDecodeError: If tool response is not valid JSON
        Exception: If tool execution fails
    """
    # Find the abstractive_summarize tool from the available tools list
    # Uses generator expression for efficient search
    summarizer_tool = next((tool for tool in tools if tool.name == "abstractive_summarize"), None)
    if not summarizer_tool:
        raise ValueError("abstractive_summarize tool not found - ensure MCP server is running")
    
    # Call the summarizer tool asynchronously with the copy-edited text
    # Uses copy_edited_text to ensure summary is based on improved version
    result = await summarizer_tool.ainvoke({"text": state["copy_edited_text"]})
    
    # Parse the JSON response from the tool
    # The tool returns a JSON string containing the summarized text
    result_data = json.loads(result)
    summary = result_data["summarized_text"]
    
    # Return updated state with the generated summary
    return {"summary": summary}

async def wordcloud_node(state: GraphState) -> GraphState:
    """
    Word cloud generation node for visual text analysis.
    
    This node generates a visual word cloud from the copy-edited text, creating
    a graphical representation where word frequency is shown through font size.
    This provides a quick visual overview of the most important themes and
    concepts in the self-review.
    
    The node processes the copy_edited_text to ensure the word cloud is based
    on the improved version of the text. The tool returns a file path to the
    generated image rather than JSON data.
    
    Args:
        state (GraphState): Current workflow state containing copy_edited_text
        
    Returns:
        GraphState: Updated state with word_cloud_path field populated
        
    Raises:
        ValueError: If word_cloud tool is not available
        Exception: If tool execution fails or image generation fails
    """
    # Find the word_cloud tool from the available tools list
    # Uses generator expression for efficient search
    wordcloud_tool = next((tool for tool in tools if tool.name == "word_cloud"), None)
    if not wordcloud_tool:
        raise ValueError("word_cloud tool not found - ensure MCP server is running")
    
    # Call the word cloud tool asynchronously with the copy-edited text
    # Uses copy_edited_text to ensure word cloud is based on improved version
    result = await wordcloud_tool.ainvoke({"text": state["copy_edited_text"]})
    
    # The word_cloud tool returns a string path directly, not JSON
    # This is different from other tools that return JSON responses
    wordcloud_path = result
    
    # Return updated state with the path to the generated word cloud image
    return {"word_cloud_path": wordcloud_path}

# =============================================================================
# GRAPH CONSTRUCTION AND WORKFLOW ORCHESTRATION
# =============================================================================

async def build_graph():
    """
    Build and configure the LangGraph workflow for self-review processing.
    
    This function constructs the complete workflow graph that orchestrates the
    self-review processing pipeline. The graph defines the execution flow and
    dependencies between different processing nodes.
    
    Workflow Structure:
    1. START -> copy_editor (initial text processing)
    2. copy_editor -> summarizer (parallel processing)
    3. copy_editor -> wordcloud (parallel processing)
    4. summarizer -> END (completion)
    5. wordcloud -> END (completion)
    
    The graph uses checkpointing for state persistence and generates a visual
    representation for documentation purposes.
    
    Returns:
        StateGraph: Compiled graph ready for execution
        
    Raises:
        Exception: If graph construction or compilation fails
    """
    # Initialize MCP components and retrieve available tools
    # This must be done before building the graph to ensure tools are available
    await initialize_components()
    
    # Create a new StateGraph builder with our defined state structure
    builder = StateGraph(GraphState)

    # Add processing nodes to the graph
    # Each node represents a specific processing step in the workflow
    builder.add_node("copy_editor", copy_editor_node)  # Grammar and clarity improvements
    builder.add_node("summarizer", summarizer_node)    # Abstractive summarization
    builder.add_node("wordcloud", wordcloud_node)      # Visual word cloud generation

    # Define the workflow edges (execution flow)
    # The graph follows a fork-join pattern where copy_editor feeds into both
    # summarizer and wordcloud nodes, which then complete independently
    builder.add_edge(START, "copy_editor")           # Start with copy editing
    builder.add_edge("copy_editor", "summarizer")    # Copy editor feeds summarizer
    builder.add_edge("copy_editor", "wordcloud")     # Copy editor feeds wordcloud (parallel)
    builder.add_edge("summarizer", END)              # Summarizer completes workflow
    builder.add_edge("wordcloud", END)               # Wordcloud completes workflow

    # Configure state persistence using in-memory checkpointing
    # This allows the graph to maintain state across multiple executions
    # and supports features like resumability and state inspection
    memory = InMemorySaver()
    
    # Compile the graph with the checkpointing system
    # This creates the executable graph with all configurations applied
    graph = builder.compile(checkpointer=memory)
    
    # Generate visual representation of the graph for documentation
    # Creates a Mermaid diagram showing the workflow structure
    graph.get_graph().draw_mermaid_png(output_file_path="self_reviewer_graph.png")
    
    return graph

# =============================================================================
# TESTING AND EXECUTION FUNCTIONS
# =============================================================================

async def test_graph():
    """
    Test function to validate the graph workflow with sample data.
    
    This function provides a simple way to test the complete workflow
    with a predefined self-review text. It demonstrates the expected
    input format and execution pattern.
    
    The test uses a sample self-review text that covers typical content
    found in employee self-reviews, including achievements and impact.
    
    Returns:
        GraphState: Complete processed results from the workflow
        
    Note:
        This function assumes the global 'graph' variable is available
        and properly initialized. It should be called after build_graph().
    """
    # Test the graph with a sample self-review text
    # This demonstrates the expected input format and workflow execution
    self_review_response = await graph.ainvoke(
        {
            "original_text": 
            '''I had an eventful cycle this summer.  Learnt agentic workflows and implemented a self-reviewer agent
            for the periodic employee self-review process.  It significantly improved employee productivity for the organization.''',            
        },
        config={"configurable": {"thread_id": "default"}}  # Use default thread for testing
    )
    return self_review_response

async def run_graph(graph: StateGraph, review_text: str, thread_id: str = "main"):
    """
    Execute the LangGraph workflow for processing self-review text.
    
    This is the main execution function that runs the complete self-review
    processing pipeline. It takes a review text input and processes it through
    all workflow stages: copy editing, summarization, and word cloud generation.
    
    The function supports state persistence through thread_id, allowing for
    resumable executions and state inspection across multiple runs.
    
    Args:
        graph (StateGraph): The compiled graph to execute (from build_graph())
        review_text (str): The self-review text to process
        thread_id (str): Unique identifier for state persistence (default: "main")
        
    Returns:
        GraphState: Complete processed results containing:
            - original_text: The input text
            - copy_edited_text: Grammar and clarity improved version
            - summary: Abstractive summary of key insights
            - word_cloud_path: Path to generated word cloud image
        None: If execution fails due to errors
        
    Raises:
        Exception: Various exceptions can occur during tool execution or graph processing
    """
    try:
        # Execute the graph asynchronously with the provided review text
        # The thread_id enables state persistence and allows for resumable executions
        result: GraphState = await graph.ainvoke(
            {
                "original_text": review_text,            
            },
            config={"configurable": {"thread_id": thread_id}}
        )
        return result
        
    except Exception as e:
        # Log the error and return None to indicate failure
        # This allows calling code to handle errors gracefully
        print(f"Error running graph: {e}")
        return None

# =============================================================================
# MODULE INITIALIZATION AND MAIN EXECUTION
# =============================================================================

# Initialize the graph when the module is imported
# This creates the workflow graph and makes it available for use
graph = asyncio.run(build_graph())

# Main execution block for testing and demonstration
if __name__ == "__main__":
    """
    Main execution block for testing the self-reviewer workflow.
    
    This block runs when the script is executed directly (not imported).
    It demonstrates the complete workflow by processing a sample self-review
    text and displaying the results in a formatted manner.
    
    The execution flow:
    1. Build and initialize the graph
    2. Run the test with sample data
    3. Display the results using rich formatting
    """
    # Execute the test workflow with sample data
    self_review_response = asyncio.run(test_graph())
    
    # Display the results with enhanced formatting
    rprint("=== Self-Reviewer Response ===")
    rprint(self_review_response)
