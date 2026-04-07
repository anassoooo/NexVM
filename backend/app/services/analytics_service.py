from fastapi import HTTPException

from app.db import get_supabase_client
from app.models.schemas import AdminAnalytics, UserAnalytics


def get_user_analytics(user_id: str) -> UserAnalytics:
    try:
        supabase = get_supabase_client()

        vm_result = (
            supabase.table("vms").select("status").eq("user_id", user_id).execute()
        )
        vms = vm_result.data or []

        ai_result = (
            supabase.table("ai_usage").select("id").eq("user_id", user_id).execute()
        )
    except Exception as exc:
        raise HTTPException(status_code=500, detail="Analytics unavailable") from exc

    return UserAnalytics(
        total_vms=len(vms),
        running_vms=sum(1 for v in vms if v["status"] == "running"),
        stopped_vms=sum(1 for v in vms if v["status"] == "stopped"),
        error_vms=sum(1 for v in vms if v["status"] == "error"),
        total_ai_commands=len(ai_result.data or []),
    )


def get_admin_analytics() -> AdminAnalytics:
    try:
        supabase = get_supabase_client()

        users_result = supabase.table("profiles").select("id").execute()
        vm_result = supabase.table("vms").select("status").execute()
        ai_result = supabase.table("ai_usage").select("id").execute()
    except Exception as exc:
        raise HTTPException(status_code=500, detail="Analytics unavailable") from exc

    vms = vm_result.data or []

    return AdminAnalytics(
        total_users=len(users_result.data or []),
        total_vms=len(vms),
        running_vms=sum(1 for v in vms if v["status"] == "running"),
        stopped_vms=sum(1 for v in vms if v["status"] == "stopped"),
        error_vms=sum(1 for v in vms if v["status"] == "error"),
        total_ai_commands=len(ai_result.data or []),
    )
