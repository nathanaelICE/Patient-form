# Admin/Guest UI + Full CRUD Design

**Date:** 2026-06-25
**Scope:** Add role-based UI (admin vs guest), Edit (Update) and Delete for patients and visits, with server-side session auth.

---

## 1. Goals

- Guests see the app read-only (no mutating controls visible).
- Admins see Edit and Delete controls next to patients and visits.
- A single seeded admin account (credentials from `.env`) authenticates via a login modal.
- Sessions are server-side (in-memory); logout fully invalidates the session.
- Patient deletes are soft (hidden, data preserved). Visit deletes are hard.

---

## 2. Architecture

```
Browser                         FastAPI
  │  GET /api/me (on load)        │
  │ ─────────────────────────────►│
  │ ◄── { is_admin: bool } ───────│
  │                                │
  │  POST /api/login               │
  │ ─────────────────────────────►│  verify bcrypt → create UUID session
  │ ◄── Set-Cookie: session_id ───│  store in app.state.sessions dict
  │                                │
  │  PUT/DELETE + Cookie           │
  │ ─────────────────────────────►│  get_admin dependency validates cookie
  │ ◄── 200 / 401 ────────────────│
```

**Session store:** `app.state.sessions: dict[str, int]` — maps `session_id → admin_user_id`. Lives in process memory; cleared on restart (acceptable; admins re-login).

---

## 3. Backend

### 3.1 New / Changed Models (`models.py`)

**`AdminUser`** (new table):
```
id               int  PK autoincrement
username         str  unique
hashed_password  str
```

**`Patient`** (changed):
- Add `deleted_at: Optional[datetime] = None`
- All `SELECT` queries filter `WHERE deleted_at IS NULL`

### 3.2 New Schemas (`schemas.py`)

| Schema | Fields |
|---|---|
| `PatientUpdate` | `name?`, `date_of_birth?`, `gender?`, `phone?` — all Optional |
| `VisitUpdate` | `date?`, `chief_complaint?`, `diagnosis?`, `notes?` — all Optional |
| `LoginRequest` | `username: str`, `password: str` |
| `MeResponse` | `is_admin: bool` |

### 3.3 Dependency (`deps.py`) — new file

`get_admin(request, session)`:
1. Read `session_id` cookie from request.
2. Look up `app.state.sessions[session_id]` → `user_id` (raise 401 if missing).
3. Fetch `AdminUser` from DB by `user_id` (raise 401 if not found).
4. Return the `AdminUser`.

### 3.4 Auth Router (`routers/auth.py`) — new file

| Endpoint | Behavior |
|---|---|
| `POST /api/login` | Parse `LoginRequest`; fetch `AdminUser` by username; verify bcrypt; create `session_id = str(uuid4())`; store `sessions[session_id] = user.id`; set cookie `session_id`, `HttpOnly=True`, `SameSite="strict"`; return `{"ok": true}` |
| `POST /api/logout` | Read cookie → remove from sessions dict → delete cookie; return `{"ok": true}` |
| `GET /api/me` | If valid session cookie → `{"is_admin": true}`; else `{"is_admin": false}` (never 401) |

### 3.5 New CRUD Endpoints

**Patients router (`routers/patients.py`):**
| Method | Path | Auth | Behavior |
|---|---|---|---|
| `PUT` | `/api/patients/{patient_id}` | `get_admin` | Partial update; apply only provided fields; commit; return updated `PatientRead` |
| `DELETE` | `/api/patients/{patient_id}` | `get_admin` | Set `patient.deleted_at = datetime.utcnow()`; commit; return `204` |

**Visits router (`routers/visits.py`):**
| Method | Path | Auth | Behavior |
|---|---|---|---|
| `PUT` | `/api/patients/{patient_id}/visits/{visit_id}` | `get_admin` | Partial update visit; verify patient_id matches; commit; return updated `VisitRead` |
| `DELETE` | `/api/patients/{patient_id}/visits/{visit_id}` | `get_admin` | Hard delete (session.delete); commit; return `204` |

### 3.6 Startup Seeding (`database.py`)

On `create_db_and_tables()`:
1. Create all tables.
2. If `AdminUser` table is empty: read `ADMIN_USERNAME` + `ADMIN_PASSWORD` from env; hash password with bcrypt; insert row.
3. Initialize `app.state.sessions = {}` in `on_startup` in `main.py`.

---

## 4. Frontend

### 4.1 Role Detection (both pages)

On every page load, before rendering mutating controls:
```js
const { is_admin: isAdmin } = await fetch('/api/me').then(r => r.json());
```
Admin controls are injected into the DOM only when `isAdmin === true`.

### 4.2 Header

- **Guest:** title only + "Login" link (top-right) that opens the login modal.
- **Admin:** title + `Admin` badge (pill, muted blue) + "Logout" button (top-right). Clicking Logout calls `POST /api/logout` and reloads the page.

### 4.3 Login Modal

- Centered modal, 360px max-width.
- Fields: Username (text), Password (password).
- Submit button: "Login as Admin".
- On `POST /api/login` 401: show inline error "Invalid credentials" below the form.
- On success: close modal, re-run role detection, inject admin controls.

### 4.4 `index.html` — Patient List (Admin View)

- Table header gains an "Actions" column (last column), hidden for guests.
- Each patient row gains two icon buttons in the Actions cell:
  - ✏️ **Edit** — opens Edit Patient modal pre-filled with row data.
  - 🗑️ **Delete** — shows an inline confirmation strip replacing the row: `"Delete [Name]? " [Confirm] [Cancel]`. On Confirm: `DELETE /api/patients/{id}` → remove row from table.
- **Edit Patient Modal:** same fields as Register modal; title "Edit Patient"; pre-populated; `PUT /api/patients/{id}` on submit; refreshes row in place.
- "Register Patient" button is shown only to admins.

### 4.5 `patient.html` — Patient Detail (Admin View)

**Patient Info Card:**
- An ✏️ Edit button appears in the card header (admin only).
- Opens Edit Patient modal (same as above, pre-filled).
- On save: re-fetches patient info and re-renders the `<dl>`.

**Visit History:**
- Table header gains an "Actions" column.
- Each visit row gains ✏️ Edit and 🗑️ Delete buttons.
- **Edit Visit Modal:** same fields as Add Visit; pre-populated; `PUT /api/patients/{id}/visits/{visit_id}` on submit.
- **Delete Visit:** inline confirmation strip, same pattern as patient delete. Hard delete.
- "Add Visit" button shown only to admins.

### 4.6 Edit Form Design

Both edit modals follow the same pattern as existing modals:
- Centered overlay backdrop.
- Dialog box: max-width 480px, white card, 24px padding, 8px border-radius.
- Title row: "Edit Patient" or "Edit Visit" in the existing `.modal-title` style.
- Fields: single-column stack, same `.form-group` / `<label>` / `<input>` pattern.
- Actions row: "Save Changes" (primary blue) + "Cancel" (secondary ghost).
- On success: modal closes, data refreshes without full page reload.

---

## 5. File Changelist

| File | Change |
|---|---|
| `models.py` | Add `AdminUser`; add `deleted_at` to `Patient` |
| `schemas.py` | Add `PatientUpdate`, `VisitUpdate`, `LoginRequest`, `MeResponse` |
| `deps.py` | New — `get_admin` dependency |
| `routers/auth.py` | New — login, logout, me endpoints |
| `routers/patients.py` | Add PUT + DELETE endpoints |
| `routers/visits.py` | Add PUT + DELETE endpoints |
| `database.py` | Add admin seeding logic |
| `main.py` | Include auth router; init `app.state.sessions` |
| `public/index.html` | Role detection, login modal, admin controls, edit/delete |
| `public/patient.html` | Role detection, admin controls, edit/delete |
| `public/style.css` | Admin badge, icon buttons, confirmation strip styles |
| `.env` | New — `ADMIN_USERNAME`, `ADMIN_PASSWORD` |
| `pyproject.toml` | Add `bcrypt` / `passlib` dependency |

---

## 6. Error Handling

- All protected endpoints return `401` (not `403`) when session is absent or invalid — the frontend interprets this as "not logged in" and shows the login modal.
- `PUT` on a soft-deleted patient returns `404`.
- Bad credentials on login return `401` with `{"detail": "Invalid credentials"}`.
- Network errors on edit/delete show an inline error message in the modal; they do not close the modal.

---

## 7. Testing

- Extend existing test suite with:
  - Auth: login success, login fail, logout, `/api/me` with/without session.
  - Patient update: valid partial update, update of nonexistent patient, update without auth.
  - Patient soft delete: patient disappears from list, still exists in DB, cannot be fetched by GET.
  - Visit update and hard delete: standard cases + auth guard.
- Use `httpx.AsyncClient` with a test session fixture that logs in before admin-only tests.
