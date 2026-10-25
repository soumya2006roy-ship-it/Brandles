import argparse

from sqlalchemy import select

from app.core.db import SessionLocal
from app.db.models import PlatformAdmin, User


def main() -> None:
    parser = argparse.ArgumentParser(description="Trusted BrandLens platform administrator management")
    subparsers = parser.add_subparsers(dest="command", required=True)
    promote = subparsers.add_parser("promote-platform-admin")
    promote.add_argument("email")
    revoke = subparsers.add_parser("revoke-platform-admin")
    revoke.add_argument("email")
    args = parser.parse_args()
    with SessionLocal() as db:
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
