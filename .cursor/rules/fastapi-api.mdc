---
description: 
globs: 
alwaysApply: true
---
---
# Maintainer: @platform‑team
description: API layer expectations.
globs: "app/api/**"
---

- Framework: **FastAPI** with `APIRouter` per resource.
- Use **Pydantic** models for request/response validation; enforce `model_config` strictness.
- Dependency Injection: use `Depends` for DB sessions, settings, and auth.
- Security: OAuth 2 + JWT as default; hash secrets with `argon2‑cffi`.
- Background tasks: FastAPI `BackgroundTasks`; offload heavy jobs to `ray` or Celery.
- Versioning: prefix routes (`/v1/…`).
- CORS: lock down origins; expose only allowed headers.
- Run **`uvicorn --workers 1 --loop uvloop --http h11 --proxy-headers`** behind **Nginx** or **Caddy**.