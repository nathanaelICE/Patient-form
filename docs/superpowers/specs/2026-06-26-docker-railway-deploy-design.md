# Design: Dockerize the Patient Registration backend for Railway deployment

**Date:** 2026-06-26
**Status:** Approved

## Goal & scope

Package the FastAPI patient-registration app into a Docker image so a managed
platform (Railway) can build and run it, reachable at a public HTTPS URL,
connected to the existing Neon (cloud Postgres) database.

**In scope:**
- A `Dockerfile` that builds the app image.
- A `.dockerignore` to keep build junk and secrets out of the image.
- Removing the redundant `registration.db` SQLite file.
- README documentation for building/running locally and deploying to Railway.

**Out of scope (deferred):**
- Self-hosting Postgres in a container (we keep using managed Neon).
- CI/CD pipelines beyond Railway's built-in auto-deploy.
- Custom domains and TLS configuration (Railway provides HTTPS by default).

## Background & decisions

- **Database: keep Neon (managed cloud Postgres).** The app already reads
  `DATABASE_URL` from the environment. The database lives outside the
  container, so the container stays a single, simple box and we avoid taking on
  database-administration burden (volumes, backups, persistence).
- **Hosting: a managed platform (Railway).** Goal is "online and
  low-maintenance," not running a server by hand. Railway auto-detects the
  Dockerfile, builds it, injects env vars, and provides HTTPS.
- **No application code changes needed.** The app already reads all config
  (`DATABASE_URL`, `ADMIN_USERNAME`, `ADMIN_PASSWORD`) from environment
  variables — already container-friendly.

## Files added or changed

| File | Action | Why |
|------|--------|-----|
| `Dockerfile` | add | The recipe to build the app image |
| `.dockerignore` | add | Exclude `.venv`, `.git`, `__pycache__`, `.env`, `registration.db`, tests from the image |
| `registration.db` | delete | Redundant SQLite leftover; the app uses Neon |
| `README.md` | update | Document build/run-locally and deploy-to-Railway steps |

## The Dockerfile

Uses the official `uv` base image so the build matches local dependency
management. Structure:

```dockerfile
FROM ghcr.io/astral-sh/uv:python3.12-bookworm-slim
WORKDIR /app

# Install dependencies first so this layer is cached unless deps change
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev

# Copy application code
COPY . .

EXPOSE 8000
# Railway provides $PORT; default to 8000 locally
CMD ["sh", "-c", "uv run uvicorn main:app --host 0.0.0.0 --port ${PORT:-8000}"]
```

Key design points:
- **Dependencies copied before code** so Docker's layer cache makes rebuilds
  fast — deps only reinstall when `pyproject.toml`/`uv.lock` change.
- **`--host 0.0.0.0`** so the app accepts connections from outside the
  container (required for Railway routing).
- **`${PORT:-8000}`** so it works on Railway (which sets `$PORT`) and locally.
- **`--no-dev`** to skip dev/test dependencies in the production image.

## Secrets / environment variables

Secrets never enter the image. `.dockerignore` excludes `.env`.

- **Locally:** run with `docker run --env-file .env ...`.
- **On Railway:** set `DATABASE_URL`, `ADMIN_USERNAME`, `ADMIN_PASSWORD` in the
  Railway Variables dashboard; Railway injects them at runtime.

## Deployment flow on Railway

1. Push code to GitHub.
2. Connect the repo to a new Railway project.
3. Railway detects the `Dockerfile`, builds the image, runs the container.
4. Set the environment variables in Railway's Variables tab.
5. Railway exposes a public HTTPS URL; redeploys automatically on each push.

## Verification

1. **Build locally:** `docker build -t patient-app .` — confirms the image builds.
2. **Run locally:** `docker run --env-file .env -p 8000:8000 patient-app`, then
   open `http://localhost:8000`, log in, confirm it reaches Neon.
3. **Deploy:** push to GitHub, connect Railway, set variables, confirm the live
   URL works.
