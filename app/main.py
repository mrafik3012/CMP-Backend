#!/usr/bin/env python
# MODIFIED: 2026-03-03 - Mounted uploads static files
"""Construction PM API. NFR-MAINT-001: OpenAPI docs."""
from fastapi import FastAPI, Depends, HTTPException, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from sqlalchemy.orm import Session

from app.api import api_router
from app.core.config import get_settings
_settings = get_settings()
from app.db.session import init_db, get_db
from app.schemas.auth import SendLoginOtpRequest
from app.services.auth_service import send_login_otp_to_user

app = FastAPI(
    title="Construction Project Management API",
    description="API for construction PM system. See REQUIREMENTS.md.",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

origins = [
    "https://cmp-frontend-0vop.onrender.com",
    "http://localhost:5173",
    "http://127.0.0.1:5173",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register send-login-otp at app level first so it always matches (avoids 404 from router ordering)
@app.post("/api/v1/auth/send-login-otp")
def send_login_otp_app(response: Response, data: SendLoginOtpRequest, db: Session = Depends(get_db)):
    """Send OTP to phone. Duplicate of auth router so this path is guaranteed."""
    response.headers["X-Backend"] = "constructiq-otp"
    result = send_login_otp_to_user(db, data.phone)
    if "error" in result:
        raise HTTPException(
            status_code=400 if result["error"] == "phone_not_found" else 403,
            detail=result["error"],
        )
    return result


def _get_routes_list():
    """Build routes list from OpenAPI; fallback if empty."""
    out = []
    try:
        openapi = app.openapi()
        for path, methods_dict in (openapi.get("paths") or {}).items():
            methods = [m.upper() for m in methods_dict if m in ("get", "post", "put", "patch", "delete", "options")]
            if methods:
                out.append({"path": path, "methods": methods})
    except Exception:
        pass
    if not out:
        out = [
            {"path": "/api/v1/auth/send-login-otp", "methods": ["POST"]},
            {"path": "/api/v1/auth/verify-login-otp", "methods": ["POST"]},
            {"path": "/api/v1/routes", "methods": ["GET"]},
        ]
    return out


@app.get("/api/v1/routes")
def list_routes_main():
    """Debug: list API routes. Registered on main app so it is never shadowed."""
    return {"backend": "constructiq", "routes": _get_routes_list()}


app.include_router(api_router)

app.mount("/uploads", StaticFiles(directory="uploads"), name="uploads")


def _collect_routes(routes, prefix=""):
    from starlette.routing import Mount
    out = []
    for r in routes:
        path = getattr(r, "path", None) or ""
        full = (prefix + path).replace("//", "/")
        if getattr(r, "methods", None):
            out.append({"methods": list(r.methods), "path": full})
        elif isinstance(r, Mount) and hasattr(r, "routes"):
            out.extend(_collect_routes(r.routes, full))
        elif getattr(r, "routes", None):
            out.extend(_collect_routes(r.routes, full))
    return out


@app.on_event("startup")
def startup():
    init_db()
    for item in _collect_routes(app.routes):
        if "send-login-otp" in item.get("path", ""):
            print(f"[ROUTES] {item}")


@app.get("/health")
def health():
    return {"status": "ok"}


@app.get("/backend-id")
def backend_id():
    """Confirm this is the ConstructIQ backend. If you get 404 here, another app is on port 8000."""
    return {"app": "ConstructIQ", "version": "1.0.0", "routes_at": "/debug-routes"}


@app.get("/debug-routes")
def debug_routes():
    """Same as /api/v1/routes but at root so it never 404s from router shadowing."""
    return {"backend": "constructiq", "routes": _get_routes_list()}
