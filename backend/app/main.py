from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from supabase import create_client, Client

from app.config import settings
from app.routes.health import router as health_router

supabase_client: Client | None = None


def get_supabase_client() -> Client:
    return supabase_client


@asynccontextmanager
async def lifespan(app: FastAPI):
    global supabase_client
    supabase_client = create_client(
        settings.SUPABASE_URL, settings.SUPABASE_SERVICE_KEY
    )
    yield
    supabase_client = None


app = FastAPI(title="myVMS API", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.FRONTEND_URL],
    allow_credentials=True,
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)

app.include_router(health_router, prefix="/api/v1")
