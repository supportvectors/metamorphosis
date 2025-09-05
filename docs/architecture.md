# System Architecture

## Overview

The Metamorphosis system implements a sophisticated AI-powered text processing architecture using modern Python frameworks and design patterns. This document provides a comprehensive view of the system's architecture, component relationships, and data flow.

## High-Level Architecture

```mermaid
graph TB
    subgraph "Presentation Layer"
        UI[Streamlit UI]
        API[FastAPI REST API]
        CLI[Command Line Tools]
    end
    
    subgraph "Orchestration Layer"
        LG[LangGraph Workflows]
        AG[Agent Coordinator]
        SM[State Manager]
    end
    
    subgraph "Processing Layer"
        MCP[MCP Tools Server]
        TM[TextModifiers Core]
        WF[Workflow Nodes]
    end
    
    subgraph "Model Layer"
        MR[Model Registry]
        LLM1[Summarizer LLM]
        LLM2[Copy Editor LLM]
        LLM3[Achievements LLM]
        LLM4[Evaluator LLM]
    end
    
    subgraph "Data Layer"
        DM[Pydantic Models]
        ST[State Storage]
        FS[File System]
    end
    
    subgraph "External Services"
        OPENAI[OpenAI API]
        WC[Word Cloud Service]
    end
    
    UI --> API
    CLI --> MCP
    API --> LG
    LG --> AG
    AG --> SM
    SM --> WF
    WF --> TM
    TM --> MCP
    MCP --> MR
    MR --> LLM1
    MR --> LLM2
    MR --> LLM3
    MR --> LLM4
    LLM1 --> OPENAI
    LLM2 --> OPENAI
    LLM3 --> OPENAI
    LLM4 --> OPENAI
    WF --> WC
    TM --> DM
    SM --> ST
    ST --> FS
```

## Component Architecture

### Core Classes and Relationships

```mermaid
classDiagram
    class TextModifiers {
        -summarizer_llm: ChatOpenAI
        -copy_editor_llm: ChatOpenAI
        -key_achievements_llm: ChatOpenAI
        -review_text_evaluator_llm: ChatOpenAI
        +summarize(text, max_words) SummarizedText
        +rationalize_text(text) CopyEditedText
        +extract_achievements(text) AchievementsList
        +evaluate_review_text(text) ReviewScorecard
        +get_model_info(method) dict
        -_log_model_details_table(method)
    }
    
    class ModelRegistry {
        -_instance: ModelRegistry
        -_initialized: bool
        +summarizer_llm: ChatOpenAI
        +copy_editor_llm: ChatOpenAI
        +key_achievements_llm: ChatOpenAI
        +review_text_evaluator_llm: ChatOpenAI
        +__new__() ModelRegistry
        -_build_chat_openai(config, api_key) ChatOpenAI
    }
    
    class GraphState {
        +review_text: str
        +copy_edited_text: str | None
        +summary: str | None
        +word_cloud_path: str | None
    }
    
    class FastAPIApp {
        +invoke(request) InvokeResponse
        +stream(request) StreamingResponse
        +health() dict
    }
    
    class StreamlitUI {
        +patch_state(dst, delta) dict
        +stream_from_server(url, data) Iterator
        +extract_values_from_event(event) dict
    }
    
    class SummarizedText {
        +summarized_text: str
        +size: int
        +unit: str
    }
    
    class CopyEditedText {
        +copy_edited_text: str
        +size: int
        +is_edited: bool
    }
    
    class AchievementsList {
        +items: List[Achievement]
        +size: int
        +unit: str
    }
    
    class ReviewScorecard {
        +metrics: List[MetricScore]
        +overall: int
        +verdict: Verdict
        +notes: List[str]
        +radar_labels: List[str]
        +radar_values: List[int]
    }
    
    class Achievement {
        +title: str
        +outcome: str
        +impact_area: ImpactArea
        +metric_strings: List[str]
        +timeframe: Optional[str]
        +ownership_scope: Optional[OwnershipScope]
        +collaborators: List[str]
    }
    
    class MetricScore {
        +name: str
        +score: int
        +rationale: str
        +suggestion: str
    }
    
    TextModifiers --> ModelRegistry : uses
    TextModifiers --> SummarizedText : creates
    TextModifiers --> CopyEditedText : creates
    TextModifiers --> AchievementsList : creates
    TextModifiers --> ReviewScorecard : creates
    AchievementsList --> Achievement : contains
    ReviewScorecard --> MetricScore : contains
    FastAPIApp --> GraphState : manages
    StreamlitUI --> FastAPIApp : communicates
    GraphState --> TextModifiers : processes_with
```

## Data Flow Architecture

### Processing Pipeline

```mermaid
sequenceDiagram
    participant User
    participant UI as Streamlit UI
    participant API as FastAPI Service
    participant LG as LangGraph
    participant TM as TextModifiers
    participant LLM as OpenAI API
    participant FS as File System
    
    User->>UI: Enter review text
    UI->>API: POST /stream {text, thread_id}
    API->>API: Generate thread_id
    API->>LG: run_graph(text, thread_id)
    
    LG->>TM: rationalize_text(text)
    TM->>LLM: Copy editing request
    LLM->>TM: Edited text
    TM->>LG: CopyEditedText
    LG->>API: Stream event {copy_edited_text}
    API->>UI: SSE event
    
    par Parallel Processing
        LG->>TM: summarize(edited_text)
        TM->>LLM: Summarization request
        LLM->>TM: Summary
        TM->>LG: SummarizedText
        LG->>API: Stream event {summary}
        API->>UI: SSE event
    and
        LG->>FS: create_word_cloud(edited_text)
        FS->>LG: Word cloud path
        LG->>API: Stream event {word_cloud_path}
        API->>UI: SSE event
    end
    
    UI->>User: Display results
```

### State Management Flow

```mermaid
stateDiagram-v2
    [*] --> Initialized
    Initialized --> Processing: User submits text
    Processing --> CopyEditing: Start workflow
    CopyEditing --> ParallelProcessing: Text edited
    
    state ParallelProcessing {
        [*] --> Summarizing
        [*] --> WordCloudGen
        Summarizing --> SummaryComplete
        WordCloudGen --> WordCloudComplete
        SummaryComplete --> [*]
        WordCloudComplete --> [*]
    }
    
    ParallelProcessing --> Complete: All tasks done
    Complete --> [*]: Results delivered
    
    Processing --> Error: Exception occurred
    Error --> [*]: Error handled
```

## Design Patterns

### Singleton Pattern (Model Registry)

```python
class ModelRegistry:
    _instance = None
    _initialized = False
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(self):
        if not self._initialized:
            # Initialize LLM clients
            self._initialize_llms()
            self._initialized = True
```

### Factory Pattern (Configuration Loading)

```python
def get_model_registry() -> ModelRegistry:
    """Factory function for ModelRegistry singleton."""
    return ModelRegistry()

def _load_config() -> dict[str, Any]:
    """Factory for configuration loading with fallbacks."""
    # Configuration loading logic
    return config_data
```

### Strategy Pattern (Text Processing)

```python
class TextModifiers:
    def __init__(self):
        # Different strategies for different processing types
        self.strategies = {
            'summarize': self._create_summarizer_chain(),
            'copy_edit': self._create_copy_editor_chain(),
            'extract_achievements': self._create_achievements_chain(),
            'evaluate': self._create_evaluator_chain()
        }
```

### Observer Pattern (Streaming Events)

```python
async def _generate_stream_events(review_text: str, thread_id: str):
    """Observer pattern for streaming workflow events."""
    async for event in run_graph(graph, review_text, thread_id):
        # Notify observers (UI clients) of state changes
        yield f"data: {json.dumps(event)}\n\n".encode("utf-8")
```

### Decorator Pattern (Validation)

```python
@validate_call
def summarize(
    self,
    *,
    text: Annotated[str, Field(min_length=1)],
    max_words: Annotated[int, Field(gt=0)] = 300,
) -> SummarizedText:
    # Method implementation with automatic validation
```

## Security Architecture

### API Security

```mermaid
graph LR
    subgraph "Security Layers"
        A[CORS Middleware]
        B[Input Validation]
        C[Rate Limiting]
        D[Error Sanitization]
    end
    
    subgraph "Data Protection"
        E[Environment Variables]
        F[Secret Management]
        G[Input Sanitization]
    end
    
    Request --> A
    A --> B
    B --> C
    C --> D
    D --> Processing
    
    Processing --> E
    E --> F
    F --> G
```

### Configuration Security

- **API Key Management**: Environment variable isolation
- **Input Validation**: Pydantic model validation
- **Error Handling**: Sanitized error responses
- **CORS Configuration**: Restricted origins in production

## Performance Architecture

### Caching Strategy

```mermaid
graph TB
    subgraph "Caching Layers"
        A[LLM Client Cache<br/>Singleton Registry]
        B[Prompt Template Cache<br/>File System]
        C[Processing Results Cache<br/>LRU Cache]
    end
    
    subgraph "Performance Optimizations"
        D[Parallel Processing<br/>AsyncIO]
        E[Connection Pooling<br/>HTTP Clients]
        F[Resource Management<br/>Memory Cleanup]
    end
    
    Request --> A
    A --> B
    B --> C
    C --> D
    D --> E
    E --> F
    F --> Response
```

### Scalability Considerations

- **Horizontal Scaling**: Stateless service design
- **Load Balancing**: Multiple service instances
- **Resource Optimization**: Efficient memory usage
- **Connection Management**: HTTP connection pooling

## Error Handling Architecture

### Exception Hierarchy

```mermaid
classDiagram
    class Exception {
        +message: str
        +args: tuple
    }
    
    class ReviewError {
        +message: str
        +context: dict
        +operation: str
        +error_code: str
    }
    
    class ValidationError {
        +validation_context: dict
    }
    
    class PostconditionError {
        +postcondition_context: dict
    }
    
    class ConfigurationError {
        +config_context: dict
    }
    
    class MCPToolError {
        +tool_context: dict
    }
    
    class FileOperationError {
        +file_context: dict
    }
    
    Exception <|-- ReviewError
    ReviewError <|-- ValidationError
    ReviewError <|-- PostconditionError
    ReviewError <|-- ConfigurationError
    ReviewError <|-- MCPToolError
    ReviewError <|-- FileOperationError
```

### Error Flow

```mermaid
sequenceDiagram
    participant Client
    participant API
    participant Service
    participant LLM
    
    Client->>API: Request
    API->>Service: Process
    Service->>LLM: LLM Call
    LLM->>Service: Error Response
    Service->>Service: Create PostconditionError
    Service->>API: Structured Error
    API->>API: Log Error Context
    API->>Client: JSON Error Response
```

## Monitoring and Observability

### Logging Architecture

```mermaid
graph TB
    subgraph "Logging Sources"
        A[TextModifiers]
        B[Model Registry]
        C[FastAPI Service]
        D[LangGraph Workflows]
    end
    
    subgraph "Log Processing"
        E[Loguru Logger]
        F[Structured Logging]
        G[Log Aggregation]
    end
    
    subgraph "Output Destinations"
        H[Console Output]
        I[File Logs]
        J[Debug Logs]
    end
    
    A --> E
    B --> E
    C --> E
    D --> E
    E --> F
    F --> G
    G --> H
    G --> I
    G --> J
```

### Metrics Collection

- **Processing Metrics**: Token usage, processing time
- **Error Metrics**: Error rates, failure patterns  
- **Performance Metrics**: Response times, throughput
- **Resource Metrics**: Memory usage, CPU utilization

## Deployment Architecture

### Container Architecture

```mermaid
graph TB
    subgraph "Application Container"
        A[Python 3.12 Runtime]
        B[FastAPI Service]
        C[Streamlit UI]
        D[MCP Tools]
    end
    
    subgraph "Configuration"
        E[Environment Variables]
        F[Config Files]
        G[Prompt Templates]
    end
    
    subgraph "External Dependencies"
        H[OpenAI API]
        I[File System Storage]
    end
    
    A --> B
    A --> C
    A --> D
    E --> A
    F --> A
    G --> A
    B --> H
    D --> I
```

### Service Dependencies

- **Runtime**: Python 3.12+
- **Core Dependencies**: FastAPI, LangChain, Pydantic, Streamlit
- **AI Services**: OpenAI API
- **Utilities**: Rich, Plotly, Loguru
- **Development**: Ruff, Pytest, Radon

## Future Architecture Considerations

### Extensibility Points

1. **New Processing Types**: Additional text processing capabilities
2. **Multiple LLM Providers**: Support for different AI services
3. **Enhanced Workflows**: More complex multi-agent workflows
4. **Real-time Processing**: WebSocket-based real-time updates
5. **Batch Processing**: Large-scale document processing

### Scalability Enhancements

1. **Microservices**: Split into smaller, focused services
2. **Message Queues**: Asynchronous processing with queues
3. **Caching Layer**: Redis or similar for distributed caching
4. **Database Integration**: Persistent storage for results
5. **Load Balancing**: Multiple service instances

---

*This architecture documentation is maintained in sync with the system implementation and updated as the system evolves.*
