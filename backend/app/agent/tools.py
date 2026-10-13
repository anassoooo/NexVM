"""Typed tool registry for the Autopilot agent (§XIV.2).

Each tool has a Pydantic argument model; the JSON schema the model sees is generated from it.
Read tools run during planning. Write tools are intercepted and become plan steps (§XIV.1).
No tool takes a user id: identity always comes from the authenticated request.
"""

import re
from dataclasses import dataclass
from enum import Enum
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


class Kind(str, Enum):
    read = "read"
    write = "write"


class Risk(str, Enum):
    none = "none"  # read-only
    low = "low"  # reversible change
    costly = "costly"  # creates resources (VMs, disk)
    destructive = "destructive"  # deletes data or powers off


OS_LABELS = (
    "Ubuntu 22.04", "Ubuntu 20.04", "Debian 12", "Debian 11", "Kali Linux", "Fedora",
    "Arch Linux", "CentOS Stream", "Rocky Linux", "AlmaLinux", "Windows 10", "Windows 11",
)
OSLabel = Literal[
    "Ubuntu 22.04", "Ubuntu 20.04", "Debian 12", "Debian 11", "Kali Linux", "Fedora",
    "Arch Linux", "CentOS Stream", "Rocky Linux", "AlmaLinux", "Windows 10", "Windows 11",
]

_VM_NAME_RE = re.compile(r"^[a-zA-Z0-9][a-zA-Z0-9 \-]{0,49}$")
_ARG_NAME_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9 _.-]{0,49}$")
_ISO_FILE_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9 _.-]{0,95}\.iso$", re.IGNORECASE)


def _check(pattern: re.Pattern, value: str, what: str) -> str:
    if not pattern.fullmatch(value):
        raise ValueError(f"invalid {what}: {value!r}")
    return value


class _Args(BaseModel):
    model_config = ConfigDict(extra="forbid")


class NoArgs(_Args):
    model_config = ConfigDict(extra="ignore")  # read-only: stray arguments are harmless


class VMRef(_Args):
    vm: str = Field(description="VM name")

    @field_validator("vm")
    @classmethod
    def _vm(cls, v: str) -> str:
        return _check(_VM_NAME_RE, v, "VM name")


class CreateVMArgs(_Args):
    name: str
    os: OSLabel = Field(default="Ubuntu 22.04")
    ram: int = Field(default=2048, ge=512, le=16384, description="MB")
    cpu: int = Field(default=2, ge=1, le=32)
    disk_size: int = Field(default=20480, ge=5120, le=512000, description="MB")

    @field_validator("name")
    @classmethod
    def _name(cls, v: str) -> str:
        return _check(_VM_NAME_RE, v, "VM name")


class ModifyVMArgs(VMRef):
    ram: int | None = Field(default=None, ge=512, le=16384, description="MB")
    cpu: int | None = Field(default=None, ge=1, le=32)

    @model_validator(mode="after")
    def _one(self) -> "ModifyVMArgs":
        if self.ram is None and self.cpu is None:
            raise ValueError("give ram and/or cpu")
        return self


class SnapshotArgs(VMRef):
    snapshot: str
    description: str = Field(default="", max_length=200)

    @field_validator("snapshot")
    @classmethod
    def _snap(cls, v: str) -> str:
        return _check(_ARG_NAME_RE, v, "snapshot name")


class RestoreSnapshotArgs(VMRef):
    snapshot: str

    @field_validator("snapshot")
    @classmethod
    def _snap(cls, v: str) -> str:
        return _check(_ARG_NAME_RE, v, "snapshot name")


class PortRuleArgs(VMRef):
    rule_name: str = Field(description="e.g. ssh")
    protocol: Literal["tcp", "udp"] = "tcp"
    host_port: int = Field(ge=1024, le=65535)
    guest_port: int = Field(ge=1, le=65535)

    @field_validator("rule_name")
    @classmethod
    def _rule(cls, v: str) -> str:
        return _check(_ARG_NAME_RE, v, "rule name")


class CloneArgs(VMRef):
    new_name: str

    @field_validator("new_name")
    @classmethod
    def _new(cls, v: str) -> str:
        return _check(_VM_NAME_RE, v, "VM name")


class AttachISOArgs(VMRef):
    iso_file: str = Field(description="file name from isos_available")

    @field_validator("iso_file")
    @classmethod
    def _iso(cls, v: str) -> str:
        return _check(_ISO_FILE_RE, v, "ISO file name")


class ActivityArgs(_Args):
    model_config = ConfigDict(extra="ignore")
    limit: int = Field(default=10, ge=1, le=20)


@dataclass(frozen=True)
class ToolSpec:
    name: str
    description: str
    args: type[_Args]
    kind: Kind
    risk: Risk = Risk.none

    def schema(self) -> dict:
        params = _strip_titles(self.args.model_json_schema())
        params.setdefault("properties", {})
        return {"type": "function", "function": {
            "name": self.name, "description": self.description, "parameters": params,
        }}


def _strip_titles(node):
    """Drop schema keys that only cost tokens; the server validates strictly anyway."""
    if isinstance(node, dict):
        options = node.get("anyOf")
        if options and {"type": "null"} in options and len(options) == 2:
            # Optional[X] -> X; leaving the field out means "unchanged"
            inner = next(o for o in options if o != {"type": "null"})
            node = {**{k: v for k, v in node.items() if k not in ("anyOf", "default")}, **inner}
        return {k: _strip_titles(v) for k, v in node.items() if k not in ("title", "additionalProperties")}
    if isinstance(node, list):
        return [_strip_titles(v) for v in node]
    return node


_R, _W = Kind.read, Kind.write
TOOLS: dict[str, ToolSpec] = {t.name: t for t in [
    # Read — run immediately during planning
    ToolSpec("list_vms", "List the user's VMs with status, OS, RAM, CPU, disk, ports and snapshots.", NoArgs, _R),
    ToolSpec("diagnose_vm", "Check one VM for problems (error state, memory/CPU pressure, attached ISO, "
             "recent failures). Use when the user asks why something is wrong or slow.", VMRef, _R),
    ToolSpec("list_isos", "List ISO files available to attach.", NoArgs, _R),
    ToolSpec("recent_activity", "The user's most recent VM actions and their outcomes.", ActivityArgs, _R),
    ToolSpec("get_quota", "VM count and disk quota: used and limit.", NoArgs, _R),
    # Write — become plan steps that the user approves
    ToolSpec("create_vm", "Create a stopped VM.", CreateVMArgs, _W, Risk.costly),
    ToolSpec("start_vm", "Start a stopped or errored VM.", VMRef, _W, Risk.low),
    ToolSpec("stop_vm", "Power off a running VM (unsaved guest data is lost).", VMRef, _W, Risk.destructive),
    ToolSpec("pause_vm", "Pause a running VM.", VMRef, _W, Risk.low),
    ToolSpec("resume_vm", "Resume a paused VM.", VMRef, _W, Risk.low),
    ToolSpec("modify_vm", "Change RAM and/or CPU of a stopped VM.", ModifyVMArgs, _W, Risk.low),
    ToolSpec("delete_vm", "Delete a stopped or errored VM and its disk.", VMRef, _W, Risk.destructive),
    ToolSpec("take_snapshot", "Snapshot a stopped VM.", SnapshotArgs, _W, Risk.low),
    ToolSpec("restore_snapshot", "Restore a stopped VM to a snapshot (current disk state is lost).",
             RestoreSnapshotArgs, _W, Risk.destructive),
    ToolSpec("add_port_rule", "Forward a host port to a guest port on a stopped VM.", PortRuleArgs, _W, Risk.low),
    ToolSpec("clone_vm", "Copy a stopped VM under a new name.", CloneArgs, _W, Risk.costly),
    ToolSpec("attach_iso", "Attach an ISO (from list_isos) to a stopped VM and boot from it.", AttachISOArgs, _W, Risk.low),
    ToolSpec("detach_iso", "Remove the ISO from a stopped VM.", VMRef, _W, Risk.low),
]}


def tool_schemas() -> list[dict]:
    return [t.schema() for t in TOOLS.values()]


def describe(tool: str, args: dict) -> str:
    """One-line, human-readable description of a plan step."""
    vm = args.get("vm")
    match tool:
        case "create_vm":
            return (f"Create VM '{args['name']}' ({args['os']}, {args['cpu']} vCPU, "
                    f"{args['ram']} MB RAM, {args['disk_size'] // 1024} GB disk)")
        case "modify_vm":
            parts = [f"{args['ram']} MB RAM" if args.get("ram") else "", f"{args['cpu']} vCPU" if args.get("cpu") else ""]
            return f"Resize '{vm}' to " + ", ".join(p for p in parts if p)
        case "take_snapshot":
            return f"Snapshot '{vm}' as '{args['snapshot']}'"
        case "restore_snapshot":
            return f"Restore '{vm}' to snapshot '{args['snapshot']}'"
        case "add_port_rule":
            return (f"Forward host port {args['host_port']} → '{vm}' port {args['guest_port']}"
                    f" ({args['protocol']}, rule '{args['rule_name']}')")
        case "clone_vm":
            return f"Clone '{vm}' as '{args['new_name']}'"
        case "attach_iso":
            return f"Attach {args['iso_file']} to '{vm}'"
        case _:
            verb = {"start_vm": "Start", "stop_vm": "Power off", "pause_vm": "Pause", "resume_vm": "Resume",
                    "delete_vm": "Delete", "detach_iso": "Detach the ISO from"}.get(tool, tool)
            return f"{verb} '{vm}'"
