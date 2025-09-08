# =============================================================================
#  Filename: self_reviewer_mcp_tools.py
#
#  Short Description: Self-reviewer agent(s) for the periodic employee self-review process.
#
#  Creation date: 2025-09-01
#  Author: Chandar L
# =============================================================================

"""Self-Reviewer Agent Implementation.

This module implements an intelligent self-review processing system using LangGraph
for workflow orchestration and uses only MCP (Model Context Protocol) tools without any agents.

Architecture:
- Uses LangGraph StateGraph for workflow management
- Integrates with MCP servers for text processing tools
- Implements async/await pattern for concurrent processing
- Supports state persistence through checkpointing
"""

from __future__ import annotations

import asyncio
import json
import os
from typing import Annotated, Optional

from langchain_mcp_adapters.client import MultiServerMCPClient
from langgraph.graph import StateGraph, START, END
from langgraph.checkpoint.memory import InMemorySaver
from typing_extensions import TypedDict
from rich import print as rprint
from pydantic import Field, validate_call
from loguru import logger
from dotenv import load_dotenv
from metamorphosis.datamodel import AchievementsList, ReviewScorecard

from metamorphosis.exceptions import (
    raise_mcp_tool_error,
    raise_postcondition_error,
)

load_dotenv()


class GraphState(TypedDict):
    """State definition for the LangGraph workflow.

    This TypedDict defines the structure of the state that flows through the LangGraph,
    containing all the data needed at each step of the workflow.

    Attributes:
        original_text: The original self-review input text from the employee.
        copy_edited_text: The grammar and clarity improved version.
        summary: The abstractive summary of the key insights.
        word_cloud_path: Path to the generated word cloud image file.
    """

    original_text: str
    copy_edited_text: Optional[str]
    summary: Optional[str]
    word_cloud_path: Optional[str]
    achievements: Optional[AchievementsList]
    review_scorecard: Optional[ReviewScorecard]


# =============================================================================
# MCP CLIENT CONFIGURATION
# =============================================================================


def _get_mcp_client() -> MultiServerMCPClient:
    """Create MCP client with environment-based configuration.

    Returns:
        MultiServerMCPClient: Configured client instance.
    """
    host = os.getenv("MCP_SERVER_HOST", "localhost")
    port = os.getenv("MCP_SERVER_PORT", "3333")
    url = f"http://{host}:{port}/mcp"

    logger.debug("Configuring MCP client for URL: {}", url)

    return MultiServerMCPClient(
        {
            "text_modifier_mcp_server": {
                "url": url,
                "transport": "streamable_http",
            }
        }
    )


# Set up MCP client for tool integration
client = _get_mcp_client()

# Global variable to store available tools from MCP servers
tools = []


def _find_tool(tool_name: str):
    """Find a tool by name from the global tools list.

    Args:
        tool_name: Name of the tool to find.

    Returns:
        Tool: The requested tool instance.

    Raises:
        ValueError: If tool is not found.
    """
    tool = next((t for t in tools if t.name == tool_name), None)
    if not tool:
        raise_mcp_tool_error(
            "tool_name tool not found", tool_name="tool_name", operation="tool_lookup"
        )
    return tool


# =============================================================================
# INITIALIZATION FUNCTIONS
# =============================================================================


async def initialize_components() -> None:
    """Initialize MCP components and retrieve available tools.

    This function establishes the connection to MCP servers and retrieves
    the list of available tools that can be used in the workflow.

    Raises:
        ConnectionError: If unable to connect to MCP servers.
        Exception: If tool retrieval fails.
    """
    global tools

    tools = await client.get_tools()
    tool_names = [tool.name for tool in tools]

    # Postcondition (O(1)): ensure tools were retrieved
    if not tools or not isinstance(tools, list):
        raise_postcondition_error(
            "No tools retrieved from MCP server",
            context={"tools_count": len(tools) if tools else 0},
            operation="mcp_tool_initialization",
        )

    logger.info("Available MCP tools: {}", tool_names)


# =============================================================================
# WORKFLOW NODE FUNCTIONS
# =============================================================================


@validate_call
async def copy_editor_node(
    state: Annotated[dict, Field(description="Current workflow state")],
) -> dict:
    """Copy editor node for grammar and clarity improvements.

    This node processes the original self-review text to improve grammar,
    spelling, punctuation, and overall clarity.

    Args:
        state: Current workflow state containing original_text.

    Returns:
        dict: Updated state with copy_edited_text field populated.

    Raises:
        ValueError: If copy_edit tool is not available or postcondition fails.
        json.JSONDecodeError: If tool response is not valid JSON.
    """
    original_text = state["original_text"]
    logger.info("copy_editor_node: processing text (length={})", len(original_text))

    copy_edit_tool = _find_tool("copy_edit")
    result = await copy_edit_tool.ainvoke({"text": original_text})

    result_data = json.loads(result)
    copy_edited_text = result_data["copy_edited_text"]

    # Postcondition (O(1)): ensure valid output
    if not copy_edited_text or not isinstance(copy_edited_text, str):
        raise_postcondition_error(
            "Copy edit output validation failed",
            context={
                "has_text": bool(copy_edited_text),
                "text_type": type(copy_edited_text).__name__,
            },
            operation="copy_edit_validation",
        )

    return {"copy_edited_text": copy_edited_text}


@validate_call
async def summarizer_node(
    state: Annotated[dict, Field(description="Current workflow state")],
) -> dict:
    """Summarizer node for abstractive text summarization.

    This node creates a concise, abstractive summary of the copy-edited text,
    extracting key insights and main points.

    Args:
        state: Current workflow state containing copy_edited_text.

    Returns:
        dict: Updated state with summary field populated.

    Raises:
        ValueError: If abstractive_summarize tool is not available or postcondition fails.
        json.JSONDecodeError: If tool response is not valid JSON.
    """
    copy_edited_text = state["copy_edited_text"]
    logger.info("summarizer_node: processing text (length={})", len(copy_edited_text))

    summarizer_tool = _find_tool("abstractive_summarize")
    result = await summarizer_tool.ainvoke({"text": copy_edited_text})

    result_data = json.loads(result)
    summary = result_data["summarized_text"]

    # Postcondition (O(1)): ensure valid output
    if not summary or not isinstance(summary, str):
        raise_postcondition_error(
            "Summarizer output validation failed",
            context={"has_text": bool(summary), "text_type": type(summary).__name__},
            operation="summarizer_validation",
        )

    return {"summary": summary}

@validate_call
async def achievements_extractor_node(
    state: Annotated[dict, Field(description="Current workflow state")],
) -> dict:
    """Achievements extractor node for extracting key achievements from the text.

    This node extracts key achievements from the copy-edited text.

    Args:
        state: Current workflow state containing copy_edited_text.

    Returns:
        dict: Updated state with achievements field populated.

    Raises:
        ValueError: If extract_achievements tool is not available or postcondition fails.
        json.JSONDecodeError: If tool response is not valid JSON.
    """
    copy_edited_text = state["copy_edited_text"]
    logger.info("achievements_extractor_node: processing text (length={})", len(copy_edited_text))

    achievements_extractor_tool = _find_tool("extract_achievements")
    result = await achievements_extractor_tool.ainvoke({"text": copy_edited_text})

    result_data = json.loads(result)
    # Create AchievementsList object from result_data
    achievements = AchievementsList(**result_data)

    # Postcondition (O(1)): ensure valid output
    if not achievements or not isinstance(achievements, AchievementsList):
        raise_postcondition_error(
            "Achievements extractor output validation failed",
            context={"has_achievements": bool(achievements), "achievements_type": type(achievements).__name__},
            operation="achievements_extractor_validation",
        )

    return {"achievements": achievements}

@validate_call
async def review_text_evaluator_node(
    state: Annotated[dict, Field(description="Current workflow state")],
) -> dict:
    """Review text evaluator node for evaluating the copy-edited text.

    This node evaluates the review text.

    Args:
        state: Current workflow state containing copy_edited_text.

    Returns:
        dict: Updated state with review_scorecard field populated.

    Raises:
        ValueError: If evaluate_review_text tool is not available or postcondition fails.
        json.JSONDecodeError: If tool response is not valid JSON.
    """
    copy_edited_text = state["copy_edited_text"]
    logger.info("review_text_evaluator_node: processing text (length={})", len(copy_edited_text))

    review_text_evaluator_tool = _find_tool("evaluate_review_text")
    result = await review_text_evaluator_tool.ainvoke({"text": copy_edited_text})

    result_data = json.loads(result)
    # Create ReviewScorecard object from result_data
    review_scorecard = ReviewScorecard(**result_data)

    # Postcondition (O(1)): ensure valid output
    if not review_scorecard or not isinstance(review_scorecard, ReviewScorecard):
        raise_postcondition_error(
            "Review text evaluator output validation failed",
            context={"has_review_scorecard": bool(review_scorecard), "review_scorecard_type": type(review_scorecard).__name__},
            operation="review_text_evaluator_validation",
        )

    return {"review_scorecard": review_scorecard}

@validate_call
async def wordcloud_node(
    state: Annotated[dict, Field(description="Current workflow state")],
) -> dict:
    """Word cloud generation node for visual text analysis.

    This node generates a visual word cloud from the copy-edited text, creating
    a graphical representation where word frequency is shown through font size.

    Args:
        state: Current workflow state containing copy_edited_text.

    Returns:
        dict: Updated state with word_cloud_path field populated.

    Raises:
        ValueError: If word_cloud tool is not available or postcondition fails.
    """
    copy_edited_text = state["copy_edited_text"]
    logger.info("wordcloud_node: processing text (length={})", len(copy_edited_text))

    wordcloud_tool = _find_tool("word_cloud")
    result = await wordcloud_tool.ainvoke({"text": copy_edited_text})

    # The word_cloud tool returns a string path directly, not JSON
    wordcloud_path = result

    # Postcondition (O(1)): ensure valid path
    if not wordcloud_path or not isinstance(wordcloud_path, str):
        raise_postcondition_error(
            "Word cloud output validation failed",
            context={"has_path": bool(wordcloud_path), "path_type": type(wordcloud_path).__name__},
            operation="wordcloud_validation",
        )

    return {"word_cloud_path": wordcloud_path}


# =============================================================================
# GRAPH CONSTRUCTION AND WORKFLOW ORCHESTRATION
# =============================================================================


async def build_graph() -> StateGraph:
    """Build and configure the LangGraph workflow for self-review processing.

    This function constructs the complete workflow graph that orchestrates the
    self-review processing pipeline.

    Returns:
        StateGraph: Compiled graph ready for execution.

    Raises:
        Exception: If graph construction or compilation fails.
    """
    await initialize_components()

    builder = StateGraph(GraphState)

    # Add processing nodes to the graph
    builder.add_node("copy_editor", copy_editor_node)
    builder.add_node("summarizer", summarizer_node)
    builder.add_node("achievements_extractor", achievements_extractor_node)
    builder.add_node("review_text_evaluator", review_text_evaluator_node)
    builder.add_node("wordcloud", wordcloud_node)

    # Define the workflow edges (execution flow)
    builder.add_edge(START, "copy_editor")
    builder.add_edge("copy_editor", "summarizer")
    builder.add_edge("copy_editor", "achievements_extractor")
    builder.add_edge("copy_editor", "review_text_evaluator")
    builder.add_edge("copy_editor", "wordcloud")
    builder.add_edge("summarizer", END)
    builder.add_edge("achievements_extractor", END)
    builder.add_edge("review_text_evaluator", END)
    builder.add_edge("wordcloud", END)

    memory = InMemorySaver()
    graph = builder.compile(checkpointer=memory)

    # Generate visual representation for documentation
    try:
        graph.get_graph().draw_mermaid_png(output_file_path="self_reviewer_graph.png")
        logger.debug("Generated graph visualization: self_reviewer_graph.png")
    except Exception as e:
        logger.warning("Failed to generate graph visualization: {}", e)

    return graph


# =============================================================================
# EXECUTION FUNCTIONS
# =============================================================================


@validate_call
async def run_graph(
    graph,
    review_text: Annotated[str, Field(min_length=1)],
    thread_id: Annotated[str, Field(min_length=1)] = "main",
) -> dict | None:
    """Execute the LangGraph workflow for processing self-review text.

    This is the main execution function that runs the complete self-review
    processing pipeline.

    Args:
        graph: The compiled graph to execute (from build_graph()).
        review_text: The self-review text to process.
        thread_id: Unique identifier for state persistence.

    Returns:
        dict | None: Complete processed results or None if execution fails.
    """
    logger.info("Running graph (thread_id={}, text_length={})", thread_id, len(review_text))

    try:
        result = await graph.ainvoke(
            {"original_text": review_text}, config={"configurable": {"thread_id": thread_id}}
        )

        # Postcondition (O(1)): ensure valid result structure
        if not isinstance(result, dict) or "original_text" not in result:
            raise_postcondition_error(
                "Graph execution result validation failed",
                context={
                    "result_type": type(result).__name__,
                    "has_original_text": "original_text" in result
                    if isinstance(result, dict)
                    else False,
                },
                operation="graph_execution_validation",
            )

        logger.info("Graph execution completed successfully (thread_id={})", thread_id)
        return result

    except Exception as e:
        logger.error("Error running graph (thread_id={}): {}", thread_id, e)
        return None


async def test_graph() -> dict | None:
    """Test function to validate the graph workflow with sample data.

    Returns:
        dict | None: Complete processed results from the workflow or None if failed.
    """
    sample_text = (
        "I had an eventful cycle this summer. Learnt agentic workflows and "
        "implemented a self-reviewer agent for the periodic employee self-review "
        "process. It significantly improved employee productivity for the organization."
    )

    return await graph.ainvoke(
        {"original_text": sample_text}, config={"configurable": {"thread_id": "default"}}
    )


# =============================================================================
# MODULE INITIALIZATION
# =============================================================================

# Initialize the graph when the module is imported
graph = asyncio.run(build_graph())


# =============================================================================
# MAIN EXECUTION BLOCK
# =============================================================================

if __name__ == "__main__":
    """Main execution block for testing the self-reviewer workflow."""

    logger.info("Testing self-reviewer workflow")
    self_review_response = asyncio.run(test_graph())

    rprint("=== Self-Reviewer Response ===")
    rprint(self_review_response)
