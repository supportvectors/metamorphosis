# =============================================================================
#  Filename: self_reviewer_agents.py
#
#  Short Description: Backward compatibility layer for refactored self-reviewer system.
#
#  Creation date: 2025-09-08
#  Author: Asif Qamar
# =============================================================================

"""Backward Compatibility Layer for Self-Reviewer Agents.

This module provides backward compatibility for existing imports while
using the new object-oriented architecture under the hood.

MIGRATION GUIDE:
Old: from metamorphosis.agents.self_reviewer_agents import graph, run_graph
New: from metamorphosis.agents.self_reviewer import WorkflowExecutor

The original 821-line monolithic file has been refactored into:
- MCPClientManager: Handles MCP connections and tools
- WorkflowNodes: Contains all node implementations  
- GraphBuilder: Constructs the LangGraph workflow
- WorkflowExecutor: Main interface for workflow execution
- GraphState: State management utilities
"""

from __future__ import annotations

import asyncio
from metamorphosis.agents.self_reviewer import WorkflowExecutor

# Initialize the executor for backward compatibility
executor = WorkflowExecutor()

# Backward compatibility - initialize synchronously
try:
    graph = asyncio.run(executor.initialize())
    graph = executor.graph
except Exception:
    # If async initialization fails in module scope, defer to first usage
    graph = None


async def run_graph(graph_instance, review_text: str, thread_id: str = "main") -> dict | None:
    """Legacy function for running the workflow.
    
    Args:
        graph_instance: Ignored (maintained for compatibility).
        review_text: The review text to process.
        thread_id: Thread identifier for state persistence.
        
    Returns:
        The workflow execution result.
    """
    # Ensure executor is initialized
    if not executor.is_initialized:
        await executor.initialize()
    
    return await executor.run_workflow(review_text, thread_id)


async def build_graph():
    """Legacy function for building the graph.
    
    Returns:
        The compiled graph from the executor.
    """
    if not executor.is_initialized:
        await executor.initialize()
    
    return executor.graph


async def test_graph() -> dict | None:
    """Legacy function for testing the workflow.
    
    Returns:
        The test workflow result.
    """
    if not executor.is_initialized:
        await executor.initialize()
    
    return await executor.test_workflow()


# Re-export the state class for compatibility
from metamorphosis.agents.self_reviewer.state import GraphState

# Export the main interface for new code
__all__ = ["WorkflowExecutor", "graph", "run_graph", "build_graph", "test_graph", "GraphState"]