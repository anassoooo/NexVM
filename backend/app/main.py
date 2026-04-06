from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from supabase import create_client

from app.config import settings
from app import db
from app.routes.health import router as health_router
from app.routes.vm import router as vm_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    db.supabase_client = create_client(
        settings.SUPABASE_URL, settings.SUPABASE_SERVICE_KEY
    )
    yield
    db.supabase_client = None


app = FastAPI(title="myVMS API", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.FRONTEND_URL],
    allow_credentials=True,
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)

app.include_router(health_router, prefix="/api/v1")
app.include_router(vm_router, prefix="/api/v1/vm", tags=["vm"])
