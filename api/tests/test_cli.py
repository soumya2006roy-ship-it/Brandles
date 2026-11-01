import sys
from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.db import Base
from app.core.security import verify_password
from app.db import models  # noqa: F401
from app.db.models import AuditEvent, PlatformAdmin, User
from app import cli
from app import main as api_main


def test_bootstrap_platform_admin_is_idempotent_and_audited(monkeypatch, capsys):
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


def test_production_bootstrap_requires_custom_environment_credentials():
    from app.auth.bootstrap import bootstrap_platform_admin

    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Base.metadata.create_all(engine)
    factory = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)

    with factory() as db:
        with pytest.raises(RuntimeError, match="Replace the example"):
            bootstrap_platform_admin(db, "admin@example.com", "replace-with-a-random-password-at-least-20-characters", required=True)
        assert db.scalar(select(PlatformAdmin.user_id)) is None

    engine.dispose()


def test_production_api_startup_bootstraps_first_admin(monkeypatch):
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Base.metadata.create_all(engine)
    factory = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)
    password = "a-private-first-admin-password-123"
    monkeypatch.setattr(api_main, "SessionLocal", lambda: factory())
    monkeypatch.setattr(api_main, "settings", SimpleNamespace(
        is_production=True,
        bootstrap_admin_email="hosted-admin@example.test",
        bootstrap_admin_password=password,
    ))

    with TestClient(api_main.app):
        pass

    with factory() as db:
        user = db.scalar(select(User).where(User.email_normalized == "hosted-admin@example.test"))
        assert user is not None
        assert verify_password(user.password_hash, password)
        assert db.get(PlatformAdmin, user.id) is not None
        assert db.scalar(select(AuditEvent).where(AuditEvent.action == "platform_admin.bootstrap_created")) is not None

    engine.dispose()
