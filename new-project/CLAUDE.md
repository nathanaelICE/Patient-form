# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this is

A patient-registration / medical-visit app. FastAPI + SQLModel (Postgres) backend at the
repo root, plus a React + TypeScript SPA under `frontend/`. In production the backend serves
the compiled SPA, so it ships as a single service.

## Commands

Backend (Python 3.12, managed with `uv`):

```bash
uv sync                              # install deps (incl. dev) from uv.lock
uv run uvicorn main:app --reload     # run API at :8000 (needs DATABASE_URL set)
uv run pytest                        # run all backend tests
uv run pytest tests/test_patients.py::test_create_patient   # single test
```

Frontend (from `frontend/`):

```bash
npm install
npm run dev        # Vite dev server at :5173, proxies /api -> :8000
npm run build      # type-check (tsc -b) + build production bundle into frontend/dist
npm test           # vitest run (jsdom + testing-library)
npm run test:watch
```

`DATABASE_URL` is required for the backend to import (it reads it at module load in
`database.py`). Tests don't need it — they use an in-memory SQLite engine via fixtures.

## Architecture

**Layering (backend).** Keep these roles separate when editing:
- `models.py` — SQLModel `table=True` classes (DB schema only: `Patient`, `Visit`, `Claim`,
  `AdminUser`).
- `schemas.py` — Pydantic request/response models with all validation (`field_validator`s for
  blank checks, gender enum, future-DOB, phone regex, and claim status/type/method enums).
  Validation lives here, **not** in models.
- `ocr_service.py` — Gemini-vision service that extracts patient fields from an uploaded image.
- `routers/` — endpoints grouped by resource (`patients`, `visits`, `claims`, `ocr`, `auth`),
  each an `APIRouter`. Claims are nested under `/api/patients/{id}/claims`; OCR exposes
  admin-only `/api/ocr/extract` and `/api/ocr/status`.
- `deps.py` — shared FastAPI dependencies (notably `get_admin`).
- `database.py` — engine, session factory, table creation, admin seeding.
- `main.py` — app assembly: registers routers, re-exposes docs behind auth, mounts the SPA.

**Two distinct auth mechanisms — don't conflate them:**
1. *App API* uses a cookie session. `POST /api/login` verifies the admin (bcrypt) and stores a
   uuid → admin-id mapping in `app.state.sessions` (an **in-memory dict**), setting an
   httponly `session_id` cookie. `get_admin` (in `deps.py`) gates every app endpoint
   (patients, visits, claims, OCR).
   Because sessions live in memory, **all logins are dropped on restart**, and this won't work
   across multiple backend replicas.
2. *API docs* (`/docs`, `/redoc`, `/openapi.json`) are disabled by default and re-exposed in
   `main.py` behind HTTP Basic using the admin env credentials — a separate path from the cookie flow.

**Single admin, env-authoritative.** There's no user table beyond one admin. `seed_admin()` runs
on startup and **overwrites** the stored admin to match `ADMIN_USERNAME`/`ADMIN_PASSWORD` every
deploy, so changing those env vars rotates the password even on an already-seeded DB.

**Patients are soft-deleted** (`deleted_at` timestamp). Every patient query must filter
`deleted_at == None` — there's no hard delete. Visits and claims are not soft-deleted; claim
endpoints hard-delete, and every claim operation first resolves the patient through
`_get_live_patient` (404s on a soft-deleted patient) and validates that any `visit_id` belongs
to that patient.

**SPA serving.** `main.py` mounts `/assets` and adds a catch-all `/{full_path:path}` route that
returns `index.html`, so client-side routes work on refresh. API routers are registered *before*
the catch-all, so order matters — new API routes must be real router routes, not paths the
fallback would swallow. The fallback only activates when `frontend/dist` exists (i.e. after a build).

**Frontend data flow.** `src/api/client.ts` is the single fetch wrapper: `apiFetch` always sends
`credentials: 'include'` (for the session cookie) and throws `ApiError` on non-2xx.
`ApiError.fieldErrors()` maps FastAPI's 422 `detail` array to `{ field: message }` for form
display. Server state goes through React Query; routing via React Router with `ProtectedRoute`
guarding the authenticated pages (`AuthContext` tracks admin state via `GET /api/me`).

## Tests

- Backend: `tests/conftest.py` provides `session` (fresh in-memory SQLite per test), `client`
  (unauthenticated), and `admin_client` (logged-in). It overrides `get_session` and forces
  `COOKIE_SECURE=0` so the TestClient can carry the cookie over HTTP. Use `admin_client` for any
  endpoint behind `get_admin`.
- Frontend: vitest + jsdom; shared render helpers in `src/test-utils.tsx`, setup in `src/setupTests.ts`.

## Deployment — two separate paths

- **Single-image:** root `Dockerfile` builds the SPA, then builds the Python image and
  copies `dist` in; one container serves API + SPA on `$PORT`, deployable to any container host.
  (This was previously deployed on Railway with GitHub auto-deploy; that setup is now archived —
  see the README's "Archived: Railway deployment" and the `railway-deploy-v1` git tag.)
- **Multi-container (local/self-host):** `compose.yml` runs separate `db`, `backend`
  (`backend.Dockerfile`), `frontend` (`frontend/Dockerfile`), `pgadmin`, `caddy`, and
  `cloudflared` (Quick Tunnel — the public URL changes on every restart). Driven by `.env`
  (`POSTGRES_*`, `DATABASE_URL`, `ADMIN_*`, `PGADMIN_*`).

When changing backend deps or runtime, remember **both** the root `Dockerfile` and
`backend.Dockerfile` may need updating.
