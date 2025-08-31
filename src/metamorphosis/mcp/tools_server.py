# =============================================================================
#  Filename: tools_server.py
#
#  Short Description: MCP tools server exposing text utilities as callable tools.
#
#  Creation date: 2025-08-31
#  Author: Asif Qamar
# =============================================================================

from __future__ import annotations

from pydantic import validate_call
from fastmcp import FastMCP, tool
from wordcloud import WordCloud

from .text_modifiers import CopyEditedText, SummarizedText, get_text_modifiers


@tool("copy_edit")
@validate_call
def copy_edit(text: str) -> CopyEditedText:
    """Copy edit the provided text.

    Args:
        text: Input text to be lightly normalized and corrected.

    Returns:
        CopyEditedText: Structured result containing the edited text and metadata.

    Raises:
        ValueError: If text is empty or only whitespace.
    """
    if text is None or not isinstance(text, str) or not text.strip():
        raise ValueError("text must be a non-empty string")
    modifiers = get_text_modifiers()
    return modifiers.copy_edit(text=text)


@tool("word_cloud")
@validate_call
def create_word_cloud(text: str) -> WordCloud:
    """Create a word cloud from the text.

    Args:
        text: Input text used to generate the word cloud.

    Returns:
        WordCloud: Generated word cloud object.

    Raises:
        ValueError: If text is empty or only whitespace.
    """
    if text is None or not isinstance(text, str) or not text.strip():
        raise ValueError("text must be a non-empty string")
    return WordCloud().generate(text)


@tool("abstractive_summarize")
@validate_call
def abstractive_summarize(text: str, max_words: int = 300) -> SummarizedText:
    """Summarize the text abstractively.

    Args:
        text: Input text to summarize.
        max_words: Target maximum words for the summary (best-effort).

    Returns:
        SummarizedText: Structured result containing the summary and metadata.

    Raises:
        ValueError: If text is empty or only whitespace or max_words < 1.
    """
    if text is None or not isinstance(text, str) or not text.strip():
        raise ValueError("text must be a non-empty string")
    if not isinstance(max_words, int) or max_words < 1:
        raise ValueError("max_words must be a positive integer")
    modifiers = get_text_modifiers()
    return modifiers.summarize(text=text, max_words=max_words)


if __name__ == "__main__":
    FastMCP().serve(host="0.0.0.0", port=3333)
