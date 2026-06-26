# SSR Migration Design

**Date:** 2026-06-26  
**Goal:** Replace client-side JS data fetching and rendering with full server-side rendering (SSR) using FastAPI + Jinja2. No JavaScript remains after migration.

---

## Context

The app is a FastAPI + SQLModel patient registration system. Two static HTML pages (`public/index.html`, `public/patient.html`) currently load blank and populate themselves via `fetch()` calls to `/api/` routes. All rendering, role detection, and form submission happen in JS.

The existing `/api/` routes (patients, visits, auth) are untouched — they remain for future React migration.

---

## Architecture

**Added:**
- `jinja2` and `python-multipart` packages
- `templates/` directory at project root
- `routers/pages.py` — owns all HTML-serving routes

**Changed:**
- `main.py`: register `pages.router`; change `StaticFiles` mount to serve only static assets (CSS) from `public/`
- `public/index.html` and `public/patient.html` deleted — replaced by Jinja2 templates

**Unchanged:**
- All `/api/` routes (`routers/auth.py`, `routers/patients.py`, `routers/visits.py`)
- `deps.py`, `models.py`, `schemas.py`, `database.py`

---

## URL Structure

HTML forms only support GET and POST, so all mutations use POST with action-suffixed URLs.

| Method | URL | Action |
|--------|-----|--------|
| GET | `/` | Redirect → `/patients` |
| GET | `/patients` | Patient list |
| GET | `/patients/new` | Register patient form (admin only) |
| POST | `/patients` | Create patient → redirect `/patients` |
| GET | `/patients/{id}` | Patient detail + visit history |
| GET | `/patients/{id}/edit` | Edit patient form (admin only) |
| POST | `/patients/{id}` | Update patient → redirect `/patients/{id}` |
| POST | `/patients/{id}/delete` | Soft-delete patient → redirect `/patients` |
| GET | `/patients/{id}/visits/new` | Add visit form (admin only) |
| POST | `/patients/{id}/visits` | Create visit → redirect `/patients/{id}` |
| GET | `/patients/{id}/visits/{vid}/edit` | Edit visit form (admin only) |
| POST | `/patients/{id}/visits/{vid}` | Update visit → redirect `/patients/{id}` |
| POST | `/patients/{id}/visits/{vid}/delete` | Delete visit → redirect `/patients/{id}` |
| GET | `/login` | Login form |
| POST | `/login` | Authenticate → redirect `/patients` or `/login?error=1` |
| POST | `/logout` | Clear session → redirect `/patients` |

---

## Templates

All templates extend `base.html`. Every route passes `is_admin` and `request` into the template context so the header renders server-side.

```
templates/
  base.html
  patients/
    list.html
    new.html
    detail.html
    edit.html
    confirm_delete.html
  visits/
    new.html
    edit.html
    confirm_delete.html
  auth/
    login.html
```

`base.html` renders the header: if `is_admin` is true, shows admin badge + logout button; otherwise shows a Login link to `/login`.

---

## Auth & Dependencies

Two new page-layer dependencies (in `routers/pages.py` or a shared `page_deps.py`):

- **`get_page_user(request)`** — returns `{"is_admin": bool}`. Always resolves; never raises. Used on all page routes to pass role into template context.
- **`require_admin_page(request)`** — redirects to `/login?next=<current_url>` if not admin. Used on form GET routes (new/edit/confirm_delete) and all POST mutation routes.

After successful login, `POST /login` checks for a `next` query param and redirects there; defaults to `/patients`.

---

## Error Handling

- **Login failure:** Redirect to `/login?error=1`; template renders "Invalid credentials" when `error=1` is in query params.
- **Patient/visit not found:** FastAPI raises 404; standard HTTP error page.
- **Validation errors on create/edit forms:** Redirect back to the form with `?error=1` as a fallback. Pydantic already validates the data models; form field `required` attributes catch most client-side issues without JS.
- **Unauthorized access to admin pages:** Redirect to `/login?next=<url>` via `require_admin_page`.

---

## Delete Confirmation Flow

Delete buttons are links to a confirmation page (GET), not direct POST actions. The confirmation page renders the patient/visit name and a `<form method="POST">` that submits to the delete URL. This replaces the current inline JS confirmation strip.

---

## What This Is Not

- No JavaScript remains after migration (no fetch, no DOM manipulation, no event listeners).
- The existing `/api/` JSON routes are not removed — they survive for future React frontend use.
- No new database changes, no schema changes, no auth system changes.
