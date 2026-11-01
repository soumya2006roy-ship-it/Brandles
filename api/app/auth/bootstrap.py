from sqlalchemy import select, text
from sqlalchemy.orm import Session

from app.core.security import hash_password, verify_password
from app.db.models import AuditEvent, PlatformAdmin, User


def bootstrap_platform_admin(
    db: Session,
    email: str | None,
    password: str | None,
    *,
    required: bool = False,
) -> bool:
    """Create the first platform admin from operator-provided environment secrets."""
    if db.get_bind().dialect.name == "postgresql":
        db.execute(text("SELECT pg_advisory_xact_lock(6273094231)"))

    if db.scalar(select(PlatformAdmin.user_id).limit(1)):
        db.rollback()
        return False

    normalized_email = (email or "").strip().lower()
    password_value = password or ""
    if not normalized_email and not password_value and not required:
        db.rollback()
        return False
    if not normalized_email or len(password_value) < 20:
        db.rollback()
        raise RuntimeError(
            "First platform administrator is not configured. Set "
            "BOOTSTRAP_ADMIN_EMAIL and a unique BOOTSTRAP_ADMIN_PASSWORD "
            "of at least 20 characters."
        )
    if normalized_email == "admin@example.com" or password_value.startswith("replace-with-"):
        db.rollback()
        raise RuntimeError("Replace the example platform administrator credentials before deployment.")

    user = db.scalar(select(User).where(User.email_normalized == normalized_email))
    if user:
        if not verify_password(user.password_hash, password_value):
            db.rollback()
            raise RuntimeError(
                "The bootstrap email already belongs to an account with a different password. "
                "Choose credentials that match the existing account."
            )
    else:
        user = User(
            email=normalized_email,
            email_normalized=normalized_email,
            display_name="BrandLens Platform Admin",
            password_hash=hash_password(password_value),
        )
        db.add(user)
        db.flush()

    db.add(PlatformAdmin(user_id=user.id))
    db.add(
        AuditEvent(
            organization_id=None,
            actor_user_id=user.id,
            action="platform_admin.bootstrap_created",
            entity_type="user",
            entity_id=user.id,
            details={},
        )
    )
    db.commit()
    return True
