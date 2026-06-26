# Backend

**Stack:** FastAPI (Python 3.12), UV

## Files
| Path | Purpose |
|---|---|
| `main.py` | FastAPI app entry point, mounts StaticFiles, wires routers |
| `schemas.py` | Pydantic request/response models |
| `routers/patients.py` | `/api/patients` endpoints |
| `routers/visits.py` | `/api/patients/{id}/visits` endpoints |
| `tests/` | Pytest test files |

## Environment
| Variable | Required | Example |
|---|---|---|
| `DATABASE_URL` | Yes | `postgresql://user:pass@localhost:5432/dbname` |
| `ADMIN_USERNAME` | No (default: `admin`) | `admin` |
| `ADMIN_PASSWORD` | No (default: `changeme123`) | `s3cr3t` |

## Rules
- One router file per resource — do not mix concerns
- All routes prefixed `/api`
- `DATABASE_URL` must be present in the environment before the app starts
- Depends on Database agent completing `models.py` before implementing endpoints
