# =============================================================================
#  Filename: __init__.py
#
#  Short Description: Package initialization for metamorphosis; loads project configuration.
#
#  Creation date: 2025-08-31
#  Author: Asif Qamar
# =============================================================================

"""Metamorphosis package entry.

This module loads environment variables and exposes a loaded configuration
object for consumers who rely on `svlearn` configuration conventions.
"""

from __future__ import annotations

from typing import Any

from dotenv import load_dotenv
from loguru import logger

load_dotenv()

# Defer third-party import to keep import-time clarity.
from svlearn.config.configuration import ConfigurationMixin  # noqa: E402

from metamorphosis.exceptions import (
    MCPToolError,
    PostconditionError,
    ValidationError,
    FileOperationError,
    raise_mcp_tool_error,
    raise_postcondition_error,
)


def _load_config() -> dict[str, Any]:
    """Load project configuration using svlearn's ConfigurationMixin.

    Returns:
        dict[str, Any]: Configuration mapping.
        
    Raises:
        Exception: If configuration loading fails.
    """
    logger.debug("Loading project configuration")
    config_data = ConfigurationMixin().load_config()
    # Postcondition (O(1)): ensure valid config
    if not isinstance(config_data, dict):
        raise_postcondition_error("Config validation failed", context={"config_type": type(config_data).__name__}, operation="config_loading_validation")
    return config_data


# Public configuration object for convenience.
config: dict[str, Any] = _load_config()

__all__ = ["config"]
