# Patient Registration

FastAPI app for patient registration, backed by Neon (cloud Postgres). The
Docker image builds the React SPA (`frontend/`) and serves it alongside the
JSON API, so the container exposes the full website on a single port.

> This app lives in the `new-project/` subdirectory of the repository. All
> Docker commands below are run from inside `new-project/`.

## Run locally with Docker

From the `new-project/` directory, build the image:

```bash
docker build -t patient-app .
```

Run it (reads secrets from your local `.env`):

```bash
docker run --rm --env-file .env -p 8000:8000 patient-app
```

Then open http://localhost:8000.

## Required environment variables

| Variable | Purpose |
|----------|---------|
| `DATABASE_URL` | Neon Postgres connection string |
| `ADMIN_USERNAME` | Seeded admin username (default `admin`) |
| `ADMIN_PASSWORD` | Seeded admin password |
| `GEMINI_API_KEY` | Enables OCR form-scanning (Gemini vision). If unset, the OCR upload button is hidden and the form works manually. |
| `OCR_MODEL` | Optional. Vision model id (default `gemini-2.5-flash`; `gemini-2.5-pro` for higher accuracy, `gemini-2.5-flash-lite` for lowest cost). |

`.env` is gitignored and excluded from the image — never commit it.

## Live deployment

The app is deployed on Railway and reachable at:

**https://patient-form-production.up.railway.app**

It runs in the Singapore (`southeast-asia`) region, co-located with the Neon
database, and redeploys automatically on every push to `master`.

## OCR form scanning

Admins can upload a photo/scan of a paper patient form on the registration
page; Gemini vision extracts the fields and pre-fills the form for review
before saving. Set `GEMINI_API_KEY` to enable it; without it the feature is
hidden and registration works manually.

## Database migration (new patient columns)

The OCR feature adds optional columns to the `patient` table. `create_all` does
not alter existing tables, so run this once against the live Postgres DB after
deploying:

```bash
cd new-project && uv run python -m scripts.migrate_add_patient_fields
```

## Deploy to Railway

1. Push this repo to GitHub.
2. In Railway, create a new project from the GitHub repo.
3. **Set the service's Root Directory to `new-project`** — the repo holds
   multiple projects, and the backend lives in this subfolder. Railway then
   finds the `Dockerfile` here and builds it.
4. In the project's **Variables** tab, set `DATABASE_URL`, `ADMIN_USERNAME`,
   and `ADMIN_PASSWORD`.
5. Railway exposes a public HTTPS URL and redeploys on every push.
