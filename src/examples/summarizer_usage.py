# =============================================================================
#  Filename: summarizer_usage.py
#
#  Short Description: Example script that summarizes the sample self-review text
#                     using the TextModifiers summarizer LLM.
#
#  Creation date: 2025-09-04
#  Author: Asif Qamar
# =============================================================================

from __future__ import annotations

from typing import Annotated

from loguru import logger
from pydantic import Field, PositiveInt, validate_call

from metamorphosis.datamodel import SummarizedText
from metamorphosis.mcp.text_modifiers import TextModifiers
from metamorphosis.utilities import get_project_root, read_text_file


@validate_call
def summarize_raw_review(max_words: Annotated[PositiveInt, Field(gt=0)] = 200) -> SummarizedText:
    """Summarize the sample self-review markdown using TextModifiers.

    Args:
        max_words: Target maximum words for the summary (best-effort).

    Returns:
        SummarizedText: Structured summary result.
    """
    project_root = get_project_root()
    raw_path = project_root / "sample_reviews" / "raw_review.md"
    logger.info("Reading review from: {}", raw_path)

    # -------------------------------------------------------------------------

    # Create TextModifiers instance
    modifiers = TextModifiers()

    # Log model details for summarizer before running
    modifiers._log_model_details_table(method="summarize")

    raw_text = read_text_file(raw_path)
    logger.info("Running summarization (max_words={})", max_words)
    result = modifiers.summarize(text=raw_text, max_words=int(max_words))

    logger.info("Summary size (tokens reported): {}", result.size)
    logger.info("Summary text:\n{}", result.summarized_text)
    return result


if __name__ == "__main__":
    summary = summarize_raw_review()
    print(summary.summarized_text)
