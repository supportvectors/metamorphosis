# Agents Package

The `metamorphosis.agents` package includes LangGraph-based agent workflows for multi‑stage text processing. It offers simple synchronous and streaming examples via a small FastAPI service.

## Package Architecture

```mermaid
%%{init: {'theme': 'base', 'themeVariables': { 'primaryColor': '#e0f2ff', 'edgeLabelBackground':'#ffffffaa', 'clusterBkg':'#f7fbff', 'fontFamily':'Inter'}}}%%
graph TB
    subgraph "FastAPI Service Layer"
        A[agent_service.py<br/>REST API Endpoints]
        B[Request/Response Models<br/>Pydantic Schemas]
    end

    subgraph "LangGraph Workflow Layer"
        C[WorkflowExecutor<br/>executor.py]
        D[GraphState<br/>state.py]
        E[Workflow Nodes<br/>nodes.py]
        GB[GraphBuilder<br/>graph_builder.py]
    end

    subgraph "Processing Integration"
        F[MCP Tools<br/>text_modifiers via MCP]
        G[External Services<br/>Word Cloud Generation]
    end

    subgraph "State Management"
        H[Thread-based Storage<br/>Conversation Persistence]
        I[Streaming Events<br/>Real-time Updates]
    end

    A --> C
    A --> B
    C --> GB
    GB --> D
    GB --> E
    E --> F
    E --> G
    D --> H
    A --> I
```

## Core Components

### 1. FastAPI Service (`agent_service.py`)

The main service provides REST API endpoints for text processing workflows.

### 2. LangGraph Workflow (`self_reviewer/`)

Implements a clear multi-step learning example.

```mermaid
%%{init: {'theme': 'base', 'themeVariables': { 'primaryColor': '#e0f2ff', 'edgeLabelBackground':'#ffffffaa', 'clusterBkg':'#f7fbff', 'fontFamily':'Inter'}}}%%
graph LR
    A[START] --> B[Copy Editor]
    B --> C[Summarizer]
    B --> D[Word Cloud]
    B --> E[Achievements Extractor]
    E -->|if tools| F[ToolNode: extract_achievements]
    F --> G[After Achievements Parser]
    G --> H[Review Text Evaluator]
    H -->|if tools| I[ToolNode: evaluate_review_text]
    I --> J[After Evaluation Parser]
    C --> K[END]
    D --> K
    J --> K
```

## Module Documentation

### Core Modules

| Module | Description | Key Components |
|--------|-------------|----------------|
| [`self_reviewer/`](self_reviewer/index.md) | LangGraph workflow implementation | Workflow nodes, state management |
| [`WorkflowExecutor`](self_reviewer/WorkflowExecutor.md) | Entry point for running the workflow | initialize, run_workflow |
| [`GraphBuilder`](self_reviewer/GraphBuilder.md) | Graph construction | nodes, edges, memory |
| [`WorkflowNodes`](self_reviewer/WorkflowNodes.md) | Node implementations | copy edit, summarize, word cloud, tools |
| [`MCPClientManager`](self_reviewer/MCPClientManager.md) | MCP client wrapper | get_tool, list_available_tools |
| [`GraphState`](self_reviewer/GraphState.md) | Workflow state | fields and transitions |

## Workflow Architecture

### Processing Flow

```mermaid
sequenceDiagram
    participant Client
    participant FastAPI
    participant LangGraph
    participant CopyEditor
    participant Summarizer
    participant WordCloud
    
    Client->>FastAPI: POST /stream
    FastAPI->>FastAPI: Generate thread_id
    FastAPI->>LangGraph: run
    
    LangGraph->>CopyEditor: Process text
    CopyEditor->>LangGraph: Edited text
    
    par Parallel Processing
        LangGraph->>Summarizer: Generate summary
        Summarizer->>LangGraph: Summary result
    and
        LangGraph->>WordCloud: Create visualization
        WordCloud->>LangGraph: Image path
    end
    
    LangGraph->>FastAPI: Stream events
    FastAPI->>Client: SSE events
```

---

This package aims for clarity, so newcomers can learn agent workflows step by step.
