import logging

from sqlalchemy.orm import Session
from sqlalchemy import select

from app.core.mail import EmailSender, OutboundEmail
from app.db.models import Membership, Notification, User

logger = logging.getLogger("brandlens.notifications")


def record_notification(db: Session, *, user_id: str, organization_id: str, kind: str, payload: dict) -> None:
    membership = db.scalar(select(Membership).where(Membership.organization_id == organization_id, Membership.user_id == user_id))
    if membership and not (membership.notification_preferences or {}).get("in_app", True):
        return
    db.add(Notification(user_id=user_id, organization_id=organization_id, kind=kind, payload=payload))


def send_user_email(db: Session, sender: EmailSender, *, user_id: str, subject: str, text: str, organization_id: str | None = None) -> None:
    user = db.get(User, user_id)
    if not user or not user.email_verified_at:
        return
    if organization_id:
        membership = db.scalar(select(Membership).where(Membership.organization_id == organization_id, Membership.user_id == user_id))
        if membership and not (membership.notification_preferences or {}).get("email", True):
            return
    try:
        sender.send(OutboundEmail(to=user.email, subject=subject, text=text))
    except Exception:
        # Email delivery is best effort; the in-app notification is persisted separately.
        logger.exception("Could not deliver workspace notification email")
