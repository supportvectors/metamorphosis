# =============================================================================
#  Filename: agent_service.py
#
#  Short Description: FastAPI service for the self-reviewer agent(s) for the periodic
#                     employee self-review process.
#
#  Creation date: 2025-09-01
#  Author: Chandar L
# =============================================================================

"""FastAPI Agent Service for Self-Review Processing.

This module provides a RESTful API service that exposes the self-reviewer agent
workflow through HTTP endpoints. It serves as the web interface layer for the
LangGraph-based self-review processing pipeline.

Architecture Overview:
- FastAPI web framework for high-performance async API endpoints
- Integration with LangGraph workflow for text processing
- Support for both synchronous and streaming (SSE) responses
- CORS-enabled for frontend integration
- Pydantic models for request/response validation

Key Features:
1. /invoke endpoint: Synchronous processing with complete results
2. /stream endpoint: Real-time streaming of workflow execution
3. Thread-based state management for conversation persistence
4. Comprehensive error handling and validation
5. Auto-generated API documentation (Swagger/ReDoc)
"""

from __future__ import annotations

import json
import os
import uuid
from typing import AsyncIterator

import uvicorn
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse, StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
from loguru import logger
from dotenv import load_dotenv
from metamorphosis.agents.self_reviewer import graph, run_graph
from metamorphosis.datamodel import InvokeRequest, StreamRequest, InvokeResponse
load_dotenv()


# =============================================================================
# DATA MODELS AND SCHEMAS
# =============================================================================

## Models moved to metamorphosis.datamodel


# =============================================================================
# FASTAPI APPLICATION SETUP
# =============================================================================

app = FastAPI(
    title="LangGraph for FastAPI Service",
    description=(
        "A FastAPI service that integrates with LangGraph for processing "
        "self-review texts through a multi-stage pipeline"
    ),
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
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


def _generate_thread_id(provided_thread_id: str | None) -> str:
    """Generate a thread ID if none provided.

    Args:
        provided_thread_id: Optional thread ID from request.

    Returns:
        str: Valid thread ID (provided or newly generated).
    """
    if provided_thread_id:
        return provided_thread_id
    return str(uuid.uuid4())


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
    
    result = {}
    for key, value in data.items():
        if isinstance(value, BaseModel):
            result[key] = value.model_dump()
        else:
            result[key] = value
    return result


async def _generate_stream_events(
    review_text: str, thread_id: str, mode: str, request: Request
) -> AsyncIterator[bytes]:
    """Generate SSE events from graph execution.

    Args:
        review_text: Text to process.
        thread_id: Thread identifier for state persistence.
        mode: Streaming mode (values or updates).
        request: FastAPI request for disconnect detection.

    Yields:
        bytes: SSE-formatted event data.
    """
    try:
        async for ev in graph.astream(
            {"original_text": review_text},
            config={"configurable": {"thread_id": thread_id}},
            stream_mode=mode,
        ):
            # Convert Pydantic objects to dictionaries for proper JSON serialization
            serializable_ev = _convert_pydantic_to_dict(ev)
            yield f"data: {json.dumps(serializable_ev, default=str)}\n\n".encode("utf-8")

            if await request.is_disconnected():
                logger.info("Client disconnected during streaming (thread_id={})", thread_id)
                break

    except Exception as e:
        error_data = {"error": str(e)}
        yield f"data: {json.dumps(error_data, default=str)}\n\n".encode("utf-8")


# =============================================================================
# API ENDPOINTS
# =============================================================================


@app.post(
    "/invoke",
    summary="Process a self-review text through the LangGraph",
    description="Submit a self-review text to be processed through the LangGraph pipeline.",
    response_description="The result of processing the self-review text through the graph",
    response_model=InvokeResponse,
)
async def invoke(payload: InvokeRequest) -> JSONResponse:
    """Main endpoint for synchronous processing of self-review text.

    Processing Pipeline:
    1. Copy editing: Grammar and clarity improvements
    2. Summarization: Abstractive summary generation (parallel)
    3. Word cloud: Visual representation generation (parallel)
    4. Achievements extraction: Key achievements extraction (parallel)
    5. Review text evaluation: Review text evaluation (parallel)

    Args:
        payload: Validated request containing review_text and optional thread_id.

    Returns:
        JSONResponse: Complete processing results or error response.

    Raises:
        Exception: Various exceptions can occur during graph execution.
    """
    review_text = payload.review_text
    thread_id = _generate_thread_id(payload.thread_id)

    logger.info("Processing review (thread_id={}, text_length={})", thread_id, len(review_text))

    try:
        result = await run_graph(graph, review_text, thread_id)
        if result is None:
            return _create_error_response("Graph execution returned no result")

        # Postcondition (O(1)): ensure valid result structure
        if not isinstance(result, dict) or "original_text" not in result:
            return _create_error_response("Invalid result structure from graph")

        logger.info("Successfully processed review (thread_id={})", thread_id)
        
        # Convert Pydantic objects to dictionaries for JSON serialization
        serializable_result = _convert_pydantic_to_dict(result)
        return JSONResponse(serializable_result)

    except Exception as e:
        return _create_error_response(f"Graph execution failed: {str(e)}")


@app.post("/stream")
async def stream(request: Request, payload: StreamRequest) -> StreamingResponse:
    """Server-Sent Events (SSE) streaming endpoint for real-time graph execution monitoring.

    This endpoint provides a live stream of the graph's execution state, allowing clients
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

    logger.info("Starting FastAPI service on {}:{}", host, port)
    logger.info("API documentation available at: http://{}:{}/docs", host, port)
    logger.info("Alternative API docs at: http://{}:{}/redoc", host, port)

    uvicorn.run(
        "agent_service:app",
        host=host,
        port=port,
        reload=True,
        log_level="info",
    )
