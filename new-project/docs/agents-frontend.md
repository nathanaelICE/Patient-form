# Frontend

**Stack:** Vanilla HTML/CSS/JS

## Files
| Path | Purpose |
|---|---|
| `public/index.html` | Patient list page with register modal |
| `public/patient.html` | Patient detail page with visit history and add-visit modal |
| `public/style.css` | Styles |

## Rules
- All data via `fetch()` against `/api/...` — no other communication with backend
- Served by FastAPI StaticFiles at `/`
- Can build HTML/CSS structure independently; wire `fetch()` calls after Backend agent is done
