import sys
from types import SimpleNamespace

from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.db import Base
from app.core.security import verify_password
from app.db import models  # noqa: F401
from app.db.models import AuditEvent, PlatformAdmin, User
from app import cli


def test_bootstrap_platform_admin_is_local_and_idempotent(monkeypatch, capsys):
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Base.metadata.create_all(engine)
    factory = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)
    monkeypatch.setattr(cli, "SessionLocal", lambda: factory())
    monkeypatch.setattr(cli, "get_settings", lambda: SimpleNamespace(
        bootstrap_admin_email="admin@example.test",
        bootstrap_admin_password="a-long-development-password-123",
    ))
    monkeypatch.setattr(sys, "argv", ["app.cli", "bootstrap-platform-admin"])

    cli.main()
    first_output = capsys.readouterr().out
    with factory() as db:
        user = db.scalar(select(User).where(User.email_normalized == "admin@example.test"))
        assert user is not None
        assert user.email_verified_at is None
        assert verify_password(user.password_hash, "a-long-development-password-123")
        assert db.get(PlatformAdmin, user.id) is not None
        assert db.scalar(select(AuditEvent).where(AuditEvent.action == "platform_admin.bootstrap_created")) is not None

    cli.main()
    second_output = capsys.readouterr().out
    with factory() as db:
        assert len(db.scalars(select(PlatformAdmin)).all()) == 1
        assert len(db.scalars(select(User)).all()) == 1
    assert "a-long-development-password-123" not in first_output + second_output
    engine.dispose()
