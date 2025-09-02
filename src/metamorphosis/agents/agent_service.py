# =============================================================================
#  Filename: agent_service.py
#
#  Short Description: FastAPI service for the self-reviewer agent(s) for the periodic employee self-review process.
#
#  Creation date: 2025-09-01
#  Author: Chandar L
# =============================================================================

"""
FastAPI Agent Service for Self-Review Processing

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

The service acts as a bridge between web clients and the underlying LangGraph
workflow, providing both traditional request-response patterns and modern
streaming capabilities for real-time user experience.
"""

# =============================================================================
# IMPORTS AND DEPENDENCIES
# =============================================================================

# Core FastAPI framework components for building high-performance async web APIs
from fastapi import FastAPI, Request  # Main FastAPI app and request handling
# Response types for handling different HTTP response formats
from fastapi.responses import JSONResponse, StreamingResponse  # JSON and streaming responses
# Type hint for async generators/iterators used in streaming endpoints
from typing import AsyncIterator  # Async generator type annotation
# Standard library imports for JSON handling and UUID generation
import json  # JSON serialization/deserialization
import uvicorn  # ASGI server for running the FastAPI application
# Pydantic for data validation, serialization, and automatic API documentation
from pydantic import BaseModel, Field  # Data models and field validation
# CORS middleware for handling cross-origin requests from web browsers
from fastapi.middleware.cors import CORSMiddleware  # Cross-Origin Resource Sharing
# Import our custom LangGraph implementation and execution function
from metamorphosis.agents.self_reviewer import graph, run_graph  # Pre-built graph and execution wrapper
# UUID generation for unique thread identification and state management
import uuid  # Unique identifier generation for conversation threads

# =============================================================================
# DATA MODELS AND SCHEMAS
# =============================================================================

# Pydantic model for incoming API requests to the /invoke endpoint
class InvokeRequest(BaseModel):
    """
    Request model for synchronous self-review processing.
    
    This model defines the structure and validation rules for incoming requests
    to the /invoke endpoint. It ensures that all required data is present and
    properly formatted before processing begins.
    
    The model includes automatic validation, serialization, and API documentation
    generation through Pydantic's integration with FastAPI.
    """
    # Required field: the review text to be processed through the LangGraph pipeline
    # This is the primary input that will go through copy editing, summarization, and word cloud generation
    review_text: str = Field(..., description="The review text to process through the LangGraph", 
        example='''
        I had an eventful cycle this summer.  Learnt agentic workflows and implemented a self-reviewer agent 
        for the periodic employee self-review process.  It significantly improved employee productivity for the organization.
        ''')
    # Optional field: thread ID for maintaining conversation state across requests
    # If not provided, a new UUID will be generated automatically to ensure state isolation
    # This enables resumable conversations and state persistence across multiple API calls
    thread_id: str = Field(None, description="Optional thread ID for state persistence. If not provided, a new UUID will be generated.", example="thread_123")

# Pydantic model for streaming requests to the /stream endpoint
class StreamRequest(BaseModel):
    """
    Request model for streaming self-review processing via Server-Sent Events (SSE).
    
    This model defines the structure for real-time streaming requests that provide
    live updates of the workflow execution. Unlike the synchronous /invoke endpoint,
    this endpoint streams intermediate results as they become available.
    
    The streaming capability enables real-time user feedback and progress monitoring
    for long-running text processing operations.
    """
    # Required field: the review text to be processed through the LangGraph pipeline
    # Same as InvokeRequest - the primary input for the workflow
    review_text: str = Field(..., description="The review text to process through the LangGraph")
    # Required field: thread ID for maintaining conversation state across streaming events
    # Unlike InvokeRequest, this is required for streaming to ensure proper state management
    thread_id: str = Field(..., description="Unique identifier for the conversation thread")
    # Optional field: streaming mode that controls what data is sent in each event
    # "updates": Only send state changes (more efficient, less data)
    # "values": Send complete state after each step (more comprehensive, more data)
    mode: str = Field("values", description="Streaming mode - 'updates' for state changes only, 'values' for full state each step")

# Pydantic model for API responses from the /invoke endpoint
class InvokeResponse(BaseModel):
    """
    Response model for synchronous self-review processing results.
    
    This model defines the structure of the complete processing results returned
    by the /invoke endpoint. It mirrors the GraphState structure from the LangGraph
    workflow, ensuring consistent data representation across the API layer.
    
    All fields except original_text are optional to handle cases where processing
    might fail at intermediate steps, allowing partial results to be returned.
    """
    # The original review text that was processed (always present as it's the input)
    original_text: str = Field(..., description="The original review text")
    # The copy-edited text with grammar and clarity improvements (from copy_editor_node)
    copy_edited_text: str = Field(None, description="The copy-edited text")
    # The abstractive summary of the copy-edited text (from summarizer_node)
    summary: str = Field(None, description="The summary of the copy-edited text")
    # The file path to the generated word cloud image (from wordcloud_node)
    word_cloud_path: str = Field(None, description="The path to the word cloud image")

# =============================================================================
# FASTAPI APPLICATION SETUP
# =============================================================================

# Initialize the FastAPI application with comprehensive metadata and configuration
# This creates the main application instance that will handle all HTTP requests
app = FastAPI(
    title="LangGraph for FastAPI Service",
    description="A FastAPI service that integrates with LangGraph for processing self-review texts through a multi-stage pipeline",
    version="1.0.0",
    docs_url="/docs",      # Swagger UI documentation endpoint for interactive API testing
    redoc_url="/redoc"     # ReDoc alternative documentation endpoint with enhanced styling
)

# =============================================================================
# MIDDLEWARE CONFIGURATION
# =============================================================================

# Add CORS middleware to handle cross-origin requests from web browsers
# This is essential for frontend applications running on different domains/ports
# to communicate with this API service
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],   # WARNING: Allow all origins - tighten this in production!
    allow_credentials=True, # Allow cookies and authentication headers to be sent
    allow_methods=["*"],   # Allow all HTTP methods (GET, POST, PUT, DELETE, etc.)
    allow_headers=["*"],   # Allow all request headers to be sent
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
    Main endpoint for synchronous processing of self-review text through the LangGraph pipeline.
    
    This endpoint provides a traditional request-response pattern for processing self-review
    text. It executes the complete workflow and returns all results once processing is finished.
    
    Processing Pipeline:
    1. Copy editing: Grammar and clarity improvements
    2. Summarization: Abstractive summary generation (parallel)
    3. Word cloud: Visual representation generation (parallel)
    
    The endpoint supports state persistence through thread_id, allowing for resumable
    conversations and state inspection across multiple requests.
    
    Args:
        payload (InvokeRequest): Validated request containing:
            - review_text: The self-review text to process
            - thread_id: Optional thread ID for state persistence
            
    Returns:
        JSONResponse: Complete processing results containing:
            - original_text: The input text
            - copy_edited_text: Grammar-improved version
            - summary: Abstractive summary
            - word_cloud_path: Path to generated word cloud image
        JSONResponse: Error response with 500 status code if processing fails
        
    Raises:
        Exception: Various exceptions can occur during graph execution, tool failures, or network issues
    """
    # Extract values from the validated Pydantic payload
    # The payload has already been validated by FastAPI/Pydantic before reaching this function
    review_text = payload.review_text
    # Generate a new UUID if no thread_id was provided, ensuring each request has a unique identifier
    # This prevents state collision between different users/sessions
    thread_id = payload.thread_id or str(uuid.uuid4())

    try:
        # Execute the LangGraph with the given review text and thread_id
        # This kicks off the multi-stage pipeline: copy editing -> summarization -> word cloud generation
        # The run_graph function handles the complete workflow execution and returns the final state
        result = await run_graph(graph, review_text, thread_id)
        return JSONResponse(result)
    except Exception as e:
        # Return a 500 error with details if the graph execution fails
        # This could happen due to graph compilation issues, runtime errors, or external service failures
        # The error message is included to help with debugging while maintaining security
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
    It's particularly useful for long-running text processing operations where users
    benefit from seeing intermediate results and progress updates.
    
    The streaming implementation uses Server-Sent Events (SSE) which provides:
    - Real-time updates as each workflow node completes
    - Automatic reconnection handling by browsers
    - Efficient one-way communication from server to client
    - Built-in support for JSON data transmission
    
    Args:
        request (Request): FastAPI request object for checking client connection status
        payload (StreamRequest): Validated request containing:
            - review_text: The self-review text to process
            - thread_id: Required thread ID for state management
            - mode: Streaming mode ("updates" or "values")
        
    Returns:
        StreamingResponse: Server-Sent Events stream containing:
            - Real-time workflow execution updates
            - Intermediate processing results
            - Error messages if processing fails
            - Connection status monitoring
            
    Note:
        The client can disconnect at any time, and the server will detect this
        and stop processing to conserve resources.
    """
    
    # Extract values from the validated Pydantic payload
    # All fields are required for streaming to ensure proper state management
    review_text = payload.review_text
    thread_id = payload.thread_id
    mode = payload.mode
    
    # Inner async generator function that yields SSE events
    # This function runs in the background and streams data to the client
    async def eventgen() -> AsyncIterator[bytes]:
        try:
            # Stream the graph execution in real-time using LangGraph's astream method
            # This provides live updates as each node in the workflow completes
            async for ev in graph.astream(
                {"original_text": review_text},  # Input data for the graph (must match GraphState.original_text)
                config={"configurable": {"thread_id": thread_id}},  # Thread configuration for state persistence
                stream_mode=mode,  # "updates" or "values" mode - controls what data is sent
            ):
                # Format each event as an SSE data line and encode as UTF-8 bytes
                # The 'default=str' parameter handles non-serializable objects by converting them to strings
                # SSE format: "data: {json_data}\n\n"
                yield f"data: {json.dumps(ev, default=str)}\n\n".encode("utf-8")
                
                # Check if the client has disconnected to stop unnecessary processing
                # This prevents wasting resources on clients that are no longer listening
                if await request.is_disconnected():
                    break
                    
        except Exception as e:
            # If an error occurs during streaming, send an error event to the client
            # This ensures the client is informed of failures rather than hanging indefinitely
            yield f"data: {json.dumps({'error': str(e)}, default=str)}\n\n".encode("utf-8")

    # Return a streaming response with the appropriate MIME type for Server-Sent Events
    # The media_type "text/event-stream" tells browsers to handle this as an SSE connection
    return StreamingResponse(eventgen(), media_type="text/event-stream")

# =============================================================================
# MAIN EXECUTION BLOCK
# =============================================================================

if __name__ == "__main__":
    """
    Main execution block for running the FastAPI service in development mode.
    
    This block runs when the script is executed directly (not imported as a module).
    It configures and starts the uvicorn ASGI server with development-friendly settings.
    
    Development Configuration:
    - Auto-reload enabled for rapid development iteration
    - Localhost binding for security (change to 0.0.0.0 for external access)
    - Info-level logging for debugging
    - Interactive API documentation available
    
    Production Considerations:
    - Disable auto-reload in production
    - Use proper logging configuration
    - Configure proper CORS origins
    - Use a production ASGI server like Gunicorn with uvicorn workers
    """
    
    # Server configuration constants
    HOST = "localhost"  # Server hostname (change to "0.0.0.0" for external access)
    PORT = 8000         # Server port number
    
    # Print startup information for developers
    # This helps developers know where to access the service and documentation
    print(f"Starting FastAPI service on {HOST}:{PORT}")
    print(f"API documentation available at: http://{HOST}:{PORT}/docs")
    print(f"Alternative API docs at: http://{HOST}:{PORT}/redoc")
    
    # Start the uvicorn ASGI server with development configuration
    uvicorn.run(
        "agent_service:app",  # Module path to the FastAPI app instance
        host=HOST,         # Host to bind to (localhost for development security)
        port=PORT,         # Port to listen on
        reload=True,       # Enable auto-reload during development (restart on file changes)
        log_level="info"   # Logging level for the server (info provides good debugging info)
    )
