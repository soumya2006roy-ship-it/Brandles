"""Integration checks run against the disposable PostgreSQL CI service."""

import os

import pytest
from sqlalchemy import create_engine, text


@pytest.mark.integration
def test_postgres_migrations_and_append_only_audit_trigger():
    database_url = os.environ.get("TEST_DATABASE_URL")
    if not database_url:
        pytest.skip("Set TEST_DATABASE_URL to run PostgreSQL integration checks.")
    engine = create_engine(database_url, pool_pre_ping=True)
    try:
        with engine.begin() as connection:
            revision = connection.scalar(text("SELECT version_num FROM alembic_version"))
            assert revision == "0008_retention_controls"
            triggers = connection.execute(text("SELECT tgname FROM pg_trigger WHERE tgrelid = 'audit_events'::regclass AND NOT tgisinternal")).scalars().all()
            assert "audit_events_append_only" in triggers
            assert connection.scalar(text("SELECT 1")) == 1
    finally:
        engine.dispose()
