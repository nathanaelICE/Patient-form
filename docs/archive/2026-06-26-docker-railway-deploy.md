# Docker / Railway Deployment Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Package the FastAPI patient-registration app into a Docker image that Railway can build and run against the existing Neon Postgres database.

**Architecture:** A single-container image built from the official `uv` Python 3.12 base image. The app reads all config (`DATABASE_URL`, admin credentials) from environment variables at runtime; the database stays external (Neon). Railway auto-builds the Dockerfile and injects env vars.

**Tech Stack:** Docker, `uv`, FastAPI, uvicorn, Neon Postgres, Railway.

## Global Constraints

- Python version: **3.12** (matches `.python-version` and `requires-python = ">=3.12"`).
- Dependency manager: **`uv`** with the committed `uv.lock` (use `--frozen`).
- Secrets (`DATABASE_URL`, `ADMIN_USERNAME`, `ADMIN_PASSWORD`) MUST NOT be baked into the image — they come from `--env-file`/Railway Variables at runtime.
- The container MUST bind `--host 0.0.0.0` and listen on `${PORT:-8000}`.
- No application code changes — the app is already env-var driven.

---

### Task 1: Add `.dockerignore`

**Files:**
- Create: `.dockerignore`

**Interfaces:**
- Consumes: nothing.
- Produces: a build-exclusion list relied on by Task 2's `COPY . .` so secrets/junk stay out of the image.

- [ ] **Step 1: Create `.dockerignore`**

Create `.dockerignore` with exactly:

```
.venv/
__pycache__/
*.py[cod]
.git/
.gitignore
.env
registration.db
.pytest_cache/
tests/
docs/
.superpowers/
*.md
.python-version
```

- [ ] **Step 2: Verify it lists the secret and the db**

Run: `grep -E '^\.env$|^registration.db$' .dockerignore`
Expected: both `.env` and `registration.db` are printed (confirms secrets and stray DB are excluded).

- [ ] **Step 3: Commit**

```bash
git add .dockerignore
git commit -m "build: add .dockerignore to keep secrets and junk out of image"
```

---

### Task 2: Add the `Dockerfile`

**Files:**
- Create: `Dockerfile`

**Interfaces:**
- Consumes: `.dockerignore` from Task 1; existing `pyproject.toml`, `uv.lock`, and app code.
- Produces: a buildable image tagged `patient-app` that starts the app via uvicorn on `${PORT:-8000}`.

- [ ] **Step 1: Create the `Dockerfile`**

Create `Dockerfile` with exactly:

```dockerfile
FROM ghcr.io/astral-sh/uv:python3.12-bookworm-slim

WORKDIR /app

# Install dependencies first so this layer caches unless deps change
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev

# Copy application code
COPY . .

EXPOSE 8000

# Railway provides $PORT; default to 8000 locally
CMD ["sh", "-c", "uv run uvicorn main:app --host 0.0.0.0 --port ${PORT:-8000}"]
```

- [ ] **Step 2: Build the image (this is the test)**

Run: `docker build -t patient-app .`
Expected: build completes with `naming to docker.io/library/patient-app` / `writing image` — no errors. If `uv sync` fails, the deps layer is the cause; re-check `pyproject.toml`/`uv.lock` are copied before `uv sync`.

- [ ] **Step 3: Commit**

```bash
git add Dockerfile
git commit -m "build: add Dockerfile for containerized FastAPI app"
```

---

### Task 3: Remove the redundant `registration.db`

**Files:**
- Delete: `registration.db`

**Interfaces:**
- Consumes: nothing.
- Produces: nothing — cleanup only. `.gitignore` already lists `registration.db`, so it is not tracked; this removes the working-copy file.

- [ ] **Step 1: Confirm it is not git-tracked**

Run: `git ls-files --error-unmatch registration.db 2>&1 || echo "NOT TRACKED"`
Expected: prints `NOT TRACKED` (it is gitignored). If instead it prints the path, it IS tracked — use `git rm registration.db` in Step 2 and commit.

- [ ] **Step 2: Delete the file**

Run: `rm -f registration.db`
Expected: no output; `ls registration.db` then reports "No such file".

- [ ] **Step 3: No commit needed (untracked file)**

Since the file is gitignored/untracked, deleting it produces no git change. Skip the commit. (Only commit here if Step 1 showed it was tracked.)

---

### Task 4: Verify the container runs end-to-end against Neon

**Files:**
- None (verification task; uses existing `.env`).

**Interfaces:**
- Consumes: `patient-app` image from Task 2; `.env` with valid `DATABASE_URL`.
- Produces: confirmation the container serves traffic and reaches Neon.

- [ ] **Step 1: Run the container with env file**

Run: `docker run --rm --env-file .env -p 8000:8000 patient-app`
Expected: logs show `Uvicorn running on http://0.0.0.0:8000` and startup completes (table creation + admin seed) with no DB connection errors.

- [ ] **Step 2: Hit the app**

In a second terminal run: `curl -i http://localhost:8000/`
Expected: an HTTP response (e.g. `200 OK` or a redirect to the login page) — confirms the app is serving and reached Neon on startup without crashing.

- [ ] **Step 3: Stop the container**

Press `Ctrl+C` in the first terminal.
Expected: container stops and is auto-removed (`--rm`).

---

### Task 5: Document build/run/deploy in the README

**Files:**
- Modify: `README.md`

**Interfaces:**
- Consumes: the `Dockerfile` and verified run command from prior tasks.
- Produces: human-facing docs; no code depends on this.

- [ ] **Step 1: Write the README content**

Replace `README.md` contents with:

````markdown
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
````

- [ ] **Step 2: Commit**

```bash
git add README.md
git commit -m "docs: document Docker build/run and Railway deployment"
```

---

## Self-Review

**Spec coverage:**
- Dockerfile → Task 2 ✓
- `.dockerignore` (excludes `.env`, `registration.db`, junk) → Task 1 ✓
- Delete `registration.db` → Task 3 ✓
- README update → Task 5 ✓
- Secrets via env at runtime (not in image) → enforced by Task 1 `.dockerignore` + Task 4 `--env-file` ✓
- `--host 0.0.0.0` and `${PORT:-8000}` → Task 2 Dockerfile ✓
- Verification (build, run, reach Neon) → Tasks 2 & 4 ✓
- No app code changes → respected (no task modifies app code) ✓
- Railway deployment steps → Task 5 README ✓

**Placeholder scan:** No TBD/TODO; every file's full contents are shown. ✓

**Type/name consistency:** Image tag `patient-app`, port `8000`/`${PORT:-8000}`, and env var names (`DATABASE_URL`, `ADMIN_USERNAME`, `ADMIN_PASSWORD`) are identical across Tasks 2, 4, and 5. ✓
