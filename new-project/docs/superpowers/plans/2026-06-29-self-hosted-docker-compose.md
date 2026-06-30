# Self-Hosted Docker Compose Stack Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace Railway hosting with a self-hosted docker-compose stack (app + caddy + cloudflared + db) running on a laptop, accessible via a Cloudflare tunnel.

**Architecture:** Four services in a chain — `db` (postgres:16-alpine) → `app` (existing Dockerfile, FastAPI + React SPA on :8000) → `caddy` (reverse proxy on :80) → `cloudflared` (tunnel to Cloudflare edge). No host ports exposed; all external ingress via the tunnel.

**Tech Stack:** Docker Compose v2, Caddy 2, cloudflare/cloudflared, postgres:16-alpine, existing FastAPI + SQLModel app.

## Global Constraints

- Dockerfile is unchanged — do not modify it
- All secrets live in `.env` only — never hardcode credentials in compose files
- `compose.override.yml` must be git-ignored — it is for local dev only
- `restart: on-failure` for `app`, `restart: unless-stopped` for all others
- No host ports declared in `compose.yml` — the override handles local access
- DATABASE_URL must use the internal Docker network hostname `db`, not Neon

---

### Task 1: Core stack config files

**Files:**
- Create: `compose.yml`
- Create: `Caddyfile`
- Modify: `.env`
- Modify: `.gitignore`
- Modify: `.dockerignore`

**Interfaces:**
- Produces: a `compose.yml` that `docker compose config` validates cleanly; a `.env` with all required vars

- [ ] **Step 1: Write `compose.yml`**

Create `compose.yml` at the project root with this exact content:

```yaml
services:
  db:
    image: postgres:16-alpine
    environment:
      POSTGRES_DB: ${POSTGRES_DB}
      POSTGRES_USER: ${POSTGRES_USER}
      POSTGRES_PASSWORD: ${POSTGRES_PASSWORD}
    volumes:
      - pgdata:/var/lib/postgresql/data
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U ${POSTGRES_USER} -d ${POSTGRES_DB}"]
      interval: 5s
      timeout: 5s
      retries: 5
    restart: unless-stopped

  app:
    build: .
    environment:
      DATABASE_URL: ${DATABASE_URL}
      ADMIN_USERNAME: ${ADMIN_USERNAME}
      ADMIN_PASSWORD: ${ADMIN_PASSWORD}
    depends_on:
      db:
        condition: service_healthy
    restart: on-failure

  caddy:
    image: caddy:2-alpine
    volumes:
      - ./Caddyfile:/etc/caddy/Caddyfile:ro
    depends_on:
      - app
    restart: unless-stopped

  cloudflared:
    image: cloudflare/cloudflared:latest
    command: tunnel --no-autoupdate run --token ${CLOUDFLARE_TUNNEL_TOKEN}
    depends_on:
      - caddy
    restart: unless-stopped

volumes:
  pgdata:
```

- [ ] **Step 2: Write `Caddyfile`**

Create `Caddyfile` at the project root:

```
:80 {
    reverse_proxy app:8000
}
```

- [ ] **Step 3: Update `.env`**

Replace the current contents of `.env` with the following. Keep existing ADMIN_* values. Replace the Neon DATABASE_URL with the local one. Fill in your actual Cloudflare tunnel token for `CLOUDFLARE_TUNNEL_TOKEN` (get it from the Cloudflare Zero Trust dashboard → Access → Tunnels → your tunnel → Configure → token).

```
ADMIN_USERNAME=admin
ADMIN_PASSWORD=meow123

POSTGRES_DB=patient
POSTGRES_USER=patient_user
POSTGRES_PASSWORD=changeme

DATABASE_URL=postgresql://patient_user:changeme@db:5432/patient

CLOUDFLARE_TUNNEL_TOKEN=<paste-your-token-here>
```

- [ ] **Step 4: Update `.gitignore`**

Add `compose.override.yml` to `.gitignore` so the local dev override never gets committed:

```
compose.override.yml
```

Append it to the existing file — do not replace the file.

- [ ] **Step 5: Update `.dockerignore`**

Add compose files and Caddyfile to `.dockerignore` so they don't get copied into the image (harmless but clean):

```
compose*.yml
Caddyfile
```

Append to the existing file.

- [ ] **Step 6: Validate the compose file**

Run:
```bash
docker compose config
```

Expected: YAML printed to stdout with no errors. If it complains about `CLOUDFLARE_TUNNEL_TOKEN` being unset, that's fine — set a dummy value temporarily in `.env` and re-run.

- [ ] **Step 7: Commit**

```bash
git add compose.yml Caddyfile .gitignore .dockerignore
git commit -m "feat(deploy): add docker-compose stack with caddy and cloudflared"
```

Do NOT commit `.env`.

---

### Task 2: Local dev compose override

**Files:**
- Create: `compose.override.yml` (git-ignored, not committed)

**Interfaces:**
- Consumes: `compose.yml` from Task 1
- Produces: ability to reach the app at `localhost:8000` without the tunnel

- [ ] **Step 1: Write `compose.override.yml`**

Create `compose.override.yml` at the project root:

```yaml
services:
  app:
    ports:
      - "8000:8000"
```

This file is automatically merged by `docker compose` when present. It exposes the app directly for local testing without going through caddy or cloudflared.

- [ ] **Step 2: Verify it is git-ignored**

Run:
```bash
git status
```

Expected: `compose.override.yml` does NOT appear in the output. If it does, check `.gitignore` from Task 1.

---

### Task 3: Smoke test the full stack

No files to create. This task verifies the stack works end-to-end.

**Prerequisite:** `CLOUDFLARE_TUNNEL_TOKEN` in `.env` must be a real token (not a placeholder) before the cloudflared service will connect. If you don't have one yet, complete steps 1–4 with a dummy token and mark that sub-step as blocked.

- [ ] **Step 1: Build the app image**

```bash
docker compose build app
```

Expected: build completes with no errors. This runs the React SPA build and Python dependency install inside Docker — it will take a few minutes on the first run.

- [ ] **Step 2: Start db and app only**

```bash
docker compose up -d db app
```

Expected: both containers start. `db` becomes healthy (watch with `docker compose ps`), then `app` starts.

- [ ] **Step 3: Verify app is reachable locally**

The `compose.override.yml` from Task 2 exposes port 8000. Open a browser or run:

```bash
curl -s -o /dev/null -w "%{http_code}" http://localhost:8000/
```

Expected: `200`. The React SPA index page is served.

- [ ] **Step 4: Verify the database seeded correctly**

```bash
docker compose logs app | grep -E "startup|seed|error" -i
```

Expected: no errors. The app's startup event calls `create_db_and_tables()` and `seed_admin()` — if DATABASE_URL is wrong you'll see a connection error here.

- [ ] **Step 5: Start the full stack**

```bash
docker compose up -d
```

Expected: caddy and cloudflared also start. Check cloudflared registered its tunnel:

```bash
docker compose logs cloudflared | grep -i "registered\|connected\|tunnel"
```

Expected: a line containing "registered tunnel" or "connected to Cloudflare".

- [ ] **Step 6: Verify all services are running**

```bash
docker compose ps
```

Expected: all four services show `running` (or `Up`). None should show `Restarting` or `Exit`.

- [ ] **Step 7: Hit the public URL (requires registered domain)**

Once your domain is pointed at the tunnel in the Cloudflare dashboard, open `https://yourdomain.com` in a browser.

Expected: the React SPA loads. The admin login at `/docs` prompts for HTTP Basic credentials (ADMIN_USERNAME / ADMIN_PASSWORD from `.env`).

- [ ] **Step 8: Tear down and confirm data persists**

```bash
docker compose down
docker compose up -d
```

After coming back up, the admin user created in step 3 should still exist (it's in the `pgdata` volume). Confirm by hitting the login endpoint:

```bash
curl -s -X POST http://localhost:8000/api/login \
  -H "Content-Type: application/json" \
  -d '{"username":"admin","password":"meow123"}'
```

Expected: `{"ok":true}` (not a 401).
