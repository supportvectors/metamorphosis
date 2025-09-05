# =============================================================================
#  Filename: tools_server.py
#
#  Short Description: MCP tools server exposing text utilities as callable tools.
#
#  Creation date: 2025-08-31
#  Author: Asif Qamar
# =============================================================================

from __future__ import annotations

import os
import uuid
from pathlib import Path
from typing import Annotated

from pydantic import Field, validate_call
from fastmcp import FastMCP
from wordcloud import WordCloud
from dotenv import load_dotenv
from loguru import logger

from functools import lru_cache
from metamorphosis.mcp.text_modifiers import TextModifiers
from metamorphosis.datamodel import CopyEditedText, SummarizedText, AchievementsList, ReviewScorecard
from metamorphosis.exceptions import (
    FileOperationError,
    raise_postcondition_error,
)

load_dotenv()


# Create a basic server instance with a name identifier
mcp = FastMCP(name="text_modifier_mcp_server")

@lru_cache(maxsize=1)
def _get_modifiers() -> TextModifiers:
    """Lazy, cached TextModifiers accessor for the MCP server."""
    return TextModifiers()

@mcp.tool("copy_edit")
@validate_call
def copy_edit(text: Annotated[str, Field(min_length=1)]) -> CopyEditedText:
    """Copy edit the provided text.

    Args:
        text: Input text to be lightly normalized and corrected.

    Returns:
        CopyEditedText: Structured result containing the edited text and metadata.

    Raises:
        pydantic.ValidationError: If input fails validation.
        ValueError: If postcondition validation fails.
    """
    logger.info("copy_edit: received text length={}.", len(text))
    modifiers = _get_modifiers()
    result = modifiers.rationalize_text(text=text)
    # Postcondition (O(1)): ensure structured output sanity
    if not isinstance(result, CopyEditedText) or not result.copy_edited_text:
        raise_postcondition_error(
            "Copy edit output validation failed",
            context={
                "result_type": type(result).__name__,
                "has_text": bool(getattr(result, "copy_edited_text", None)),
            },
            operation="copy_edit_tool_validation",
        )
    return result


@mcp.tool("word_cloud")
@validate_call
def create_word_cloud(text: Annotated[str, Field(min_length=1)]) -> str:
    """Create a word cloud from the text.

    Args:
        text: Input text used to generate the word cloud.

    Returns:
        str: Path to the generated word cloud image file.

    Raises:
        pydantic.ValidationError: If input fails validation.
        ValueError: If postcondition validation fails.
        OSError: If word cloud directory creation or file save fails.
    """
    logger.info("word_cloud: generating for text length={}.", len(text))
    word_cloud = WordCloud().generate(text)

    # Ensure word_clouds directory exists
    output_dir = Path("./word_clouds")
    output_dir.mkdir(exist_ok=True)

    # Generate unique filename
    word_cloud_path = output_dir / f"word_cloud_{uuid.uuid4()}.png"
    word_cloud.to_file(str(word_cloud_path))

    # Postcondition (O(1)): ensure file was created
    if not word_cloud_path.exists():
        raise FileOperationError(
            "Word cloud file was not created",
            file_path=str(word_cloud_path),
            operation_type="create",
            operation="word_cloud_generation",
            error_code="FILE_NOT_CREATED",
        )

    return str(word_cloud_path)


@mcp.tool("abstractive_summarize")
@validate_call
def abstractive_summarize(
    text: Annotated[str, Field(min_length=1)],
    max_words: Annotated[int, Field(gt=0)] = 300,
) -> SummarizedText:
    """Summarize the text abstractively.

    Args:
        text: Input text to summarize.
        max_words: Target maximum words for the summary (best-effort).

    Returns:
        SummarizedText: Structured result containing the summary and metadata.

    Raises:
        pydantic.ValidationError: If input fails validation.
        ValueError: If postcondition validation fails.
    """
    logger.info("abstractive_summarize: text length={}, max_words={}.", len(text), max_words)
    modifiers = _get_modifiers()
    result = modifiers.summarize(text=text, max_words=max_words)
    # Postcondition (O(1)): ensure structured output sanity
    if not isinstance(result, SummarizedText) or not result.summarized_text:
        raise_postcondition_error(
            "Summarization output validation failed",
            context={
                "result_type": type(result).__name__,
                "has_text": bool(getattr(result, "summarized_text", None)),
            },
            operation="summarize_tool_validation",
        )
    return result

@mcp.tool("extract_achievements")
@validate_call
def extract_achievements(
    text: Annotated[str, Field(min_length=1)],
) -> AchievementsList:
    """Extract the achievements from the text.

    Args:
        text: Input text to extract the achievements from.

    Returns:
        AchievementsList: Structured result containing the achievements and metadata.

    Raises:
        pydantic.ValidationError: If input fails validation.
        ValueError: If postcondition validation fails.
    """
    logger.info("extract_achievements: text length={}.", len(text))
    modifiers = _get_modifiers()
    result = modifiers.extract_achievements(text=text)
    # Postcondition (O(1)): ensure structured output sanity
    if not isinstance(result, AchievementsList) or not result.items or len(result.items) == 0:
        raise_postcondition_error(
            "Achievements extraction output validation failed",
            context={
                "result_type": type(result).__name__,
                "has_items": bool(getattr(result, "items", None)),
                "items_count": len(result.items),
            },
            operation="extract_achievements_tool_validation",
        )
    return result

@mcp.tool("evaluate_review_text")
@validate_call
def evaluate_review_text(
    text: Annotated[str, Field(min_length=1)],
) -> ReviewScorecard:
    """Evaluate the review text.

    Args:
        text: Input text to evaluate.

    Returns:
        ReviewScorecard: Structured result containing the review scorecard and metadata.

    Raises:
        pydantic.ValidationError: If input fails validation.
        ValueError: If postcondition validation fails.
    """
    logger.info("evaluate_review_text: text length={}.", len(text))
    modifiers = _get_modifiers()
    result = modifiers.evaluate_review_text(text=text)
    # Postcondition (O(1)): ensure structured output sanity
    if not isinstance(result, ReviewScorecard) or not result.metrics or len(result.metrics) == 0:
        raise_postcondition_error(
            "Review text evaluation output validation failed",
            context={
                "result_type": type(result).__name__,
                "has_metrics": bool(getattr(result, "metrics", None)),
                "metrics_count": len(result.metrics),
            },
            operation="evaluate_review_text_tool_validation",
        )
    return result

if __name__ == "__main__":
    host = os.getenv("MCP_SERVER_HOST", "127.0.0.1")
    port = int(os.getenv("MCP_SERVER_PORT", "3333"))
    logger.info("Starting MCP tools server at {}:{}", host, port)
    mcp.run(transport="http", host=host, port=port)

