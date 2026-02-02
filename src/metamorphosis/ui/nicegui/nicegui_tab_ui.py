# =============================================================================
#  Filename: nicegui_full_ui.py
#
#  Short Description: NiceGUI-based tabbed UI for the Metamorphosis self-review
#                     processing system with dark mode and error handling.
#
#  Creation date: 2026-01-21
#  Author: Ashwath Bhat
# =============================================================================

"""
NiceGUI Tabbed UI for Metamorphosis Self-Review System

This module provides the main NiceGUI application for the self-reviewer agent.
It features a 6-tab interface (Input, Rationalized, Summary, Visuals, Achievements,
Scorecard), manages UI state, streams results via Server-Sent Events (SSE), and
displays various outputs including tables and radar plots.

Features:
    - Robust error handling with retry capability
    - Real-time progress tracking via SSE streaming
    - Interactive achievements and scorecard displays
"""

import os
import uuid
import asyncio
from concurrent.futures import ThreadPoolExecutor

import requests
from dotenv import load_dotenv
from loguru import logger
from nicegui import ui

# UI helper imports
from metamorphosis.ui.nicegui.nicegui_ui_helpers import (
    extract_values_from_event,
    patch_state,
    sse_events,
    validate_review_text,
    display_achievements_table,
    display_metrics_table,
    display_radar_plot,
    safe_markdown
)
from metamorphosis.datamodel import AchievementsList, ReviewScorecard

load_dotenv()

# =============================================================================
# CONFIGURATION
# =============================================================================
SERVICE_BASE = os.getenv("SERVICE_BASE", "http://localhost:8000")
STREAM_URL = f"{SERVICE_BASE}/stream"
ICON = 'docs/images/overlapping_logo.png'

io_executor = ThreadPoolExecutor(max_workers=10)

# =============================================================================
# ASYNC WRAPPER
# =============================================================================
async def async_sse_generator(url, data):
    loop = asyncio.get_event_loop()
    queue = asyncio.Queue()
    
    def run_stream():
        try:
            for event in sse_events(url, data):
                loop.call_soon_threadsafe(queue.put_nowait, event)
            loop.call_soon_threadsafe(queue.put_nowait, None)
        except Exception as e:
            loop.call_soon_threadsafe(queue.put_nowait, e)

    loop.run_in_executor(io_executor, run_stream)

    while True:
        item = await queue.get()
        if item is None:
            break
        if isinstance(item, Exception):
            raise item
        yield item

# =============================================================================
# UI STATE CLASS
# =============================================================================
class UIState:
    def __init__(self):
        self.thread_id = str(uuid.uuid4())
        self.state = {}
        self.running = False
        self.progress_steps = []
        self.progress_value = 0.0
        self.review_text = ""
        self.review_title = "Self-review Q1–Q2 / H1 2025"
        self.stream_mode = "values"
        self.last_error = None  # Track last error for retry capability
        
        try:
            root_dir = os.getenv("PROJECT_ROOT_DIR", ".")
            sample_file_path = os.path.join(root_dir, "sample_reviews", "poor_review.md")
            if os.path.exists(sample_file_path):
                with open(sample_file_path, 'r', encoding='utf-8') as f:
                    self.review_text = f.read().strip()
            else:
                self.review_text = "I had an eventful cycle this summer..."
        except Exception:
            self.review_text = "I had an eventful cycle this summer..."

# =============================================================================
# HELPER: COPY TO CLIPBOARD
# =============================================================================
async def copy_to_clipboard(text: str):
    if not text:
        ui.notify('Nothing to copy!', type='warning')
        return
    # Escape backticks and backslashes for JS
    js_text = text.replace('\\', '\\\\').replace('`', '\\`').replace('$', '')
    await ui.run_javascript(f'navigator.clipboard.writeText(`{js_text}`)')
    ui.notify('Copied to clipboard!', type='positive', icon='content_copy')

# =============================================================================
# MAIN PAGE
# =============================================================================
@ui.page('/')
async def main_page():
    state = UIState()
    client = ui.context.client
    
    # --- STYLING ---
    ui.add_head_html('''
        <link rel="preconnect" href="https://fonts.googleapis.com">
        <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
        <link href="https://fonts.googleapis.com/css2?family=Google+Sans:ital,opsz,wght@0,17..18,400..700;1,17..18,400..700&family=Lora:ital,wght@0,400..700;1,400..700&display=swap" rel="stylesheet">
    ''')
    ui.add_css('''
        body, .q-app { font-family: 'Lora', sans-serif !important; }
        backdrop-filter: blur(10px); border: 1px solid rgba(0,0,0,0.05); }
    ''')   
    
    ui.colors(primary='#1A3263', secondary='#547792', accent='#FAB95B', positive='#27AE60', negative='#C0392B')

    # --- HEADER ---
    with ui.header(elevated=True).classes('bg-primary text-white flex items-center p-3 shadow-md'):
        ui.button(icon='menu', on_click=lambda: left_drawer.toggle()).props('flat round color=white')
        ui.image(ICON).classes('w-8 h-8 ml-2')
        ui.label('Metamorphosis Self-Review').classes('text-xl font-bold ml-3 tracking-wide')
        ui.space()

    # --- SIDEBAR ---
    with ui.left_drawer(value=True).classes('bg-white p-6 shadow-lg border-r border-gray-200') as left_drawer:
        ui.label('Configuration').classes('text-xs font-bold text-gray-400 uppercase tracking-wider mb-2')
        ui.input('Review Title').bind_value(state, 'review_title').props('outlined dense').classes('w-full mb-6')
        
        ui.label('Actions').classes('text-xs font-bold text-gray-400 uppercase tracking-wider mb-2')
        start_btn = ui.button('Start Analysis', icon='play_arrow').classes('w-full mb-3 shadow-sm').props('color=primary')
        stop_btn = ui.button('Stop Stream', icon='stop').classes('w-full mb-3').props('outline color=primary')
        reset_btn = ui.button('New Session', icon='refresh').classes('w-full mb-3').props('flat color=secondary')
        retry_btn = ui.button('Retry Analysis', icon='replay').classes('w-full hidden').props('outline color=negative')
        
        ui.separator().classes('my-6')
        
        ui.label('Progress').classes('text-xs font-bold text-gray-400 uppercase tracking-wider mb-2')
        ui.linear_progress(value=0, show_value=False).classes('w-full rounded-full h-2').bind_value(
            state, 'progress_value'
        )
        
        progress_column = ui.column().classes('w-full mt-2 gap-1')
        status_label = ui.label('Ready').classes('text-sm text-gray-600 mt-2 font-medium')

    # --- MAIN CONTENT ---
    with ui.column().classes('w-full max-w-7xl mx-auto p-6'):
        
        with ui.card().classes('w-full glass-panel rounded-xl shadow-sm p-0'):
            # Tabs Header
            with ui.tabs().classes('w-full text-primary bg-gray-50 border-b border-gray-200') as tabs:
                t1 = ui.tab('Input', icon='edit')
                t2 = ui.tab('Rationalized', icon='auto_fix_high')
                t3 = ui.tab('Summary', icon='summarize')
                t4 = ui.tab('Visuals', icon='image')
                t5 = ui.tab('Achievements', icon='emoji_events')
                t6 = ui.tab('Scorecard', icon='analytics')

            # Tabs Content
            with ui.tab_panels(tabs, value=t1).classes('w-full p-6 bg-transparent'):
                
                # --- TAB 1: INPUT ---
                with ui.tab_panel(t1):
                    with ui.row().classes('w-full items-center justify-between mb-2'):
                         ui.label('Draft Review').classes('text-lg font-medium text-gray-700')
                         validation_label = ui.label().classes('text-sm text-negative font-medium')
                    
                    editor = ui.textarea(placeholder='Enter your review text here......').bind_value(state, 'review_text') \
                        .props('outlined rounded outlined input-class="font-mono text-sm"').classes('w-full shadow-inner bg-white')

                # --- TAB 2: RATIONALIZED TEXT ---
                with ui.tab_panel(t2):
                    with ui.row().classes('w-full justify-between items-center mb-4'):
                        ui.label('Polished Version').classes('text-lg text-secondary')
                        # QoL 2: Copy Button
                        ui.button('Copy Text', icon='content_copy', on_click=lambda: copy_to_clipboard(state.state.get('copy_edited_text', ''))) \
                            .props('flat dense size=sm color=primary')
                    
                    rationalized_container = ui.markdown().classes('w-full prose max-w-none text-gray-800')

                # --- TAB 3: SUMMARY ---
                with ui.tab_panel(t3):
                    with ui.row().classes('w-full justify-between items-center mb-4'):
                        ui.label('Executive Summary').classes('text-lg text-secondary')
                        ui.button('Copy Summary', icon='content_copy', on_click=lambda: copy_to_clipboard(state.state.get('summary', ''))) \
                            .props('flat dense size=sm color=primary')
                            
                    summary_container = ui.markdown().classes('w-full prose max-w-none text-gray-800')

                # --- TAB 4: WORD CLOUD ---
                with ui.tab_panel(t4):
                    with ui.column().classes('w-full items-center'):
                        wc_image = ui.image().classes('w-full max-w-2xl rounded-lg shadow-lg border border-gray-200')
                        wc_path_label = ui.label().classes('text-caption text-gray-400 mt-2')

                # --- TAB 5: ACHIEVEMENTS ---
                with ui.tab_panel(t5):
                    achievements_anchor = ui.column().classes('w-full')
                    @ui.refreshable
                    def achievements_panel():
                        achievements_anchor.clear()
                        current = state.state
                        
                        # QoL 3: Empty State / Skeleton
                        if 'achievements' not in current:
                            with achievements_anchor.classes('items-center justify-center py-12'):
                                ui.icon('emoji_events', size='4rem', color='grey-3')
                                ui.label('Waiting for achievements data...').classes('text-grey-4 text-lg mt-2')
                                if state.running:
                                    ui.spinner('dots', size='2rem', color='primary').classes('mt-2')
                            return

                        raw_data = current['achievements']

                        try:
                            if isinstance(raw_data, dict):
                                alist = AchievementsList(**raw_data)
                                display_achievements_table(alist, achievements_anchor)
                            elif isinstance(raw_data, list):
                                try:
                                    alist = AchievementsList(achievements=raw_data)
                                    display_achievements_table(alist, achievements_anchor)
                                except Exception:
                                    alist = AchievementsList(items=raw_data)
                                    display_achievements_table(alist, achievements_anchor)
                            else:
                                ui.label("Invalid data format").classes('text-negative')
                        except Exception as e:
                            ui.label(f"Render Error: {e}").classes('text-negative bg-red-50 p-2 rounded')

                    achievements_panel()

                # --- TAB 6: SCORECARD ---
                with ui.tab_panel(t6):
                    scorecard_anchor = ui.column().classes('w-full')
                    @ui.refreshable
                    def scorecard_panel():
                        scorecard_anchor.clear()
                        current = state.state

                        if 'review_scorecard' not in current:
                            with scorecard_anchor.classes('items-center justify-center py-12'):
                                ui.icon('analytics', size='4rem', color='grey-3')
                                ui.label('Waiting for metrics...').classes('text-grey-4 text-lg mt-2')
                                if state.running:
                                    ui.spinner('dots', size='2rem', color='primary').classes('mt-2')
                            return

                        raw_data = current['review_scorecard']

                        try:
                            if isinstance(raw_data, dict):
                                sc = ReviewScorecard(**raw_data)
                                display_radar_plot(sc, scorecard_anchor)
                                display_metrics_table(sc, scorecard_anchor)
                            else:
                                ui.label("Expected Dict data").classes('text-warning')
                        except Exception as e:
                            ui.label(f"Render Error: {e}").classes('text-negative')

                    scorecard_panel()

    # =============================================================================
    # LOGIC
    # =============================================================================
    def update_ui():
        if not client.connected:
            return

        try:
            # Validation
            is_valid, msg = validate_review_text(state.review_text)
            validation_label.text = msg if not is_valid else "Ready to process"
            validation_label.classes(replace='text-positive' if is_valid else 'text-negative')
            
            # Content
            current = state.state
            
            # QoL 4: Better Empty Text handling
            rationalized_container.content = current.get('copy_edited_text', '*Waiting for analysis...*')
            summary_container.content = safe_markdown(current.get('summary', '*Waiting for analysis...*'))
            
            wc_path = current.get('word_cloud_path')
            if wc_path and os.path.exists(wc_path):
                wc_image.source = wc_path
                wc_image.classes(remove='hidden')
                wc_path_label.text = f"File: {os.path.basename(wc_path)}"
            else:
                wc_image.classes(add='hidden') # Hide broken image icon
                wc_path_label.text = "Generating visualization..." if state.running else "No image available"
            
            achievements_panel.refresh()
            scorecard_panel.refresh()

            # Progress Steps
            progress_column.clear()
            with progress_column:
                for step in state.progress_steps:
                    with ui.row().classes('items-center gap-2'):
                        ui.icon('check_circle', color='positive', size='xs')
                        ui.label(step.replace('✅ ', '')).classes('text-sm text-gray-700')
            
            # Button States
            if state.running:
                status_label.text = "Processing..."
                status_label.classes(replace='text-primary animate-pulse')
                start_btn.disable()
                retry_btn.classes(add='hidden')
                editor.disable() # Lock input while running
            elif state.last_error:
                status_label.text = "Error occurred"
                status_label.classes(replace='text-negative font-bold')
                start_btn.enable()
                retry_btn.classes(remove='hidden')
                editor.enable()
            elif state.state:
                status_label.text = "Analysis Complete"
                status_label.classes(replace='text-positive font-bold')
                state.progress_value = 1.0
                start_btn.enable()
                retry_btn.classes(add='hidden')
                editor.enable()
            else:
                status_label.text = "Ready to Start"
                status_label.classes(replace='text-gray-500')
                state.progress_value = 0.0
                start_btn.enable()
                retry_btn.classes(add='hidden')
                editor.enable()
                
        except Exception as e:
            if "Client has been deleted" not in str(e):
                logger.warning("UI Warning: {}", e)

    async def start_streaming():
        if not client.connected:
            return

        is_valid, msg = validate_review_text(state.review_text)
        if not is_valid:
            ui.notify(f"Cannot start: {msg}", type='negative', position='top')
            return

        # 1. RESET PHASE
        state.thread_id = str(uuid.uuid4())
        state.running = True
        state.state = {}           # Wipe old data
        state.progress_steps = []  # Wipe old checklist
        state.progress_value = 0.0 # Reset bar to 0
        count = 0
        

        
        # 2. FORCE UI REFRESH
        # We explicitly update the UI to show the empty state
        update_ui()
        
        # 3. CRITICAL PAUSE (The Fix)
        # This gives the browser 100ms to visually render the "0%" bar 
        # before we start doing heavy work. Without this, it looks like it never reset.
        await asyncio.sleep(0.1)
        
        # 4. START PROCESSING
        # Switch to the results tab automatically
        tabs.set_value(t2)
        
        request_data = {
            "thread_id": state.thread_id, 
            "review_text": state.review_text, 
            "mode": "values"
        }
        
        try:
            async for ev in async_sse_generator(STREAM_URL, request_data):
                if not client.connected:
                    return
                if not state.running:
                    break

                vals = extract_values_from_event(ev)
                if vals:
                    state.state.update(vals)
                if "updates" in ev:
                    state.state = patch_state(state.state, ev["updates"])
                
                # Calculate Progress
                curr = state.state
                steps = []
                count = 0
                if curr.get("copy_edited_text"):
                    steps.append("✅ Copy Editing")
                    count += 1
                if curr.get("summary"):
                    steps.append("✅ Summarization")
                    count += 1
                if curr.get("word_cloud_path"):
                    steps.append("✅ Word Cloud")
                    count += 1
                if curr.get("achievements"):
                    steps.append("✅ Achievements")
                    count += 1
                if curr.get("review_scorecard"):
                    steps.append("✅ Scorecard")
                    count += 1
                
                state.progress_steps = steps
                state.progress_value = count / 5.0
                
                update_ui()
                
            if client.connected:
                state.running = False
                state.last_error = None  # Clear error on success
                update_ui()
                ui.notify("Analysis finished successfully", type='positive')
            
        except requests.exceptions.ConnectionError:
            state.running = False
            state.last_error = "connection"
            if client.connected:
                ui.notify("Connection failed. Is the agent service running?", type='negative', position='top', timeout=5000)
            update_ui()
        except requests.exceptions.Timeout:
            state.running = False
            state.last_error = "timeout"
            if client.connected:
                ui.notify("Request timed out. The service may be overloaded.", type='warning', position='top', timeout=5000)
            update_ui()
        except Exception as e:
            state.running = False
            state.last_error = str(e)
            error_msg = str(e)
            # Provide user-friendly error messages
            if "refused" in error_msg.lower():
                friendly_msg = "Cannot connect to agent service. Please ensure it's running."
            elif "timeout" in error_msg.lower():
                friendly_msg = "Request timed out. Try again or check the service."
            elif "json" in error_msg.lower():
                friendly_msg = "Invalid response from service. Check server logs."
            else:
                friendly_msg = f"Error: {error_msg[:100]}" if len(error_msg) > 100 else f"Error: {error_msg}"
            
            if client.connected:
                ui.notify(friendly_msg, type='negative', position='top', timeout=5000)
            update_ui()

    def stop_streaming():
        state.running = False
        update_ui()

    def reset_session():
        state.thread_id = str(uuid.uuid4())
        state.state = {}
        state.progress_steps = []
        state.progress_value = 0.0
        state.running = False
        state.last_error = None  # Clear error on reset
        tabs.set_value(t1) # Go back to input
        ui.notify("Session reset", icon='refresh')
        update_ui()

    # Link buttons
    start_btn.on_click(start_streaming)
    stop_btn.on_click(stop_streaming)
    reset_btn.on_click(reset_session)
    retry_btn.on_click(start_streaming)  # Retry just re-runs start_streaming

    update_ui()

if __name__ in {"__main__", "__mp_main__"}:
    # UPDATE THIS to your actual output folder!
    # app.add_static_files('/outputs', 'outputs') 
    ui.run(title='Metamorphosis Self-Review', port=8082, favicon=ICON)