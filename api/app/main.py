import logging
import re
import uuid

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse, PlainTextResponse
from redis import Redis
from sqlalchemy import text

from app.auth.router import router as auth_router
from app.orgs.settings_router import router as organization_settings_router
from app.core.config import get_settings
from app.orgs.router import router as org_router
from app.storage.router import router as private_files_router
from app.sources.router import router as sources_router
from app.campaigns.router import router as campaigns_router
from app.observability import increment, log_json, metric_snapshot, request_started
from app.core.db import engine

settings = get_settings()
logger = logging.getLogger("brandlens.api")
if settings.sentry_dsn:
    try:
        import sentry_sdk

        sentry_sdk.init(dsn=settings.sentry_dsn, traces_sample_rate=settings.sentry_traces_sample_rate, send_default_pii=False)
    except ImportError:
        logger.warning("SENTRY_DSN is configured but sentry-sdk is not installed")
if settings.is_production:
    if settings.app_secret_key == "local-only-change-me" or len(settings.app_secret_key) < 32:
        raise RuntimeError("APP_SECRET_KEY must be a unique secret with at least 32 characters in production")
    if not settings.session_cookie_secure:
        raise RuntimeError("SESSION_COOKIE_SECURE must be true in production")

app = FastAPI(
    title="BrandLens API",
    version="0.1.0",
    description="BrandLens organisation, source-evidence, campaign scanning, findings and version-bound review API.",
    docs_url="/docs" if not settings.is_production else None,
    redoc_url=None,
    openapi_url="/api/openapi.json",
)


@app.middleware("http")
async def check_browser_origin(request: Request, call_next):
    request_id = request.headers.get("x-request-id", "")
    if not re.fullmatch(r"[A-Za-z0-9._-]{1,80}", request_id):
        request_id = str(uuid.uuid4())
    request.state.request_id = request_id
    started = request_started()
    if request.method not in {"GET", "HEAD", "OPTIONS"}:
        origin = request.headers.get("origin")
        fetch_site = request.headers.get("sec-fetch-site", "").casefold()
        if origin and origin.rstrip("/") != settings.frontend_origin.rstrip("/"):
            response = JSONResponse(status_code=403, content={"detail": "Request origin is not allowed."})
            response.headers["X-Request-ID"] = request_id
            return response
        if fetch_site == "cross-site":
            response = JSONResponse(status_code=403, content={"detail": "Cross-site requests are not allowed."})
            response.headers["X-Request-ID"] = request_id
            return response
    try:
        response = await call_next(request)
    except Exception:
        increment("http_errors_total")
        log_json(logger, "request_failed", request_id=request_id, method=request.method, path=request.url.path, status_code=500)
        raise
    duration = request_started() - started
    increment("http_requests_total")
    increment("http_errors_total", 1 if response.status_code >= 500 else 0)
    increment("http_request_duration_seconds_total", duration)
    response.headers["X-Request-ID"] = request_id
    log_json(logger, "request_complete", request_id=request_id, method=request.method, path=request.url.path, status_code=response.status_code, duration_ms=round(duration * 1000, 2))
    return response


@app.middleware("http")
async def api_security_headers(request: Request, call_next):
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Cross-Origin-Opener-Policy"] = "same-origin"
    response.headers["Permissions-Policy"] = "camera=(), microphone=(), geolocation=()"
    response.headers["Content-Security-Policy"] = "default-src 'none'; frame-ancestors 'none'; base-uri 'none'"
    response.headers["Cache-Control"] = "no-store"
    if settings.is_production:
        response.headers["Strict-Transport-Security"] = "max-age=63072000; includeSubDomains; preload"
    return response


@app.get("/health", tags=["health"])
def health():
    return {"status": "ok"}


@app.get("/ready", tags=["health"])
def readiness():
    checks = {"database": False, "redis": False}
    try:
        with engine.connect() as connection:
            connection.execute(text("SELECT 1"))
        checks["database"] = True
    except Exception:
        pass
    try:
        checks["redis"] = bool(Redis.from_url(settings.redis_url, socket_connect_timeout=0.5, socket_timeout=0.5).ping())
    except Exception:
        pass
    if not all(checks.values()):
        return JSONResponse(status_code=503, content={"status": "not_ready", "checks": checks})
    return {"status": "ready", "checks": checks}


@app.get("/metrics", tags=["health"], response_class=PlainTextResponse)
def metrics():
    counters = metric_snapshot()
    lines = ["# HELP brandlens_process_counter Process-local operational counters", "# TYPE brandlens_process_counter counter"]
    lines.extend(f"brandlens_{name} {value}" for name, value in sorted(counters.items()))
    return PlainTextResponse("\n".join(lines) + "\n", media_type="text/plain; version=0.0.4; charset=utf-8")


app.include_router(auth_router, prefix="/api/v1")
app.include_router(org_router, prefix="/api/v1")
app.include_router(organization_settings_router, prefix="/api/v1")
app.include_router(private_files_router, prefix="/api/v1")
app.include_router(sources_router, prefix="/api/v1")
app.include_router(campaigns_router, prefix="/api/v1")
