"""Spec 012 F3 — a slow VBoxManage call must not block other requests."""

import asyncio
import time
import uuid
from unittest.mock import patch

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

from app.dependencies import UserClaims, get_current_user
from app.routes.health import router as health_router
from app.routes.vm import router as vm_router


def _slow_start(*_args, **_kwargs):
    time.sleep(1.5)
    raise RuntimeError("done sleeping")


@pytest.mark.asyncio
async def test_health_answers_while_vm_start_is_blocked():
    app = FastAPI()
    app.include_router(health_router, prefix="/api/v1")
    app.include_router(vm_router, prefix="/api/v1/vm")
    app.dependency_overrides[get_current_user] = lambda: UserClaims(id="u", email="")

    with (
        patch("app.services.vm_service.start_vm", side_effect=_slow_start),
        patch("app.routes.health._get_vbox_version", return_value="7.2"),
    ):
        async with AsyncClient(
            transport=ASGITransport(app=app, raise_app_exceptions=False), base_url="http://test"
        ) as client:
            # Time from before the slow request: if it blocks the event loop, even the
            # short sleep below can't return until the 1.5 s call has finished.
            started = time.perf_counter()
            slow = asyncio.create_task(client.post("/api/v1/vm/start", json={"vm_id": str(uuid.uuid4())}))
            await asyncio.sleep(0.2)  # let the slow request start
            health = await client.get("/api/v1/health")
            elapsed = time.perf_counter() - started
            await slow

    assert health.status_code == 200
    assert elapsed < 1.0, f"health took {elapsed:.2f}s — the event loop was blocked"
