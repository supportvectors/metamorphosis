# =============================================================================
#  Filename: review_tools.py
#
#  Short Description: Langgraph tools for generating achievements and review scorecard for the periodic employee self-review process.
#
#  Creation date: 2025-09-07
#  Author: Chandar L
# =============================================================================

"""Langgraph tools for generating achievements and review scorecard for the periodic employee self-review process."""

from langchain_core.tools import tool
from functools import lru_cache

from metamorphosis.mcp.text_modifiers import TextModifiers

@lru_cache(maxsize=1)
def _get_modifiers() -> TextModifiers:
    """Lazy, cached TextModifiers accessor for the Langgraph tools."""
    return TextModifiers()

@tool
def extract_achievements(text: str) -> dict:
    """Extract the key achievements from the text using the extract_achievements method of the text_modifiers."""
    modifier = _get_modifiers()
    return modifier.extract_achievements(text=text).model_dump()

@tool
def evaluate_review_text(text: str) -> dict:
    """Evaluate the review text using the evaluate_review_text method of the text_modifiers."""
    modifier = _get_modifiers()
    return modifier.evaluate_review_text(text=text).model_dump()