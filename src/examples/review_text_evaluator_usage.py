# =============================================================================
#  Filename: review_text_evaluator_usage.py
#
#  Short Description: Example usage of TextModifiers.evaluate_review_text with
#                     rich table formatting and JSONL output.
#
#  Creation date: 2025-01-23
#  Author: Asif Qamar
# =============================================================================

"""Example usage of the TextModifiers.evaluate_review_text method.

This script demonstrates how to:
1. Load a sample employee review from the sample_reviews directory
2. Evaluate the writing quality using the TextModifiers class
3. Display the results in a beautiful rich table format
4. Save the structured evaluation data to a JSONL file

Run this script from the project root:
    python -m src.examples.review_text_evaluator_usage
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

from rich.console import Console
from rich.panel import Panel
from rich import box
from loguru import logger

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from metamorphosis.mcp.text_modifiers import TextModifiers
from metamorphosis.datamodel import ReviewScorecard
from metamorphosis.utilities import (get_project_root, 
                create_summary_panel_evaluation, 
                create_metrics_table, 
                create_radar_chart_info)

def load_sample_review() -> str:
    """Load the sample copy-edited review from sample_reviews directory.

    Returns:
        The content of the copy_edited.md file.

    Raises:
        FileNotFoundError: If the sample review file doesn't exist.
    """
    project_root = get_project_root()
    sample_file = project_root / "sample_reviews" / "copy_edited.md"

    if not sample_file.exists():
        raise FileNotFoundError(f"Sample review file not found: {sample_file}")

    return sample_file.read_text(encoding="utf-8")


def write_evaluation_to_jsonl(scorecard: ReviewScorecard, output_path: Path) -> None:
    """Write the evaluation results to a JSONL file.

    Args:
        scorecard: The ReviewScorecard object containing evaluation results.
        output_path: Path to the output JSONL file.
    """
    # Create the directory if it doesn't exist
    output_path.parent.mkdir(parents=True, exist_ok=True)

    # Convert the ReviewScorecard to dict and write to JSONL
    with output_path.open("w", encoding="utf-8") as f:
        # Write the full ReviewScorecard object as one JSON line
        scorecard_dict = scorecard.model_dump()
        f.write(json.dumps(scorecard_dict, ensure_ascii=False) + "\n")

    logger.debug("Wrote evaluation results to JSONL file: {}", output_path)


def main() -> None:
    """Main function that demonstrates review text evaluation."""
    console = Console()

    try:
        # Display header
        console.print("\n")
        console.print(
            Panel.fit(
                "📊 Review Text Quality Evaluation Demo\n\n"
                "This example loads a sample employee review and evaluates\n"
                "its writing quality using the TextModifiers.evaluate_review_text method.",
                title="Metamorphosis Text Processing",
                style="bold blue",
            )
        )

        # Load the sample review
        console.print("\n📖 Loading sample review from sample_reviews/copy_edited.md...")
        review_text = load_sample_review()
        console.print(f"✅ Loaded review text ({len(review_text):,} characters)")

        # Initialize TextModifiers
        console.print("\n🤖 Initializing TextModifiers with LLM clients...")
        modifier = TextModifiers()
        console.print("✅ TextModifiers initialized successfully")

        # Evaluate review text
        console.print("\n📊 Evaluating review text quality...")
        with console.status("[bold green]Processing with LLM..."):
            evaluation = modifier.evaluate_review_text(text=review_text)

        console.print("✅ Evaluation completed successfully!")

        # Write evaluation to JSONL file
        console.print("\n📝 Writing evaluation results to JSONL file...")
        project_root = get_project_root()
        jsonl_output_path = project_root / "sample_reviews" / "text_evaluator_results.jsonl"
        write_evaluation_to_jsonl(evaluation, jsonl_output_path)
        console.print(f"✅ Saved evaluation results to: {jsonl_output_path}")

        # Display results
        console.print("\n")
        console.print(create_summary_panel_evaluation(evaluation))
        console.print("\n")
        console.print(create_metrics_table(evaluation))
        console.print("\n")
        console.print(create_radar_chart_info(evaluation))

        # Display integration notes
        console.print("\n")
        console.print(
            Panel(
                "💡 Tip: The evaluation results are returned as structured Pydantic objects\n"
                "that can be easily integrated into HR systems or quality dashboards.\n\n"
                "Each MetricScore contains: name, score (0-100), rationale, and suggestion.\n"
                "The ReviewScorecard includes: metrics, overall score, verdict, notes, "
                "and radar data.\n\n"
                f"📄 The complete evaluation data has been saved to: {jsonl_output_path.name}",
                title="ℹ️  Integration Notes",
                style="dim cyan",
            )
        )

    except FileNotFoundError as e:
        console.print(f"❌ Error: {e}", style="bold red")
        sys.exit(1)
    except Exception as e:
        logger.exception("Unexpected error during review text evaluation")
        console.print(f"❌ Unexpected error: {e}", style="bold red")
        sys.exit(1)


if __name__ == "__main__":
    main()
