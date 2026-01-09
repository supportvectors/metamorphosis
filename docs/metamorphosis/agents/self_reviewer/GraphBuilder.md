### GraphBuilder

::: metamorphosis.agents.self_reviewer.graph_builder.GraphBuilder

## Purpose

Builds the LangGraph by adding nodes, wiring edges, and enabling a simple in‑memory checkpoint.

## Workflow outline

```mermaid
%%{init: {'theme': 'base', 'themeVariables': { 'primaryColor': '#e0f2ff', 'edgeLabelBackground':'#ffffffaa', 'clusterBkg':'#f7fbff', 'fontFamily':'Inter'}}}%%
graph LR
    START([START]) --> CE[copy_editor]
    CE --> SUM[summarizer]
    CE --> WC[wordcloud]
    CE --> AE[achievements_extractor]
    AE -->|tools?| AET[achievements_extractor_tool_node]
    AET --> AEP[after_achievements_parser]
    AEP --> EV[review_text_evaluator]
    EV -->|tools?| EVT[review_text_evaluator_tool_node]
    EVT --> EVP[after_evaluation_parser]
    SUM --> END([END])
    WC --> END
    EVP --> END
```







