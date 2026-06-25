import os
from sqlmodel import Session, select
from models import AdminUser


def test_admin_user_model_exists(session: Session):
    admin = AdminUser(username="testadmin", hashed_password="fakehash")
    session.add(admin)
    session.commit()
    result = session.exec(select(AdminUser).where(AdminUser.username == "testadmin")).first()
    assert result is not None
    assert result.username == "testadmin"


def test_admin_seeded_on_startup(session):
    from database import seed_admin
    os.environ["ADMIN_USERNAME"] = "seedtest"
    os.environ["ADMIN_PASSWORD"] = "seedpass"
    seed_admin(session)
    result = session.exec(select(AdminUser)).first()
    assert result is not None
    assert result.username == "seedtest"


def test_admin_not_duplicated_on_second_seed(session):
    from database import seed_admin
    os.environ["ADMIN_USERNAME"] = "seedtest"
    os.environ["ADMIN_PASSWORD"] = "seedpass"
    seed_admin(session)
    seed_admin(session)
    results = session.exec(select(AdminUser)).all()
    assert len(results) == 1
