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

`.env` is gitignored and excluded from the image — never commit it.

## Deploy to Railway

1. Push this repo to GitHub.
2. In Railway, create a new project from the GitHub repo.
3. **Set the service's Root Directory to `new-project`** — the repo holds
   multiple projects, and the backend lives in this subfolder. Railway then
   finds the `Dockerfile` here and builds it.
4. In the project's **Variables** tab, set `DATABASE_URL`, `ADMIN_USERNAME`,
   and `ADMIN_PASSWORD`.
5. Railway exposes a public HTTPS URL and redeploys on every push.
