import subprocess

from fastapi import APIRouter

from app.config import settings

router = APIRouter()


@router.get("/health")
async def health_check():
    vboxmanage_version = None
    try:
        result = subprocess.run(
            [settings.VBOXMANAGE_PATH or "VBoxManage", "--version"],
            capture_output=True,
            text=True,
            timeout=5,
        )
        if result.returncode == 0:
            vboxmanage_version = result.stdout.strip()
        else:
            vboxmanage_version = f"error: {result.stderr.strip()}"
    except FileNotFoundError:
        vboxmanage_version = "error: VBoxManage not found"
    except subprocess.TimeoutExpired:
        vboxmanage_version = "error: timed out"

    return {
        "status": "ok",
        "vboxmanage": vboxmanage_version,
    }
