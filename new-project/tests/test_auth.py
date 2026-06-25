from sqlmodel import Session, select
from models import AdminUser


def test_admin_user_model_exists(session: Session):
    admin = AdminUser(username="testadmin", hashed_password="fakehash")
    session.add(admin)
    session.commit()
    result = session.exec(select(AdminUser).where(AdminUser.username == "testadmin")).first()
    assert result is not None
    assert result.username == "testadmin"
