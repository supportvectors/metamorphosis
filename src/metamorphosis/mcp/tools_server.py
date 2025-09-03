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

load_dotenv()

from metamorphosis.mcp.text_modifiers import CopyEditedText, SummarizedText, get_text_modifiers
from metamorphosis.exceptions import (
    PostconditionError,
    FileOperationError,
    raise_postcondition_error,
)

# Create a basic server instance with a name identifier
mcp = FastMCP(name="text_modifier_mcp_server")

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
    modifiers = get_text_modifiers()
    result = modifiers.copy_edit(text=text)
    # Postcondition (O(1)): ensure structured output sanity
    if not isinstance(result, CopyEditedText) or not result.copy_edited_text:
        raise_postcondition_error(
            "Copy edit output validation failed",
            context={"result_type": type(result).__name__, "has_text": bool(getattr(result, 'copy_edited_text', None))},
            operation="copy_edit_tool_validation"
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
            error_code="FILE_NOT_CREATED"
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
    logger.info(
        "abstractive_summarize: text length={}, max_words={}.", len(text), max_words
    )
    modifiers = get_text_modifiers()
    result = modifiers.summarize(text=text, max_words=max_words)
    # Postcondition (O(1)): ensure structured output sanity
    if not isinstance(result, SummarizedText) or not result.summarized_text:
        raise_postcondition_error(
            "Summarization output validation failed",
            context={"result_type": type(result).__name__, "has_text": bool(getattr(result, 'summarized_text', None))},
            operation="summarize_tool_validation"
        )
    return result

if __name__ == "__main__":
    host = os.getenv("MCP_SERVER_HOST", "127.0.0.1")
    port = int(os.getenv("MCP_SERVER_PORT", "3333"))
    logger.info("Starting MCP tools server at {}:{}", host, port)
    mcp.run(transport="http", host=host, port=port)