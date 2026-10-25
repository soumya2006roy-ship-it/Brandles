import hashlib
import secrets
from datetime import UTC, datetime, timedelta

from argon2 import PasswordHasher
from argon2.exceptions import InvalidHashError, VerificationError, VerifyMismatchError

password_hasher = PasswordHasher(time_cost=3, memory_cost=65536, parallelism=2, hash_len=32, salt_len=16)


def hash_password(password: str) -> str:
    return password_hasher.hash(password)


def verify_password(password_hash: str, password: str) -> bool:
    try:
        return password_hasher.verify(password_hash, password)
    except (InvalidHashError, VerificationError, VerifyMismatchError):
        return False


def new_secret() -> str:
    return secrets.token_urlsafe(32)


def digest_secret(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def expires_in(*, minutes: int = 0, hours: int = 0) -> datetime:
    return datetime.now(UTC) + timedelta(minutes=minutes, hours=hours)


def as_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value.astimezone(UTC)
