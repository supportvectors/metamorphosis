# =============================================================================
#  Filename: exceptions.py
#
#  Short Description: Custom exception hierarchy for the metamorphosis project.
#
#  Creation date: 2025-01-15
#  Author: Asif Qamar
# =============================================================================

"""Custom exception hierarchy for metamorphosis project.

This module defines a comprehensive exception hierarchy that provides contextual
error information across all components of the metamorphosis system. All exceptions
inherit from ReviewError base class for consistent error handling.

Exception Hierarchy:
- ReviewError (base)
  ├── ConfigurationError (configuration/environment issues)
  ├── ValidationError (input validation failures)
  ├── ProcessingError (text processing failures)
  │   ├── LLMProcessingError (LLM-specific failures)
  │   ├── PromptError (prompt template issues)
  │   └── PostconditionError (output validation failures)
  ├── MCPError (MCP protocol/tool issues)
  │   ├── MCPConnectionError (connection failures)
  │   ├── MCPToolError (tool execution failures)
  │   └── MCPServerError (server-side issues)
  ├── WorkflowError (LangGraph workflow issues)
  │   ├── GraphBuildError (graph construction failures)
  │   ├── NodeExecutionError (node processing failures)
  │   └── StateError (state management issues)
  └── FileOperationError (file system operations)
"""

from __future__ import annotations

from typing import Any, Optional


class ReviewError(Exception):
    """Base exception for all metamorphosis review processing errors.
    
    This is the root exception class that all other custom exceptions inherit from.
    It provides structured error information with context, operation details, and
    optional error codes for programmatic handling.
    
    Attributes:
        message: Human-readable error description.
        context: Optional dictionary with additional error context.
        operation: Optional string describing what operation failed.
        error_code: Optional string for programmatic error handling.
        original_error: Optional reference to the underlying exception.
    """
    
    def __init__(
        self,
        message: str,
        *,
        context: Optional[dict[str, Any]] = None,
        operation: Optional[str] = None,
        error_code: Optional[str] = None,
        original_error: Optional[Exception] = None,
    ) -> None:
        """Initialize ReviewError with contextual information.
        
        Args:
            message: Human-readable error description.
            context: Additional error context (e.g., {"text_length": 1500, "thread_id": "abc"}).
            operation: Description of the operation that failed (e.g., "copy_editing").
            error_code: Machine-readable error code (e.g., "INVALID_INPUT").
            original_error: The underlying exception that caused this error.
        """
        super().__init__(message)
        self.message = message
        self.context = context or {}
        self.operation = operation
        self.error_code = error_code
        self.original_error = original_error
    
    def __str__(self) -> str:
        """Return formatted error message with context."""
        parts = [self.message]
        
        if self.operation:
            parts.append(f"Operation: {self.operation}")
        
        if self.error_code:
            parts.append(f"Code: {self.error_code}")
        
        if self.context:
            context_str = ", ".join(f"{k}={v}" for k, v in self.context.items())
            parts.append(f"Context: {context_str}")
        
        if self.original_error:
            parts.append(f"Caused by: {type(self.original_error).__name__}: {self.original_error}")
        
        return " | ".join(parts)


# =============================================================================
# CONFIGURATION AND ENVIRONMENT ERRORS
# =============================================================================

class ConfigurationError(ReviewError):
    """Raised when configuration or environment setup fails.
    
    This exception is used for missing environment variables, invalid configuration
    values, or setup issues that prevent the system from initializing properly.
    """
    
    def __init__(
        self,
        message: str,
        *,
        missing_vars: Optional[list[str]] = None,
        invalid_vars: Optional[dict[str, str]] = None,
        **kwargs
    ) -> None:
        """Initialize ConfigurationError with environment context.
        
        Args:
            message: Error description.
            missing_vars: List of missing environment variables.
            invalid_vars: Dictionary of invalid variable names and their values.
            **kwargs: Additional ReviewError arguments.
        """
        context = kwargs.get("context", {})
        if missing_vars:
            context["missing_variables"] = missing_vars
        if invalid_vars:
            context["invalid_variables"] = invalid_vars
        
        super().__init__(message, context=context, **kwargs)


# =============================================================================
# INPUT VALIDATION ERRORS
# =============================================================================

class ValidationError(ReviewError):
    """Raised when input validation fails.
    
    This exception is used for invalid input parameters, malformed data,
    or constraint violations in user-provided data.
    """
    
    def __init__(
        self,
        message: str,
        *,
        field_name: Optional[str] = None,
        field_value: Optional[Any] = None,
        constraint: Optional[str] = None,
        **kwargs
    ) -> None:
        """Initialize ValidationError with field context.
        
        Args:
            message: Error description.
            field_name: Name of the field that failed validation.
            field_value: The invalid value that caused the error.
            constraint: Description of the validation constraint that was violated.
            **kwargs: Additional ReviewError arguments.
        """
        context = kwargs.get("context", {})
        if field_name:
            context["field"] = field_name
        if field_value is not None:
            context["value"] = str(field_value)
        if constraint:
            context["constraint"] = constraint
        
        super().__init__(message, context=context, **kwargs)


class PostconditionError(ReviewError):
    """Raised when postcondition validation fails.
    
    This exception is used when a function's output doesn't meet its
    expected postconditions, indicating a logic error or unexpected result.
    """
    
    def __init__(
        self,
        message: str,
        *,
        expected: Optional[str] = None,
        actual: Optional[str] = None,
        **kwargs
    ) -> None:
        """Initialize PostconditionError with expectation context.
        
        Args:
            message: Error description.
            expected: Description of what was expected.
            actual: Description of what was actually received.
            **kwargs: Additional ReviewError arguments.
        """
        context = kwargs.get("context", {})
        if expected:
            context["expected"] = expected
        if actual:
            context["actual"] = actual
        
        super().__init__(message, context=context, **kwargs)


# =============================================================================
# TEXT PROCESSING ERRORS
# =============================================================================

class ProcessingError(ReviewError):
    """Base class for text processing errors.
    
    This exception is used as a base for all text processing related errors
    including LLM failures, prompt issues, and processing pipeline errors.
    """
    pass


class LLMProcessingError(ProcessingError):
    """Raised when LLM processing fails.
    
    This exception is used for LLM-specific errors such as API failures,
    token limits, model unavailability, or unexpected LLM responses.
    """
    
    def __init__(
        self,
        message: str,
        *,
        model_name: Optional[str] = None,
        prompt_length: Optional[int] = None,
        response_length: Optional[int] = None,
        **kwargs
    ) -> None:
        """Initialize LLMProcessingError with LLM context.
        
        Args:
            message: Error description.
            model_name: Name of the LLM model that failed.
            prompt_length: Length of the prompt that was sent.
            response_length: Length of the response received (if any).
            **kwargs: Additional ReviewError arguments.
        """
        context = kwargs.get("context", {})
        if model_name:
            context["model"] = model_name
        if prompt_length is not None:
            context["prompt_length"] = prompt_length
        if response_length is not None:
            context["response_length"] = response_length
        
        super().__init__(message, context=context, **kwargs)


class PromptError(ProcessingError):
    """Raised when prompt template operations fail.
    
    This exception is used for prompt template loading, parsing, or
    formatting errors.
    """
    
    def __init__(
        self,
        message: str,
        *,
        prompt_file: Optional[str] = None,
        template_vars: Optional[dict[str, Any]] = None,
        **kwargs
    ) -> None:
        """Initialize PromptError with prompt context.
        
        Args:
            message: Error description.
            prompt_file: Path to the prompt file that caused the error.
            template_vars: Variables that were being substituted in the template.
            **kwargs: Additional ReviewError arguments.
        """
        context = kwargs.get("context", {})
        if prompt_file:
            context["prompt_file"] = prompt_file
        if template_vars:
            context["template_variables"] = template_vars
        
        super().__init__(message, context=context, **kwargs)


# =============================================================================
# MCP PROTOCOL ERRORS
# =============================================================================

class MCPError(ReviewError):
    """Base class for MCP (Model Context Protocol) errors.
    
    This exception is used as a base for all MCP-related errors including
    connection issues, tool failures, and protocol violations.
    """
    pass


class MCPConnectionError(MCPError):
    """Raised when MCP server connection fails.
    
    This exception is used for network connectivity issues, server unavailability,
    or authentication problems with MCP servers.
    """
    
    def __init__(
        self,
        message: str,
        *,
        server_url: Optional[str] = None,
        timeout: Optional[float] = None,
        **kwargs
    ) -> None:
        """Initialize MCPConnectionError with connection context.
        
        Args:
            message: Error description.
            server_url: URL of the MCP server that failed.
            timeout: Connection timeout value used.
            **kwargs: Additional ReviewError arguments.
        """
        context = kwargs.get("context", {})
        if server_url:
            context["server_url"] = server_url
        if timeout is not None:
            context["timeout"] = timeout
        
        super().__init__(message, context=context, **kwargs)


class MCPToolError(MCPError):
    """Raised when MCP tool execution fails.
    
    This exception is used for tool-specific errors such as missing tools,
    invalid tool parameters, or tool execution failures.
    """
    
    def __init__(
        self,
        message: str,
        *,
        tool_name: Optional[str] = None,
        tool_params: Optional[dict[str, Any]] = None,
        available_tools: Optional[list[str]] = None,
        **kwargs
    ) -> None:
        """Initialize MCPToolError with tool context.
        
        Args:
            message: Error description.
            tool_name: Name of the tool that failed.
            tool_params: Parameters that were passed to the tool.
            available_tools: List of available tools for debugging.
            **kwargs: Additional ReviewError arguments.
        """
        context = kwargs.get("context", {})
        if tool_name:
            context["tool_name"] = tool_name
        if tool_params:
            context["tool_parameters"] = tool_params
        if available_tools:
            context["available_tools"] = available_tools
        
        super().__init__(message, context=context, **kwargs)


class MCPServerError(MCPError):
    """Raised when MCP server returns an error.
    
    This exception is used for server-side errors returned by MCP servers,
    including internal server errors and protocol violations.
    """
    pass


# =============================================================================
# WORKFLOW AND GRAPH ERRORS
# =============================================================================

class WorkflowError(ReviewError):
    """Base class for LangGraph workflow errors.
    
    This exception is used as a base for all workflow-related errors including
    graph construction, node execution, and state management issues.
    """
    pass


class GraphBuildError(WorkflowError):
    """Raised when LangGraph construction fails.
    
    This exception is used for errors during graph building, compilation,
    or configuration that prevent the workflow from being created.
    """
    
    def __init__(
        self,
        message: str,
        *,
        graph_type: Optional[str] = None,
        node_count: Optional[int] = None,
        **kwargs
    ) -> None:
        """Initialize GraphBuildError with graph context.
        
        Args:
            message: Error description.
            graph_type: Type of graph being built.
            node_count: Number of nodes in the graph.
            **kwargs: Additional ReviewError arguments.
        """
        context = kwargs.get("context", {})
        if graph_type:
            context["graph_type"] = graph_type
        if node_count is not None:
            context["node_count"] = node_count
        
        super().__init__(message, context=context, **kwargs)


class NodeExecutionError(WorkflowError):
    """Raised when a workflow node fails to execute.
    
    This exception is used for errors during individual node execution
    within a LangGraph workflow.
    """
    
    def __init__(
        self,
        message: str,
        *,
        node_name: Optional[str] = None,
        thread_id: Optional[str] = None,
        state_keys: Optional[list[str]] = None,
        **kwargs
    ) -> None:
        """Initialize NodeExecutionError with execution context.
        
        Args:
            message: Error description.
            node_name: Name of the node that failed.
            thread_id: Thread ID of the execution.
            state_keys: Available keys in the state when the error occurred.
            **kwargs: Additional ReviewError arguments.
        """
        context = kwargs.get("context", {})
        if node_name:
            context["node_name"] = node_name
        if thread_id:
            context["thread_id"] = thread_id
        if state_keys:
            context["available_state_keys"] = state_keys
        
        super().__init__(message, context=context, **kwargs)


class StateError(WorkflowError):
    """Raised when workflow state management fails.
    
    This exception is used for state validation errors, missing state keys,
    or state corruption issues in LangGraph workflows.
    """
    
    def __init__(
        self,
        message: str,
        *,
        expected_keys: Optional[list[str]] = None,
        actual_keys: Optional[list[str]] = None,
        **kwargs
    ) -> None:
        """Initialize StateError with state context.
        
        Args:
            message: Error description.
            expected_keys: List of expected state keys.
            actual_keys: List of actual state keys present.
            **kwargs: Additional ReviewError arguments.
        """
        context = kwargs.get("context", {})
        if expected_keys:
            context["expected_keys"] = expected_keys
        if actual_keys:
            context["actual_keys"] = actual_keys
        
        super().__init__(message, context=context, **kwargs)


# =============================================================================
# FILE SYSTEM ERRORS
# =============================================================================

class FileOperationError(ReviewError):
    """Raised when file system operations fail.
    
    This exception is used for file reading, writing, or path resolution errors.
    """
    
    def __init__(
        self,
        message: str,
        *,
        file_path: Optional[str] = None,
        operation_type: Optional[str] = None,
        **kwargs
    ) -> None:
        """Initialize FileOperationError with file context.
        
        Args:
            message: Error description.
            file_path: Path to the file that caused the error.
            operation_type: Type of operation that failed (read, write, create).
            **kwargs: Additional ReviewError arguments.
        """
        context = kwargs.get("context", {})
        if file_path:
            context["file_path"] = file_path
        if operation_type:
            context["operation_type"] = operation_type
        
        super().__init__(message, context=context, **kwargs)


# =============================================================================
# CONVENIENCE FUNCTIONS
# =============================================================================

def raise_configuration_error(
    message: str,
    *,
    missing_var: Optional[str] = None,
    invalid_var: Optional[str] = None,
    invalid_value: Optional[str] = None,
) -> None:
    """Convenience function to raise ConfigurationError with common patterns.
    
    Args:
        message: Error description.
        missing_var: Name of missing environment variable.
        invalid_var: Name of invalid environment variable.
        invalid_value: Invalid value that was provided.
        
    Raises:
        ConfigurationError: Always raises this exception.
    """
    context = {}
    if missing_var:
        context["missing_variable"] = missing_var
    if invalid_var and invalid_value:
        context["invalid_variable"] = invalid_var
        context["invalid_value"] = invalid_value
    
    raise ConfigurationError(
        message,
        context=context,
        operation="configuration_validation",
        error_code="CONFIG_ERROR"
    )


def raise_mcp_tool_error(
    message: str,
    *,
    tool_name: str,
    available_tools: Optional[list[str]] = None,
    tool_params: Optional[dict[str, Any]] = None,
) -> None:
    """Convenience function to raise MCPToolError with tool context.
    
    Args:
        message: Error description.
        tool_name: Name of the tool that failed.
        available_tools: List of available tools.
        tool_params: Parameters passed to the tool.
        
    Raises:
        MCPToolError: Always raises this exception.
    """
    raise MCPToolError(
        message,
        tool_name=tool_name,
        available_tools=available_tools,
        tool_params=tool_params,
        operation="mcp_tool_execution",
        error_code="TOOL_ERROR"
    )


def raise_postcondition_error(
    message: str,
    *,
    function_name: str,
    expected: str,
    actual: str,
) -> None:
    """Convenience function to raise PostconditionError with validation context.
    
    Args:
        message: Error description.
        function_name: Name of the function where postcondition failed.
        expected: Description of expected result.
        actual: Description of actual result.
        
    Raises:
        PostconditionError: Always raises this exception.
    """
    raise PostconditionError(
        message,
        expected=expected,
        actual=actual,
        operation=function_name,
        error_code="POSTCONDITION_FAILED"
    )
