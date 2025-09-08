# Self-Reviewer Agents Refactoring Proposal

## Current State
- **File**: `src/metamorphosis/agents/self_reviewer_agents.py` (821 lines)
- **Issues**: Monolithic, procedural, violates SRP, hard to test/maintain

## Proposed Object-Oriented Architecture

### 1. Core Classes Structure

```
src/metamorphosis/agents/
├── __init__.py
├── self_reviewer/
│   ├── __init__.py
│   ├── client.py          # MCPClientManager class
│   ├── nodes.py           # WorkflowNodes class  
│   ├── graph_builder.py   # GraphBuilder class
│   ├── executor.py        # WorkflowExecutor class
│   ├── state.py           # GraphState + state management
│   └── tools.py           # Tool management utilities
├── review_tools.py        # (existing)
└── agent_service.py       # (existing - minimal changes)
```

### 2. Class Responsibilities

#### `MCPClientManager` (client.py)
```python
class MCPClientManager:
    """Manages MCP client connections and tool discovery."""
    
    def __init__(self, config: Optional[dict] = None)
    async def initialize(self) -> None
    def get_tool(self, tool_name: str) -> Tool
    def list_available_tools(self) -> List[str]
    async def close(self) -> None
```

#### `WorkflowNodes` (nodes.py)
```python
class WorkflowNodes:
    """Contains all workflow node implementations."""
    
    def __init__(self, mcp_client: MCPClientManager)
    async def copy_editor_node(self, state: GraphState) -> dict
    async def summarizer_node(self, state: GraphState) -> dict
    async def wordcloud_node(self, state: GraphState) -> dict
    async def achievements_extractor_node(self, state: GraphState) -> dict
    async def after_achievements_parser(self, state: GraphState) -> dict
    # ... other nodes
```

#### `GraphBuilder` (graph_builder.py)
```python
class GraphBuilder:
    """Builds and configures the LangGraph workflow."""
    
    def __init__(self, nodes: WorkflowNodes)
    async def build(self) -> StateGraph
    def _add_nodes(self, builder: StateGraph) -> None
    def _add_edges(self, builder: StateGraph) -> None
    def _add_conditional_edges(self, builder: StateGraph) -> None
```

#### `WorkflowExecutor` (executor.py)
```python
class WorkflowExecutor:
    """High-level interface for executing workflows."""
    
    def __init__(self, config: Optional[dict] = None)
    async def initialize(self) -> None
    async def run_workflow(self, review_text: str, thread_id: str = "main") -> dict
    async def test_workflow(self) -> dict
    def get_graph_visualization(self) -> str
```

### 3. Benefits of This Architecture

#### **Modularity**
- Each class has a single, clear responsibility
- Easy to test individual components in isolation
- Better code organization and navigation

#### **Extensibility**
- New node types can be added to `WorkflowNodes` without touching other classes
- Different graph configurations can be supported via `GraphBuilder` subclasses
- MCP client implementations can be swapped via `MCPClientManager`

#### **Testability**
- Mock dependencies easily (MCP client, individual nodes)
- Unit test each class independently
- Integration tests can focus on specific workflows

#### **Maintainability**
- Changes to node logic don't affect graph building
- MCP client issues are isolated to one class
- Clear separation of concerns makes debugging easier

#### **Consistency with Codebase**
- Follows the same patterns as `TextModifiers` and `ModelRegistry`
- Uses dependency injection like other classes
- Maintains the same error handling patterns

### 4. Migration Strategy

#### Phase 1: Extract Classes
1. Create the new directory structure
2. Move MCP client code to `MCPClientManager`
3. Move node functions to `WorkflowNodes` class
4. Create `GraphBuilder` with graph construction logic

#### Phase 2: Create Facade
1. Implement `WorkflowExecutor` as the main interface
2. Update imports in `agent_service.py`
3. Maintain backward compatibility

#### Phase 3: Clean Up
1. Remove the monolithic file
2. Update documentation
3. Add comprehensive tests for each class

### 5. Example Usage (After Refactoring)

```python
# Simple usage
executor = WorkflowExecutor()
await executor.initialize()
result = await executor.run_workflow("My self-review text...")

# Advanced usage with custom config
config = {"mcp_server_host": "localhost", "mcp_server_port": "3333"}
executor = WorkflowExecutor(config)
await executor.initialize()
result = await executor.run_workflow("My self-review text...", thread_id="session_123")
```

### 6. Alignment with Project Standards

- **Design-by-Contract**: All classes use `@validate_call`, `@require`, `@ensure`
- **Type Safety**: Full type annotations throughout
- **Error Handling**: Uses project's custom exception hierarchy
- **Logging**: Consistent `loguru` usage
- **Documentation**: Google-style docstrings for all classes/methods
- **Testing**: Each class designed for easy unit testing

This refactoring transforms the monolithic procedural code into a clean, object-oriented architecture that aligns with the rest of the codebase while maintaining all existing functionality.
