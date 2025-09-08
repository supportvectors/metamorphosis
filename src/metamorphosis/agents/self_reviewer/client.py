# =============================================================================
#  Filename: client.py
#
#  Short Description: MCP client management for self-reviewer workflows.
#
#  Creation date: 2025-09-08
#  Author: Asif Qamar
# =============================================================================

"""MCP Client Management for Self-Reviewer Workflows.

This module provides the MCPClientManager class that handles all MCP
(Model Context Protocol) client connections, tool discovery, and tool
access for the self-reviewer workflow system.
"""

from __future__ import annotations

import os
from typing import List, Optional

from langchain_mcp_adapters.client import MultiServerMCPClient
from loguru import logger
from pydantic import validate_call
from icontract import require, ensure

from metamorphosis.exceptions import raise_mcp_tool_error, raise_postcondition_error


class MCPClientManager:
    """Manages MCP client connections and tool discovery.

    This class encapsulates all MCP client functionality including connection
    management, tool discovery, and tool access. It provides a clean interface
    for the workflow system to interact with MCP servers.

    Attributes:
        client: The underlying MultiServerMCPClient instance.
        tools: List of available tools from MCP servers.
    """

    def __init__(self, config: Optional[dict] = None) -> None:
        """Initialize the MCP client manager.

        Args:
            config: Optional configuration dictionary. If not provided,
                   uses environment variables for configuration.
        """
        self.config = config or {}
        self.client: Optional[MultiServerMCPClient] = None
        self.tools: List = []
        self._initialized = False

    @validate_call
    @require(lambda: True, "Environment should be properly configured")
    @ensure(lambda result: result is not None, "MCP client must be created successfully")
    def _create_client(self) -> MultiServerMCPClient:
        """Create MCP client with environment-based configuration.

        Returns:
            MultiServerMCPClient: Configured client instance.
        """
        host = self.config.get("mcp_server_host") or os.getenv("MCP_SERVER_HOST", "localhost")
        port = self.config.get("mcp_server_port") or os.getenv("MCP_SERVER_PORT", "3333")
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

    @validate_call
    @ensure(lambda self: len(self.tools) > 0, "Tools must be retrieved from MCP server")
    async def initialize(self) -> None:
        """Initialize MCP client and retrieve available tools.

        This method establishes the connection to MCP servers and retrieves
        the list of available tools that can be used in the workflow.

        Raises:
            ConnectionError: If unable to connect to MCP servers.
            Exception: If tool retrieval fails.
        """
        if self._initialized:
            return

        logger.debug("Initializing MCP client manager")

        # Create the client
        self.client = self._create_client()

        # Retrieve available tools
        self.tools = await self.client.get_tools()
        tool_names = [tool.name for tool in self.tools]

        # Postcondition: ensure tools were retrieved
        if not self.tools or not isinstance(self.tools, list):
            raise_postcondition_error(
                "No tools retrieved from MCP server",
                context={"tools_count": len(self.tools) if self.tools else 0},
                operation="mcp_tool_initialization",
            )

        logger.info("Available MCP tools: {}", tool_names)
        self._initialized = True

    @validate_call
    @require(
        lambda tool_name: isinstance(tool_name, str) and len(tool_name) > 0,
        "Tool name must be non-empty string",
    )
    @ensure(lambda result: result is not None, "Tool must be found")
    def get_tool(self, tool_name: str):
        """Get a tool by name from the available tools.

        Args:
            tool_name: Name of the tool to retrieve.

        Returns:
            Tool: The requested tool instance.

        Raises:
            ValueError: If tool is not found.
            RuntimeError: If client is not initialized.
        """
        if not self._initialized:
            raise RuntimeError("MCP client manager not initialized. Call initialize() first.")

        tool = next((t for t in self.tools if t.name == tool_name), None)
        if not tool:
            raise_mcp_tool_error(
                f"{tool_name} tool not found", tool_name=tool_name, operation="tool_lookup"
            )
        return tool

    def list_available_tools(self) -> List[str]:
        """Get list of available tool names.

        Returns:
            List[str]: Names of all available tools.

        Raises:
            RuntimeError: If client is not initialized.
        """
        if not self._initialized:
            raise RuntimeError("MCP client manager not initialized. Call initialize() first.")

        return [tool.name for tool in self.tools]

    async def close(self) -> None:
        """Close the MCP client connection.

        This method should be called when the client manager is no longer needed
        to properly clean up resources.
        """
        if self.client:
            # Note: MultiServerMCPClient doesn't have a close method in current version
            # but we include this for future compatibility
            logger.debug("Closing MCP client connection")
            self.client = None
        self._initialized = False

    @property
    def is_initialized(self) -> bool:
        """Check if the client manager is initialized.

        Returns:
            bool: True if initialized, False otherwise.
        """
        return self._initialized
