import asyncio
import subprocess

from fastapi import APIRouter

from app.config import settings

router = APIRouter()


def _get_vbox_version() -> str:
    try:
        result = subprocess.run(
            [settings.VBOXMANAGE_PATH or "VBoxManage", "--version"],
            capture_output=True,
            text=True,
            timeout=5,
        )
        if result.returncode == 0:
            return result.stdout.strip()
        return f"error: {result.stderr.strip()}"
    except FileNotFoundError:
        return "error: VBoxManage not found"
    except subprocess.TimeoutExpired:
        return "error: timed out"


@router.get("/health")
async def health_check():
    vboxmanage_version = await asyncio.to_thread(_get_vbox_version)
    return {
        "status": "ok",
        "vboxmanage": vboxmanage_version,
    }
