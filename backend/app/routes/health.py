import asyncio

from fastapi import APIRouter

from app.config import settings

router = APIRouter()


@router.get("/health")
async def health_check():
    vboxmanage_version = None
    try:
        proc = await asyncio.create_subprocess_exec(
            settings.VBOXMANAGE_PATH or "VBoxManage",
            "--version",
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=5)
        if proc.returncode == 0:
            vboxmanage_version = stdout.decode().strip()
        else:
            vboxmanage_version = f"error: {stderr.decode().strip()}"
    except FileNotFoundError:
        vboxmanage_version = "error: VBoxManage not found"
    except TimeoutError:
        proc.kill()
        vboxmanage_version = "error: timed out"

    return {
        "status": "ok",
        "vboxmanage": vboxmanage_version,
    }
