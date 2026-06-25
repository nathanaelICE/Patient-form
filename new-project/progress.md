# Patient Registration Harness — Progress Ledger

## Status: Tests Pending (all other tasks complete)

## Tasks

- [x] Task 1 (Tab 1): Database Layer — `database.py`, `models.py`
  - [x] Implement SQLite engine and session dependency
  - [x] Define `Patient` SQLModel table class
  - [x] Define `Visit` SQLModel table class
  - [x] Export `create_db_and_tables()`

- [x] Task 2 (Tab 2): Backend — `schemas.py`, `routers/`, `main.py`
  - [x] Define `PatientCreate`, `PatientRead`, `VisitCreate`, `VisitRead` schemas
  - [x] Implement patient endpoints (`POST /api/patients`, `GET /api/patients`, `GET /api/patients/{id}`)
  - [x] Implement visit endpoints (`POST /api/patients/{id}/visits`, `GET /api/patients/{id}/visits`)
  - [x] Wire routers and `create_db_and_tables()` into `main.py`

- [x] Task 3 (Tab 3): Frontend — `public/`
  - [x] Patient list page with register modal (`index.html`)
  - [x] Patient detail page with visit history and add-visit modal (`patient.html`)
  - [x] Wire up all `fetch()` calls against `/api/...`

- [ ] Task 4: Tests — `tests/`
  - [ ] Write patient endpoint tests (`test_patients.py`)
  - [ ] Write visit endpoint tests (`test_visits.py`)

## Commits

- 987bf80 — feat: initialize patient registration harness (skeleton, all stubs)
- eb0a0a7 — chore: remove snake-premium and unrelated files, keep only new-project
