import logging
import os
import sys
from contextlib import asynccontextmanager

import httpx
import uvicorn
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
from supabase import ClientOptions, create_client

from app.config import settings
from app import db
from app.services import schedule_service
from app.routes.admin_vm import router as admin_vm_router
from app.routes.ai import router as ai_router
from app.routes.analytics import router as analytics_router
from app.routes.auth import router as auth_router
from app.routes.health import router as health_router
from app.routes.logs import router as logs_router
from app.routes.schedules import router as schedules_router
from app.routes.vm import router as vm_router

# --- Logging setup (dev mode) ---
logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s [%(levelname)s] %(name)s — %(message)s",
    datefmt="%H:%M:%S",
    handlers=[logging.StreamHandler(sys.stdout)],
)
logger = logging.getLogger("NexVM")

# Suppress noisy third-party loggers in dev
logging.getLogger("httpx").setLevel(logging.WARNING)
logging.getLogger("httpcore").setLevel(logging.WARNING)
logging.getLogger("supabase").setLevel(logging.INFO)


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Starting up — connecting to Supabase (%s)", settings.SUPABASE_URL)
    db.supabase_client = create_client(
        settings.SUPABASE_URL,
        settings.SUPABASE_SECRET_KEY,
        options=ClientOptions(httpx_client=httpx.Client(http2=False)),
    )
    logger.info("Supabase client ready")

    storage_path = settings.VM_STORAGE_PATH or os.path.join(os.path.expanduser("~"), "VirtualBox VMs")
    try:
        os.makedirs(storage_path, exist_ok=True)
        logger.info("VM storage path: %s", storage_path)
    except OSError as exc:
        logger.warning("VM storage path could not be created: %s", exc)

    schedule_service.start_scheduler()
    yield
    logger.info("Shutting down — releasing Supabase client")
    schedule_service.stop_scheduler()
    db.supabase_client = None


app = FastAPI(title="NexVM API", lifespan=lifespan)


async def _log_requests(request: Request, call_next):
    logger.debug(">> %s %s", request.method, request.url.path)
    response = await call_next(request)
    logger.debug("<< %s %s %d", request.method, request.url.path, response.status_code)
    return response


# Logging middleware added FIRST (becomes inner) so CORS stays outermost.
app.add_middleware(BaseHTTPMiddleware, dispatch=_log_requests)
app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.FRONTEND_URL],
    allow_credentials=True,
    allow_methods=["GET", "POST", "DELETE", "PUT", "PATCH", "OPTIONS"],
    allow_headers=["*"],
)


# Ensure CORS headers are present even on unhandled 500 errors.
# BaseHTTPMiddleware can swallow them otherwise.
@app.exception_handler(Exception)
async def _unhandled_exception_handler(request: Request, exc: Exception):
    origin = request.headers.get("origin", "")
    logger.exception("Unhandled exception on %s %s", request.method, request.url.path)
    headers = {}
    if origin in (settings.FRONTEND_URL, ""):
        headers["Access-Control-Allow-Origin"] = origin or settings.FRONTEND_URL
        headers["Access-Control-Allow-Credentials"] = "true"
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal server error"},
        headers=headers,
    )


app.include_router(health_router, prefix="/api/v1")
app.include_router(auth_router, prefix="/api/v1/auth", tags=["auth"])
app.include_router(vm_router, prefix="/api/v1/vm", tags=["vm"])
app.include_router(admin_vm_router, prefix="/api/v1/admin/vm", tags=["admin-vm"])
app.include_router(ai_router, prefix="/api/v1/ai", tags=["ai"])
app.include_router(analytics_router, prefix="/api/v1/analytics", tags=["analytics"])
app.include_router(logs_router, prefix="/api/v1/logs", tags=["logs"])
app.include_router(schedules_router, prefix="/api/v1/schedules", tags=["schedules"])


if __name__ == "__main__":
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True, log_level="debug")
