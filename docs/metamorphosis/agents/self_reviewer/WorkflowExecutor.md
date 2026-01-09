### WorkflowExecutor

::: metamorphosis.agents.self_reviewer.executor.WorkflowExecutor

## What it does

The `WorkflowExecutor` is the friendly entry point. It initializes the MCP client, builds the LangGraph, and runs the workflow for a given piece of text and `thread_id`.

## Typical use

```python
import asyncio
from metamorphosis.agents.self_reviewer import WorkflowExecutor

async def main():
    ex = WorkflowExecutor()
    await ex.initialize()
    result = await ex.run_workflow("Your self‑review text here", thread_id="demo-1")
    print(result)

asyncio.run(main())
```

## Small class diagram

```mermaid
%%{init: {'theme': 'base', 'themeVariables': { 'primaryColor': '#e0f2ff', 'edgeLabelBackground':'#ffffffaa', 'clusterBkg':'#f7fbff', 'fontFamily':'Inter'}}}%%
classDiagram
    class WorkflowExecutor {
        +initialize() async
        +run_workflow(review_text, thread_id) async dict|None
        +list_available_tools() list~str~
        +get_graph_visualization() str
        +close() async
        +is_initialized: bool
    }
    WorkflowExecutor --> MCPClientManager
    WorkflowExecutor --> GraphBuilder
    WorkflowExecutor --> WorkflowNodes
```







