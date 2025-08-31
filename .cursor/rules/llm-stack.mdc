---
description: 
globs: 
alwaysApply: true
---
---
# Maintainer: @llm‑guild
description: Conventions for LLM pipelines & ML engineering.
globs:
  - "src/llm/**"
  - "src/agents/**"
  - "src/pipelines/**"
---

### Libraries & Frameworks
- Prefer **Hugging Face Transformers** for model loading; `device_map="auto"`, `torch_dtype="auto"`.
- Orchestrate multi‑step chains with **LangGraph** (or CrewAI if justified).
- Retrieval: **LlamaIndex** by default; *LLM team lead to reassess alternatives quarterly*.
- Vector DB: **Qdrant** via HTTP or gRPC driver.

### Prompt Management
- Store templates under `prompts/` – plain Jinja2; version every change.
- Keep prompt revisions in Git for auditability.

### Experimentation & Tracking
- Config: YAML files under `configs/`.
- Track runs with **MLflow**; log params, metrics, artifacts, commit SHA.
- Hyper‑parameter search: **Optuna** preferred; log in the same MLflow run.

### Context & Memory Handling
- Manage chat context with `collections.deque` or specialised memory object.
- Stream tokens via FastAPI `EventSourceResponse` when beneficial.

### Safety & Ethics
- Run generated content through `openai_moderation()` (or equivalent) before external display.
- Log moderation outcomes.