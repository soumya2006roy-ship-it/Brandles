from datetime import UTC, datetime

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from sqlalchemy import select, update
from sqlalchemy.orm import Session

from app.auth.dependencies import AuthContext, get_auth_context, get_current_user
from app.auth.schemas import LoginRequest, PasswordResetConfirm, PasswordResetRequest, RegisterRequest, SessionResponse, UserResponse
from app.core.config import get_settings
from app.core.db import get_db
from app.core.mail import EmailSender, OutboundEmail, get_email_sender
from app.core.rate_limit import enforce_rate_limit
from app.core.security import as_utc, digest_secret, expires_in, hash_password, new_secret, verify_password
from app.db.models import AuthToken, SessionRecord, User

router = APIRouter(prefix="/auth", tags=["auth"])
_dummy_password_hash = hash_password("not-a-real-account-password")


def _now() -> datetime:
    return datetime.now(UTC)


def _client_key(request: Request, action: str) -> str:
    host = request.client.host if request.client else "unknown"
    return f"{action}:{host}"


def _new_auth_token(db: Session, user: User, purpose: str, ttl_minutes: int) -> str:
    raw = new_secret()
    db.add(AuthToken(user_id=user.id, token_hash=digest_secret(raw), purpose=purpose, expires_at=expires_in(minutes=ttl_minutes)))
    return raw


def _send_verification(sender: EmailSender, user: User, raw_token: str) -> None:
    url = f"{get_settings().frontend_origin.rstrip('/')}/verify-email?token={raw_token}"
    sender.send(OutboundEmail(user.email, "Verify your BrandLens account", f"Hello {user.display_name},\n\nVerify your email to continue: {url}\n\nIf you did not create this account, ignore this message."))


@router.post("/register", status_code=status.HTTP_202_ACCEPTED)
def register(payload: RegisterRequest, request: Request, db: Session = Depends(get_db), sender: EmailSender = Depends(get_email_sender)):
    enforce_rate_limit(_client_key(request, "register"), limit=5, window_seconds=3600)
    normalized_email = str(payload.email).strip().lower()
    if db.scalar(select(User.id).where(User.email_normalized == normalized_email)):
        raise HTTPException(status_code=409, detail="An account already exists for this email address.")
    user = User(email=str(payload.email).strip(), email_normalized=normalized_email, display_name=payload.display_name, password_hash=hash_password(payload.password))
    db.add(user)
    db.flush()
    raw_token = _new_auth_token(db, user, "email_verification", get_settings().verification_token_ttl_minutes)
    db.commit()
    try:
        _send_verification(sender, user, raw_token)
    except Exception:
        raise HTTPException(status_code=503, detail="Your account is saved, but verification email could not be sent. Try requesting a new verification email.") from None
    return {"message": "Check your email for a verification link."}


@router.post("/verification-email", status_code=status.HTTP_202_ACCEPTED)
def resend_verification(payload: PasswordResetRequest, request: Request, db: Session = Depends(get_db), sender: EmailSender = Depends(get_email_sender)):
    enforce_rate_limit(_client_key(request, "verification"), limit=5, window_seconds=3600)
    email = str(payload.email).strip().lower()
    user = db.scalar(select(User).where(User.email_normalized == email, User.is_active.is_(True)))
    if user and not user.email_verified_at:
        raw_token = _new_auth_token(db, user, "email_verification", get_settings().verification_token_ttl_minutes)
        db.commit()
        try:
            _send_verification(sender, user, raw_token)
        except Exception:
            pass
    return {"message": "If the account needs verification, an email will arrive shortly."}


@router.get("/verify-email")
def verify_email(token: str, db: Session = Depends(get_db)):
    token_record = db.scalar(select(AuthToken).where(
        AuthToken.token_hash == digest_secret(token),
        AuthToken.purpose == "email_verification",
        AuthToken.consumed_at.is_(None),
        AuthToken.expires_at > _now(),
    ))
    if not token_record:
        raise HTTPException(status_code=400, detail="This verification link is invalid or expired.")
    user = db.get(User, token_record.user_id)
    if not user or not user.is_active:
        raise HTTPException(status_code=400, detail="This verification link is invalid or expired.")
    user.email_verified_at = _now()
    token_record.consumed_at = _now()
    db.commit()
    return {"message": "Email verified. You can now sign in."}


@router.post("/login")
def login(payload: LoginRequest, request: Request, response: Response, db: Session = Depends(get_db)):
    enforce_rate_limit(_client_key(request, "login"), limit=10, window_seconds=900)
    email = str(payload.email).strip().lower()
    user = db.scalar(select(User).where(User.email_normalized == email, User.is_active.is_(True)))
    password_hash = user.password_hash if user else _dummy_password_hash
    valid_password = verify_password(password_hash, payload.password)
    if not user or not valid_password:
        raise HTTPException(status_code=401, detail="Email or password is incorrect.")
    if not user.email_verified_at:
        raise HTTPException(status_code=403, detail="Verify your email before signing in.")
    raw_session = new_secret()
    session = SessionRecord(user_id=user.id, token_hash=digest_secret(raw_session), expires_at=expires_in(hours=get_settings().session_ttl_hours), user_agent=(request.headers.get("user-agent") or "")[:500])
    db.add(session)
    db.commit()
    settings = get_settings()
    response.set_cookie(settings.session_cookie_name, raw_session, httponly=True, secure=settings.session_cookie_secure or settings.is_production, samesite="lax", max_age=settings.session_ttl_hours * 3600, path="/")
    return {"user": UserResponse.model_validate(user)}


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
def logout(response: Response, context: AuthContext = Depends(get_auth_context), db: Session = Depends(get_db)):
    context.session.revoked_at = _now()
    db.commit()
    response.delete_cookie(get_settings().session_cookie_name, path="/", httponly=True, secure=get_settings().session_cookie_secure or get_settings().is_production, samesite="lax")


@router.get("/me", response_model=UserResponse)
def me(user: User = Depends(get_current_user)):
    return user


@router.post("/password-reset", status_code=status.HTTP_202_ACCEPTED)
def request_password_reset(payload: PasswordResetRequest, request: Request, db: Session = Depends(get_db), sender: EmailSender = Depends(get_email_sender)):
    enforce_rate_limit(_client_key(request, "password-reset"), limit=5, window_seconds=3600)
    email = str(payload.email).strip().lower()
    user = db.scalar(select(User).where(User.email_normalized == email, User.is_active.is_(True)))
    if user:
        token = _new_auth_token(db, user, "password_reset", get_settings().password_reset_ttl_minutes)
        db.commit()
        reset_url = f"{get_settings().frontend_origin.rstrip('/')}/reset-password?token={token}"
        try:
            sender.send(OutboundEmail(user.email, "Reset your BrandLens password", f"Use this single-use link to reset your password: {reset_url}\n\nIf you did not request a reset, ignore this message."))
        except Exception:
            pass
    return {"message": "If an account exists for that address, a password reset link will arrive shortly."}


@router.post("/password-reset/confirm")
def confirm_password_reset(payload: PasswordResetConfirm, db: Session = Depends(get_db)):
    token_record = db.scalar(select(AuthToken).where(
        AuthToken.token_hash == digest_secret(payload.token),
        AuthToken.purpose == "password_reset",
        AuthToken.consumed_at.is_(None),
        AuthToken.expires_at > _now(),
    ))
    if not token_record:
        raise HTTPException(status_code=400, detail="This reset link is invalid or expired.")
    user = db.get(User, token_record.user_id)
    if not user or not user.is_active:
        raise HTTPException(status_code=400, detail="This reset link is invalid or expired.")
    user.password_hash = hash_password(payload.password)
    token_record.consumed_at = _now()
    db.execute(update(SessionRecord).where(SessionRecord.user_id == user.id, SessionRecord.revoked_at.is_(None)).values(revoked_at=_now()))
    db.commit()
    return {"message": "Password updated. Sign in with your new password."}


@router.get("/sessions", response_model=list[SessionResponse])
def sessions(context: AuthContext = Depends(get_auth_context), db: Session = Depends(get_db)):
    now = _now()
    records = db.scalars(select(SessionRecord).where(SessionRecord.user_id == context.user.id, SessionRecord.revoked_at.is_(None), SessionRecord.expires_at > now).order_by(SessionRecord.created_at.desc())).all()
    return [SessionResponse(id=item.id, created_at=item.created_at, expires_at=item.expires_at, current=item.id == context.session.id) for item in records]


@router.delete("/sessions/{session_id}", status_code=status.HTTP_204_NO_CONTENT)
def revoke_session(session_id: str, context: AuthContext = Depends(get_auth_context), db: Session = Depends(get_db)):
    record = db.scalar(select(SessionRecord).where(SessionRecord.id == session_id, SessionRecord.user_id == context.user.id, SessionRecord.revoked_at.is_(None)))
    if not record:
        raise HTTPException(status_code=404, detail="Session not found.")
    record.revoked_at = _now()
    db.commit()
