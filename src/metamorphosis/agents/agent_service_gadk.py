# =============================================================================
#  Filename: agent_service_gadk.py
#
#  Short Description: FastAPI service for the ADK-based self-reviewer agent for the periodic
#                     employee self-review process.
#
#  Creation date: 2025-10-27
#  Author: Chandar L
# =============================================================================

"""FastAPI Agent Service for ADK-based Self-Review Processing.

This module provides a RESTful API service that exposes the ADK-based self-reviewer agent
through HTTP endpoints. It serves as the web interface layer for the Google ADK-based
self-review processing pipeline.

Architecture Overview:
- FastAPI web framework for high-performance async API endpoints
- Integration with Google ADK agents for text processing
- Support for both synchronous and streaming (SSE) responses
- CORS-enabled for frontend integration
- Pydantic models for request/response validation

Key Features:
1. /invoke endpoint: Synchronous processing with complete results
2. /stream endpoint: Real-time streaming of agent execution
3. Session-based state management for conversation persistence
4. Comprehensive error handling and validation
5. Auto-generated API documentation (Swagger/ReDoc)
"""

from __future__ import annotations

import json
import os
import uuid
from contextlib import asynccontextmanager
from typing import AsyncIterator

import uvicorn
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse, StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
from loguru import logger
from dotenv import load_dotenv
from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from google.genai import types

from metamorphosis.agents.self_reviewer_gadk.agent import ReviewAgent, mcp_toolset
from metamorphosis.datamodel import InvokeRequest, StreamRequest, InvokeResponse

load_dotenv()

# =============================================================================
# GLOBAL AGENT AND SESSION SERVICE
# =============================================================================

# Initialize the agent and session service
app_name = "self_reviewer_gadk"
agent = ReviewAgent()
session_service = InMemorySessionService()

# =============================================================================
# LIFESPAN CONTEXT MANAGER
# =============================================================================

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage application lifespan: startup and shutdown events.
    
    This context manager handles resource initialization on startup and
    cleanup on shutdown, replacing the deprecated @app.on_event decorators.
    
    Args:
        app: The FastAPI application instance.
    
    Yields:
        None: Control is yielded to the application runtime.
    """
    # Startup
    logger.info("ADK Agent Service starting up...")
    logger.info("Agent and session service initialized successfully")
    
    yield
    
    # Shutdown
    logger.info("Shutting down ADK Agent Service...")
    await mcp_toolset.close()
    logger.info("ADK Agent Service shut down successfully")

# =============================================================================
# DATA MODELS AND SCHEMAS
# =============================================================================

## Models imported from metamorphosis.datamodel

# =============================================================================
# FASTAPI APPLICATION SETUP
# =============================================================================

app = FastAPI(
    title="ADK Agent Service for FastAPI",
    description=(
        "A FastAPI service that integrates with Google ADK agents for processing "
        "self-review texts through a multi-stage pipeline"
    ),
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
)

# =============================================================================
# MIDDLEWARE CONFIGURATION
# =============================================================================

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # WARNING: Allow all origins - tighten this in production!
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# =============================================================================
# HELPER FUNCTIONS
# =============================================================================

def _generate_session_id(provided_thread_id: str | None) -> tuple[str, str]:
    """Generate session ID and user ID from thread ID.
    
    Args:
        provided_thread_id: Optional thread ID from request.
    
    Returns:
        tuple: (user_id, session_id) pair for ADK session management.
    """
    if provided_thread_id:
        # Use thread_id as both user_id and session_id for consistency
        return provided_thread_id, provided_thread_id
    session_id = str(uuid.uuid4())
    return session_id, session_id


def _create_error_response(error_message: str, status_code: int = 500) -> JSONResponse:
    """Create standardized error response.
    
    Args:
        error_message: Error description for the response.
        status_code: HTTP status code (default 500).
    
    Returns:
        JSONResponse: Formatted error response.
    """
    logger.error("API error ({}): {}", status_code, error_message)
    return JSONResponse({"error": error_message}, status_code=status_code)


def _convert_pydantic_to_dict(data: dict) -> dict:
    """Convert Pydantic objects in a dictionary to plain dictionaries for JSON serialization.
    
    Args:
        data: Dictionary that may contain Pydantic objects as values.
    
    Returns:
        dict: Dictionary with all Pydantic objects converted to dictionaries.
    """
    from pydantic import BaseModel

    def _normalize_value(value: object) -> object:
        if isinstance(value, BaseModel):
            return value.model_dump()
        if isinstance(value, dict):
            return {key: _normalize_value(item) for key, item in value.items()}
        if isinstance(value, list):
            return [_normalize_value(item) for item in value]
        if isinstance(value, tuple):
            return tuple(_normalize_value(item) for item in value)
        return value

    return _normalize_value(data)


def _map_session_state_to_response(state: dict) -> dict:
    """Map ADK session state to InvokeResponse format.
    
    Args:
        state: ADK session state dictionary.
    
    Returns:
        dict: Mapped response dictionary matching InvokeResponse structure.
    """
    return {
        "original_text": state.get("original_text", ""),
        "copy_edited_text": state.get("reviewed_text"),
        "summary": state.get("summarized_text"),
        "word_cloud_path": state.get("wordcloud_path"),
        "achievements": state.get("achievements"),
        "review_scorecard": state.get("evaluation"),
        "review_complete": state.get("review_complete"),
    }


async def _ensure_session_exists(user_id: str, session_id: str) -> None:
    """Ensure a session exists, creating it if necessary.
    
    Args:
        user_id: User identifier for the session.
        session_id: Session identifier.
    """
    # Try to get the session first
    session_exists = False
    try:
        session = await session_service.get_session(
            app_name=app_name,
            user_id=user_id,
            session_id=session_id
        )
        if session is not None:
            session_exists = True
            logger.debug("Session already exists (user_id={}, session_id={})", user_id, session_id)
    except Exception as e:
        # Session doesn't exist - this is expected for new sessions
        logger.debug("Session not found (will create): {}", str(e))
        session_exists = False
    
    # Create session if it doesn't exist
    if not session_exists:
        logger.info("Creating new session (user_id={}, session_id={})", user_id, session_id)
        try:
            await session_service.create_session(
                app_name=app_name,
                user_id=user_id,
                session_id=session_id,
                state={},
            )
            # Verify the session was created successfully
            verify_session = await session_service.get_session(
                app_name=app_name,
                user_id=user_id,
                session_id=session_id
            )
            if verify_session is None:
                raise ValueError("Session creation failed - verification returned None")
            logger.info("Session created and verified successfully (user_id={}, session_id={})", user_id, session_id)
        except Exception as create_error:
            # If session already exists, that's okay - just log it
            error_msg = str(create_error).lower()
            if "already exists" in error_msg or "duplicate" in error_msg:
                logger.debug("Session already exists (user_id={}, session_id={})", user_id, session_id)
                # Verify we can still get it
                verify_session = await session_service.get_session(
                    app_name=app_name,
                    user_id=user_id,
                    session_id=session_id
                )
                if verify_session is None:
                    raise ValueError("Session reported as existing but cannot be retrieved")
            else:
                logger.error("Failed to create session: {}", create_error)
                raise ValueError(f"Failed to create session: {create_error}") from create_error


async def _generate_stream_events(
    review_text: str, thread_id: str, mode: str, request: Request
) -> AsyncIterator[bytes]:
    """Generate SSE events from ADK agent execution.
    
    Args:
        review_text: Text to process.
        thread_id: Thread identifier for state persistence.
        mode: Streaming mode (values or updates) - for ADK, we'll stream all events.
        request: FastAPI request for disconnect detection.
    
    Yields:
        bytes: SSE-formatted event data.
    """
    user_id, session_id = _generate_session_id(thread_id)
    
    try:
        await _ensure_session_exists(user_id, session_id)
        
        # Create user input
        user_input = types.Content(
            parts=[types.Part(text=review_text)]
        )
        
        # Create runner
        runner = Runner(agent=agent, session_service=session_service, app_name=app_name)
        
        async with runner:
            async for event in runner.run_async(
                user_id=user_id,
                session_id=session_id,
                new_message=user_input
            ):
                # Convert event to serializable format
                event_data = {
                    "author": event.author,
                    "content": str(event.content),
                }
                
                # If mode is "values", also include current session state
                if mode == "values":
                    try:
                        session = await session_service.get_session(
                            app_name=app_name,
                            user_id=user_id,
                            session_id=session_id
                        )
                        event_data["state"] = _map_session_state_to_response(session.state)
                    except Exception:
                        pass  # Continue even if state fetch fails
                
                serializable_ev = _convert_pydantic_to_dict(event_data)
                yield f"data: {json.dumps(serializable_ev)}\n\n".encode("utf-8")
                
                if await request.is_disconnected():
                    logger.info("Client disconnected during streaming (thread_id={})", thread_id)
                    break
        
    except Exception as e:
        error_data = {"error": str(e)}
        yield f"data: {json.dumps(error_data)}\n\n".encode("utf-8")


# =============================================================================
# API ENDPOINTS
# =============================================================================

@app.post(
    "/invoke",
    summary="Process a self-review text through the ADK agent",
    description="Submit a self-review text to be processed through the ADK agent pipeline.",
    response_description="The result of processing the self-review text through the agent",
    response_model=InvokeResponse,
)
async def invoke(payload: InvokeRequest) -> JSONResponse:
    """Main endpoint for synchronous processing of self-review text.
    
    Processing Pipeline:
    1. Copy editing: Grammar and clarity improvements
    2. Summarization: Abstractive summary generation
    3. Word cloud: Visual representation generation
    4. Achievements extraction: Key achievements extraction
    5. Review text evaluation: Review text evaluation
    
    Args:
        payload: Validated request containing review_text and optional thread_id.
    
    Returns:
        JSONResponse: Complete processing results or error response.
    
    Raises:
        Exception: Various exceptions can occur during agent execution.
    """
    review_text = payload.review_text
    user_id, session_id = _generate_session_id(payload.thread_id)
    
    logger.info("Processing review (session_id={}, text_length={})", session_id, len(review_text))
    
    try:
        await _ensure_session_exists(user_id, session_id)
        
        # Create user input
        user_input = types.Content(
            parts=[types.Part(text=review_text)]
        )
        
        # Create runner and execute
        runner = Runner(agent=agent, session_service=session_service, app_name=app_name)
        
        # Collect all events
        events = []
        async with runner:
            async for event in runner.run_async(
                user_id=user_id,
                session_id=session_id,
                new_message=user_input
            ):
                events.append(event)
        
        # Get final session state
        final_session = await session_service.get_session(
            app_name=app_name,
            user_id=user_id,
            session_id=session_id
        )
        
        if not final_session or not final_session.state:
            return _create_error_response("Agent execution returned no result")
        
        # Postcondition (O(1)): ensure valid result structure
        if "original_text" not in final_session.state:
            return _create_error_response("Invalid result structure from agent")
        
        logger.info("Successfully processed review (session_id={})", session_id)
        
        # Map session state to response format
        response_data = _map_session_state_to_response(final_session.state)
        
        # Convert Pydantic objects to dictionaries for JSON serialization
        serializable_result = _convert_pydantic_to_dict(response_data)
        return JSONResponse(serializable_result)
    
    except Exception as e:
        logger.exception("Agent execution failed: {}", str(e))
        return _create_error_response(f"Agent execution failed: {str(e)}")


@app.post("/stream")
async def stream(request: Request, payload: StreamRequest) -> StreamingResponse:
    """Server-Sent Events (SSE) streaming endpoint for real-time agent execution monitoring.
    
    This endpoint provides a live stream of the agent's execution events, allowing clients
    to monitor progress in real-time rather than waiting for the entire process to complete.
    
    Args:
        request: FastAPI request object for checking client connection status.
        payload: Validated request containing review_text, thread_id, and mode.
    
    Returns:
        StreamingResponse: Server-Sent Events stream with real-time updates.
    
    Note:
        The client can disconnect at any time, and the server will detect this
        and stop processing to conserve resources.
    """
    logger.info(
        "Starting stream (thread_id={}, text_length={}, mode={})",
        payload.thread_id,
        len(payload.review_text),
        payload.mode,
    )
    
    event_generator = _generate_stream_events(
        payload.review_text, payload.thread_id, payload.mode, request
    )
    
    return StreamingResponse(event_generator, media_type="text/event-stream")


# =============================================================================
# MAIN EXECUTION BLOCK
# =============================================================================

if __name__ == "__main__":
    """Main execution block for running the FastAPI service in development mode.
    
    This block runs when the script is executed directly (not imported as a module).
    It configures and starts the uvicorn ASGI server with development-friendly settings.
    """
    
    host = os.getenv("FASTAPI_HOST", "localhost")
    port = int(os.getenv("FASTAPI_PORT", "8000"))  
    
    logger.info("Starting ADK Agent FastAPI service on {}:{}", host, port)
    logger.info("API documentation available at: http://{}:{}/docs", host, port)
    logger.info("Alternative API docs at: http://{}:{}/redoc", host, port)
    
    uvicorn.run(
        "agent_service_gadk:app",
        host=host,
        port=port,
        reload=True,
        log_level="info",
    )
