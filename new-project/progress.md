# Patient Registration Harness — Progress Ledger

## Status: In Progress

## Tasks

- [ ] Task 1 (Tab 1): Database Layer — `database.py`, `models.py`
  - [ ] Implement SQLite engine and session dependency
  - [ ] Define `Patient` SQLModel table class
  - [ ] Define `Visit` SQLModel table class
  - [ ] Export `create_db_and_tables()`

- [ ] Task 2 (Tab 2): Backend — `schemas.py`, `routers/`, `main.py`
  - [ ] Define `PatientCreate`, `PatientRead`, `VisitCreate`, `VisitRead` schemas
  - [ ] Implement patient endpoints (`POST /api/patients`, `GET /api/patients`, `GET /api/patients/{id}`)
  - [ ] Implement visit endpoints (`POST /api/patients/{id}/visits`, `GET /api/patients/{id}/visits`)
  - [ ] Wire routers and `create_db_and_tables()` into `main.py`
  - *Depends on Task 1 completing `models.py` first*

- [ ] Task 3 (Tab 3): Frontend — `public/`
  - [ ] Patient list page with register modal (`index.html`)
  - [ ] Patient detail page with visit history and add-visit modal (`patient.html`)
  - [ ] Wire up all `fetch()` calls against `/api/...`
  - *Can build HTML/CSS structure before Task 2; wire fetch() after*

- [ ] Task 4: Tests — `tests/`
  - [ ] Write patient endpoint tests (`test_patients.py`)
  - [ ] Write visit endpoint tests (`test_visits.py`)

## Commits

- 987bf80 — feat: initialize patient registration harness (skeleton, all stubs)
