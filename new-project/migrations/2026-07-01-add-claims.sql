-- Run once against the production Postgres after deploying the Claim model.
-- The `claim` table itself is created automatically by SQLModel.create_all on
-- startup; only the new patient columns need a manual ALTER.
ALTER TABLE patient ADD COLUMN IF NOT EXISTS employment_status VARCHAR;
ALTER TABLE patient ADD COLUMN IF NOT EXISTS income DOUBLE PRECISION;
