# Database

**Stack:** PostgreSQL via SQLModel + psycopg2

## Files
| Path | Purpose |
|---|---|
| `database.py` | PostgreSQL engine, session dependency, `create_db_and_tables()`, `seed_admin()` |
| `models.py` | SQLModel table definitions — `Patient`, `Visit`, `AdminUser` |

## Connection
- Connection string read from `DATABASE_URL` environment variable (e.g. `postgresql://user:pass@localhost:5432/dbname`)
- No `connect_args` needed (SQLite-specific `check_same_thread` is removed)
- `psycopg2-binary` is the sync driver; add it to `pyproject.toml` dependencies

## Rules
- Export `create_db_and_tables()` from `database.py` for use by `main.py`
- `Patient`, `Visit`, and `AdminUser` are the only table classes — define all three in `models.py`
- `DATABASE_URL` must be set before starting the server — fail fast if missing
- Must complete `models.py` before Backend agent can implement endpoints
