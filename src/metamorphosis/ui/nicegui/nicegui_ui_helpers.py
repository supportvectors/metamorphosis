# =============================================================================
#  Filename: nicegui_ui_helpers.py
#
#  Short Description: Helper functions for the NiceGUI self-review UI flow.
#
#  Creation date: 2026-01-21
#  Author: Ashwath Bhat
# =============================================================================

"""
Helper Functions for NiceGUI Self-Review UI

This module contains the reusable helper functions used by the NiceGUI UI
flow for the self-reviewer agent. It includes rendering utilities, SSE
stream parsing, and input validation.
"""

import json
from typing import Any, Dict, Optional
import requests
from nicegui import ui
from rich.console import Console

from metamorphosis.datamodel import AchievementsList, ReviewScorecard
from metamorphosis.utilities import create_radar_plot

def render_rich(
    rich_renderable: object,
    *,
    char_width: int = 100,
    container: Optional[ui.element] = None,
) -> str:
    """
    Render a Rich Panel/Table into NiceGUI.
    
    Args:
        rich_renderable: The Rich object to render.
        char_width: Approximate characters per line.
        container: Optional NiceGUI container to add the HTML to.
        
    Returns:
        The generated HTML string.
    """
    console = Console(record=True, width=char_width)
    console.print(rich_renderable)
    html = console.export_html(inline_styles=True)
    
    if container:
        with container:
            ui.html(html, sanitize=False).classes('w-full overflow-auto')
    
    return html

def safe_markdown(text: str) -> str:
    """
    Escapes dollar signs for markdown rendering consistency.
    """
    return text.replace("$", "\\$")

def create_html_achievements_table(achievements_list: AchievementsList) -> str:
    """
    Create an HTML table with proper text wrapping for achievements.
    """
    html = """
    <style>
    .achievements-table {
        width: 100%;
        border-collapse: collapse;
        margin: 10px 0;
        font-family: Arial, sans-serif;
    }
    .achievements-table th {
        background-color: #f0f2f6;
        color: #262730;
        font-weight: bold;
        padding: 12px 8px;
        text-align: left;
        border: 1px solid #e6e9ef;
        white-space: nowrap;
    }
    .achievements-table td {
        padding: 12px 8px;
        border: 1px solid #e6e9ef;
        vertical-align: top;
        word-wrap: break-word;
        word-break: break-word;
        white-space: pre-wrap;
        max-width: 200px;
    }
    .achievements-table tr:nth-child(even) {
        background-color: #fafafa;
    }
    .achievements-table tr:hover {
        background-color: #f0f2f6;
    }
    .title-cell { font-weight: bold; color: #1f77b4; }
    .impact-cell { text-align: center; font-weight: bold; }
    .metrics-cell { font-style: italic; color: #2ca02c; }
    .details-cell { font-size: 0.9em; color: #666; }
    .contribution-cell { text-align: center; font-weight: bold; font-size: 0.9em; }
    .contribution-minor { color: #95a5a6; }
    .contribution-medium { color: #f39c12; }
    .contribution-significant { color: #e74c3c; }
    .contribution-critical { color: #8e44ad; }
    </style>

    <table class="achievements-table">
        <thead>
            <tr>
                <th>🏆 Title</th>
                <th>📋 Outcome</th>
                <th>🎯 Impact Area</th>
                <th>📊 Metrics</th>
                <th>⭐ Contribution</th>
                <th>ℹ️ Details</th>
            </tr>
        </thead>
        <tbody>
    """

    for i, achievement in enumerate(achievements_list.items, 1):
        metrics_text = ", ".join(achievement.metric_strings) if achievement.metric_strings else "—"
        
        contribution_text = achievement.contribution or "—"
        contribution_class = f"contribution-{achievement.contribution.lower()}" if achievement.contribution else ""

        details_parts = []
        if achievement.timeframe: details_parts.append(f"⏰ {achievement.timeframe}")
        if achievement.ownership_scope: details_parts.append(f"👤 {achievement.ownership_scope}")
        if achievement.collaborators:
            collabs = ", ".join(achievement.collaborators[:2])
            if len(achievement.collaborators) > 2: collabs += f" +{len(achievement.collaborators) - 2}"
            details_parts.append(f"🤝 {collabs}")
        if achievement.project_name: details_parts.append(f"🏗️ {achievement.project_name}")
        
        details_text = "\n".join(details_parts) if details_parts else "—"

        impact_colors = {
            "reliability": "#ff6b6b", "performance": "#4ecdc4", "security": "#45b7d1",
            "cost": "#96ceb4", "revenue": "#feca57", "customer": "#ff9ff3",
            "delivery_speed": "#54a0ff", "quality": "#5f27cd", "compliance": "#00d2d3",
            "team": "#ff9f43",
        }
        impact_color = impact_colors.get(achievement.impact_area, "#666")

        html += f"""
            <tr>
                <td class="title-cell">{i}. {achievement.title}</td>
                <td>{achievement.outcome}</td>
                <td class="impact-cell" style="color: {impact_color};">{achievement.impact_area.replace('_', ' ').title()}</td>
                <td class="metrics-cell">{metrics_text}</td>
                <td class="contribution-cell {contribution_class}">{contribution_text}</td>
                <td class="details-cell">{details_text}</td>
            </tr>
        """

    html += "</tbody></table>"
    return html

def display_achievements_table(achievements_list: AchievementsList, container: ui.element):
    """
    Display achievements using HTML table in a NiceGUI container.
    """
    with container:
        ui.markdown(f"### 🏆 Extracted Key Achievements\n**{len(achievements_list.items)} items** • **~{achievements_list.size} tokens**")
        ui.html(create_html_achievements_table(achievements_list), sanitize=False).classes('w-full overflow-auto')

def create_html_metrics_table(review_scorecard: ReviewScorecard) -> str:
    """
    Create an HTML table with proper text wrapping for review metrics.
    """
    weights = {
        "OutcomeOverActivity": "25%", "QuantitativeSpecificity": "25%",
        "ClarityCoherence": "15%", "Conciseness": "15%",
        "OwnershipLeadership": "10%", "Collaboration": "10%",
    }

    def get_score_color(score: int) -> str:
        if score >= 85: return "#2ecc71"
        elif score >= 70: return "#27ae60"
        elif score >= 50: return "#f39c12"
        else: return "#e74c3c"

    html = """
    <style>
    .metrics-table {
        width: 100%;
        border-collapse: collapse;
        margin: 10px 0;
        font-family: Arial, sans-serif;
    }
    .metrics-table th {
        background-color: #f0f2f6;
        color: #262730;
        font-weight: bold;
        padding: 12px 8px;
        text-align: left;
        border: 1px solid #e6e9ef;
        white-space: nowrap;
    }
    .metrics-table td {
        padding: 12px 8px;
        border: 1px solid #e6e9ef;
        vertical-align: top;
        word-wrap: break-word;
        word-break: break-word;
        white-space: pre-wrap;
        max-width: 200px;
    }
    .metrics-table tr:nth-child(even) { background-color: #fafafa; }
    .metrics-table tr:hover { background-color: #f0f2f6; }
    .metric-name-cell { font-weight: bold; color: #1f77b4; width: 20%; }
    .score-cell { text-align: center; font-weight: bold; width: 10%; }
    .rationale-cell { width: 35%; }
    .suggestion-cell { font-style: italic; color: #2ca02c; width: 35%; }
    </style>

    <table class="metrics-table">
        <thead>
            <tr>
                <th>📊 Metric</th>
                <th>🎯 Score</th>
                <th>💭 Rationale</th>
                <th>💡 Suggestion</th>
            </tr>
        </thead>
        <tbody>
    """

    for metric in review_scorecard.metrics:
        weight = weights.get(metric.name, "")
        metric_name = f"{metric.name}<br>({weight})"
        score_color = get_score_color(metric.score)

        html += f"""
            <tr>
                <td class="metric-name-cell">{metric_name}</td>
                <td class="score-cell" style="color: {score_color};">{metric.score}/100</td>
                <td class="rationale-cell">{metric.rationale}</td>
                <td class="suggestion-cell">{metric.suggestion}</td>
            </tr>
        """

    html += "</tbody></table>"
    return html

def display_metrics_table(review_scorecard: ReviewScorecard, container: ui.element):
    """
    Display metrics using HTML table in a NiceGUI container.
    """
    with container:
        ui.markdown(f"### 📊 Review Quality Evaluation\n**Overall Score: {review_scorecard.overall}/100** • **Verdict: {review_scorecard.verdict.title()}**")
        ui.html(create_html_metrics_table(review_scorecard), sanitize=False).classes('w-full overflow-auto')

def display_radar_plot(review_scorecard: ReviewScorecard, container: ui.element):
    """
    Display radar plot using Plotly in a NiceGUI container.
    """
    with container:
        # Convert Pydantic model to dict for create_radar_plot
        evaluation_data = review_scorecard.model_dump()
        fig = create_radar_plot(evaluation_data)
        
        # Adjust figure size for NiceGUI
        fig.update_layout(width=None) # Let it be responsive-ish
        
        ui.plotly(fig).classes('w-full')

def validate_review_text(text: str) -> tuple[bool, str]:
    """
    Simple validation for review text input.
    """
    if not text or not text.strip():
        return False, "Please enter some review text before starting."
    if len(text.strip()) < 10:
        return False, "Review text should be at least 10 characters long."
    if len(text) > 10000:
        return False, "Review text is too long (max 10,000 characters)."
    return True, ""

def patch_state(dst: Dict[str, Any], delta: Dict[str, Any]) -> Dict[str, Any]:
    """
    Performs a shallow merge of two dictionaries for 'updates' mode.
    """
    dst = dict(dst or {})
    for k, v in (delta or {}).items():
        dst[k] = v
    return dst

def sse_events(url: str, data: Dict[str, Any]):
    """
    Minimal Server-Sent Events (SSE) client.
    """
    with requests.post(url, json=data, stream=True, timeout=600) as resp:
        resp.raise_for_status()
        for raw in resp.iter_lines(decode_unicode=False):
            if raw is None or not raw:
                continue
            if raw.startswith(b"data:"):
                try:
                    payload = raw[len(b"data:") :].strip().decode("utf-8")
                    if payload:
                        yield json.loads(payload)
                except Exception:
                    pass

def extract_values_from_event(ev: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """
    Extracts the actual state values from various LangGraph event formats.
    """
    if not isinstance(ev, dict):
        return None

    if isinstance(ev.get("values"), dict):
        return ev["values"]
    if isinstance(ev.get("data"), dict) and isinstance(ev["data"].get("values"), dict):
        return ev["data"]["values"]
    if isinstance(ev.get("state"), dict):
        return ev["state"]
    if isinstance(ev.get("data"), dict) and isinstance(ev["data"].get("state"), dict):
        return ev["data"]["state"]

    expected_keys = {
        "original_text", "copy_edited_text", "summary",
        "word_cloud_path", "achievements", "review_scorecard",
        "review_complete",
    }
    if expected_keys.intersection(ev.keys()):
        return ev

    return None
