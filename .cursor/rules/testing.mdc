---
description: 
globs: 
alwaysApply: true
---
---
# Maintainer: @qa‑team
description: Testing, coverage, and quality gates.
globs: "tests/**"
---

- Framework: **`pytest`** (install `pytest‑asyncio` via `[project.optional-dependencies.dev]`).
- Target ≥ **90 %** coverage (`pytest --cov=src --cov-fail-under=90`).
- Parametrise edge‑cases; test async flows with `pytest‑asyncio`.
- Use fixtures for expensive set‑up; mark long‑running tests `slow`.
- Ensure Ruff passes on test code too (style parity).