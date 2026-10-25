import smtplib
from dataclasses import dataclass
from email.message import EmailMessage
from typing import Protocol

import httpx

from app.core.config import get_settings


@dataclass(frozen=True)
class OutboundEmail:
    to: str
    subject: str
    text: str


class EmailSender(Protocol):
    def send(self, email: OutboundEmail) -> None: ...


class ResendEmailSender:
    def send(self, email: OutboundEmail) -> None:
        settings = get_settings()
        if not settings.resend_api_key:
            raise RuntimeError("Resend email is not configured")
        response = httpx.post(
            "https://api.resend.com/emails",
            headers={"Authorization": f"Bearer {settings.resend_api_key}"},
            json={"from": settings.resend_from_email, "to": [email.to], "subject": email.subject, "text": email.text},
            timeout=10.0,
        )
        response.raise_for_status()


class SmtpEmailSender:
    def send(self, email: OutboundEmail) -> None:
        settings = get_settings()
        if not settings.smtp_host:
            raise RuntimeError("SMTP email is not configured")
        message = EmailMessage()
        message["From"] = settings.resend_from_email
        message["To"] = email.to
        message["Subject"] = email.subject
        message.set_content(email.text)
        with smtplib.SMTP(settings.smtp_host, settings.smtp_port, timeout=10) as client:
            if settings.smtp_starttls:
                client.starttls()
            if settings.smtp_username and settings.smtp_password:
                client.login(settings.smtp_username, settings.smtp_password)
            client.send_message(message)


def get_email_sender() -> EmailSender:
    settings = get_settings()
    if settings.email_provider == "smtp":
        return SmtpEmailSender()
    return ResendEmailSender()
