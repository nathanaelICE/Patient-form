# Patient Registration Harness

## Stack
- **Backend:** FastAPI (Python 3.12)
- **Database:** SQLite via SQLModel
- **Package manager:** UV
- **Frontend:** Vanilla HTML/CSS/JS (served by FastAPI StaticFiles)

## Commands
```bash
# Install dependencies
uv sync

# Run dev server (auto-reload)
uv run uvicorn main:app --reload

# Run tests
uv run pytest
```

App runs at `http://localhost:8000`.
API docs at `http://localhost:8000/docs`.

## File Conventions
| Path | Purpose |
|---|---|
| `main.py` | FastAPI app entry point |
| `database.py` | SQLite engine, session dependency, table init |
| `models.py` | SQLModel table definitions (Patient, Visit) |
| `schemas.py` | Pydantic request/response models |
| `routers/patients.py` | `/api/patients` endpoints |
| `routers/visits.py` | `/api/patients/{id}/visits` endpoints |
| `public/` | Static frontend files served at `/` |
| `tests/` | Pytest test files |

## Rules
- Never commit `registration.db` or `.env`
- Keep each router file focused on its own resource only
- All API routes are prefixed with `/api`
- Frontend communicates with backend only via `fetch()` against `/api/...`
