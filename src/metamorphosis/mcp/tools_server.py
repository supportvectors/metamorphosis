# =============================================================================
#  Filename: tools_server.py
#
#  Short Description: MCP tools server exposing text utilities as callable tools.
#
#  Creation date: 2025-08-31
#  Author: Asif Qamar
# =============================================================================

from __future__ import annotations

from typing import Annotated
from pydantic import Field, validate_call
from fastmcp import FastMCP
from wordcloud import WordCloud
import uuid
from metamorphosis.mcp.text_modifiers import CopyEditedText, SummarizedText, get_text_modifiers

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
    """
    print(f"Copy-editing text: {text}")
    modifiers = get_text_modifiers()
    return modifiers.copy_edit(text=text)


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
    """
    print(f"Creating word cloud for text: {text}")
    word_cloud = WordCloud().generate(text)
    #save the word cloud to a unique file
    word_cloud_path = f"word_cloud_{uuid.uuid4()}.png"
    word_cloud.to_file(word_cloud_path)
    return word_cloud_path


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
    """
    print(f"Summarizing text: {text}")
    modifiers = get_text_modifiers()
    return modifiers.summarize(text=text, max_words=max_words)

if __name__ == "__main__":
    # Run the MCP server with HTTP transport on localhost at port 3333
    mcp.run(transport="http", host="127.0.0.1", port=3333)