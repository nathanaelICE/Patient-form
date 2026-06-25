# Patient Registration Harness

## Quick Start
```bash
uv sync                                  # install dependencies
uv run uvicorn main:app --reload         # dev server (auto-reload)
uv run pytest                            # run tests
```

App: `http://localhost:8000` — API docs: `http://localhost:8000/docs`

## Hard Constraints
- Never commit `registration.db` or `.env`
- All API routes prefixed `/api`
- Each router file owns one resource only
- Frontend communicates with backend only via `fetch()` against `/api/...`

## Topic Docs
- [Frontend](docs/agents-frontend.md)
- [Backend](docs/agents-backend.md)
- [Database](docs/agents-database.md)

## Agent Assignments
Three agents work in parallel, each owning specific files. Do not edit another agent's files.

### Agent 1 — Database
**Owns:** `database.py`, `models.py`
See [Database topic doc](docs/agents-database.md).

### Agent 2 — Backend
**Owns:** `schemas.py`, `routers/patients.py`, `routers/visits.py`, `main.py`
See [Backend topic doc](docs/agents-backend.md).
Depends on Agent 1 completing `models.py` before implementing endpoints.

### Agent 3 — Frontend
**Owns:** `public/index.html`, `public/patient.html`, `public/style.css`
See [Frontend topic doc](docs/agents-frontend.md).
Can build HTML/CSS structure independently; wire `fetch()` after Agent 2 is done.

## Dependency Order
1. Agent 1 finishes `models.py` → Agent 2 can implement endpoints
2. Agent 2 finishes API endpoints → Agent 3 can wire up `fetch()` calls
