# =============================================================================
#  Filename: graph_builder.py
#
#  Short Description: Graph construction and configuration for self-reviewer workflows.
#
#  Creation date: 2025-09-08
#  Author: Asif Qamar
# =============================================================================

"""Graph Construction and Configuration for Self-Reviewer Workflows.

This module provides the GraphBuilder class that handles the construction
and configuration of LangGraph workflows for the self-reviewer system.
"""

from __future__ import annotations

from langgraph.graph import StateGraph, START, END
from langgraph.checkpoint.memory import InMemorySaver
from loguru import logger
from pydantic import validate_call
from icontract import ensure

from metamorphosis.agents.self_reviewer.state import GraphState
from metamorphosis.agents.self_reviewer.nodes import WorkflowNodes


class GraphBuilder:
    """Builds and configures the LangGraph workflow.

    This class is responsible for constructing the complete workflow graph
    that orchestrates the self-review processing pipeline. It handles node
    registration, edge configuration, and graph compilation.

    Attributes:
        nodes: The workflow nodes instance containing all node implementations.
    """

    def __init__(self, nodes: WorkflowNodes) -> None:
        """Initialize the graph builder.

        Args:
            nodes: Initialized workflow nodes instance.
        """
        self.nodes = nodes

    @validate_call
    @ensure(lambda result: result is not None, "Graph must be built successfully")
    async def build(self) -> StateGraph:
        """Build and configure the LangGraph workflow for self-review processing.

        This method constructs the complete workflow graph that orchestrates the
        self-review processing pipeline. It initializes components, adds nodes,
        defines edges, and compiles the graph with memory support.

        Returns:
            StateGraph: Compiled graph ready for execution.

        Raises:
            Exception: If graph construction or compilation fails.
        """
        logger.debug("Building LangGraph workflow")

        builder = StateGraph(GraphState)

        # Add all processing nodes to the graph
        self._add_nodes(builder)

        # Define the workflow edges (execution flow)
        self._add_edges(builder)

        # Add conditional edges for decision points
        self._add_conditional_edges(builder)

        # Compile the graph with memory support
        memory = InMemorySaver()
        graph = builder.compile(checkpointer=memory)

        # Generate visual representation for documentation
        self._generate_graph_visualization(graph)

        logger.debug("LangGraph workflow built successfully")
        return graph

    # -----------------------------------------------------------------------------

    def _add_nodes(self, builder: StateGraph) -> None:
        """Add all processing nodes to the graph.

        Args:
            builder: The StateGraph builder instance.
        """
        # Core processing nodes
        builder.add_node("copy_editor", self.nodes.copy_editor_node)
        builder.add_node("summarizer", self.nodes.summarizer_node)
        builder.add_node("wordcloud", self.nodes.wordcloud_node)

        # Agent-based nodes
        builder.add_node("achievements_extractor", self.nodes.achievements_extractor_node)
        builder.add_node("review_text_evaluator", self.nodes.review_text_evaluator_node)

        # Post-processing nodes
        builder.add_node("after_achievements_parser", self.nodes.after_achievements_parser)
        builder.add_node("after_evaluation_parser", self.nodes.after_evaluation_parser)

        # Tool nodes
        builder.add_node(
            "achievements_extractor_tool_node", self.nodes.achievements_extractor_tool_node
        )
        builder.add_node(
            "review_text_evaluator_tool_node", self.nodes.review_text_evaluator_tool_node
        )

    # -----------------------------------------------------------------------------

    def _add_edges(self, builder: StateGraph) -> None:
        """Add basic edges to the graph.

        Args:
            builder: The StateGraph builder instance.
        """
        # Main processing flow
        builder.add_edge(START, "copy_editor")
        builder.add_edge("copy_editor", "summarizer")
        builder.add_edge("copy_editor", "wordcloud")
        builder.add_edge("summarizer", END)
        builder.add_edge("wordcloud", END)

        # Achievement extraction flow
        builder.add_edge("copy_editor", "achievements_extractor")
        builder.add_edge("achievements_extractor_tool_node", "after_achievements_parser")

        # Review evaluation flow
        builder.add_edge("review_text_evaluator_tool_node", "after_evaluation_parser")
        builder.add_edge("after_evaluation_parser", END)

    # -----------------------------------------------------------------------------

    def _add_conditional_edges(self, builder: StateGraph) -> None:
        """Add conditional edges for decision points.

        Args:
            builder: The StateGraph builder instance.
        """
        # Achievement extraction decision point
        builder.add_conditional_edges(
            "achievements_extractor",
            self.nodes.should_call_achievements_extractor_tools,
            {
                "tools": "achievements_extractor_tool_node",
                "no_tools": END,
            },
        )

        # Review continuation decision point
        builder.add_conditional_edges(
            "after_achievements_parser",
            self.nodes.should_continue_review,
            {
                "continue": "review_text_evaluator",
                "no_continue": END,
            },
        )

        # Review evaluation decision point
        builder.add_conditional_edges(
            "review_text_evaluator",
            self.nodes.should_call_review_text_evaluator_tools,
            {
                "tools": "review_text_evaluator_tool_node",
                "no_tools": END,
            },
        )

    # -----------------------------------------------------------------------------

    def _generate_graph_visualization(self, graph: StateGraph) -> None:
        """Generate visual representation for documentation.

        Args:
            graph: The compiled graph to visualize.
        """
        try:
            graph.get_graph().draw_mermaid_png(output_file_path="self_reviewer_agents.png")
            logger.debug("Generated graph visualization: self_reviewer_agents.png")
        except Exception as e:
            logger.warning("Failed to generate graph visualization: {}", e)
