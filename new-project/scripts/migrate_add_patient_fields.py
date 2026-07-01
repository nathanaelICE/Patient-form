"""Add OCR-related columns to the patient table on the live Postgres DB.

Run once after deploying the model change:
    cd new-project && uv run python -m scripts.migrate_add_patient_fields

SQLModel.create_all() does NOT alter existing tables, so production needs this.
Tests use a fresh SQLite schema and do not run it.
"""
from sqlalchemy import text
from database import engine

COLUMNS = [
    "national_id VARCHAR",
    "place_of_birth VARCHAR",
    "marital_status VARCHAR",
    "occupation VARCHAR",
    "religion VARCHAR",
    "nationality VARCHAR",
    "blood_type VARCHAR",
    "allergies VARCHAR",
    "known_conditions VARCHAR",
]


def main() -> None:
    with engine.begin() as conn:
        for col in COLUMNS:
            conn.execute(text(f"ALTER TABLE patient ADD COLUMN IF NOT EXISTS {col}"))
        conn.execute(
            text("CREATE INDEX IF NOT EXISTS ix_patient_national_id ON patient (national_id)")
        )
    print("Migration complete: patient table now has OCR columns.")


if __name__ == "__main__":
    main()
