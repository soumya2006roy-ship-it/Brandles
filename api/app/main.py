import logging
import re
import uuid
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.openapi.utils import get_openapi
from fastapi.responses import JSONResponse, PlainTextResponse
from redis import Redis
from sqlalchemy import text

from app.auth.router import router as auth_router
from app.auth.bootstrap import bootstrap_platform_admin
from app.orgs.settings_router import router as organization_settings_router
from app.core.config import get_settings
from app.orgs.router import router as org_router
from app.storage.router import router as private_files_router
from app.sources.router import router as sources_router
from app.campaigns.router import router as campaigns_router
from app.observability import increment, log_json, metric_snapshot, request_started
from app.core.db import SessionLocal, engine

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

@asynccontextmanager
async def lifespan(_: FastAPI):
    if settings.is_production:
        with SessionLocal() as db:
            created = bootstrap_platform_admin(
                db,
                settings.bootstrap_admin_email,
                settings.bootstrap_admin_password,
                required=True,
            )
        if created:
            logger.info("Initial platform administrator created; remove bootstrap credentials from the service environment")
    yield


app = FastAPI(
    title="BrandLens API",
    version="0.1.0",
    description="BrandLens organisation, source-evidence, campaign scanning, findings and version-bound review API.",
    docs_url="/docs" if not settings.is_production else None,
    redoc_url=None,
    openapi_url="/api/openapi.json",
    lifespan=lifespan,
)


@app.exception_handler(RequestValidationError)
async def request_validation_error(_request: Request, exc: RequestValidationError):
    # Keep validation responses concise; errors may otherwise include submitted input values.
    errors = [{"loc": error.get("loc", []), "msg": error.get("msg", "Invalid value"), "type": error.get("type", "value_error")} for error in exc.errors()]
    return JSONResponse(status_code=400, content={"detail": errors})


def custom_openapi() -> dict:
    if app.openapi_schema:
        return app.openapi_schema
    schema = get_openapi(
        title=app.title,
        version=app.version,
        description=app.description,
        routes=app.routes,
    )
    schema.setdefault("components", {}).setdefault("securitySchemes", {})[
        "BrandLensSession"
    ] = {
        "type": "apiKey",
        "in": "cookie",
        "name": settings.session_cookie_name,
        "description": "Session cookie set by the BrandLens login endpoint.",
    }
    public_routes = {
        ("GET", "/health"),
        ("GET", "/ready"),
        ("GET", "/metrics"),
        ("POST", "/api/v1/auth/register"),
        ("POST", "/api/v1/auth/login"),
        ("POST", "/api/v1/auth/password-reset"),
        ("POST", "/api/v1/auth/password-reset/confirm"),
    }
    for path, path_item in schema.get("paths", {}).items():
        for method, operation in path_item.items():
            if method.upper() not in {"GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS", "HEAD"}:
                continue
            if (method.upper(), path) in public_routes:
                operation.pop("security", None)
            else:
                operation["security"] = [{"BrandLensSession": []}]
    app.openapi_schema = schema
    return schema


app.openapi = custom_openapi


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
        logger.exception("Unhandled API request failure", extra={"request_id": request_id, "method": request.method, "path": request.url.path, "status_code": 500})
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
        logger.exception("Database readiness check failed")
    try:
        checks["redis"] = bool(Redis.from_url(settings.redis_url, socket_connect_timeout=0.5, socket_timeout=0.5).ping())
    except Exception:
        logger.exception("Redis readiness check failed")
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
