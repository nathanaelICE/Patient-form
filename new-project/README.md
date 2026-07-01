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

## Deployment

The `Dockerfile` builds a single self-contained image (SPA + API on one port),
so the app can be deployed to any container host. Provide the environment
variables above and expose the container's port.

> **Railway (archived).** This app was previously deployed on Railway with
> GitHub auto-deploy. That setup is no longer active. The full Railway config
> and instructions are preserved in git at tag `railway-deploy-v1` — see
> [Archived: Railway deployment](#archived-railway-deployment) below to restore.

## OCR form scanning

Admins can upload a photo/scan of a paper patient form on the registration
page; Gemini vision extracts the fields and pre-fills the form for review
before saving. Set `GEMINI_API_KEY` to enable it; without it the feature is
hidden and registration works manually.

## Insurance claims

Each patient has an insurance-claims section on their detail page. Admins can
record, edit, and delete claims tied to a patient (and optionally to a specific
visit). A claim captures the claim date and amount, optional diagnosis/procedure
codes, provider details, and three validated fields:

- **status** — `pending` (default), `approved`, or `denied`
- **type** — `inpatient`, `outpatient`, `emergency`, or `routine`
- **submission method** — `online`, `paper`, or `phone`

Registration also collects the patient's **employment status** and **income**,
which support downstream claim workflows.

Claims are served under `/api/patients/{id}/claims` (GET/POST/PUT/DELETE) and,
like every app endpoint, require an admin session. Unlike patients, claims are
**hard-deleted** (no `deleted_at`).

## Database migrations (new columns)

`create_all` creates new tables (like `claim`) on startup but does **not** alter
existing tables, so new columns on the existing `patient` table need a manual
migration once against the live Postgres DB after deploying.

The OCR feature added identity/medical columns:

```bash
cd new-project && uv run python -m scripts.migrate_add_patient_fields
```

The claims feature added `employment_status` and `income` to `patient` (the
`claim` table itself is auto-created). Apply the SQL once:

```bash
cd new-project && psql "$DATABASE_URL" -f migrations/2026-07-01-add-claims.sql
```

## Archived: Railway deployment

The app previously ran on Railway (project `lucid-manifestation`, Singapore
region) with GitHub auto-deploy on every push to `master`. That deployment has
been retired. The steps below are kept for reference if you want to bring it
back; the exact repo state from when it was live is tagged `railway-deploy-v1`.

1. Push this repo to GitHub.
2. In Railway, create a new project from the GitHub repo.
3. **Set the service's Root Directory to `new-project`** — the repo holds
   multiple projects, and the backend lives in this subfolder. Railway then
   finds the `Dockerfile` here and builds it.
4. In the project's **Variables** tab, set `DATABASE_URL`, `ADMIN_USERNAME`,
   and `ADMIN_PASSWORD`.
5. Railway exposes a public HTTPS URL and redeploys on every push.
