# =============================================================================
#  Filename: rationalize_usage.py
#
#  Short Description: Example script that rationalizes the sample data engineer
#                     self-review text using the TextModifiers rationalize_text method.
#
#  Creation date: 2025-01-27
#  Author: Asif Qamar
# =============================================================================

from __future__ import annotations

from typing import Annotated

from loguru import logger
from pydantic import Field, validate_call

from metamorphosis.datamodel import CopyEditedText
from metamorphosis.mcp.text_modifiers import TextModifiers
from metamorphosis.utilities import get_project_root, read_text_file


@validate_call
def rationalize_data_engineer_review() -> CopyEditedText:
    """Rationalize the sample data engineer self-review using TextModifiers.

    This function demonstrates the text rationalization capability by processing
    a raw, intentionally messy self-review that contains typical issues found
    in employee self-reviews pasted from personal docs or Slack:
    
    - Spelling errors and typos
    - Inconsistent formatting and punctuation
    - Casual shorthand and informal language
    - Grammar issues and inconsistent capitalization
    
    The rationalization process will clean up these issues while preserving
    the original meaning, structure, and all numerical data.

    Returns:
        CopyEditedText: Structured result containing the rationalized text,
                       token count, and whether changes were made.
    """
    project_root = get_project_root()
    review_path = project_root / "sample_reviews" / "data_engineer_review.md"
    logger.info("Reading data engineer review from: {}", review_path)

    # Read the raw review text
    raw_text = read_text_file(review_path)
    
    # Extract just the review content (skip the explanatory header)
    # Find the actual review content starting from the role line
    lines = raw_text.split('\n')
    review_start_idx = None
    for i, line in enumerate(lines):
        if line.strip().startswith('**role**:'):
            review_start_idx = i
            break
    
    if review_start_idx is not None:
        # Take everything from the role line onwards
        review_content = '\n'.join(lines[review_start_idx:])
    else:
        # Fallback to using the entire content
        review_content = raw_text

    # Initialize the TextModifiers and perform rationalization
    modifiers = TextModifiers()
    logger.info("Running text rationalization (input length: {} chars)", len(review_content))
    
    result = modifiers.rationalize_text(text=review_content)

    logger.info("Rationalization completed:")
    logger.info("- Output length: {} chars", len(result.copy_edited_text))
    logger.info("- Token count: {}", result.size)
    logger.info("- Text was edited: {}", result.is_edited)
    
    return result


def pretty_print_comparison(original: str, rationalized: str) -> None:
    """Pretty print a side-by-side comparison of original vs rationalized text.
    
    Args:
        original: The original text before rationalization.
        rationalized: The rationalized text after processing.
    """
    print("=" * 100)
    print("TEXT RATIONALIZATION COMPARISON")
    print("=" * 100)
    print()
    
    print("🔴 ORIGINAL TEXT (Raw Draft):")
    print("-" * 50)
    print(original)
    print()
    
    print("🟢 RATIONALIZED TEXT (Copy-Edited):")
    print("-" * 50)
    print(rationalized)
    print()
    
    print("📊 STATISTICS:")
    print("-" * 50)
    print(f"Original length:     {len(original):,} characters")
    print(f"Rationalized length: {len(rationalized):,} characters")
    print(f"Length difference:   {len(rationalized) - len(original):+,} characters")
    print(f"Change percentage:   {((len(rationalized) - len(original)) / len(original) * 100):+.1f}%")
    print()


if __name__ == "__main__":
    # Run the rationalization
    result = rationalize_data_engineer_review()
    
    # Get the original text for comparison
    project_root = get_project_root()
    review_path = project_root / "sample_reviews" / "data_engineer_review.md"
    raw_text = read_text_file(review_path)
    
    # Extract the review content (same logic as in the function)
    lines = raw_text.split('\n')
    review_start_idx = None
    for i, line in enumerate(lines):
        if line.strip().startswith('**role**:'):
            review_start_idx = i
            break
    
    if review_start_idx is not None:
        original_content = '\n'.join(lines[review_start_idx:])
    else:
        original_content = raw_text
    
    # Display the pretty-printed comparison
    pretty_print_comparison(original_content, result.copy_edited_text)
    
    # Also show just the clean result for easy copying
    print("=" * 100)
    print("CLEAN RATIONALIZED TEXT (for copying):")
    print("=" * 100)
    print(result.copy_edited_text)
