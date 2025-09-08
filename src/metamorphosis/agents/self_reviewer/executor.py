# =============================================================================
#  Filename: executor.py
#
#  Short Description: Main workflow executor for self-reviewer system.
#
#  Creation date: 2025-09-08
#  Author: Asif Qamar
# =============================================================================

"""Main Workflow Executor for Self-Reviewer System.

This module provides the WorkflowExecutor class, which serves as the main
high-level interface for executing self-review workflows. It orchestrates
all the components and provides a clean API for external usage.
"""

from __future__ import annotations

from typing import Optional

from loguru import logger
from pydantic import validate_call, Field
from typing import Annotated
from icontract import require

from metamorphosis.agents.self_reviewer.client import MCPClientManager
from metamorphosis.agents.self_reviewer.nodes import WorkflowNodes
from metamorphosis.agents.self_reviewer.graph_builder import GraphBuilder
from metamorphosis.utilities import read_text_file, get_project_root
from metamorphosis.exceptions import raise_postcondition_error


class WorkflowExecutor:
    """High-level interface for executing review workflows.

    This class provides a simple, clean interface for running self-review
    workflows. It handles all the complexity of component initialization,
    graph construction, and execution orchestration.

    Attributes:
        config: Optional configuration dictionary.
        mcp_client: The MCP client manager instance.
        nodes: The workflow nodes instance.
        graph_builder: The graph builder instance.
        graph: The compiled workflow graph.
    """

    def __init__(self, config: Optional[dict] = None) -> None:
        """Initialize the workflow executor.

        Args:
            config: Optional configuration dictionary for customizing behavior.
        """
        self.config = config or {}
        self.mcp_client: Optional[MCPClientManager] = None
        self.nodes: Optional[WorkflowNodes] = None
        self.graph_builder: Optional[GraphBuilder] = None
        self.graph = None
        self._initialized = False

    @validate_call
    async def initialize(self) -> None:
        """Initialize all components and build the workflow graph.

        This method sets up all the necessary components including the MCP client,
        workflow nodes, graph builder, and compiles the final workflow graph.

        Raises:
            Exception: If initialization fails at any step.
        """
        if self._initialized:
            return

        logger.info("Initializing WorkflowExecutor")

        # Initialize MCP client
        self.mcp_client = MCPClientManager(self.config)
        await self.mcp_client.initialize()

        # Initialize workflow nodes
        self.nodes = WorkflowNodes(self.mcp_client)

        # Initialize graph builder
        self.graph_builder = GraphBuilder(self.nodes)

        # Build the workflow graph
        self.graph = await self.graph_builder.build()

        self._initialized = True
        logger.info("WorkflowExecutor initialized successfully")

    @validate_call
    @require(lambda self: self.graph is not None, "Graph must not be None")
    @require(lambda review_text: len(review_text.strip()) > 0, "Review text must not be empty")
    @require(lambda thread_id: len(thread_id.strip()) > 0, "Thread ID must not be empty")
    async def run_workflow(
        self,
        review_text: Annotated[str, Field(min_length=1)],
        thread_id: Annotated[str, Field(min_length=1)] = "main",
    ) -> dict | None:
        """Execute the LangGraph workflow for processing self-review text.

        This is the main execution method that runs the complete self-review
        processing pipeline.

        Args:
            review_text: The self-review text to process.
            thread_id: Unique identifier for state persistence.

        Returns:
            dict | None: Complete processed results or None if execution fails.

        Raises:
            RuntimeError: If executor is not initialized.
        """
        if not self._initialized:
            raise RuntimeError("WorkflowExecutor not initialized. Call initialize() first.")

        logger.info("Running workflow (thread_id={}, text_length={})", thread_id, len(review_text))

        try:
            result = await self.graph.ainvoke(
                {"original_text": review_text}, config={"configurable": {"thread_id": thread_id}}
            )

            self._validate_graph_result(result)
            logger.info("Workflow execution completed successfully (thread_id={})", thread_id)
            return result

        except Exception as e:
            logger.error("Error running workflow (thread_id={}): {}", thread_id, e)
            return None

    # -----------------------------------------------------------------------------

    def _validate_graph_result(self, result: dict) -> None:
        """Validate graph execution result structure.

        Args:
            result: The result to validate.

        Raises:
            ValueError: If result structure is invalid.
        """
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

    # -----------------------------------------------------------------------------

    @validate_call
    async def test_workflow(self) -> dict | None:
        """Test function to validate the workflow with sample data.

        This method loads a sample review from the data_engineer_review.md file
        and processes it through the complete workflow to validate functionality.

        Returns:
            dict | None: Complete processed results from the workflow or None if failed.

        Raises:
            RuntimeError: If executor is not initialized.
        """
        if not self._initialized:
            raise RuntimeError("WorkflowExecutor not initialized. Call initialize() first.")

        logger.info("Running workflow test with sample data")

        project_root = get_project_root()
        review_path = project_root / "sample_reviews" / "data_engineer_review.md"
        sample_text = read_text_file(review_path)

        return await self.run_workflow(sample_text, thread_id="test")

    # -----------------------------------------------------------------------------

    def get_graph_visualization(self) -> str:
        """Get the path to the generated graph visualization.

        Returns:
            str: Path to the graph visualization PNG file.

        Raises:
            RuntimeError: If executor is not initialized.
        """
        if not self._initialized:
            raise RuntimeError("WorkflowExecutor not initialized. Call initialize() first.")

        return "self_reviewer_agents.png"

    # -----------------------------------------------------------------------------

    def list_available_tools(self) -> list[str]:
        """Get list of available MCP tools.

        Returns:
            list[str]: Names of all available MCP tools.

        Raises:
            RuntimeError: If executor is not initialized.
        """
        if not self._initialized:
            raise RuntimeError("WorkflowExecutor not initialized. Call initialize() first.")

        return self.mcp_client.list_available_tools()

    # -----------------------------------------------------------------------------

    async def close(self) -> None:
        """Clean up resources and close connections.

        This method should be called when the executor is no longer needed
        to properly clean up resources.
        """
        if self.mcp_client:
            await self.mcp_client.close()

        self._initialized = False
        logger.debug("WorkflowExecutor closed")

    # -----------------------------------------------------------------------------

    @property
    def is_initialized(self) -> bool:
        """Check if the executor is initialized.

        Returns:
            bool: True if initialized, False otherwise.
        """
        return self._initialized
