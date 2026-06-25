# Multi-Agent Conventions

This project is built using 3 parallel PowerShell tabs. Each tab owns specific files and must not edit files outside its scope.

## Tab Assignments

### Tab 1 — Database
**Owns:** `database.py`, `models.py`
- Implement SQLite engine and session dependency
- Define `Patient` and `Visit` SQLModel table classes
- Export `create_db_and_tables()` for use by `main.py`

### Tab 2 — Backend
**Owns:** `schemas.py`, `routers/patients.py`, `routers/visits.py`, `main.py`
- Implement all 5 API endpoints
- Wire routers into `main.py`
- Mount `public/` as StaticFiles
- Depends on Tab 1 completing `models.py` before implementing endpoints

### Tab 3 — Frontend
**Owns:** `public/index.html`, `public/patient.html`, `public/style.css`
- Implement patient list page with register modal
- Implement patient detail page with visit history and add-visit modal
- All data via `fetch()` against `/api/...`
- Can work on HTML/CSS structure independently; wire up fetch() after Tab 2 is done

## Dependency Order
1. Tab 1 finishes `models.py` → Tab 2 can implement endpoints
2. Tab 2 finishes API endpoints → Tab 3 can wire up `fetch()` calls

## Coordination Rule
Each tab commits its own work. Do not edit another tab's files.
