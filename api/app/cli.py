import argparse
from sqlalchemy import select

from app.core.db import SessionLocal
from app.core.config import get_settings
from app.auth.bootstrap import bootstrap_platform_admin
from app.db.models import PlatformAdmin, User


def main() -> None:
    parser = argparse.ArgumentParser(description="Trusted BrandLens platform administrator management")
    subparsers = parser.add_subparsers(dest="command", required=True)
    promote = subparsers.add_parser("promote-platform-admin")
    promote.add_argument("email")
    revoke = subparsers.add_parser("revoke-platform-admin")
    revoke.add_argument("email")
    subparsers.add_parser("bootstrap-platform-admin", help="Create the first platform admin only if none exists")
    args = parser.parse_args()
    with SessionLocal() as db:
        if args.command == "bootstrap-platform-admin":
            settings = get_settings()
            created = bootstrap_platform_admin(
                db,
                settings.bootstrap_admin_email,
                settings.bootstrap_admin_password,
                required=True,
            )
            print("Platform administrator created." if created else "A platform administrator already exists; no bootstrap changes were made.")
            return
        email = args.email.strip().lower()
        user = db.scalar(select(User).where(User.email_normalized == email))
        if not user:
            raise SystemExit("An account with that email must exist first.")
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
