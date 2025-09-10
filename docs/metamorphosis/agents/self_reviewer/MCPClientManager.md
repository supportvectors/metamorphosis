### MCPClientManager

::: metamorphosis.agents.self_reviewer.client.MCPClientManager

## Purpose

Wraps `MultiServerMCPClient` so nodes can look up tools by name and call them.

## Tool lookup flow

```mermaid
%%{init: {'theme': 'base', 'themeVariables': { 'primaryColor': '#e0f2ff', 'edgeLabelBackground':'#ffffffaa', 'clusterBkg':'#f7fbff', 'fontFamily':'Inter'}}}%%
sequenceDiagram
    participant Node
    participant MCP as MCPClientManager
    participant Srv as MCP Server

    Node->>MCP: get_tool("copy_edit")
    MCP->>Srv: get_tools()
    Srv-->>MCP: [copy_edit, abstractive_summarize, word_cloud]
    MCP-->>Node: Tool(copy_edit)
    Node->>Tool: ainvoke({text})
    Tool-->>Node: result
```



