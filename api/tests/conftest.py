from collections.abc import Generator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.db import Base, get_db
from app.core.mail import OutboundEmail, get_email_sender
from app.core.rate_limit import _login_blocks, _login_failures, _memory
from app.db import models  # noqa: F401
from app.main import app


class FakeEmailSender:
    def __init__(self) -> None:
        self.sent: list[OutboundEmail] = []

    def send(self, email: OutboundEmail) -> None:
        self.sent.append(email)


@pytest.fixture
def mailer() -> FakeEmailSender:
    return FakeEmailSender()


@pytest.fixture
def client(mailer: FakeEmailSender) -> Generator[TestClient, None, None]:
    _memory.clear()
    _login_blocks.clear()
    _login_failures.clear()
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Base.metadata.create_all(engine)
    factory = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)

    def override_db():
        with factory() as db:
            yield db

    app.dependency_overrides[get_db] = override_db
    app.dependency_overrides[get_email_sender] = lambda: mailer
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()
    Base.metadata.drop_all(engine)
    engine.dispose()
