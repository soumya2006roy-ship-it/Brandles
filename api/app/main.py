from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from app.auth.router import router as auth_router
from app.orgs.settings_router import router as organization_settings_router
from app.core.config import get_settings
from app.orgs.router import router as org_router
from app.storage.router import router as private_files_router
from app.sources.router import router as sources_router

settings = get_settings()
if settings.is_production:
    if settings.app_secret_key == "local-only-change-me" or len(settings.app_secret_key) < 32:
        raise RuntimeError("APP_SECRET_KEY must be a unique secret with at least 32 characters in production")
    if not settings.session_cookie_secure:
        raise RuntimeError("SESSION_COOKIE_SECURE must be true in production")

app = FastAPI(
    title="BrandLens API",
    version="0.1.0",
    description="Organisation accounts, verification, membership and invitation API for BrandLens.",
    docs_url="/api/docs" if not settings.is_production else None,
    redoc_url=None,
    openapi_url="/api/openapi.json",
)


@app.middleware("http")
async def check_browser_origin(request: Request, call_next):
    if request.method not in {"GET", "HEAD", "OPTIONS"}:
        origin = request.headers.get("origin")
        if origin and origin.rstrip("/") != settings.frontend_origin.rstrip("/"):
            return JSONResponse(status_code=403, content={"detail": "Request origin is not allowed."})
    return await call_next(request)


@app.middleware("http")
async def api_security_headers(request: Request, call_next):
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Cross-Origin-Opener-Policy"] = "same-origin"
    response.headers["Permissions-Policy"] = "camera=(), microphone=(), geolocation=()"
    response.headers["Content-Security-Policy"] = "default-src 'none'; frame-ancestors 'none'; base-uri 'none'"
    if settings.is_production:
        response.headers["Strict-Transport-Security"] = "max-age=63072000; includeSubDomains; preload"
    return response


@app.get("/health", tags=["health"])
def health():
    return {"status": "ok", "environment": settings.app_env}


app.include_router(auth_router, prefix="/api/v1")
app.include_router(org_router, prefix="/api/v1")
app.include_router(organization_settings_router, prefix="/api/v1")
app.include_router(private_files_router, prefix="/api/v1")
app.include_router(sources_router, prefix="/api/v1")
