import os
import re
import subprocess

from app.config import settings

VBOXMANAGE_COMMANDS = {
    "createvm",
    "startvm",
    "controlvm",
    "unregistervm",
    "showvminfo",
    "modifyvm",
    "storagectl",
    "storageattach",
    "createmedium",
    "snapshot",
    "clonevm",
    "export",
    "import",
    "metrics",
}

# VirtualBox ostype IDs (VBoxManage list ostypes)
OS_TYPE_MAP: dict[str, str] = {
    "ubuntu": "Ubuntu_64",
    "ubuntu 22.04": "Ubuntu_64",
    "ubuntu 20.04": "Ubuntu_64",
    "ubuntu 18.04": "Ubuntu_64",
    "debian": "Debian_64",
    "debian 12": "Debian_64",
    "debian 11": "Debian_64",
    "kali": "Debian_64",
    "kali linux": "Debian_64",
    "fedora": "Fedora_64",
    "arch": "ArchLinux_64",
    "arch linux": "ArchLinux_64",
    "centos": "RedHat_64",
    "centos 7": "RedHat_64",
    "centos stream": "RedHat_64",
    "rocky": "RedHat_64",
    "rocky linux": "RedHat_64",
    "almalinux": "RedHat_64",
    "rhel": "RedHat_64",
    "windows 10": "Windows10_64",
    "windows 11": "Windows11_64",
    "windows server 2019": "Windows2019_64",
    "windows server 2022": "Windows2022_64",
    "freebsd": "FreeBSD_64",
    "openbsd": "OpenBSD_64",
    "linux": "Linux_64",
}


def get_ostype(os_name: str) -> str:
    return OS_TYPE_MAP.get(os_name.lower().strip(), "Linux_64")


def get_storage_base() -> str:
    if settings.VM_STORAGE_PATH:
        return settings.VM_STORAGE_PATH
    return os.path.join(os.path.expanduser("~"), "VirtualBox VMs")


def get_vm_disk_path(vm_name: str) -> str:
    return os.path.join(get_storage_base(), vm_name, f"{vm_name}.vdi")


def extract_vbox_uuid(output: str) -> str | None:
    match = re.search(r"UUID:\s*([0-9a-f\-]{36})", output, re.IGNORECASE)
    return match.group(1) if match else None


def parse_vbox_state(showvminfo_output: str) -> str | None:
    for line in showvminfo_output.splitlines():
        if line.startswith("VMState="):
            return line.split("=", 1)[1].strip('"')
    return None


VBOX_STATE_MAP: dict[str, str] = {
    "running": "running",
    "poweroff": "stopped",
    "saved": "stopped",
    "paused": "paused",
    "aborted": "error",
    "stuck": "error",
    "starting": "starting",
    "stopping": "stopping",
    "restoring": "starting",
    "saving": "stopping",
    "livesnapshotting": "running",
    "teleporting": "running",
}


def run_vbox_command(cmd: list[str], timeout: int = 60) -> subprocess.CompletedProcess:
    if len(cmd) < 2 or cmd[1] not in VBOXMANAGE_COMMANDS:
        subcommand = cmd[1] if len(cmd) >= 2 else "(missing)"
        raise ValueError(f"Subcommand '{subcommand}' is not whitelisted")
    return subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)


def build_vbox_path() -> str:
    return settings.VBOXMANAGE_PATH or "VBoxManage"
