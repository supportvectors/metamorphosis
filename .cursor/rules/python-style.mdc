---
description: 
globs: 
alwaysApply: true
---
---
# Maintainer: @backend‑guild
description: Core language version, style, and general coding mandates.
requiredTools:
  - uv>=0.1.39
  - ruff>=0.4.0
alwaysApply: true
---

### Language & Tooling
- **Python 3.12+** – use new features when they simplify code.
- Dependency management: **`uv`** (`pyproject.toml` is source of truth).
- Formatting & linting: **`ruff`** (`ruff check .` and `ruff format` in CI).
- Strict **type annotations** everywhere (functions, methods, class members).
- Docstrings: **Google style**.
- Logging: **`loguru`** only – never `print` in production code (allowed inside exploratory notebooks).

### Pythonic Practices
1. **Elegance & Readability** – favour clear, idiomatic code that future maintainers grasp at a glance; optimise *after* clarity is achieved.
2. **Object‑oriented first** – unless a functional script is clearly superior.
3. **PEP 8** compliance via Ruff; favour explicit over implicit behaviour.
4. Apply **optimal** design patterns *only when they materially improve clarity, testability, or extensibility*; **do not over‑engineer** by adding patterns that introduce needless indirection or complexity.
5. Keep the **Zen of Python** in mind when choosing APIs.

### Modular Design
- Follow the **Single Responsibility Principle** for modules.
- Build **reusable components** — design functions and classes that can be safely composed across pipelines and projects.
- Prefer **composition over inheritance**; package logically.

### Performance & Concurrency
- Use `async`/`await` for I/O‑bound work.
- Employ `functools.lru_cache`/`@cache` for deterministic pure functions.
- Use `psutil` for resource monitoring; release memory promptly.

### Code Example Requirements
- All public APIs typed & documented.
- Include usage snippets (`__main__` or `tests/`).
- Handle errors with specific exceptions; never bare `except:`.

### CI Reference
A full sample workflow is available in `@.github/workflows/ci.yml`.

