import argparse
from datetime import UTC, datetime

from sqlalchemy import select

from app.core.db import SessionLocal
from app.core.config import get_settings
from app.core.security import hash_password, verify_password
from app.db.models import AuditEvent, PlatformAdmin, User


def main() -> None:
    parser = argparse.ArgumentParser(description="Trusted BrandLens platform administrator management")
    subparsers = parser.add_subparsers(dest="command", required=True)
    promote = subparsers.add_parser("promote-platform-admin")
    promote.add_argument("email")
    revoke = subparsers.add_parser("revoke-platform-admin")
    revoke.add_argument("email")
    subparsers.add_parser("bootstrap-platform-admin", help="Create the development bootstrap admin only if none exists")
    args = parser.parse_args()
    with SessionLocal() as db:
        if args.command == "bootstrap-platform-admin":
            if db.query(PlatformAdmin).first():
                print("A platform administrator already exists; no bootstrap changes were made.")
                return
            settings = get_settings()
            email = (settings.bootstrap_admin_email or "").strip().lower()
            password = settings.bootstrap_admin_password or ""
            if not email or not password or len(password) < 20:
                raise SystemExit("Set BOOTSTRAP_ADMIN_EMAIL and a 20-character BOOTSTRAP_ADMIN_PASSWORD in api/.env first.")
            user = db.scalar(select(User).where(User.email_normalized == email))
            if user:
                if not user.email_verified_at or not verify_password(user.password_hash, password):
                    raise SystemExit("The configured bootstrap email already belongs to an account; use its verified account or choose a new bootstrap email.")
            else:
                user = User(
                    email=email,
                    email_normalized=email,
                    display_name="BrandLens Platform Admin",
                    password_hash=hash_password(password),
                    email_verified_at=datetime.now(UTC),
                )
                db.add(user)
                db.flush()
            db.add(PlatformAdmin(user_id=user.id))
            db.add(AuditEvent(organization_id=None, actor_user_id=user.id, action="platform_admin.bootstrap_created", entity_type="user", entity_id=user.id, details={}))
            db.commit()
            print("The development platform administrator was created. Credentials are in the local .env file; change the password after signing in.")
            return
        email = args.email.strip().lower()
        user = db.scalar(select(User).where(User.email_normalized == email, User.email_verified_at.is_not(None)))
        if not user:
            raise SystemExit("A verified account with that email must exist first.")
        record = db.get(PlatformAdmin, user.id)
        if args.command == "promote-platform-admin":
            if not record:
                db.add(PlatformAdmin(user_id=user.id))
            db.commit()
            print("Platform administrator role granted.")
        else:
            if record:
                db.delete(record)
                db.commit()
            print("Platform administrator role revoked.")


if __name__ == "__main__":
    main()
