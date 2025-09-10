### Slides: Metamorphosis — Learning AI Agents by Building One

> Lightweight slide deck in Markdown (works well with Reveal.js or as handout)

---

## Why agents?
- Small, clear steps
- Compose simple capabilities
- Learn by building

---

## The three moving parts
- Workflow (LangGraph)
- Tools (MCP)
- State (small dict)

```mermaid
flowchart LR
    UX[WorkflowExecutor] --> GB[GraphBuilder]
    GB --> N[WorkflowNodes]
    N --> S[(GraphState)]
    N --> MCP[MCP Tools]
```

---

## The workflow sketch
```mermaid
flowchart LR
    A[START] --> B[Copy Editor]
    B --> C[Summarizer]
    B --> D[Word Cloud]
    B --> E[Achievements Extractor]
    E -->|if tools| F[ToolNode]
    F --> G[After Achievements Parser]
    G --> H[Review Text Evaluator]
    H -->|if tools| I[ToolNode]
    I --> J[After Evaluation Parser]
    C --> K[END]
    D --> K
    J --> K
```

---

## Demo steps
1. Initialize `WorkflowExecutor`
2. Run workflow on sample text
3. Watch events: copy edit → summary → word cloud
4. Show achievements and evaluation branches

---

## Lessons
- Keep nodes tiny and readable
- Validate inputs/outputs
- Prefer simple branches over clever logic



