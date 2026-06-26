# Patient Registration

FastAPI app for patient registration, backed by Neon (cloud Postgres).

## Run locally with Docker

Build the image:

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
3. Railway auto-detects the `Dockerfile` and builds the image.
4. In the project's **Variables** tab, set `DATABASE_URL`, `ADMIN_USERNAME`,
   and `ADMIN_PASSWORD`.
5. Railway exposes a public HTTPS URL and redeploys on every push.
