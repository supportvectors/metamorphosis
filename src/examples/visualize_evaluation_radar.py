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
import math
import sys
from pathlib import Path

import plotly.graph_objects as go
import plotly.io as pio
from rich.console import Console
from rich.panel import Panel
from loguru import logger

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from metamorphosis.utilities import get_project_root


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
    fig.add_trace(go.Scatterpolar(
        r=goal_values,
        theta=labels,
        fill='toself',
        name='Writing Goal (90% target)',
        line=dict(color='rgba(255, 165, 0, 0.8)', width=2, dash='dash'),
        fillcolor='rgba(255, 165, 0, 0.1)',
        hovertemplate='<b>%{theta}</b><br>Writing Goal: %{r}/100<extra></extra>',
        opacity=0.7
    ))
    
    # Add the main radar trace (actual scores)
    fig.add_trace(go.Scatterpolar(
        r=values,
        theta=labels,
        fill='toself',
        name=f'Current Performance (Overall: {overall_score}/100)',
        line=dict(color='rgb(0, 123, 255)', width=3),
        fillcolor='rgba(0, 123, 255, 0.3)',
        hovertemplate='<b>%{theta}</b><br>Current Score: %{r}/100<extra></extra>'
    ))
    
    # Customize the layout
    fig.update_layout(
        polar=dict(
            radialaxis=dict(
                visible=True,
                range=[0, 105],  # Extended range to show 100% circle clearly
                tickvals=[20, 40, 60, 80, 100],
                ticktext=['20', '40', '60', '80', '100'],
                tickfont=dict(size=11, color='#333'),
                gridcolor='rgba(200, 200, 200, 0.5)',
                linecolor='rgba(150, 150, 150, 0.8)',
                gridwidth=1
            ),
            angularaxis=dict(
                tickfont=dict(size=13, color='darkblue', family='Arial Bold'),
                rotation=90,  # Start from top
                direction='clockwise',
                linecolor='rgba(150, 150, 150, 0.8)',
                gridcolor='rgba(200, 200, 200, 0.3)'
            ),
            bgcolor='rgba(248, 249, 250, 0.9)'
        ),
        title=dict(
            text=f"📊 Review Quality Evaluation - {verdict.title()}<br>"
                 f"<sub style='color:#666;'>Overall Score: {overall_score}/100 | "
                 f"🎯 Target: 90% across all metrics</sub>",
            x=0.5,
            font=dict(size=18, color='darkblue', family='Arial Bold')
        ),
        font=dict(family='Arial', size=12),
        width=750,
        height=750,
        margin=dict(l=90, r=90, t=120, b=90),
        paper_bgcolor='white',
        plot_bgcolor='rgba(248, 249, 250, 0.3)',
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
            font=dict(size=11)
        )
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
        score_color = 'green' if value >= 90 else 'orange' if value >= 70 else 'red'
        
        fig.add_annotation(
            x=x_pos,
            y=y_pos,
            text=f"<b>{value}</b>",
            showarrow=False,
            font=dict(size=12, color=score_color, family='Arial Bold'),
            bgcolor='rgba(255, 255, 255, 0.9)',
            bordercolor=score_color,
            borderwidth=2,
            borderpad=4
        )
    
    return fig


def save_and_display_plot(fig: go.Figure, output_path: Path) -> None:
    """Save the plot as HTML and display in browser.
    
    Args:
        fig: The Plotly figure to save and display.
        output_path: Path where to save the HTML file.
    """
    # Save as HTML file
    fig.write_html(str(output_path), include_plotlyjs='cdn')
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
  Overall Score: {evaluation_data['overall']}/100
  Verdict: {evaluation_data['verdict'].title()}
  
📈 Individual Metrics:
{chr(10).join(metrics_info)}

🏷️  Quality Flags: {len(evaluation_data['notes'])} detected
"""
    
    if evaluation_data['notes']:
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
        console.print(Panel.fit(
            "📊 Review Evaluation Radar Plot Visualization\n\n"
            "This script creates an interactive radar chart from the\n"
            "text_evaluator_results.jsonl evaluation data using Plotly.",
            title="Metamorphosis Visualization",
            style="bold blue"
        ))
        
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
        console.print(Panel(
            "💡 Tip: The radar plot is interactive! You can:\n"
            "  • Hover over data points to see detailed scores\n"
            "  • Compare current performance vs. the 90% writing goal (orange dashed line)\n"
            "  • Use the toolbar to zoom, pan, and download the chart\n"
            "  • Toggle traces on/off using the legend\n"
            "  • The HTML file can be shared or embedded in reports\n\n"
            f"🎯 The orange dashed polygon shows the 90% writing goal target\n"
            f"📄 Interactive chart saved as: {output_path.name}",
            title="ℹ️  Visualization Notes",
            style="dim cyan"
        ))
        
    except FileNotFoundError as e:
        console.print(f"❌ Error: {e}", style="bold red")
        console.print("\n💡 Hint: Run the review_text_evaluator_usage.py script first to generate the evaluation results.", style="dim yellow")
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
