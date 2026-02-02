# =============================================================================
#  Filename: streamlit_ui.py
#
#  Short Description: Streamlit UI for the self-reviewer agent(s) for the periodic
#                     employee self-review process.
#
#  Creation date: 2025-09-01
#  Author: Chandar L
# =============================================================================

"""
Streamlit User Interface for Self-Review Processing

This module provides a web-based user interface for interacting with
the self-reviewer agent workflow. It implements real-time streaming capabilities
using Server-Sent Events (SSE) to provide live updates during text processing.

Key Features:
- Real-time streaming of LangGraph workflow execution
- Interactive text input and processing controls
- Live progress monitoring and result display
- Debug information and event inspection
- Session state management for conversation persistence
- Responsive UI with dynamic content updates

Architecture:
- Streamlit frontend with session state management
- SSE client for real-time communication with FastAPI backend
- Event-driven UI updates during workflow execution
- Robust error handling and connection management
- Multi-column layout for optimal information display

The interface serves as a monitoring and interaction tool for the LangGraph
workflow, providing both user-friendly controls and detailed debugging
capabilities for developers and power users.
"""

# Standard library imports for JSON handling, timing, and unique ID generation
import json  # JSON serialization/deserialization for event data
import os  # Operating system functions for file paths
import time  # Timestamp generation and timing operations
import uuid  # Unique identifier generation for session management

# Third-party imports for HTTP requests and web UI framework
import requests  # HTTP client for SSE streaming and API communication
import streamlit as st  # Web UI framework for building interactive applications
from dotenv import load_dotenv  # Load environment variables from .env file

from metamorphosis.ui.streamlit_ui_helpers import (
    extract_values_from_event,
    patch_state,
    populate_tabs,
    sse_events,
    validate_review_text,
)

load_dotenv()

# =============================================================================
# CONFIGURATION SECTION
# =============================================================================

# Base URL for the FastAPI backend service that runs LangGraph workflows / G-ADK Agent service
# This should match the host and port where the agent_service.py is running
SERVICE_BASE = "http://localhost:8000"
# Endpoint for streaming Server-Sent Events (SSE) from the LangGraph execution
# This connects to the /stream endpoint in the FastAPI service
STREAM_URL = f"{SERVICE_BASE}/stream"

# Configure Streamlit page settings for optimal display
# Wide layout provides more space for the multi-column interface
st.set_page_config(page_title="Employee Self-Review", layout="wide")

# =============================================================================
# SIMPLE CONFIGURATION CONSTANTS
# =============================================================================

# Performance optimization constants
MAX_EVENTS = 50  # Reduced from 200 for better memory usage

# =============================================================================
# STREAMLIT SESSION STATE INITIALIZATION
# =============================================================================

# Version check to force reset when code changes
# This ensures that session state is reset when the application is updated
APP_VERSION = "1.1.0"  # Increment this when you want to force a session reset

# Check if this is a new version and reset session state if needed
if "app_version" not in st.session_state or st.session_state.app_version != APP_VERSION:
    # Clear all session state for new version
    for key in list(st.session_state.keys()):
        del st.session_state[key]
    st.session_state.app_version = APP_VERSION

# Initialize persistent session state variables that survive Streamlit reruns
# These maintain state between user interactions and streaming updates

# Unique identifier for each conversation thread (resets when review title changes)
# This ensures state isolation between different review sessions
if "thread_id" not in st.session_state:
    st.session_state.thread_id = str(uuid.uuid4())

# Current LangGraph state - gets updated with each streaming event
# This stores the latest merged state from the workflow execution
if "state" not in st.session_state:
    st.session_state.state = {}  # latest GraphState (merged)

# Current review title for the LangGraph workflow (default example review title)
# This provides a user-friendly identifier for the review session
if "current_review_title" not in st.session_state:
    st.session_state.current_review_title = "Self-review Q1–Q2 / H1 2025"  # default

# Current review text content that will be processed by the workflow
# This stores the user's input and gets sent to the LangGraph for processing
if "current_review_text" not in st.session_state:
    # Load default review text from sample file
    try:
        root_dir = os.getenv("PROJECT_ROOT_DIR")
        sample_file_path = os.path.join(root_dir, "sample_reviews", "poor_review.md") # data_engineer_review.md
        print(f"Loading review text from {sample_file_path}")
        with open(sample_file_path, 'r', encoding='utf-8') as f:
            st.session_state.current_review_text = f.read().strip()
    except Exception:
        # Fallback to a simple default if file reading fails
        st.session_state.current_review_text = """I had an eventful cycle this summer.  Learnt agentic workflows and implemented a self-reviewer agent 
        for the periodic employee self-review process.  It significantly improved employee productivity for the organization."""

# Timestamp of last state update (for display purposes)
# This tracks when the workflow state was last modified for UI feedback
if "last_update" not in st.session_state:
    st.session_state.last_update = 0.0

# Flag indicating if streaming is currently active
# This controls the main streaming loop and UI state display
if "running" not in st.session_state:
    st.session_state.running = False

# Buffer of recent raw events for debugging (keeps last MAX_EVENTS events)
# This maintains a rolling history of SSE events for troubleshooting
if "events" not in st.session_state:
    st.session_state.events = []  # recent raw events (debug)

# Track which results have been displayed to prevent duplicates
if "results_displayed" not in st.session_state:
    st.session_state.results_displayed = {
        "copy_edited": False,
        "summary": False,
        "word_cloud": False,
        "achievements": False,
        "review_scorecard": False,
    }

# =============================================================================
# USER INTERFACE - CONTROL PANEL
# =============================================================================

# Main application title with emoji for visual appeal
st.title("🐾 Employee Self-Review Wizard")

# Sidebar for user controls - provides dedicated space for configuration options
with st.sidebar:
    st.header("Run Controls")

    # Review title input field - allows users to customize their session identifier
    # This provides a user-friendly way to organize different review sessions
    review_title = st.text_input(
        label="Review Title",
        value=st.session_state.current_review_title,
        key="review_title_input",
        placeholder="Enter a title for your review session",
    )

    # Streaming mode selection - controls how data is received from the server
    # "values" mode provides complete state snapshots, "updates" mode provides deltas
    mode = st.radio(
        "Stream mode",
        options=["values", "updates"],
        index=0,
        help="Use 'values' for full state snapshots per step, or 'updates' for deltas.",
    )

    # Review title change detection and cleanup
    # If user changed review title, reset thread and state for isolation
    # This ensures clean separation between different review sessions
    if review_title != st.session_state.current_review_title:
        st.session_state.current_review_title = review_title
        # Generate new thread ID for clean separation
        st.session_state.thread_id = str(uuid.uuid4())
        # Clear previous state to prevent data contamination
        st.session_state.state = {}
        # Clear previous events for clean debugging
        st.session_state.events = []
        # Clear previous progress steps to prevent accumulation of old steps
        st.session_state.progress_steps = []

    # Start button - initiates the LangGraph workflow and streaming
    # Primary button with visual emphasis to indicate main action
    start_btn = st.button("▶️ Start & Stream", width="stretch", type="primary")

    # Stop button - stops the client-side streaming loop
    # Allows users to interrupt long-running processes
    stop_btn = st.button("⏹️ Stop (client-side)", width="stretch")
    
    # Reset button - clears all session state and reloads defaults
    # Useful for testing or when you want to start fresh
    reset_btn = st.button("🔄 Reset Session", width="stretch", type="secondary")

    # Handle start button click - initialize new workflow execution
    if start_btn:
        # Validate input before starting
        is_valid, validation_message = validate_review_text(st.session_state.current_review_text)
        if not is_valid:
            st.error(f"❌ Cannot start: {validation_message}")
        else:
            st.session_state.running = True  # Enable streaming loop
            st.session_state.state = {}  # Clear previous results
            st.session_state.events = []  # Clear event history
            st.session_state.last_update = time.time()  # Reset timestamp
            # Reset results display tracking for new run
            st.session_state.results_displayed = {
                "copy_edited": False,
                "summary": False,
                "word_cloud": False,
                "achievements": False,
                "review_scorecard": False,
            }

    # Handle stop button click - gracefully terminate streaming
    if stop_btn:
        # This just stops the client loop; the server run will end on its own.
        # The server continues running until the LangGraph workflow completes
        # This prevents resource waste while allowing server-side cleanup
        st.session_state.running = False

    # Handle reset button click - clear all session state and reload defaults
    if reset_btn:
        # Clear all session state
        for key in list(st.session_state.keys()):
            del st.session_state[key]
        # Set the app version to trigger reinitialization
        st.session_state.app_version = APP_VERSION
        # Force a rerun to reinitialize everything
        st.rerun()

    review_validation_container = st.container()
    status_container = st.container()
    progress_container = st.container()
    progress_container.subheader("📊 Progress Status")
    progress_steps = [] if "progress_steps" not in st.session_state else st.session_state.progress_steps
    st.session_state.progress_steps = progress_steps
# =============================================================================
# USER INTERFACE - MAIN INPUT PANEL
# =============================================================================

# =============================================================================
# TABBED INTERFACE - MAIN CONTENT AREA
# =============================================================================

# Check if graph execution has completed to determine which tabs are available
current = st.session_state.state or {}
graph_completed = any(k in current for k in ["copy_edited_text", 
"summary", 
"word_cloud_path", 
"achievements", 
"review_scorecard", 
"review_complete"])

# Define tab labels and their availability
tab_labels = [
    "📝 Review Text",
    "📝 Rationalized Text", 
    "📋 Summary",
    "🖼️ Word Cloud",
    "🏆 Achievements",
    "📊 Review Scorecard"
]

tabs = st.tabs(tab_labels)

# Populate tabs with content - called at the beginning
review_text = populate_tabs(tabs, graph_completed, current, review_validation_container)

# =============================================================================
# USER INTERFACE - STATUS DISPLAY
# =============================================================================

# Display current application status with context-aware messaging
if st.session_state.running:
    # Active streaming state - inform user that processing is ongoing
    status_container.info("🔄 **Streaming run in progress…**")
else:
    if st.session_state.state:
        # Completed state - previous run finished with results
        status_container.success("✅ **Last run finished**")
    else:
        # Ready state - waiting for user to start processing
        status_container.info("⏸️ **Ready** — enter your review text and click Start in the sidebar")

# =============================================================================
# USER INTERFACE - STREAMING EVENTS EXPANDER
# =============================================================================

# Final results are now displayed in the tabbed interface above

# Collapsible section for streaming events debug information
# This provides developers with insight into the event structure and data flow
with st.expander("🔍 Streaming Events", expanded=False):
    events_container = st.container()  # raw event display for debugging

# =============================================================================
# USER INTERFACE - MAIN CONTENT AREA (FULL WIDTH)
# =============================================================================

# Main content area using full width of the screen
# Results section - dynamic content area for processing outputs
with st.expander("✨ Processing Results", expanded=False):
    processing_results_container = st.container()

# Create containers for dynamic content that will be updated during streaming
# Using containers instead of empty placeholders to avoid key conflicts
# Containers allow for dynamic content updates without Streamlit key issues
copy_edited_container = processing_results_container.container()  # Copy-edited text display
summary_container = processing_results_container.container()  # Summary text display
word_cloud_path_container = processing_results_container.container()  # Word cloud path display
word_cloud_image_container = processing_results_container.container()  # Word cloud image display
achievements_container = processing_results_container.container()  # Achievements dictionary display
review_scorecard_container = processing_results_container.container()  # Review scorecard dictionary display

# =============================================================================
# MAIN STREAMING LOOP
# =============================================================================
    
# This is the core of the application - the streaming loop that processes events
# If running, drive the stream (this call blocks the script until the server finishes or user stops)
if st.session_state.running:
    try:
        # Prepare data for the streaming request
        # This data will be sent to the FastAPI /stream endpoint
        data = {
            "thread_id": st.session_state.thread_id,  # Unique conversation identifier for state persistence
            "review_text": st.session_state.current_review_text,  # What the agent should work on
            "mode": mode,  # Streaming mode (values vs updates)
        }

        # Track the most recent event for debug display
        # This allows us to show the latest event in the debug panel
        recent_event = None

        # Main streaming loop - processes each event from the SSE stream
        # This loop runs until the server completes the workflow or user stops
        for ev in sse_events(STREAM_URL, data):
            # Check if user hit Stop button during streaming
            # This allows graceful termination of the streaming process
            if not st.session_state.running:
                # user hit Stop — exit the loop
                break

            # Add event to history buffer (for debugging)
            # Maintain a rolling history of events for troubleshooting
            st.session_state.events.append(ev)
            # Keep only last MAX_EVENTS to prevent memory issues
            # This prevents unbounded memory growth during long sessions
            if len(st.session_state.events) > MAX_EVENTS:
                st.session_state.events = st.session_state.events[-MAX_EVENTS:]

            # =================================================================
            # STATE UPDATE LOGIC (Robust handling of different event formats)
            # =================================================================

            # Strategy 1: Prefer full snapshots (values/state) if present
            # This handles mode="values" and provides complete state
            # Full snapshots are preferred as they provide the most complete state information
            values = extract_values_from_event(ev)
            if values is not None:
                st.session_state.state = values

            # Strategy 2: Also merge deltas if present (covers mode="updates" or mixed shapes)
            # This handles incremental updates and merges them into existing state
            # Delta updates are useful for efficiency but require careful merging
            if "updates" in ev and isinstance(ev["updates"], dict):
                # Direct updates field - most common format for delta updates
                st.session_state.state = patch_state(st.session_state.state, ev["updates"])
            elif isinstance(ev.get("data"), dict) and isinstance(ev["data"].get("updates"), dict):
                # Nested updates in data field - alternative format for some configurations
                st.session_state.state = patch_state(st.session_state.state, ev["data"]["updates"])

            # Update timestamp for display purposes
            # This tracks when the state was last modified for UI feedback
            st.session_state.last_update = time.time()
            # Track most recent event for debug display
            # This allows the debug panel to show the latest event structure
            recent_event = ev

            # =================================================================
            # REAL-TIME UI RENDERING (Live updates during streaming)
            # =================================================================

            # Get current state for display (use empty dict if none)
            # This ensures we always have a valid dictionary for display operations
            current = st.session_state.state or {}
            graph_completed = any(k in current for k in [
                "copy_edited_text", 
                "summary", 
                "word_cloud_path", 
                "achievements", 
                "review_scorecard", 
                "review_complete"])

            # Clear previous content in containers to avoid duplication
            # This prevents content from accumulating during streaming updates
            # Note: Individual containers are cleared before each update below

            # Display copy-edited text as a non-editable text area
            # This shows the grammar and clarity improved version of the input text
            copy_edited_text = current.get("copy_edited_text", "Not yet processed")

            if (
                copy_edited_text != "Not yet processed"
                and not st.session_state.results_displayed["copy_edited"]
            ):
                # Result is available and not yet displayed - show it
                copy_edited_container.empty()  # Clear any previous content
                copy_edited_container.text_area(
                    "📝 Copy-Edited Text",
                    value=copy_edited_text,
                    height=None,
                    disabled=True,  # Read-only display
                    help="This is the copy-edited version of your review text, returned by the LangGraph agent.",
                    key=f"copy_edited_{st.session_state.thread_id}",  # Fixed key - no timestamp
                )
                st.session_state.results_displayed["copy_edited"] = True

            # Display summary as a non-editable text area
            # This shows the abstractive summary of the review content
            summary = current.get("summary", "Not yet processed")

            if summary != "Not yet processed" and not st.session_state.results_displayed["summary"]:
                # Result is available and not yet displayed - show it
                summary_container.empty()  # Clear any previous content
                summary_container.text_area(
                    "📋 Summary",
                    value=summary,
                    height=None,
                    disabled=True,  # Read-only display
                    help="This is the summary of your review text, generated by the LangGraph agent.",
                    key=f"summary_{st.session_state.thread_id}",  # Fixed key - no timestamp
                )
                st.session_state.results_displayed["summary"] = True

            # Display word cloud path and image
            # This shows both the file path and the actual generated word cloud image
            word_cloud_path = current.get("word_cloud_path", "Not yet processed")

            if (
                word_cloud_path != "Not yet processed"
                and not st.session_state.results_displayed["word_cloud"]
            ):
                # Result is available and not yet displayed - show it
                word_cloud_path_container.empty()  # Clear any previous content
                word_cloud_path_container.write(f"**🖼️ Word Cloud Path:** `{word_cloud_path}`")

                # Try to display the wordcloud image if the path exists
                # This provides visual feedback of the word cloud generation
                try:
                    import os

                    if os.path.exists(word_cloud_path):
                        word_cloud_image_container.image(
                            word_cloud_path,
                            caption="Generated Word Cloud",
                            width="stretch",  # Responsive width
                        )
                    else:
                        word_cloud_image_container.warning(
                            f"⚠️ Word cloud image not found at path: {word_cloud_path}"
                        )
                except Exception as e:
                    word_cloud_image_container.error(f"❌ Error displaying word cloud: {e}")
                st.session_state.results_displayed["word_cloud"] = True

            # Display achievements dictionary
            # This shows the extracted achievements from the review text
            achievements = current.get("achievements", "Not yet processed")

            if (
                achievements != "Not yet processed"
                and not st.session_state.results_displayed["achievements"]
            ):
                # Result is available and not yet displayed - show it
                achievements_container.empty()  # Clear any previous content
                achievements_container.subheader("🏆 Achievements")
                if isinstance(achievements, dict):
                    # Display as a nicely formatted dictionary
                    achievements_container.json(achievements)
                else:
                    # Fallback for non-dict values
                    achievements_container.write(str(achievements))
                st.session_state.results_displayed["achievements"] = True

            # Display review scorecard dictionary
            # This shows the review scorecard evaluation results
            review_scorecard = current.get("review_scorecard", "Not yet processed")

            if (
                review_scorecard != "Not yet processed"
                and not st.session_state.results_displayed["review_scorecard"]
            ):
                # Result is available and not yet displayed - show it
                review_scorecard_container.empty()  # Clear any previous content
                review_scorecard_container.subheader("📊 Review Scorecard")
                if isinstance(review_scorecard, dict):
                    # Display as a nicely formatted dictionary
                    review_scorecard_container.json(review_scorecard)
                else:
                    # Fallback for non-dict values
                    review_scorecard_container.write(str(review_scorecard))
                st.session_state.results_displayed["review_scorecard"] = True

            # =================================================================
            # DEBUG DISPLAY (Raw event information)
            # =================================================================

            # Show the most recent raw event for debugging purposes
            # This provides developers with insight into the event structure and data flow
            try:
                events_container.code(
                    json.dumps(recent_event, indent=2),
                    key=f"debug_event_{st.session_state.thread_id}_{int(time.time())}",
                )
            except Exception:
                # Fallback if JSON serialization fails
                # This handles cases where the event contains non-serializable objects
                events_container.write(str(recent_event))

        # =================================================================
        # STREAMING COMPLETION
        # =================================================================

        # If the for-loop ends naturally (no break), consider execution completed
        # This indicates that the server has finished processing and closed the connection
        st.session_state.running = False

        # Display final progress in the main area
        # This provides a summary of what was completed during the workflow execution
        # Check each workflow step and show completion status
        progress_steps.append(
            "✅ Copy Editing"
            if current.get("copy_edited_text") is not None
            else "⏳ Copy Editing"
        )
        progress_steps.append(
            "✅ Summarization" if current.get("summary") is not None else "⏳ Summarization"
        )
        progress_steps.append(
            "✅ Word Cloud Generation"
            if current.get("word_cloud_path") is not None
            else "⏳ Word Cloud Generation"
        )
        progress_steps.append(
            "✅ Achievements Extraction"
            if current.get("achievements") is not None
            else "⏳ Achievements Extraction"
        )
        progress_steps.append(
            "✅ Review Scorecard"
            if current.get("review_scorecard") is not None
            else "⏳ Review Scorecard"
        )
        st.session_state.progress_steps = progress_steps
        # Re-populate tabs with updated data after graph execution completes
        # This ensures all tabs show the latest results
        st.rerun()  # This will trigger a rerun and call populate_tabs again with updated data

    except requests.RequestException as e:
        # Handle HTTP/network errors
        # This covers connection issues, timeouts, and server errors
        st.session_state.running = False
        st.error(f"Stream error: {e}")
    except Exception as e:
        # Handle any other unexpected errors
        # This is a catch-all for any other issues that might occur
        st.session_state.running = False
        st.error(f"Unexpected error: {e}")

# =============================================================================
# FINAL RENDERING AND PERSISTENT INFORMATION
# =============================================================================
if len(st.session_state.progress_steps) > 0:
    progress_container.write("**Progress:** ")
    for step in st.session_state.progress_steps:
        progress_container.write(f"• {step}")

graph_all_completed = all(k in current for k in [
    "copy_edited_text", 
    "summary", 
    "word_cloud_path", 
    "achievements", 
    "review_scorecard", 
    "review_complete"])

if graph_all_completed:
    if current["review_complete"]:
        progress_container.success("✅ **Self-Reviewer Wizard completed successfully!**")
    else:
        progress_container.error("❌ **There were issues found with the self-review text. Please study and fix these:**")
        progress_container.warning("⚠️ **Issue:** There were too few achievements found.")
        progress_container.warning("💡 **Solution:** Elaborate on the details and add measurable achievements. Then try again.")
elif graph_completed:
    progress_container.error("❌ **Some steps of the Self-Reviewer Wizard did not complete successfully**")
else:
    progress_container.info("▶️ **Self-Reviewer Wizard has not run yet. Please click 'Start & Stream' to begin processing.**")

# Get current state for final display
# This ensures we have the latest state data for the summary display
current = st.session_state.state or {}

# Show last update timestamp if available
# This provides temporal context for when the results were generated
if st.session_state.last_update > 0:
    progress_container.caption(
        f"Last updated: {time.strftime('%H:%M:%S', time.localtime(st.session_state.last_update))}"
    )

# =============================================================================
# DEBUG SECTION - RAW JSON DATA
# =============================================================================

# Show the raw JSON for debugging in a collapsible section
# This provides developers with access to the complete state data
with st.expander("🔍 Raw JSON Data", expanded=False):
    json_container = st.container()
    json_container.json(current)

