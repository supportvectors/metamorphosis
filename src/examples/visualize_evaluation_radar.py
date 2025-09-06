# =============================================================================
#  Filename: visualize_evaluation_radar.py
#
#  Short Description: Create radar plot visualization from review evaluation results
#                     using Plotly for interactive charts.
#
#  Creation date: 2025-01-23
#  Author: Asif Qamar
# =============================================================================

"""Create radar plot visualization from review evaluation results.

This script demonstrates how to:
1. Load evaluation results from the text_evaluator_results.jsonl file
2. Create an interactive radar plot using Plotly
3. Display the chart in browser and save as HTML file

Run this script from the project root:
    python -m src.examples.visualize_evaluation_radar
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import plotly.graph_objects as go
from rich.console import Console
from rich.panel import Panel
from loguru import logger

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from metamorphosis.utilities import get_project_root, create_radar_plot


def load_evaluation_results(jsonl_path: Path) -> dict:
    """Load evaluation results from JSONL file.

    Args:
        jsonl_path: Path to the text_evaluator_results.jsonl file.

    Returns:
        Dictionary containing the evaluation results.

    Raises:
        FileNotFoundError: If the JSONL file doesn't exist.
        json.JSONDecodeError: If the file contains invalid JSON.
    """
    if not jsonl_path.exists():
        raise FileNotFoundError(f"Evaluation results file not found: {jsonl_path}")

    with jsonl_path.open("r", encoding="utf-8") as f:
        # Read the single line JSON object
        line = f.readline().strip()
        if not line:
            raise ValueError("Empty evaluation results file")
        return json.loads(line)

def save_and_display_plot(fig: go.Figure, output_path: Path) -> None:
    """Save the plot as HTML and display in browser.

    Args:
        fig: The Plotly figure to save and display.
        output_path: Path where to save the HTML file.
    """
    # Save as HTML file
    fig.write_html(str(output_path), include_plotlyjs="cdn")
    logger.debug("Saved radar plot to: {}", output_path)

    # Display in browser
    fig.show()


def create_summary_info(evaluation_data: dict) -> str:
    """Create a summary text from evaluation data.

    Args:
        evaluation_data: Dictionary containing evaluation results.

    Returns:
        Formatted summary string.
    """
    metrics_info = []
    for metric in evaluation_data["metrics"]:
        metrics_info.append(f"  • {metric['name']}: {metric['score']}/100")

    summary = f"""
📊 Evaluation Summary:
  Overall Score: {evaluation_data["overall"]}/100
  Verdict: {evaluation_data["verdict"].title()}
  
📈 Individual Metrics:
{chr(10).join(metrics_info)}

🏷️  Quality Flags: {len(evaluation_data["notes"])} detected
"""

    if evaluation_data["notes"]:
        summary += f"   • {', '.join(evaluation_data['notes'])}\n"
    else:
        summary += "   • No issues detected\n"

    return summary


def main() -> None:
    """Main function that creates the radar plot visualization."""
    console = Console()

    try:
        # Display header
        console.print("\n")
        console.print(
            Panel.fit(
                "📊 Review Evaluation Radar Plot Visualization\n\n"
                "This script creates an interactive radar chart from the\n"
                "text_evaluator_results.jsonl evaluation data using Plotly.",
                title="Metamorphosis Visualization",
                style="bold blue",
            )
        )

        # Load evaluation results
        console.print("\n📖 Loading evaluation results from text_evaluator_results.jsonl...")
        project_root = get_project_root()
        jsonl_path = project_root / "sample_reviews" / "text_evaluator_results.jsonl"
        evaluation_data = load_evaluation_results(jsonl_path)
        console.print("✅ Loaded evaluation results successfully")

        # Display summary
        summary_text = create_summary_info(evaluation_data)
        console.print(Panel(summary_text, title="📋 Evaluation Data", style="dim blue"))

        # Create radar plot
        console.print("\n📊 Creating radar plot visualization...")
        fig = create_radar_plot(evaluation_data)
        console.print("✅ Radar plot created successfully")

        # Save and display
        console.print("\n💾 Saving plot and opening in browser...")
        output_path = project_root / "sample_reviews" / "evaluation_radar_plot.html"
        save_and_display_plot(fig, output_path)
        console.print(f"✅ Radar plot saved to: {output_path}")
        console.print("✅ Interactive plot opened in your default browser")

        # Display final info
        console.print("\n")
        console.print(
            Panel(
                "💡 Tip: The radar plot is interactive! You can:\n"
                "  • Hover over data points to see detailed scores\n"
                "  • Compare current performance vs. the 90% writing goal (orange dashed line)\n"
                "  • Use the toolbar to zoom, pan, and download the chart\n"
                "  • Toggle traces on/off using the legend\n"
                "  • The HTML file can be shared or embedded in reports\n\n"
                f"🎯 The orange dashed polygon shows the 90% writing goal target\n"
                f"📄 Interactive chart saved as: {output_path.name}",
                title="ℹ️  Visualization Notes",
                style="dim cyan",
            )
        )

    except FileNotFoundError as e:
        console.print(f"❌ Error: {e}", style="bold red")
        console.print(
            "\n💡 Hint: Run the review_text_evaluator_usage.py script first to generate the evaluation results.",
            style="dim yellow",
        )
        sys.exit(1)
    except json.JSONDecodeError as e:
        console.print(f"❌ JSON Error: {e}", style="bold red")
        console.print("The evaluation results file appears to be corrupted.", style="dim red")
        sys.exit(1)
    except Exception as e:
        logger.exception("Unexpected error during radar plot creation")
        console.print(f"❌ Unexpected error: {e}", style="bold red")
        sys.exit(1)


if __name__ == "__main__":
    main()
