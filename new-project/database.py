import os
from sqlmodel import SQLModel, create_engine, Session, select
from typing import Generator
from passlib.context import CryptContext

DATABASE_URL = os.environ["DATABASE_URL"]

# pool_pre_ping checks a pooled connection is still alive before use and
# transparently reconnects — Neon drops idle connections, which otherwise
# surfaces as "SSL connection has been closed unexpectedly" on the next request.
engine = create_engine(DATABASE_URL, pool_pre_ping=True, pool_recycle=300)

_pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def create_db_and_tables():
    from models import Patient, Visit, Claim, AdminUser, OcrJob  # noqa: F401
    SQLModel.metadata.create_all(engine)


def seed_admin(session: Session) -> None:
    from models import AdminUser
    username = os.environ.get("ADMIN_USERNAME", "admin")
    password = os.environ.get("ADMIN_PASSWORD", "changeme123")
    existing = session.exec(select(AdminUser)).first()
    if existing:
        # Keep the admin credentials authoritative to the configured env vars
        # so ADMIN_PASSWORD takes effect on every deploy, even on a database
        # that was seeded earlier with a different password.
        if existing.username != username or not _pwd_context.verify(
            password, existing.hashed_password
        ):
            existing.username = username
            existing.hashed_password = _pwd_context.hash(password)
            session.add(existing)
            session.commit()
        return
    admin = AdminUser(username=username, hashed_password=_pwd_context.hash(password))
    session.add(admin)
    session.commit()


def get_session() -> Generator[Session, None, None]:
    with Session(engine) as session:
        yield session
