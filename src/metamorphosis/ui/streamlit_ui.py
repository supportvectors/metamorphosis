# =============================================================================
#  Filename: streamlit_ui.py
#
#  Short Description: Streamlit UI for the self-reviewer agent(s) for the periodic employee self-review process.
#
#  Creation date: 2025-09-01
#  Author: Chandar L
# =============================================================================

import json
import time
import uuid
from typing import Dict, Any

import requests
import streamlit as st

# =============================================================================
# CONFIGURATION SECTION
# =============================================================================

# Base URL for the FastAPI backend service that runs LangGraph workflows
SERVICE_BASE = "http://localhost:8000"  
# Endpoint for streaming Server-Sent Events (SSE) from the LangGraph execution
STREAM_URL = f"{SERVICE_BASE}/stream"

# Configure Streamlit page settings
st.set_page_config(page_title="LangGraph Monitor", layout="wide")

# =============================================================================
# UTILITY FUNCTIONS
# =============================================================================

def patch_state(dst: Dict[str, Any], delta: Dict[str, Any]) -> Dict[str, Any]:
    """
    Performs a shallow merge of two dictionaries for 'updates' mode.
    
    This function is used when the server sends delta updates instead of full state snapshots.
    It merges the delta changes into the existing destination dictionary.
    
    Args:
        dst: Destination dictionary to merge into (will be copied to avoid mutation)
        delta: Dictionary containing updates to apply
        
    Returns:
        New dictionary with merged state
        
    Example:
        patch_state({"a": 1, "b": 2}, {"b": 3, "c": 4}) 
        -> {"a": 1, "b": 3, "c": 4}
    """
    # Create a copy to avoid mutating the original destination
    dst = dict(dst or {})
    # Apply each key-value pair from the delta
    for k, v in (delta or {}).items():
        dst[k] = v
    return dst

def sse_events(url: str, data: Dict[str, Any]):
    """
    Minimal Server-Sent Events (SSE) client using the requests library.
    
    This function establishes an HTTP connection to the server and yields decoded JSON payloads
    from lines that start with 'data:'. It's the core function that drives the server-side
    LangGraph execution because the /stream endpoint calls graph.astream(...).
    
    SSE Format: The server sends data in the format:
        data: {"message": "Hello"}
        data: {"message": "World"}
        
    Args:
        url: The SSE endpoint URL to connect to
        data: Data to send with the request (thread_id, review_text, mode)
        
    Yields:
        Parsed JSON objects from the SSE stream
        
    Note:
        - Uses POST request to handle large review text data
        - Uses decode_unicode=False to get raw bytes for proper SSE parsing
        - Handles malformed lines gracefully by catching exceptions and continuing
        - Times out after 300 seconds to prevent hanging connections
    """
    # Establish streaming HTTP connection with timeout using POST
    with requests.post(url, json=data, stream=True, timeout=300) as resp:
        # Raise exception for HTTP error status codes
        resp.raise_for_status()
        
        # Iterate through response lines as raw bytes (not decoded to unicode)
        for raw in resp.iter_lines(decode_unicode=False):
            # Skip empty lines and None values (SSE event boundaries)
            if raw is None or not raw:
                # SSE event boundary (blank line) — ignore
                continue
                
            # Check if line starts with "data:" prefix (standard SSE format)
            if raw.startswith(b"data:"):
                try:
                    # Extract payload: remove "data:" prefix, strip whitespace, decode to UTF-8
                    payload = raw[len(b"data:"):].strip().decode("utf-8")
                    if payload:
                        # Parse JSON and yield the resulting object
                        yield json.loads(payload)
                except Exception:
                    # Ignore malformed lines; keep streaming to maintain connection
                    # This prevents one bad line from breaking the entire stream
                    pass

def extract_values_from_event(ev: Dict[str, Any]) -> Dict[str, Any] | None:
    """
    Extracts the actual state values from various LangGraph event formats.
    
    LangGraph events can have different structures depending on the configuration:
    - Some wrap state in "values" field
    - Some wrap state in "data.values" nested structure  
    - Some wrap state in "state" field
    - Some have state at the top level
    
    This function handles all these cases and returns the actual state dictionary.
    
    Args:
        ev: Raw event dictionary from the SSE stream
        
    Returns:
        Extracted state dictionary, or None if no valid state found
        
    Note:
        The function checks multiple common patterns to be robust against
        different LangGraph event formats and server configurations.
    """
    # Validate input is a dictionary
    if not isinstance(ev, dict):
        return None

    # Pattern A: Standard LangGraph wrapper formats
    # Check if state is wrapped in "values" field
    if isinstance(ev.get("values"), dict):
        return ev["values"]
    # Check if state is wrapped in "data.values" nested structure
    if isinstance(ev.get("data"), dict) and isinstance(ev["data"].get("values"), dict):
        return ev["data"]["values"]
    # Check if state is wrapped in "state" field
    if isinstance(ev.get("state"), dict):
        return ev["state"]
    # Check if state is wrapped in "data.state" nested structure
    if isinstance(ev.get("data"), dict) and isinstance(ev["data"].get("state"), dict):
        return ev["data"]["state"]

    # Pattern B: Custom server format - state is at TOP LEVEL
    # Define expected keys that indicate this is a GraphState object
    expected_keys = {"original_text", "copy_edited_text", "summary", "word_cloud_path"}
    # If any of these expected keys exist, treat the whole event as the current state
    if expected_keys.intersection(ev.keys()):
        return ev  # treat the whole event as the current state

    # No valid state found
    return None

# =============================================================================
# STREAMLIT SESSION STATE INITIALIZATION
# =============================================================================

# Initialize persistent session state variables that survive Streamlit reruns
# These maintain state between user interactions and streaming updates

# Unique identifier for each conversation thread (resets when review title changes)
if "thread_id" not in st.session_state:
    st.session_state.thread_id = str(uuid.uuid4())

# Current LangGraph state - gets updated with each streaming event
if "state" not in st.session_state:
    st.session_state.state = {}       # latest GraphState (merged)

# Current review title for the LangGraph workflow (default example review title)
if "current_review_title" not in st.session_state:
    st.session_state.current_review_title = "Employee self-review - cycle 2025"  # default

if "current_review_text" not in st.session_state:
    st.session_state.current_review_text = '''I had an eventful cycle this summer.  Learnt agentic workflows and implemented a self-reviewer agent 
    for the periodic employee self-review process.  It significantly improved employee productivity for the organization.'''  # default

# Timestamp of last state update (for display purposes)
if "last_update" not in st.session_state:
    st.session_state.last_update = 0.0

# Flag indicating if streaming is currently active
if "running" not in st.session_state:
    st.session_state.running = False

# Buffer of recent raw events for debugging (keeps last 200 events)
if "events" not in st.session_state:
    st.session_state.events = []      # recent raw events (debug)

# =============================================================================
# USER INTERFACE - CONTROL PANEL
# =============================================================================

# Main application title
st.title("🐾 LangGraph State Monitor (Streamlit)")

# Sidebar for user controls
with st.sidebar:
    st.header("Run Controls")
    
    # Review title input field
    review_title = st.text_input(
        "Review Title",
        value=st.session_state.current_review_title,
        help="Enter a title for your review session"
    )
    
    # Streaming mode selection
    mode = st.radio(
        "Stream mode",
        options=["values", "updates"],
        index=0,
        help="Use 'values' for full state snapshots per step, or 'updates' for deltas.",
    )

    # Review title change detection and cleanup
    # If user changed review title, reset thread and state for isolation
    if review_title != st.session_state.current_review_title:
        st.session_state.current_review_title = review_title
        # Generate new thread ID for clean separation
        st.session_state.thread_id = str(uuid.uuid4())
        # Clear previous state
        st.session_state.state = {}
        # Clear previous events
        st.session_state.events = []

    # Start button - initiates the LangGraph workflow and streaming
    start_btn = st.button("▶️ Start & Stream", width='stretch', type="primary")
    
    # Stop button - stops the client-side streaming loop
    stop_btn = st.button("⏹️ Stop (client-side)", width='stretch')

    # Handle start button click
    if start_btn:
        st.session_state.running = True
        st.session_state.state = {}
        st.session_state.events = []
        st.session_state.last_update = time.time()

    # Handle stop button click
    if stop_btn:
        # This just stops the client loop; the server run will end on its own.
        # The server continues running until the LangGraph workflow completes
        st.session_state.running = False

# =============================================================================
# USER INTERFACE - MAIN INPUT PANEL
# =============================================================================

# Main review text input area at the top
st.subheader("📝 Enter Your Review Text")
review_text = st.text_area(
    "Review Text",
    value=st.session_state.current_review_text,
    height=300,
    placeholder="Enter your detailed review text here...",
    help="Enter your review text here. This will be processed by the LangGraph agent to generate copy-edited text, summary, and word cloud.",
    key=f"main_review_input_{st.session_state.thread_id}"
)

# Handle review text changes
if review_text != st.session_state.current_review_text:
    st.session_state.current_review_text = review_text
    # Generate new thread ID for clean separation
    st.session_state.thread_id = str(uuid.uuid4())
    # Clear previous state
    st.session_state.state = {}
    # Clear previous events
    st.session_state.events = []

# =============================================================================
# USER INTERFACE - STATUS DISPLAY
# =============================================================================

# Display current application status
if st.session_state.running:
    st.info("🔄 **Streaming run in progress…**")
else:
    if st.session_state.state:
        st.success("✅ **Last run finished**")
    else:
        st.info("⏸️ **Ready** — enter your review text above and click Start in the sidebar")

# =============================================================================
# USER INTERFACE - THREE-COLUMN LAYOUT
# =============================================================================

# Create two columns with left panel wider: input info and debug
input_col, events_col = st.columns([1.5, 1], gap="large")

# Left column: Review title, input info, progress, and results display
with input_col:
    st.subheader("📋 Review Session Info")
    
    # Display review title
    st.text_input(
        "Review Title",
        value=st.session_state.current_review_title,
        disabled=True,
        help="Current review session title",
        key=f"left_title_{st.session_state.thread_id}"
    )
    
    # Display review text preview (first 200 characters)
    review_preview = st.session_state.current_review_text[:200] + "..." if len(st.session_state.current_review_text) > 200 else st.session_state.current_review_text
    st.text_area(
        "Review Text Preview",
        value=review_preview,
        height=100,
        disabled=True,
        help="Preview of the review text being processed",
        key=f"left_preview_{st.session_state.thread_id}"
    )
    
    # Results section
    st.subheader("✨ Processing Results")
    
    # Create containers for dynamic content that will be updated during streaming
    # Using containers instead of empty placeholders to avoid key conflicts
    copy_edited_container = st.container()
    summary_container = st.container()
    word_cloud_path_container = st.container()
    word_cloud_image_container = st.container()

# Right column: Debug information
with events_col:
    st.subheader("🔍 Stream Events (Debug)")
    events_container = st.container()  # raw event display

# =============================================================================
# MAIN STREAMING LOOP
# =============================================================================

# This is the core of the application - the streaming loop that processes events
# If running, drive the stream (this call blocks the script until the server finishes or user stops)
if st.session_state.running:
    try:
        # Prepare data for the streaming request
        data = {
            "thread_id": st.session_state.thread_id,  # Unique conversation identifier
            "review_text": st.session_state.current_review_text,   # What the agent should work on
            "mode": mode,                             # Streaming mode (values vs updates)
        }

        # Track the most recent event for debug display
        recent_event = None

        # Main streaming loop - processes each event from the SSE stream
        for ev in sse_events(STREAM_URL, data):
            # Check if user hit Stop button during streaming
            if not st.session_state.running:
                # user hit Stop — exit the loop
                break

            # Add event to history buffer (for debugging)
            st.session_state.events.append(ev)
            # Keep only last 200 events to prevent memory issues
            if len(st.session_state.events) > 200:
                st.session_state.events = st.session_state.events[-200:]

            # =================================================================
            # STATE UPDATE LOGIC (Robust handling of different event formats)
            # =================================================================
            
            # Strategy 1: Prefer full snapshots (values/state) if present
            # This handles mode="values" and provides complete state
            values = extract_values_from_event(ev)
            if values is not None:
                st.session_state.state = values

            # Strategy 2: Also merge deltas if present (covers mode="updates" or mixed shapes)
            # This handles incremental updates and merges them into existing state
            if "updates" in ev and isinstance(ev["updates"], dict):
                # Direct updates field
                st.session_state.state = patch_state(st.session_state.state, ev["updates"])
            elif isinstance(ev.get("data"), dict) and isinstance(ev["data"].get("updates"), dict):
                # Nested updates in data field
                st.session_state.state = patch_state(st.session_state.state, ev["data"]["updates"])

            # Update timestamp for display purposes
            st.session_state.last_update = time.time()
            # Track most recent event for debug display
            recent_event = ev

            # =================================================================
            # REAL-TIME UI RENDERING (Live updates during streaming)
            # =================================================================
            
            # Get current state for display (use empty dict if none)
            current = st.session_state.state or {}

            # Clear previous content in containers to avoid duplication
            copy_edited_container.empty()
            summary_container.empty()
            word_cloud_path_container.empty()
            word_cloud_image_container.empty()

            # Display copy-edited text as a non-editable text area
            copy_edited_text = current.get('copy_edited_text', 'Not yet processed')
            if copy_edited_text != 'Not yet processed':
                copy_edited_container.text_area(
                    "📝 Copy-Edited Text",
                    value=copy_edited_text,
                    height=200,
                    disabled=True,
                    help="This is the copy-edited version of your review text, returned by the LangGraph agent.",
                    key=f"copy_edited_{st.session_state.thread_id}_{int(time.time())}"
                )
            else:
                copy_edited_container.write(f"**📝 Copy-Edited Text:** `{copy_edited_text}`")

            # Display summary as a non-editable text area
            summary = current.get('summary', 'Not yet processed')
            if summary != 'Not yet processed':
                summary_container.text_area(
                    "📋 Summary",
                    value=summary,
                    height=150,
                    disabled=True,
                    help="This is the summary of your review text, generated by the LangGraph agent.",
                    key=f"summary_{st.session_state.thread_id}_{int(time.time())}"
                )
            else:
                summary_container.write(f"**📋 Summary:** `{summary}`")

            # Display word cloud path and image
            word_cloud_path = current.get('word_cloud_path', 'Not yet processed')
            if word_cloud_path != 'Not yet processed':
                word_cloud_path_container.write(f"**🖼️ Word Cloud Path:** `{word_cloud_path}`")
                
                # Try to display the wordcloud image if the path exists
                try:
                    import os
                    if os.path.exists(word_cloud_path):
                        word_cloud_image_container.image(
                            word_cloud_path,
                            caption="Generated Word Cloud",
                            width='stretch'
                        )
                    else:
                        word_cloud_image_container.warning(f"⚠️ Word cloud image not found at path: {word_cloud_path}")
                except Exception as e:
                    word_cloud_image_container.error(f"❌ Error displaying word cloud: {e}")
            else:
                word_cloud_path_container.write(f"**🖼️ Word Cloud Path:** `{word_cloud_path}`")
                word_cloud_image_container.empty()  # Clear any previous image

            # =================================================================
            # DEBUG DISPLAY (Raw event information)
            # =================================================================
            
            # Show the most recent raw event for debugging purposes
            try:
                events_container.code(json.dumps(recent_event, indent=2), key=f"debug_event_{st.session_state.thread_id}_{int(time.time())}")
            except Exception:
                # Fallback if JSON serialization fails
                events_container.write(str(recent_event))

        # =================================================================
        # STREAMING COMPLETION
        # =================================================================
        
        # If the for-loop ends naturally (no break), consider execution completed
        st.session_state.running = False
        
        # Display final progress in the right panel
        with events_col:
            st.subheader("📊 Final Progress")
            progress_steps = []
            progress_steps.append("✅ Copy Editing" if current.get('copy_edited_text') is not None else "⏳ Copy Editing")
            progress_steps.append("✅ Summarization" if current.get('summary') is not None else "⏳ Summarization")
            progress_steps.append("✅ Word Cloud Generation" if current.get('word_cloud_path') is not None else "⏳ Word Cloud Generation")
            st.write("**Progress:** " + " → ".join(progress_steps))
        
        st.success("✅ **Graph execution completed!**")

    except requests.RequestException as e:
        # Handle HTTP/network errors
        st.session_state.running = False
        st.error(f"Stream error: {e}")
    except Exception as e:
        # Handle any other unexpected errors
        st.session_state.running = False
        st.error(f"Unexpected error: {e}")

# =============================================================================
# FINAL RENDERING AND PERSISTENT INFORMATION
# =============================================================================

# Get current state for final display
current = st.session_state.state or {}

# Show last update timestamp if available
if st.session_state.last_update > 0:
    st.caption(f"Last updated: {time.strftime('%H:%M:%S', time.localtime(st.session_state.last_update))}")

# Display final execution summary if we have meaningful state data
if current and any(k in current for k in ['copy_edited_text', 'summary', 'word_cloud_path']):
    st.success("**Execution Summary:**")
    
    # Show review session info
    st.subheader("📋 Review Session Details")
    col1, col2 = st.columns(2)
    with col1:
        st.text_input("Review Title", value=st.session_state.current_review_title, disabled=True, key=f"final_title_{st.session_state.thread_id}")
    with col2:
        st.text_input("Review Text Length", value=f"{len(st.session_state.current_review_text)} characters", disabled=True, key=f"final_length_{st.session_state.thread_id}")
    
    # Create a nice summary display with the results
    if current.get('copy_edited_text'):
        st.subheader("📝 Final Copy-Edited Text")
        st.text_area(
            "Copy-Edited Result",
            value=current['copy_edited_text'],
            height=200,
            disabled=True,
            help="Final copy-edited version of your review text",
            key=f"final_copy_edited_{st.session_state.thread_id}"
        )
    
    if current.get('summary'):
        st.subheader("📋 Final Summary")
        st.text_area(
            "Summary Result",
            value=current['summary'],
            height=150,
            disabled=True,
            help="Final summary of your review text",
            key=f"final_summary_{st.session_state.thread_id}"
        )
    
    if current.get('word_cloud_path'):
        st.subheader("🖼️ Final Word Cloud")
        try:
            import os
            if os.path.exists(current['word_cloud_path']):
                st.image(
                    current['word_cloud_path'],
                    caption="Final Generated Word Cloud",
                    width='stretch'
                )
            else:
                st.warning(f"⚠️ Word cloud image not found at final path: {current['word_cloud_path']}")
        except Exception as e:
            st.error(f"❌ Error displaying final word cloud: {e}")
    
    # Also show the raw JSON for debugging
    with st.expander("🔍 Raw JSON Data"):
        st.json(current)

# =============================================================================
# DEBUG INFORMATION EXPANDER
# =============================================================================

# Collapsible section with detailed debug information
with st.expander("🔍 Debug Information"):
    st.write(f"**Current State Keys:** {list(current.keys())}")
    st.write(f"**Running Status:** {st.session_state.running}")
    st.write(f"**Thread ID:** {st.session_state.thread_id}")
    st.write(f"**Current Review Text:** {st.session_state.current_review_text[:100]}{'...' if len(st.session_state.current_review_text) > 100 else ''}")
    st.write(
        f"**Last Update:** {time.strftime('%H:%M:%S', time.localtime(st.session_state.last_update)) if st.session_state.last_update > 0 else 'Never'}"
    )
    st.write(f"**Total Events kept:** {len(st.session_state.events)}")




