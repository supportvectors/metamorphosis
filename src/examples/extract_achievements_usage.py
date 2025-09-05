# =============================================================================
#  Filename: extract_achievements_usage.py
#
#  Short Description: Example usage of TextModifiers.extract_achievements with
#                     rich table formatting for pretty output.
#
#  Creation date: 2025-01-23
#  Author: Asif Qamar
# =============================================================================

"""Example usage of the TextModifiers.extract_achievements method.

This script demonstrates how to:
1. Load a sample employee review from the sample_reviews directory
2. Extract key achievements using the TextModifiers class
3. Display the results in a beautiful rich table format
4. Save the structured achievements data to a JSONL file

Run this script from the project root:
    python -m src.examples.extract_achievements_usage
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

from rich.console import Console
from rich.table import Table
from rich.text import Text
from rich.panel import Panel
from rich import box
from loguru import logger

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from metamorphosis.mcp.text_modifiers import TextModifiers
from metamorphosis.datamodel import AchievementsList
from metamorphosis.utilities import get_project_root


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


def create_achievements_table(achievements_list: AchievementsList) -> Table:
    """Create a rich table displaying the extracted achievements.

    Args:
        achievements_list: The AchievementsList object containing extracted achievements.

    Returns:
        A rich Table object formatted for display.
    """
    # Create the main table
    table = Table(
        title=(
            f"🏆 Extracted Key Achievements "
            f"({len(achievements_list.items)} items, ~{achievements_list.size} tokens)"
        ),
        box=box.ROUNDED,
        show_header=True,
        header_style="bold magenta",
        title_style="bold blue",
        expand=True,
    )

    # Add columns
    table.add_column("Title", style="bold cyan", width=25)
    table.add_column("Outcome", style="white", width=40)
    table.add_column("Impact Area", style="bold green", justify="center", width=12)
    table.add_column("Metrics", style="bold yellow", width=15)
    table.add_column("Details", style="dim white", width=20)

    # Add rows for each achievement
    for i, achievement in enumerate(achievements_list.items, 1):
        # Format metrics as a comma-separated string
        metrics_text = ", ".join(achievement.metric_strings) if achievement.metric_strings else "—"

        # Format additional details (timeframe, scope, collaborators)
        details_parts = []
        if achievement.timeframe:
            details_parts.append(f"⏰ {achievement.timeframe}")
        if achievement.ownership_scope:
            details_parts.append(f"👤 {achievement.ownership_scope}")
        if achievement.collaborators:
            collabs = ", ".join(achievement.collaborators[:2])  # Show first 2 collaborators
            if len(achievement.collaborators) > 2:
                collabs += f" +{len(achievement.collaborators) - 2}"
            details_parts.append(f"🤝 {collabs}")

        details_text = "\n".join(details_parts) if details_parts else "—"

        # Color-code impact areas
        impact_colors = {
            "reliability": "red",
            "performance": "blue",
            "security": "magenta",
            "cost": "green",
            "revenue": "bold green",
            "customer": "cyan",
            "delivery_speed": "yellow",
            "quality": "white",
            "compliance": "dim white",
            "team": "bold blue",
        }
        impact_color = impact_colors.get(achievement.impact_area, "white")
        impact_text = Text(achievement.impact_area, style=impact_color)

        # Add the row
        table.add_row(
            f"{i}. {achievement.title}",
            achievement.outcome,
            impact_text,
            metrics_text,
            details_text,
        )

    return table


def write_achievements_to_jsonl(achievements_list: AchievementsList, output_path: Path) -> None:
    """Write the achievements to a JSONL file.

    Args:
        achievements_list: The AchievementsList object containing extracted achievements.
        output_path: Path to the output JSONL file.
    """
    # Create the directory if it doesn't exist
    output_path.parent.mkdir(parents=True, exist_ok=True)

    # Convert the AchievementsList to dict and write to JSONL
    with output_path.open("w", encoding="utf-8") as f:
        # Write the full AchievementsList object as one JSON line
        achievements_dict = achievements_list.model_dump()
        f.write(json.dumps(achievements_dict, ensure_ascii=False) + "\n")

    logger.debug("Wrote achievements to JSONL file: {}", output_path)


def create_summary_panel(achievements_list: AchievementsList) -> Panel:
    """Create a summary panel with statistics about the achievements.

    Args:
        achievements_list: The AchievementsList object containing extracted achievements.

    Returns:
        A rich Panel object with summary statistics.
    """
    if not achievements_list.items:
        return Panel(
            "No achievements were extracted from the review text.",
            title="📊 Summary",
            style="dim red",
        )

    # Count achievements by impact area
    impact_counts: dict[str, int] = {}
    total_metrics = 0
    achievements_with_timeframes = 0
    achievements_with_collaborators = 0

    for achievement in achievements_list.items:
        impact_counts[achievement.impact_area] = impact_counts.get(achievement.impact_area, 0) + 1
        total_metrics += len(achievement.metric_strings)
        if achievement.timeframe:
            achievements_with_timeframes += 1
        if achievement.collaborators:
            achievements_with_collaborators += 1

    # Format the summary text
    summary_lines = [
        f"📈 Total Achievements: {len(achievements_list.items)}",
        f"📊 Total Metrics Found: {total_metrics}",
        f"⏰ With Timeframes: {achievements_with_timeframes}",
        f"🤝 With Collaborators: {achievements_with_collaborators}",
        f"🎯 Token Estimate: {achievements_list.size}",
        "",
        "📋 Impact Areas:",
    ]

    # Add impact area breakdown
    for impact_area, count in sorted(impact_counts.items()):
        summary_lines.append(f"  • {impact_area}: {count}")

    return Panel(
        "\n".join(summary_lines), title="📊 Achievements Summary", style="dim blue", box=box.SIMPLE
    )


def main() -> None:
    """Main function that demonstrates achievement extraction."""
    console = Console()

    try:
        # Display header
        console.print("\n")
        console.print(
            Panel.fit(
                "🔍 Achievement Extraction Demo\n\n"
                "This example loads a sample employee review and extracts\n"
                "key achievements using the TextModifiers.extract_achievements method.",
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

        # Extract achievements
        console.print("\n🔍 Extracting key achievements from the review...")
        with console.status("[bold green]Processing with LLM..."):
            achievements = modifier.extract_achievements(text=review_text)

        console.print(f"✅ Extracted {len(achievements.items)} achievements")

        # Write achievements to JSONL file
        console.print("\n📝 Writing achievements to JSONL file...")
        project_root = get_project_root()
        jsonl_output_path = project_root / "sample_reviews" / "key_achievements.jsonl"
        write_achievements_to_jsonl(achievements, jsonl_output_path)
        console.print(f"✅ Saved achievements to: {jsonl_output_path}")

        # Display results
        console.print("\n")
        console.print(create_summary_panel(achievements))
        console.print("\n")
        console.print(create_achievements_table(achievements))

        # Display raw data option
        console.print("\n")
        console.print(
            Panel(
                "💡 Tip: The achievements are returned as structured Pydantic objects\n"
                "that can be easily serialized to JSON or integrated into other systems.\n\n"
                "Each Achievement object contains: title, outcome, impact_area,\n"
                "metric_strings, timeframe, ownership_scope, and collaborators.\n\n"
                f"📄 The complete data has been saved to: {jsonl_output_path.name}",
                title="ℹ️  Integration Notes",
                style="dim cyan",
            )
        )

    except FileNotFoundError as e:
        console.print(f"❌ Error: {e}", style="bold red")
        sys.exit(1)
    except Exception as e:
        logger.exception("Unexpected error during achievement extraction")
        console.print(f"❌ Unexpected error: {e}", style="bold red")
        sys.exit(1)


if __name__ == "__main__":
    main()
