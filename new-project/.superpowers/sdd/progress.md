# Docker Compose Self-Hosted Stack — Progress Ledger

## Tasks

- Task 1: Core stack config files — complete (commits 3931c22..8a293c5, review clean; minor: no explicit named network, cloudflared uses :latest)

- Task 2: Local dev compose override — complete (no commit — file is git-ignored; review clean)
- Task 3: Smoke test — MANUAL, not automated; stop here and report to user
- Task 3: Smoke test — partially complete (Steps 1–4, 5–6 partial, 8 done)
  - Build: ✅ image built cleanly
  - db + app: ✅ both healthy, HTTP 200 at localhost:8000
  - Logs: ✅ no errors (bcrypt __about__ warning is cosmetic)
  - Full stack (caddy): ✅ running
  - cloudflared: ⏸ restarting — placeholder token, needs real CLOUDFLARE_TUNNEL_TOKEN
  - Data persistence: ✅ login returns {"ok":true} after down+up cycle
  - Steps 7 (public URL): blocked on tunnel token + domain setup
