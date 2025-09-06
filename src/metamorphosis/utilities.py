# =============================================================================
#  Filename: utilities.py
#
#  Short Description: Common utility functions used across the metamorphosis project.
#
#  Creation date: 2025-01-15
#  Author: Asif Qamar
# =============================================================================

"""Common utility functions for the metamorphosis project.

This module provides reusable utility functions that are used across multiple
components of the metamorphosis system. All utilities follow Design-by-Contract
principles with proper validation and error handling.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Annotated
from rich.table import Table
from rich.text import Text
from rich.panel import Panel
from rich import box
from pydantic import Field, validate_call
from loguru import logger
import plotly.graph_objects as go
import math

from metamorphosis.exceptions import FileOperationError, ConfigurationError
from metamorphosis.datamodel import AchievementsList, ReviewScorecard


@validate_call
def read_text_file(
    file_path: Annotated[Path | str, Field(description="Path to the text file to read")],
) -> str:
    """Read a UTF-8 text file with comprehensive error handling.

    This utility function provides robust file reading with proper error handling
    and validation. It's designed to be reused across the project for consistent
    file operations.

    Args:
        file_path: Path to the text file to read (Path object or string).

    Returns:
        str: Content of the file, stripped of leading/trailing whitespace.

    Raises:
        FileOperationError: If file not found, not accessible, or empty.
    """
    # Convert string to Path if necessary
    if isinstance(file_path, str):
        file_path = Path(file_path)

    logger.debug("Reading text file: {}", file_path)

    # Precondition validation via pydantic is already done by @validate_call

    if not file_path.exists():
        raise FileOperationError(
            f"File not found: {file_path}",
            file_path=str(file_path),
            operation_type="read",
            operation="file_existence_check",
            error_code="FILE_NOT_FOUND",
        )

    if not file_path.is_file():
        raise FileOperationError(
            f"Path is not a file: {file_path}",
            file_path=str(file_path),
            operation_type="read",
            operation="file_type_check",
            error_code="NOT_A_FILE",
        )

    try:
        content = file_path.read_text(encoding="utf-8").strip()
    except (OSError, UnicodeDecodeError) as e:
        raise FileOperationError(
            f"Failed to read file: {file_path}",
            file_path=str(file_path),
            operation_type="read",
            operation="file_content_read",
            error_code="READ_FAILED",
            original_error=e,
        ) from e

    if not content:
        raise FileOperationError(
            f"File is empty: {file_path}",
            file_path=str(file_path),
            operation_type="read",
            operation="content_validation",
            error_code="EMPTY_FILE",
        )

    # Postcondition (O(1)): ensure we return non-empty string
    if not isinstance(content, str) or not content:
        raise FileOperationError(
            "Postcondition failed: content must be non-empty string",
            file_path=str(file_path),
            operation_type="read",
            operation="postcondition_check",
            error_code="POSTCONDITION_FAILED",
        )

    logger.debug("Successfully read file: {} ({} chars)", file_path, len(content))
    return content


@validate_call
def get_project_root(
    env_var_name: Annotated[str, Field(min_length=1)] = "PROJECT_ROOT_DIR",
    fallback_levels: Annotated[int, Field(ge=1, le=10)] = 3,
) -> Path:
    """Get project root directory from environment variable or path resolution.

    This utility provides a consistent way to locate the project root directory
    across different modules, supporting both environment variable configuration
    and automatic path resolution.

    Args:
        env_var_name: Name of environment variable containing project root path.
        fallback_levels: Number of parent directories to traverse for fallback.

    Returns:
        Path: Absolute path to the project root directory.

    Raises:
        ConfigurationError: If project root cannot be determined.
    """
    logger.debug(
        "Resolving project root (env_var={}, fallback_levels={})", env_var_name, fallback_levels
    )

    # Try environment variable first
    project_root_str = os.getenv(env_var_name)
    if project_root_str:
        project_root = Path(project_root_str).resolve()
        if project_root.exists() and project_root.is_dir():
            logger.debug("Using project root from {}: {}", env_var_name, project_root)
            return project_root
        else:
            raise ConfigurationError(
                f"Project root from {env_var_name} does not exist or is not a directory",
                context={"env_var": env_var_name, "path": project_root_str},
                operation="project_root_resolution",
                error_code="INVALID_PROJECT_ROOT",
            )

    # Fallback to path resolution
    try:
        # Get the current file's directory and traverse up
        current_file = Path(__file__).resolve()
        project_root = current_file.parents[fallback_levels - 1]

        # Postcondition (O(1)): ensure we found a valid directory
        if not project_root.exists() or not project_root.is_dir():
            raise ConfigurationError(
                f"Fallback project root resolution failed: {project_root}",
                context={"fallback_levels": fallback_levels, "current_file": str(current_file)},
                operation="project_root_fallback",
                error_code="FALLBACK_FAILED",
            )

        logger.debug("Using fallback project root: {}", project_root)
        return project_root

    except (IndexError, OSError) as e:
        raise ConfigurationError(
            "Could not determine project root directory",
            context={"env_var": env_var_name, "fallback_levels": fallback_levels},
            operation="project_root_resolution",
            error_code="ROOT_RESOLUTION_FAILED",
            original_error=e,
        ) from e


@validate_call
def ensure_directory_exists(
    directory_path: Annotated[Path | str, Field(description="Directory path to create if needed")],
) -> Path:
    """Ensure a directory exists, creating it if necessary.

    Args:
        directory_path: Path to the directory (Path object or string).

    Returns:
        Path: Absolute path to the directory.

    Raises:
        FileOperationError: If directory cannot be created.
    """
    if isinstance(directory_path, str):
        directory_path = Path(directory_path)

    directory_path = directory_path.resolve()

    if directory_path.exists():
        if not directory_path.is_dir():
            raise FileOperationError(
                f"Path exists but is not a directory: {directory_path}",
                file_path=str(directory_path),
                operation_type="create",
                operation="directory_validation",
                error_code="NOT_A_DIRECTORY",
            )
        return directory_path

    try:
        directory_path.mkdir(parents=True, exist_ok=True)
        logger.debug("Created directory: {}", directory_path)
        return directory_path
    except OSError as e:
        raise FileOperationError(
            f"Failed to create directory: {directory_path}",
            file_path=str(directory_path),
            operation_type="create",
            operation="directory_creation",
            error_code="CREATE_FAILED",
            original_error=e,
        ) from e

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

def create_summary_panel_evaluation(scorecard: ReviewScorecard) -> Panel:
    """Create a summary panel with overall evaluation statistics.

    Args:
        scorecard: The ReviewScorecard object containing evaluation results.

    Returns:
        A rich Panel object with summary statistics.
    """
    # Verdict styling
    verdict_colors = {
        "excellent": "bright_green",
        "strong": "green",
        "mixed": "yellow",
        "weak": "red",
    }
    verdict_color = verdict_colors.get(scorecard.verdict, "white")

    # Calculate score statistics
    scores = [metric.score for metric in scorecard.metrics]
    avg_score = sum(scores) / len(scores)
    max_score = max(scores)
    min_score = min(scores)

    # Find best and worst performing metrics
    best_metric = max(scorecard.metrics, key=lambda m: m.score)
    worst_metric = min(scorecard.metrics, key=lambda m: m.score)

    # Format the summary text
    summary_lines = [
        f"🎯 Overall Score: {scorecard.overall}/100",
        f"📈 Verdict: {scorecard.verdict.title()}",
        f"📊 Average Score: {avg_score:.1f}/100",
        f"🔝 Highest Score: {max_score}/100 ({best_metric.name})",
        f"🔻 Lowest Score: {min_score}/100 ({worst_metric.name})",
        "",
        f"🏷️  Quality Flags: {len(scorecard.notes)} detected",
    ]

    # Add flags if any
    if scorecard.notes:
        summary_lines.append("   • " + ", ".join(scorecard.notes))
    else:
        summary_lines.append("   • No quality issues detected")

    return Panel(
        "\n".join(summary_lines),
        title="📋 Evaluation Summary",
        style=f"dim {verdict_color}",
        box=box.SIMPLE,
    )

def create_metrics_table(scorecard: ReviewScorecard) -> Table:
    """Create a rich table displaying the evaluation metrics.

    Args:
        scorecard: The ReviewScorecard object containing evaluation results.

    Returns:
        A rich Table object formatted for display.
    """
    # Create the main table
    table = Table(
        title=(
            f"📊 Review Quality Evaluation "
            f"(Overall: {scorecard.overall}/100 - {scorecard.verdict.title()})"
        ),
        box=box.ROUNDED,
        show_header=True,
        header_style="bold magenta",
        title_style="bold blue",
        expand=True,
    )

    # Add columns
    table.add_column("Metric", style="bold cyan", width=20)
    table.add_column("Score", style="bold white", justify="center", width=8)
    table.add_column("Rationale", style="white", width=50)
    table.add_column("Suggestion", style="bold yellow", width=40)

    # Define weights for display
    weights = {
        "OutcomeOverActivity": "25%",
        "QuantitativeSpecificity": "25%",
        "ClarityCoherence": "15%",
        "Conciseness": "15%",
        "OwnershipLeadership": "10%",
        "Collaboration": "10%",
    }

    # Color coding based on score ranges
    def get_score_color(score: int) -> str:
        if score >= 85:
            return "bright_green"
        elif score >= 70:
            return "green"
        elif score >= 50:
            return "yellow"
        else:
            return "red"

    # Add rows for each metric
    for metric in scorecard.metrics:
        weight = weights.get(metric.name, "")
        metric_name = f"{metric.name}\n({weight})"

        score_color = get_score_color(metric.score)
        score_text = Text(f"{metric.score}/100", style=score_color)

        # Add the row
        table.add_row(metric_name, score_text, metric.rationale, metric.suggestion)

    return table

def create_radar_chart_info(scorecard: ReviewScorecard) -> Panel:
    """Create an info panel with radar chart data.

    Args:
        scorecard: The ReviewScorecard object containing evaluation results.

    Returns:
        A rich Panel object with radar chart information.
    """
    # Format radar data
    radar_data = []
    for label, value in zip(scorecard.radar_labels, scorecard.radar_values):
        radar_data.append(f"  • {label}: {value}/100")

    radar_text = "📡 Radar Chart Data (for visualization):\n\n" + "\n".join(radar_data)

    return Panel(radar_text, title="📈 Visualization Data", style="dim blue", box=box.SIMPLE)

def create_radar_plot(evaluation_data: dict) -> go.Figure:
    """Create a radar plot from evaluation data.

    Args:
        evaluation_data: Dictionary containing evaluation results with radar_labels and radar_values.

    Returns:
        Plotly Figure object containing the radar plot.
    """
    # Extract radar data
    labels = evaluation_data["radar_labels"]
    values = evaluation_data["radar_values"]
    overall_score = evaluation_data["overall"]
    verdict = evaluation_data["verdict"]

    # Create the radar plot
    fig = go.Figure()

    # Add the "Writing Goal" reference polygon (90% on all metrics)
    goal_values = [90] * len(labels)
    fig.add_trace(
        go.Scatterpolar(
            r=goal_values,
            theta=labels,
            fill="toself",
            name="Writing Goal (90% target)",
            line=dict(color="rgba(255, 165, 0, 0.8)", width=2, dash="dash"),
            fillcolor="rgba(255, 165, 0, 0.1)",
            hovertemplate="<b>%{theta}</b><br>Writing Goal: %{r}/100<extra></extra>",
            opacity=0.7,
        )
    )

    # Add the main radar trace (actual scores)
    fig.add_trace(
        go.Scatterpolar(
            r=values,
            theta=labels,
            fill="toself",
            name=f"Current Performance (Overall: {overall_score}/100)",
            line=dict(color="rgb(0, 123, 255)", width=3),
            fillcolor="rgba(0, 123, 255, 0.3)",
            hovertemplate="<b>%{theta}</b><br>Current Score: %{r}/100<extra></extra>",
        )
    )

    # Customize the layout
    fig.update_layout(
        polar=dict(
            radialaxis=dict(
                visible=True,
                range=[0, 105],  # Extended range to show 100% circle clearly
                tickvals=[20, 40, 60, 80, 100],
                ticktext=["20", "40", "60", "80", "100"],
                tickfont=dict(size=11, color="#333"),
                gridcolor="rgba(200, 200, 200, 0.5)",
                linecolor="rgba(150, 150, 150, 0.8)",
                gridwidth=1,
            ),
            angularaxis=dict(
                tickfont=dict(size=13, color="darkblue", family="Arial Bold"),
                rotation=90,  # Start from top
                direction="clockwise",
                linecolor="rgba(150, 150, 150, 0.8)",
                gridcolor="rgba(200, 200, 200, 0.3)",
            ),
            bgcolor="rgba(248, 249, 250, 0.9)",
        ),
        title=dict(
            text=f"📊 Review Quality Evaluation - {verdict.title()}<br>"
            f"<sub style='color:#666;'>Overall Score: {overall_score}/100 | "
            f"🎯 Target: 90% across all metrics</sub>",
            x=0.5,
            font=dict(size=18, color="darkblue", family="Arial Bold"),
        ),
        font=dict(family="Arial", size=12),
        width=750,
        height=750,
        margin=dict(l=90, r=90, t=120, b=90),
        paper_bgcolor="white",
        plot_bgcolor="rgba(248, 249, 250, 0.3)",
        showlegend=True,
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=-0.1,
            xanchor="center",
            x=0.5,
            bgcolor="rgba(255, 255, 255, 0.8)",
            bordercolor="rgba(200, 200, 200, 0.5)",
            borderwidth=1,
            font=dict(size=11),
        ),
    )

    # Add improved score annotations positioned outside the radar
    for i, (label, value) in enumerate(zip(labels, values)):
        # Calculate proper polar coordinates for annotation positioning
        angle_deg = 90 - i * 360 / len(labels)  # Start from top, go clockwise
        angle_rad = angle_deg * 3.14159 / 180

        # Position annotations at radius 115 (outside the 105 max range)
        r_annotation = 115
        x_pos = r_annotation * 0.01 * math.cos(angle_rad)
        y_pos = r_annotation * 0.01 * math.sin(angle_rad)

        # Choose color based on performance vs goal
        score_color = "green" if value >= 90 else "orange" if value >= 70 else "red"

        fig.add_annotation(
            x=x_pos,
            y=y_pos,
            text=f"<b>{value}</b>",
            showarrow=False,
            font=dict(size=12, color=score_color, family="Arial Bold"),
            bgcolor="rgba(255, 255, 255, 0.9)",
            bordercolor=score_color,
            borderwidth=2,
            borderpad=4,
        )

    return fig