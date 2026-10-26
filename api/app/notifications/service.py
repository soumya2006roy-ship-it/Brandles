import logging

from sqlalchemy.orm import Session

from app.core.mail import EmailSender, OutboundEmail
from app.db.models import Notification, User

logger = logging.getLogger("brandlens.notifications")


def record_notification(db: Session, *, user_id: str, organization_id: str, kind: str, payload: dict) -> None:
    db.add(Notification(user_id=user_id, organization_id=organization_id, kind=kind, payload=payload))


def send_user_email(db: Session, sender: EmailSender, *, user_id: str, subject: str, text: str) -> None:
    user = db.get(User, user_id)
    if not user or not user.email_verified_at:
        return
    try:
        sender.send(OutboundEmail(to=user.email, subject=subject, text=text))
    except Exception:
        # Email delivery is best effort; the in-app notification is persisted separately.
        logger.exception("Could not deliver workspace notification email")
