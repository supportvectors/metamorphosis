# =============================================================================
#  Filename: agent_service.py
#
#  Short Description: FastAPI service for the self-reviewer agent(s) for the periodic employee self-review process.
#
#  Creation date: 2025-09-01
#  Author: Chandar L
# =============================================================================

# =============================================================================
# IMPORTS AND DEPENDENCIES
# =============================================================================
# FastAPI framework for building high-performance web APIs
from fastapi import FastAPI, Request
# Response types for handling different HTTP response formats
from fastapi.responses import JSONResponse, StreamingResponse
# Type hint for async generators/iterators
from typing import AsyncIterator
# Standard library imports for JSON handling and UUID generation
import json
import uvicorn
# Pydantic for data validation and serialization
from pydantic import BaseModel, Field
# CORS middleware for handling cross-origin requests
from fastapi.middleware.cors import CORSMiddleware
# Import our custom LangGraph implementation and execution function
from metamorphosis.agents.self_reviewer import graph, run_graph
# UUID generation for unique thread identification
import uuid

# =============================================================================
# DATA MODELS AND SCHEMAS
# =============================================================================
# Pydantic model for incoming API requests
class InvokeRequest(BaseModel):
    # Required field: the review text to be processed through the LangGraph pipeline
    review_text: str = Field(..., description="The review text to process through the LangGraph", 
        example='''
        I had an eventful cycle this summer.  Learnt agentic workflows and implemented a self-reviewer agent 
        for the periodic employee self-review process.  It significantly improved employee productivity for the organization.
        ''')
    # Optional field: thread ID for maintaining conversation state across requests
    # If not provided, a new UUID will be generated automatically
    thread_id: str = Field(None, description="Optional thread ID for state persistence. If not provided, a new UUID will be generated.", example="thread_123")

# Pydantic model for streaming requests
class StreamRequest(BaseModel):
    # Required field: the review text to be processed
    review_text: str = Field(..., description="The review text to process through the LangGraph")
    # Required field: thread ID for maintaining conversation state
    thread_id: str = Field(..., description="Unique identifier for the conversation thread")
    # Optional field: streaming mode
    mode: str = Field("values", description="Streaming mode - 'updates' for state changes only, 'values' for full state each step")

# Pydantic model for API responses
class InvokeResponse(BaseModel):
    # The original review text that was processed
    original_text: str = Field(..., description="The original review text")
    # The copy-edited text
    copy_edited_text: str = Field(None, description="The copy-edited text")
    # The summary of the copy-edited text
    summary: str = Field(None, description="The summary of the copy-edited text")
    # The path to the word cloud image
    word_cloud_path: str = Field(None, description="The path to the word cloud image")

# =============================================================================
# FASTAPI APPLICATION SETUP
# =============================================================================
# Initialize the FastAPI application with metadata and configuration
app = FastAPI(
    title="LangGraph for FastAPI Service",
    description="A FastAPI service that integrates with LangGraph for processing self-review texts through a multi-stage pipeline",
    version="1.0.0",
    docs_url="/docs",      # Swagger UI documentation endpoint
    redoc_url="/redoc"     # ReDoc alternative documentation endpoint
)

# =============================================================================
# MIDDLEWARE CONFIGURATION
# =============================================================================
# Add CORS middleware to handle cross-origin requests
# This allows the frontend to communicate with the API from different domains
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],   # WARNING: Allow all origins - tighten this in production!
    allow_credentials=True, # Allow cookies and authentication headers
    allow_methods=["*"],   # Allow all HTTP methods (GET, POST, PUT, DELETE, etc.)
    allow_headers=["*"],   # Allow all request headers
)

# =============================================================================
# API ENDPOINTS
# =============================================================================
@app.post("/invoke", 
          summary="Process a self-review text through the LangGraph",
          description='''Submit a self-review text to be processed through the LangGraph pipeline. 
          The self-review text will go through copy editing, summarization, and word cloud generation.''',
          response_description="The result of processing the self-review text through the graph",
          response_model=InvokeResponse)
async def invoke(payload: InvokeRequest):
    """
    Main endpoint for processing review text through the LangGraph pipeline.
    
    This function:
    1. Extracts and validates the incoming request data
    2. Generates a thread ID if none is provided
    3. Executes the LangGraph with the given review text
    4. Returns the processing results or error information
    
    Args:
        payload (InvokeRequest): Validated request containing review text and optional thread_id
        
    Returns:
        JSONResponse: Either the processing results or an error message
    """
    # Extract values from the validated Pydantic payload
    review_text = payload.review_text
    # Generate a new UUID if no thread_id was provided, ensuring each request has a unique identifier
    thread_id = payload.thread_id or str(uuid.uuid4())

    try:
        # Execute the LangGraph with the given review text and thread_id
        # This kicks off the multi-stage pipeline: copy editing -> summarization -> word cloud generation
        result = await run_graph(graph, review_text, thread_id)
        return JSONResponse(result)
    except Exception as e:
        # Return a 500 error with details if the graph execution fails
        # This could happen due to graph compilation issues, runtime errors, or external service failures
        return JSONResponse({"error": f"Graph execution failed: {str(e)}"}, status_code=500)

# =============================================================================
# STREAMING ENDPOINT
# =============================================================================
@app.post("/stream")
async def stream(request: Request, payload: StreamRequest):
    """
    Server-Sent Events (SSE) streaming endpoint for real-time graph execution monitoring.
    
    This endpoint provides a live stream of the graph's execution state, allowing clients
    to monitor progress in real-time rather than waiting for the entire process to complete.
    
    Args:
        request (Request): FastAPI request object for checking client connection status
        payload (StreamRequest): Validated request containing review_text, thread_id, and mode
        
    Returns:
        StreamingResponse: Server-Sent Events stream of graph execution data
    """
    
    # Extract values from the validated Pydantic payload
    review_text = payload.review_text
    thread_id = payload.thread_id
    mode = payload.mode
    
    # Inner async generator function that yields SSE events
    async def eventgen() -> AsyncIterator[bytes]:
        try:
            # Stream the graph execution in real-time
            # IMPORTANT: Pass the review_text as input so the graph can actually run
            # The config parameter sets the thread_id for state management
            async for ev in graph.astream(
                {"original_text": review_text},  # Input data for the graph (must match GraphState.original_text)
                config={"configurable": {"thread_id": thread_id}},  # Thread configuration for state persistence
                stream_mode=mode,  # "updates" or "values" mode
            ):
                # Format each event as an SSE data line and encode as UTF-8 bytes
                # The 'default=str' parameter handles non-serializable objects by converting them to strings
                yield f"data: {json.dumps(ev, default=str)}\n\n".encode("utf-8")
                
                # Check if the client has disconnected to stop unnecessary processing
                if await request.is_disconnected():
                    break
                    
        except Exception as e:
            # If an error occurs during streaming, send an error event to the client
            yield f"data: {json.dumps({'error': str(e)}, default=str)}\n\n".encode("utf-8")

    # Return a streaming response with the appropriate MIME type for Server-Sent Events
    return StreamingResponse(eventgen(), media_type="text/event-stream")

# =============================================================================
# MAIN EXECUTION BLOCK
# =============================================================================
if __name__ == "__main__":
    # Server configuration constants
    HOST = "localhost"  # Server hostname (change to "0.0.0.0" for external access)
    PORT = 8000         # Server port number
    
    # Print startup information for developers
    print(f"Starting FastAPI service on {HOST}:{PORT}")
    print(f"API documentation available at: http://{HOST}:{PORT}/docs")
    print(f"Alternative API docs at: http://{HOST}:{PORT}/redoc")
    
    # Start the uvicorn ASGI server
    uvicorn.run(
        "agent_service:app",  # Module path to the FastAPI app instance
        host=HOST,         # Host to bind to
        port=PORT,         # Port to listen on
        reload=True,       # Enable auto-reload during development (restart on file changes)
        log_level="info"   # Logging level for the server
    )
