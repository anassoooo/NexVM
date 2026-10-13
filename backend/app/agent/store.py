"""Persistence for agent runs (table agent_runs, migration 005)."""

import threading
import uuid
from datetime import datetime, timezone
from typing import Protocol

from app.db import get_supabase_client

SUMMARY_FIELDS = "id,conversation_id,prompt,status,answer,plan_version,model,total_tokens,latency_ms,created_at"


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


class RunStore(Protocol):
    def create(self, run: dict) -> dict: ...
    def update(self, run_id: str, fields: dict) -> dict: ...
    def get(self, run_id: str, user_id: str) -> dict | None: ...
    def list_runs(self, user_id: str, limit: int) -> list[dict]: ...
    def conversation(self, conversation_id: str, user_id: str, limit: int) -> list[dict]: ...


class SupabaseRunStore:
    def create(self, run: dict) -> dict:
        return get_supabase_client().table("agent_runs").insert(run).execute().data[0]

    def update(self, run_id: str, fields: dict) -> dict:
        res = (get_supabase_client().table("agent_runs")
               .update({**fields, "updated_at": _now()}).eq("id", run_id).execute())
        return res.data[0]

    def get(self, run_id: str, user_id: str) -> dict | None:
        res = (get_supabase_client().table("agent_runs").select("*")
               .eq("id", run_id).eq("user_id", user_id).execute())
        return res.data[0] if res.data else None

    def list_runs(self, user_id: str, limit: int) -> list[dict]:
        return (get_supabase_client().table("agent_runs").select(SUMMARY_FIELDS)
                .eq("user_id", user_id).order("created_at", desc=True).limit(limit).execute().data or [])

    def conversation(self, conversation_id: str, user_id: str, limit: int) -> list[dict]:
        rows = (get_supabase_client().table("agent_runs").select("prompt,answer,plan,status")
                .eq("conversation_id", conversation_id).eq("user_id", user_id)
                .order("created_at", desc=True).limit(limit).execute().data or [])
        return list(reversed(rows))


class InMemoryRunStore:
    """For tests: same contract, thread-safe."""

    def __init__(self):
        self.rows: dict[str, dict] = {}
        self._lock = threading.Lock()

    def create(self, run: dict) -> dict:
        with self._lock:
            row = {"id": str(uuid.uuid4()), "created_at": _now(), "updated_at": _now(),
                   "plan_version": 0, "repairs": 0, "error": None, **run}
            self.rows[row["id"]] = row
            return dict(row)

    def update(self, run_id: str, fields: dict) -> dict:
        with self._lock:
            self.rows[run_id].update(fields, updated_at=_now())
            return dict(self.rows[run_id])

    def get(self, run_id: str, user_id: str) -> dict | None:
        row = self.rows.get(run_id)
        return dict(row) if row and row["user_id"] == user_id else None

    def list_runs(self, user_id: str, limit: int) -> list[dict]:
        rows = [r for r in self.rows.values() if r["user_id"] == user_id]
        return sorted(rows, key=lambda r: r["created_at"], reverse=True)[:limit]

    def conversation(self, conversation_id: str, user_id: str, limit: int) -> list[dict]:
        rows = [r for r in self.rows.values() if r["conversation_id"] == conversation_id and r["user_id"] == user_id]
        return sorted(rows, key=lambda r: r["created_at"])[-limit:]
