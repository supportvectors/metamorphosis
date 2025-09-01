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
from fastmcp import FastMCP, tool
from wordcloud import WordCloud

from .text_modifiers import CopyEditedText, SummarizedText, get_text_modifiers


@tool("copy_edit")
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
    modifiers = get_text_modifiers()
    return modifiers.copy_edit(text=text)


@tool("word_cloud")
@validate_call
def create_word_cloud(text: Annotated[str, Field(min_length=1)]) -> WordCloud:
    """Create a word cloud from the text.

    Args:
        text: Input text used to generate the word cloud.

    Returns:
        WordCloud: Generated word cloud object.

    Raises:
        pydantic.ValidationError: If input fails validation.
    """
    return WordCloud().generate(text)


@tool("abstractive_summarize")
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
    modifiers = get_text_modifiers()
    return modifiers.summarize(text=text, max_words=max_words)


if __name__ == "__main__":
    FastMCP().serve(host="0.0.0.0", port=3333)
