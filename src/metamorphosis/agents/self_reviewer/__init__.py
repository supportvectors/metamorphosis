# =============================================================================
#  Filename: __init__.py
#
#  Short Description: Self-reviewer module initialization and public API.
#
#  Creation date: 2025-09-08
#  Author: Asif Qamar
# =============================================================================

"""Self-Reviewer Module for Employee Review Processing.

This module provides an object-oriented interface for processing employee
self-reviews using LangGraph workflows and MCP tools.

Main Classes:
    WorkflowExecutor: High-level interface for executing review workflows
    MCPClientManager: Manages MCP client connections and tools
    WorkflowNodes: Contains all workflow node implementations
    GraphBuilder: Constructs and configures LangGraph workflows

Example:
    >>> from metamorphosis.agents.self_reviewer import WorkflowExecutor
    >>> executor = WorkflowExecutor()
    >>> await executor.initialize()
    >>> result = await executor.run_workflow("My self-review text...")
"""

from __future__ import annotations

from metamorphosis.agents.self_reviewer.executor import WorkflowExecutor

# Public API
__all__ = [
    "WorkflowExecutor",
]
