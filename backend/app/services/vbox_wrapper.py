import subprocess

from app.config import settings

VBOXMANAGE_COMMANDS = {"createvm", "startvm", "controlvm", "unregistervm", "showvminfo"}


def run_vbox_command(cmd: list[str], timeout: int = 30) -> subprocess.CompletedProcess:
    if len(cmd) < 2 or cmd[1] not in VBOXMANAGE_COMMANDS:
        subcommand = cmd[1] if len(cmd) >= 2 else "(missing)"
        raise ValueError(f"Subcommand '{subcommand}' is not whitelisted")
    return subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)


def build_vbox_path() -> str:
    return settings.VBOXMANAGE_PATH or "VBoxManage"
