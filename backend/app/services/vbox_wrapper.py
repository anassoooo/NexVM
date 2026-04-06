import subprocess

from app.config import settings

VBOXMANAGE_COMMANDS = {"createvm", "startvm", "controlvm", "unregistervm", "showvminfo"}


def run_vbox_command(cmd: list[str], timeout: int = 30) -> subprocess.CompletedProcess:
    assert cmd[1] in VBOXMANAGE_COMMANDS, f"Subcommand '{cmd[1]}' is not whitelisted"
    return subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)


def build_vbox_path() -> str:
    return settings.VBOXMANAGE_PATH or "VBoxManage"
