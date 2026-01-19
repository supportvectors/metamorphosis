# =============================================================================
#  Filename: streamlit_ui_helpers.py
#
#  Short Description: Helper functions for the Streamlit self-review UI flow.
#
#  Creation date: 2026-01-19
#  Author: Chandar L
# =============================================================================

"""
Helper Functions for Streamlit Self-Review UI

This module contains the reusable helper functions used by the Streamlit UI
flow for the self-reviewer agent. It includes rendering utilities, SSE
stream parsing, input validation, and tab population helpers.
"""

# Standard library imports for JSON handling, timing, and unique ID generation
import json  # JSON serialization/deserialization for event data
import math  # Math functions for calculation
import uuid  # Unique identifier generation for session management
from typing import Any, Dict  # Type hints for data structures

# Third-party imports for HTTP requests and web UI framework
import requests  # HTTP client for SSE streaming and API communication
import streamlit as st  # Web UI framework for building interactive applications
from streamlit_ace import st_ace

from metamorphosis.datamodel import AchievementsList, ReviewScorecard
from metamorphosis.utilities import (
    create_summary_panel,
    create_summary_panel_evaluation,
    create_radar_chart_info,
    create_radar_plot,
)

# Rich imports for converting Rich objects to HTML
from rich.console import Console


def render_rich(
    rich_renderable: object,
    *,
    char_width: int = 100,  # approximate characters per line (affects wrapping)
    line_height_px: int = 20,  # monospace-ish line height
    padding_px: int = 24,  # top+bottom padding
    min_height: int = 120,
    max_height: int = 800,
    scrolling: bool = True,
):
    """
    Render a Rich Panel/Table (or any renderable) into Streamlit and auto-pick a height.

    Strategy: render to text to count lines -> derive pixel height -> render HTML at that height.
    """
    # 1) Render once to measure (text)
    measure_console = Console(record=True, width=char_width)
    measure_console.print(rich_renderable)
    text = measure_console.export_text(clear=False)

    # 2) Count lines (includes wrapped lines because of width=char_width)
    line_count = text.count("\n") + 1

    # 3) Convert to pixels (very close for monospace; tweak constants to taste)
    measured_height = line_count * line_height_px + padding_px
    height = max(min_height, min(int(measured_height), max_height))

    # 4) Export HTML from the same buffer so the look matches the measurement
    html = measure_console.export_html(inline_styles=True)

    # 5) Embed
    st.components.v1.html(html, height=height, scrolling=scrolling)


def safe_markdown(text: str):
    """
    Replace $ with \\$, so that the markdown rendering is not broken.
    This is a workaround to avoid the markdown rendering breaking when $ is present in the text.
    """
    return text.replace("$", "\\$")


def display_achievements_table(achievements_list: AchievementsList):
    """
    Display achievements using HTML table with proper text wrapping.

    Args:
        achievements_list: The AchievementsList object containing extracted achievements.
    """
    # Create header with summary information
    st.markdown(
        f"""
    ### 🏆 Extracted Key Achievements
    **{len(achievements_list.items)} items** • **~{achievements_list.size} tokens**
    """
    )

    # Create HTML table with proper text wrapping
    html_table = create_html_achievements_table(achievements_list)
    html_doc = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="utf-8" />
    </head>
    <body>
        {html_table}
    </body>
    </html>
    """

    st.components.v1.html(html_doc, height=500, scrolling=True)


def create_html_achievements_table(achievements_list: AchievementsList) -> str:
    """
    Create an HTML table with proper text wrapping for achievements.

    Args:
        achievements_list: The AchievementsList object containing extracted achievements.

    Returns:
        HTML string for the achievements table.
    """
    # Start building the HTML table
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
    .title-cell {
        font-weight: bold;
        color: #1f77b4;
    }
    .impact-cell {
        text-align: center;
        font-weight: bold;
    }
    .metrics-cell {
        font-style: italic;
        color: #2ca02c;
    }
    .details-cell {
        font-size: 0.9em;
        color: #666;
    }
    .contribution-cell {
        text-align: center;
        font-weight: bold;
        font-size: 0.9em;
    }
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

    # Add rows for each achievement
    for i, achievement in enumerate(achievements_list.items, 1):
        # Format metrics as a comma-separated string
        metrics_text = ", ".join(achievement.metric_strings) if achievement.metric_strings else "—"

        # Format contribution level with color coding
        contribution_text = "—"
        contribution_class = ""
        if achievement.contribution:
            contribution_text = achievement.contribution
            contribution_class = f"contribution-{achievement.contribution.lower()}"

        # Format additional details (timeframe, scope, collaborators, project info)
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

        # Add project-related information if available
        if achievement.project_name:
            details_parts.append(f"🏗️ {achievement.project_name}")
        if achievement.project_department:
            details_parts.append(f"🏢 {achievement.project_department}")
        if achievement.project_impact_category:
            details_parts.append(f"💼 {achievement.project_impact_category}")
        if achievement.project_effort_size:
            details_parts.append(f"⚡ {achievement.project_effort_size}")
        if achievement.project_text:
            # Truncate project text for display (show first 150 chars)
            project_text_short = (
                achievement.project_text[:150] + "..."
                if len(achievement.project_text) > 150
                else achievement.project_text
            )
            details_parts.append(f"📝 {project_text_short}")

        # Add rationale if available (truncated for display)
        if achievement.rationale:
            rationale_short = (
                achievement.rationale[:100] + "..."
                if len(achievement.rationale) > 100
                else achievement.rationale
            )
            details_parts.append(f"💭 {rationale_short}")

        details_text = "\n".join(details_parts) if details_parts else "—"

        # Color-code impact areas
        impact_colors = {
            "reliability": "#ff6b6b",
            "performance": "#4ecdc4",
            "security": "#45b7d1",
            "cost": "#96ceb4",
            "revenue": "#feca57",
            "customer": "#ff9ff3",
            "delivery_speed": "#54a0ff",
            "quality": "#5f27cd",
            "compliance": "#00d2d3",
            "team": "#ff9f43",
        }
        impact_color = impact_colors.get(achievement.impact_area, "#666")

        # Add the row
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

    # Close the table
    html += """
        </tbody>
    </table>
    """
    return html


def display_metrics_table(review_scorecard: ReviewScorecard):
    """
    Display metrics using HTML table with proper text wrapping.

    Args:
        review_scorecard: The ReviewScorecard object containing evaluation results.
    """
    # Create header with summary information
    st.markdown(
        f"""
    ### 📊 Review Quality Evaluation
    **Overall Score: {review_scorecard.overall}/100** • **Verdict: {review_scorecard.verdict.title()}**
    """
    )

    # Create HTML table with proper text wrapping
    html_table = create_html_metrics_table(review_scorecard)
    html_doc = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="utf-8" />
    </head>
    <body>
        {html_table}
    </body>
    </html>
    """

    st.components.v1.html(html_doc, height=500, scrolling=True)


def create_html_metrics_table(review_scorecard: ReviewScorecard) -> str:
    """
    Create an HTML table with proper text wrapping for review metrics.

    Args:
        review_scorecard: The ReviewScorecard object containing evaluation results.

    Returns:
        HTML string for the metrics table.
    """
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
            return "#2ecc71"  # bright green
        elif score >= 70:
            return "#27ae60"  # green
        elif score >= 50:
            return "#f39c12"  # yellow
        else:
            return "#e74c3c"  # red

    # Start building the HTML table
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
    .metrics-table tr:nth-child(even) {
        background-color: #fafafa;
    }
    .metrics-table tr:hover {
        background-color: #f0f2f6;
    }
    .metric-name-cell {
        font-weight: bold;
        color: #1f77b4;
        width: 20%;
    }
    .score-cell {
        text-align: center;
        font-weight: bold;
        width: 10%;
    }
    .rationale-cell {
        width: 35%;
    }
    .suggestion-cell {
        font-style: italic;
        color: #2ca02c;
        width: 35%;
    }
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

    # Add rows for each metric
    for metric in review_scorecard.metrics:
        weight = weights.get(metric.name, "")
        metric_name = f"{metric.name}\n({weight})"

        score_color = get_score_color(metric.score)

        # Add the row
        html += f"""
            <tr>
                <td class="metric-name-cell">{metric_name}</td>
                <td class="score-cell" style="color: {score_color};">{metric.score}/100</td>
                <td class="rationale-cell">{metric.rationale}</td>
                <td class="suggestion-cell">{metric.suggestion}</td>
            </tr>
        """

    # Close the table
    html += """
        </tbody>
    </table>
    """

    return html


def count_visual_lines(text: str, chars_per_line: int = 80) -> int:
    """
    Approximate how many lines the text will take in the textarea,
    given an average chars_per_line before wrapping.
    """
    if not text:
        return 1
    return sum(math.ceil(len(line) / chars_per_line) for line in text.split("\n"))


def validate_review_text(text: str) -> tuple[bool, str]:
    """
    Simple validation for review text input.

    Args:
        text: The review text to validate

    Returns:
        tuple: (is_valid, error_message)
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

    This function is used when the server sends delta updates instead of full state snapshots.
    It merges the delta changes into the existing destination dictionary, creating a new
    dictionary to avoid mutating the original. This is essential for handling incremental
    updates from the LangGraph streaming mode.

    The function handles None inputs gracefully and ensures that the destination dictionary
    is never modified in place, which is important for Streamlit's session state management.

    Args:
        dst (Dict[str, Any]): Destination dictionary to merge into (will be copied to avoid mutation)
        delta (Dict[str, Any]): Dictionary containing updates to apply

    Returns:
        Dict[str, Any]: New dictionary with merged state

    Example:
        >>> patch_state({"a": 1, "b": 2}, {"b": 3, "c": 4})
        {"a": 1, "b": 3, "c": 4}

    Note:
        - Both dst and delta can be None, which will be handled gracefully
        - The function creates a shallow copy, so nested dictionaries are not deep-copied
        - This is intentional for performance and matches the expected behavior for state updates
    """
    # Create a copy to avoid mutating the original destination
    # Handle None case by providing empty dict as default
    dst = dict(dst or {})
    # Apply each key-value pair from the delta
    # Handle None delta case by providing empty dict as default
    for k, v in (delta or {}).items():
        dst[k] = v
    return dst


def sse_events(url: str, data: Dict[str, Any]):
    """
    Minimal Server-Sent Events (SSE) client using the requests library.

    This function establishes an HTTP connection to the server and yields decoded JSON payloads
    from lines that start with 'data:'. It's the core function that drives the server-side
    LangGraph execution because the /stream endpoint calls graph.astream(...).

    The function implements a robust SSE client that handles various edge cases and provides
    real-time streaming of LangGraph workflow execution. It's designed to be resilient to
    network issues and malformed data while maintaining a stable connection.

    SSE Format: The server sends data in the format:
        data: {"message": "Hello"}
        data: {"message": "World"}

    Args:
        url (str): The SSE endpoint URL to connect to (typically /stream endpoint)
        data (Dict[str, Any]): Data to send with the request containing:
            - thread_id: Unique conversation identifier
            - review_text: The text to process through the workflow
            - mode: Streaming mode ("values" or "updates")

    Yields:
        Dict[str, Any]: Parsed JSON objects from the SSE stream representing workflow events

    Raises:
        requests.RequestException: For HTTP errors, connection issues, or timeouts
        json.JSONDecodeError: For malformed JSON in the stream (handled gracefully)

    Note:
        - Uses POST request to handle large review text data in the request body
        - Uses decode_unicode=False to get raw bytes for proper SSE parsing
        - Handles malformed lines gracefully by catching exceptions and continuing
        - Times out after 600 seconds to prevent hanging connections
        - Maintains connection stability by ignoring bad lines rather than failing
        - The generator pattern allows for memory-efficient streaming of large datasets
    """
    # Establish streaming HTTP connection with timeout using POST
    # POST is used instead of GET to handle large review text data in the request body
    with requests.post(url, json=data, stream=True, timeout=600) as resp:
        # Raise exception for HTTP error status codes (4xx, 5xx)
        # This ensures we fail fast on server errors rather than processing error responses
        resp.raise_for_status()

        # Iterate through response lines as raw bytes (not decoded to unicode)
        # This is crucial for proper SSE parsing as we need to handle the "data:" prefix
        for raw in resp.iter_lines(decode_unicode=False):
            # Skip empty lines and None values (SSE event boundaries)
            # SSE uses blank lines to separate events, so we ignore them
            if raw is None or not raw:
                # SSE event boundary (blank line) — ignore
                continue

            # Check if line starts with "data:" prefix (standard SSE format)
            # Only process lines that contain actual data payloads
            if raw.startswith(b"data:"):
                try:
                    # Extract payload: remove "data:" prefix, strip whitespace, decode to UTF-8
                    # The prefix is exactly 5 bytes ("data:"), so we slice from index 5
                    payload = raw[len(b"data:") :].strip().decode("utf-8")
                    if payload:
                        # Parse JSON and yield the resulting object
                        # This converts the string payload into a Python dictionary
                        yield json.loads(payload)
                except Exception:
                    # Ignore malformed lines; keep streaming to maintain connection
                    # This prevents one bad line from breaking the entire stream
                    # Common issues: invalid JSON, encoding problems, truncated data
                    pass


def extract_values_from_event(ev: Dict[str, Any]) -> Dict[str, Any] | None:
    """
    Extracts the actual state values from various LangGraph event formats.

    LangGraph events can have different structures depending on the configuration,
    streaming mode, and server implementation. This function provides robust handling
    for multiple event formats to ensure compatibility across different setups.

    The function implements a hierarchical checking strategy that looks for state
    data in common locations, falling back to pattern matching for custom formats.
    This approach ensures maximum compatibility while maintaining performance.

    Supported Event Formats:
    - Standard LangGraph: {"values": {...}} or {"data": {"values": {...}}}
    - State wrapper: {"state": {...}} or {"data": {"state": {...}}}
    - Direct format: {"original_text": "...", "copy_edited_text": "...", ...}
    - Custom wrappers: Various nested structures

    Args:
        ev (Dict[str, Any]): Raw event dictionary from the SSE stream

    Returns:
        Dict[str, Any] | None: Extracted state dictionary containing workflow data,
            or None if no valid state structure is found

    Note:
        The function checks multiple common patterns to be robust against
        different LangGraph event formats and server configurations. It uses
        set intersection for efficient key matching and type checking for
        safe dictionary access.
    """
    # Validate input is a dictionary to prevent type errors
    if not isinstance(ev, dict):
        return None

    # Pattern A: Standard LangGraph wrapper formats
    # These are the most common formats used by LangGraph in different modes

    # Check if state is wrapped in "values" field (common in "values" mode)
    if isinstance(ev.get("values"), dict):
        return ev["values"]
    # Check if state is wrapped in "data.values" nested structure (some server configs)
    if isinstance(ev.get("data"), dict) and isinstance(ev["data"].get("values"), dict):
        return ev["data"]["values"]
    # Check if state is wrapped in "state" field (alternative naming)
    if isinstance(ev.get("state"), dict):
        return ev["state"]
    # Check if state is wrapped in "data.state" nested structure (nested alternative)
    if isinstance(ev.get("data"), dict) and isinstance(ev["data"].get("state"), dict):
        return ev["data"]["state"]

    # Pattern B: Custom server format - state is at TOP LEVEL
    # This handles cases where the server sends the state directly without wrapping
    # Define expected keys that indicate this is a GraphState object
    expected_keys = {
        "original_text",
        "copy_edited_text",
        "summary",
        "word_cloud_path",
        "achievements",
        "review_scorecard",
        "review_complete",
    }
    # If any of these expected keys exist, treat the whole event as the current state
    # Using set intersection for efficient key checking
    if expected_keys.intersection(ev.keys()):
        return ev  # treat the whole event as the current state

    # No valid state found - return None to indicate no state data in this event
    return None


def populate_tabs(tabs, graph_completed: bool, current: dict, review_validation_container) -> str:
    """
    Populate the tabbed interface with content based on graph execution status.

    This function handles the content for all tabs, showing appropriate content
    based on whether the graph execution has completed and what data is available.

    Args:
        tabs: The Streamlit tabs object
        graph_completed (bool): Whether the graph execution has completed
        current (dict): Current session state data
        review_validation_container: Container for review validation messages

    Returns:
        str: The review text from the first tab
    """
    # =============================================================================
    # TAB 1: REVIEW TEXT INPUT
    # =============================================================================
    with tabs[0]:
        # Create radio button for mode selection
        mode = st.radio("Choose mode:", ["📝 Edit", "👁️ View"], horizontal=True)
        review_text = st.session_state.current_review_text
        if mode == "📝 Edit":
            st.subheader("📝 Enter Your Review Text in Markdown Format")
            review_text = st_ace(
                value=st.session_state.current_review_text,
                language="markdown",
                theme="monokai",
                key="markdown_editor",
                height=min(
                    max(100, count_visual_lines(st.session_state.current_review_text) * 20 + 60),
                    800,
                ),
                auto_update=True,
                wrap=True,
                font_size=14,
            )
        else:
            st.subheader("📝 Review Text Preview")
            st.markdown(st.session_state.current_review_text, unsafe_allow_html=True)

        # Validate input and show feedback
        is_valid, validation_message = validate_review_text(review_text)
        if not is_valid:
            review_validation_container.warning(f"⚠️ {validation_message}")

        # Handle review text changes - automatic state management
        # When content changes, we need to reset the session to prevent mixing old and new data
        if review_text != st.session_state.current_review_text:
            st.session_state.current_review_text = review_text
            # Generate new thread ID for clean separation between different content
            st.session_state.thread_id = str(uuid.uuid4())
            # Clear previous state to prevent data contamination from old content
            st.session_state.state = {}
            # Clear previous events for clean debugging of new content
            st.session_state.events = []
            # Clear previous progress steps to prevent accumulation of old steps
            st.session_state.progress_steps = []

    # =============================================================================
    # TAB 2: COPY-EDITED TEXT
    # =============================================================================
    with tabs[1]:
        if graph_completed and current.get("copy_edited_text"):
            st.subheader("📝 Rationalized Text")
            st.markdown(current["copy_edited_text"], unsafe_allow_html=True)
        else:
            st.info("⏳ Copy-edited text will appear here after graph execution completes.")
            if not graph_completed:
                st.caption(
                    "💡 Complete the review text input and click 'Start & Stream' to begin processing."
                )

    # =============================================================================
    # TAB 3: SUMMARY
    # =============================================================================
    with tabs[2]:
        if graph_completed and current.get("summary"):
            st.subheader("📋 Summary")
            st.markdown(safe_markdown(current["summary"]), unsafe_allow_html=True)
        else:
            st.info("⏳ Summary will appear here after graph execution completes.")
            if not graph_completed:
                st.caption(
                    "💡 Complete the review text input and click 'Start & Stream' to begin processing."
                )

    # =============================================================================
    # TAB 4: WORD CLOUD
    # =============================================================================
    with tabs[3]:
        if graph_completed and current.get("word_cloud_path"):
            st.subheader("🖼️ Word Cloud")
            try:
                import os

                if os.path.exists(current["word_cloud_path"]):
                    st.image(
                        current["word_cloud_path"],
                        caption="Final Generated Word Cloud",
                        width="stretch",
                    )
                else:
                    st.warning(
                        f"⚠️ Word cloud image not found at final path: {current['word_cloud_path']}"
                    )
            except Exception as e:
                st.error(f"❌ Error displaying final word cloud: {e}")
        else:
            st.info("⏳ Word cloud will appear here after graph execution completes.")
            if not graph_completed:
                st.caption(
                    "💡 Complete the review text input and click 'Start & Stream' to begin processing."
                )

    # =============================================================================
    # TAB 5: ACHIEVEMENTS
    # =============================================================================
    with tabs[4]:
        if graph_completed and current.get("achievements"):
            st.subheader("🏆 Achievements")
            try:
                achievements_data = current["achievements"]
                achievements = None

                # Handle both dict and string representations of achievements
                if isinstance(achievements_data, dict):
                    achievements = AchievementsList(**achievements_data)
                else:
                    st.write("⚠️ Achievements data not parse-able")
                    st.write(achievements_data)

                # Only display the achievements if we successfully parsed them
                if achievements is not None:
                    # Render the summary panel as HTML
                    summary_panel = create_summary_panel(achievements)
                    render_rich(summary_panel)

                    display_achievements_table(achievements)

            except Exception as e:
                st.error(f"❌ Error displaying final achievements: {e}")
        else:
            st.info("⏳ Achievements will appear here after graph execution completes.")
            if not graph_completed:
                st.caption(
                    "💡 Complete the review text input and click 'Start & Stream' to begin processing."
                )

    # =============================================================================
    # TAB 6: REVIEW SCORECARD
    # =============================================================================
    with tabs[5]:
        if graph_completed and current.get("review_scorecard"):
            st.subheader("📊 Review Scorecard")
            try:
                review_scorecard_data = current["review_scorecard"]
                review_scorecard = None

                # Handle both dict and string representations of review scorecard
                if isinstance(review_scorecard_data, dict):
                    review_scorecard = ReviewScorecard(**review_scorecard_data)
                else:
                    st.write("⚠️ Review scorecard data not parse-able")
                    st.write(review_scorecard_data)

                # Only display the review scorecard if we successfully parsed it
                if review_scorecard is not None:
                    # Render the radar plot (this should be a Plotly figure)
                    st.plotly_chart(create_radar_plot(review_scorecard.model_dump()))

                    # Render the radar chart info as HTML
                    radar_info = create_radar_chart_info(review_scorecard)
                    render_rich(radar_info)

                    # Render the evaluation summary panel as HTML
                    eval_summary_panel = create_summary_panel_evaluation(review_scorecard)
                    render_rich(eval_summary_panel)

                    # Display the metrics table using HTML table with text wrapping
                    display_metrics_table(review_scorecard)

            except Exception as e:
                st.error(f"❌ Error displaying final review scorecard: {e}")
        else:
            st.info("⏳ Review scorecard will appear here after graph execution completes.")
            if not graph_completed:
                st.caption(
                    "💡 Complete the review text input and click 'Start & Stream' to begin processing."
                )

    return review_text
