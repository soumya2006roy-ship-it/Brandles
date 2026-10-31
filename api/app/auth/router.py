from datetime import UTC, datetime

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from sqlalchemy import select, update
from sqlalchemy.orm import Session

from app.auth.dependencies import AuthContext, get_auth_context, get_current_user
from app.auth.schemas import LoginRequest, PasswordResetConfirm, PasswordResetRequest, RecoveryPasswordReset, RegisterRequest, SessionResponse, UserResponse
from app.core.config import get_settings
from app.core.db import get_db
from app.core.mail import EmailSender, OutboundEmail, get_email_sender
from app.core.rate_limit import clear_login_failures, client_ip, enforce_login_delay, enforce_rate_limit, record_login_failure
from app.core.security import as_utc, digest_secret, expires_in, hash_password, new_secret, verify_password
from app.db.models import AuditEvent, AuthToken, Membership, SessionRecord, User

router = APIRouter(prefix="/auth", tags=["auth"])
_dummy_password_hash = hash_password("not-a-real-account-password")
_dummy_recovery_hash = hash_password("not-a-real-recovery-answer")


def _now() -> datetime:
    return datetime.now(UTC)


def _client_key(request: Request, action: str) -> str:
    host = client_ip(request)
    return f"{action}:{host}"


def _record_auth_event(db: Session, user: User, action: str) -> None:
    organization_ids = db.scalars(select(Membership.organization_id).where(Membership.user_id == user.id)).all()
    targets = organization_ids or [None]
    for organization_id in targets:
        db.add(AuditEvent(organization_id=organization_id, actor_user_id=user.id, action=action, entity_type="authentication", entity_id=user.id, details={}))


def _new_auth_token(db: Session, user: User, purpose: str, ttl_minutes: int) -> str:
    raw = new_secret()
    db.add(AuthToken(user_id=user.id, token_hash=digest_secret(raw), purpose=purpose, expires_at=expires_in(minutes=ttl_minutes)))
    return raw


def _normalize_recovery_answer(answer: str) -> str:
    return " ".join(answer.casefold().split())


@router.post("/register", status_code=status.HTTP_201_CREATED)
def register(payload: RegisterRequest, request: Request, db: Session = Depends(get_db)):
    enforce_rate_limit(_client_key(request, "register"), limit=5, window_seconds=3600)
    normalized_email = str(payload.email).strip().lower()
    existing = db.scalar(select(User).where(User.email_normalized == normalized_email))
    if existing:
        return {"message": "If this address can be registered, the account will be ready to sign in."}
    user = User(email=str(payload.email).strip(), email_normalized=normalized_email, display_name=payload.display_name, password_hash=hash_password(payload.password), recovery_question=payload.recovery_question, recovery_answer_hash=hash_password(_normalize_recovery_answer(payload.recovery_answer)))
    db.add(user)
    db.flush()
    _record_auth_event(db, user, "auth.registered")
    db.commit()
    return {"message": "Your account is ready. Sign in to continue."}


@router.post("/login")
def login(payload: LoginRequest, request: Request, response: Response, db: Session = Depends(get_db)):
    request_key = _client_key(request, "login")
    enforce_rate_limit(request_key, limit=10, window_seconds=900)
    enforce_login_delay(request_key)
    email = str(payload.email).strip().lower()
    user = db.scalar(select(User).where(User.email_normalized == email, User.is_active.is_(True)))
    password_hash = user.password_hash if user else _dummy_password_hash
    valid_password = verify_password(password_hash, payload.password)
    if not user or not valid_password:
        record_login_failure(request_key)
        if user:
            _record_auth_event(db, user, "auth.login_failed")
        else:
            db.add(AuditEvent(organization_id=None, actor_user_id=None, action="auth.login_failed", entity_type="authentication", entity_id="unidentified", details={}))
        db.commit()
        raise HTTPException(status_code=401, detail="Email or password is incorrect.")
    clear_login_failures(request_key)
    raw_session = new_secret()
    session = SessionRecord(user_id=user.id, token_hash=digest_secret(raw_session), expires_at=expires_in(hours=get_settings().session_ttl_hours), user_agent=(request.headers.get("user-agent") or "")[:500])
    db.add(session)
    _record_auth_event(db, user, "auth.login")
    db.commit()
    settings = get_settings()
    response.set_cookie(settings.session_cookie_name, raw_session, httponly=True, secure=settings.session_cookie_secure or settings.is_production, samesite="lax", max_age=settings.session_ttl_hours * 3600, path="/")
    return {"user": UserResponse.model_validate(user)}


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
def logout(response: Response, context: AuthContext = Depends(get_auth_context), db: Session = Depends(get_db)):
    context.session.revoked_at = _now()
    _record_auth_event(db, context.user, "auth.logout")
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
        _record_auth_event(db, user, "auth.password_reset_requested")
        token = _new_auth_token(db, user, "password_reset", get_settings().password_reset_ttl_minutes)
        db.commit()
        reset_url = f"{get_settings().frontend_origin.rstrip('/')}/reset-password?token={token}"
        try:
            sender.send(OutboundEmail(user.email, "Reset your BrandLens password", f"Use this single-use link to reset your password: {reset_url}\n\nIf you did not request a reset, ignore this message."))
        except Exception:
            pass
    return {"message": "If an account exists for that address, a password reset link will arrive shortly."}


@router.post("/password-reset/recovery-question", status_code=status.HTTP_202_ACCEPTED)
def reset_password_with_recovery_question(payload: RecoveryPasswordReset, request: Request, db: Session = Depends(get_db)):
    normalized_email = str(payload.email).strip().lower()
    enforce_rate_limit(_client_key(request, "password-reset-question"), limit=10, window_seconds=900)
    enforce_rate_limit(f"password-reset-question-account:{digest_secret(normalized_email)}", limit=5, window_seconds=3600)
    user = db.scalar(select(User).where(User.email_normalized == normalized_email, User.is_active.is_(True)))
    answer_hash = user.recovery_answer_hash if user and user.recovery_answer_hash else _dummy_recovery_hash
    correct_answer = verify_password(answer_hash, _normalize_recovery_answer(payload.recovery_answer))
    if user and user.recovery_question == payload.recovery_question and user.recovery_answer_hash and correct_answer:
        user.password_hash = hash_password(payload.password)
        db.execute(update(SessionRecord).where(SessionRecord.user_id == user.id, SessionRecord.revoked_at.is_(None)).values(revoked_at=_now()))
        _record_auth_event(db, user, "auth.password_recovery_question_completed")
        db.commit()
    # Keep account existence and recovery success out of the response body.
    return {"message": "If the recovery details match, the password has been updated. Otherwise, check your answer or use the email reset option."}


@router.post("/password-reset/confirm")
def confirm_password_reset(payload: PasswordResetConfirm, request: Request, db: Session = Depends(get_db)):
    enforce_rate_limit(_client_key(request, "password-reset-confirm"), limit=10, window_seconds=900)
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
    _record_auth_event(db, user, "auth.password_reset_completed")
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
