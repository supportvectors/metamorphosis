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

load_dotenv()

# Defer third-party import to keep import-time clarity.
from svlearn.config.configuration import ConfigurationMixin  # noqa: E402


def _load_config() -> dict[str, Any]:
    """Load project configuration using svlearn's ConfigurationMixin.

    Returns:
        dict[str, Any]: Configuration mapping.
    """

    return ConfigurationMixin().load_config()


# Public configuration object for convenience.
config: dict[str, Any] = _load_config()

__all__ = ["config"]


from svlearn.config.configuration import ConfigurationMixin

from dotenv import load_dotenv
load_dotenv()

config = ConfigurationMixin().load_config()
