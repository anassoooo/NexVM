import functools
import uuid as uuid_lib
from typing import Any

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel, Field

from app.agent.backend import LiveBackend
from app.agent.llm import GroqLLM
from app.agent.service import AgentService, risk_summary
from app.agent.store import SupabaseRunStore
from app.dependencies import UserClaims, get_current_user
from app.services import ai_service

router = APIRouter()


@functools.lru_cache(maxsize=1)
def get_agent_service() -> AgentService:
    return AgentService(GroqLLM(), LiveBackend(), SupabaseRunStore())


class AgentRequest(BaseModel):
    prompt: str = Field(min_length=1, max_length=2000)
    conversation_id: uuid_lib.UUID | None = None


class ApproveRequest(BaseModel):
    plan_version: int = Field(ge=1)


class AgentRun(BaseModel):
    id: uuid_lib.UUID
    conversation_id: uuid_lib.UUID
    prompt: str
    status: str
    answer: str | None = None
    plan: list[dict[str, Any]] = []
    plan_version: int = 0
    findings: list[dict[str, Any]] = []
    trace: list[dict[str, Any]] = []
    model: str | None = None
    total_tokens: int = 0
    latency_ms: int = 0
    repairs: int = 0
    error: str | None = None
    created_at: str
    risk: dict[str, int] = {}
    resources: dict[str, int] = {}


class AgentRunSummary(BaseModel):
    id: uuid_lib.UUID
    conversation_id: uuid_lib.UUID
    prompt: str
    status: str
    answer: str | None = None
    plan_version: int = 0
    model: str | None = None
    total_tokens: int = 0
    latency_ms: int = 0
    created_at: str


def _resources(plan: list[dict]) -> dict[str, int]:
    """What the pending steps would add (FR-303)."""
    out = {"new_vms": 0, "ram_mb": 0, "cpu": 0, "disk_mb": 0}
    for s in plan:
        if s["status"] != "pending":
            continue
        if s["tool"] in ("create_vm", "clone_vm"):
            out["new_vms"] += 1
        if s["tool"] == "create_vm":
            out["ram_mb"] += s["args"]["ram"]
            out["cpu"] += s["args"]["cpu"]
            out["disk_mb"] += s["args"]["disk_size"]
    return out


def _view(run: dict) -> dict:
    return {**run, "created_at": str(run["created_at"]),
            "risk": risk_summary(run.get("plan") or []), "resources": _resources(run.get("plan") or [])}


@router.post("/runs", response_model=AgentRun, status_code=201)
def create_run(body: AgentRequest, claims: UserClaims = Depends(get_current_user),
               service: AgentService = Depends(get_agent_service)):
    ai_service._check_rate_limit(claims.id)
    run = service.start(claims.id, body.prompt, str(body.conversation_id) if body.conversation_id else None)
    ai_service._log_ai_usage(claims.id, body.prompt, run.get("answer") or "", run.get("total_tokens", 0))
    return _view(run)


@router.get("/runs", response_model=list[AgentRunSummary])
def list_runs(limit: int = Query(default=30, ge=1, le=100), claims: UserClaims = Depends(get_current_user),
              service: AgentService = Depends(get_agent_service)):
    return [{**r, "created_at": str(r["created_at"])} for r in service.list_runs(claims.id, limit)]


@router.get("/runs/{run_id}", response_model=AgentRun)
def get_run(run_id: uuid_lib.UUID, claims: UserClaims = Depends(get_current_user),
            service: AgentService = Depends(get_agent_service)):
    return _view(service.get(claims.id, str(run_id)))


@router.post("/runs/{run_id}/approve", response_model=AgentRun)
def approve_run(run_id: uuid_lib.UUID, body: ApproveRequest, claims: UserClaims = Depends(get_current_user),
                service: AgentService = Depends(get_agent_service)):
    return _view(service.approve(claims.id, str(run_id), body.plan_version))


@router.post("/runs/{run_id}/cancel", response_model=AgentRun)
def cancel_run(run_id: uuid_lib.UUID, claims: UserClaims = Depends(get_current_user),
               service: AgentService = Depends(get_agent_service)):
    return _view(service.cancel(claims.id, str(run_id)))
