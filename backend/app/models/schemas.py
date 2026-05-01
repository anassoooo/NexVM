import os
import re
import uuid
from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, EmailStr, Field, field_validator, model_validator

from app.models.enums import LogAction, LogStatus, VMStatus

_VM_NAME_RE = re.compile(r"^[a-zA-Z0-9][a-zA-Z0-9 \-]{0,49}$")


class VMCreate(BaseModel):
    name: str = Field(min_length=1, max_length=50)
    os: str = Field(min_length=1)
    ram: int = Field(ge=512, le=16384)
    cpu: int = Field(ge=1, le=32, default=2)
    disk_size: int = Field(ge=5120, le=512000, default=20480)

    @field_validator("name")
    @classmethod
    def validate_name(cls, v: str) -> str:
        if not _VM_NAME_RE.match(v):
            raise ValueError(
                "Name must be 1-50 characters: alphanumeric, hyphens, and spaces only"
            )
        return v


class PortFwdRule(BaseModel):
    name: str
    protocol: Literal["tcp", "udp"]
    host_port: int
    guest_port: int


class VMResponse(BaseModel):
    id: uuid.UUID
    user_id: uuid.UUID
    name: str
    os: str
    ram: int
    cpu: int
    disk_size: int
    vbox_id: str | None
    status: VMStatus
    error_message: str | None
    iso_path: str | None
    vrde_enabled: bool
    vrde_port: int | None
    nat_rules: list[PortFwdRule]
    created_at: datetime
    updated_at: datetime


class VMActionRequest(BaseModel):
    vm_id: uuid.UUID


class ISOAttachRequest(BaseModel):
    vm_id: uuid.UUID
    iso_path: str = Field(min_length=1)

    @field_validator("iso_path")
    @classmethod
    def validate_iso_path(cls, v: str) -> str:
        if not os.path.isabs(v):
            raise ValueError("iso_path must be an absolute path")
        if not v.lower().endswith(".iso"):
            raise ValueError("iso_path must end with .iso")
        return v


class ISODetachRequest(BaseModel):
    vm_id: uuid.UUID


class VRDEEnableRequest(BaseModel):
    vm_id: uuid.UUID
    port: int = Field(ge=1024, le=65535)


class VRDEDisableRequest(BaseModel):
    vm_id: uuid.UUID


class VMModifyRequest(BaseModel):
    vm_id: uuid.UUID
    ram: int | None = Field(default=None, ge=512, le=16384)
    cpu: int | None = Field(default=None, ge=1, le=32)

    @model_validator(mode="after")
    def at_least_one_field(self) -> "VMModifyRequest":
        if self.ram is None and self.cpu is None:
            raise ValueError("At least one of ram or cpu must be provided")
        return self


class PortFwdAddRequest(BaseModel):
    vm_id: uuid.UUID
    name: str = Field(min_length=1, max_length=50)
    protocol: Literal["tcp", "udp"]
    host_port: int = Field(ge=1024, le=65535)
    guest_port: int = Field(ge=1, le=65535)


class PortFwdDeleteRequest(BaseModel):
    vm_id: uuid.UUID
    name: str = Field(min_length=1)


class SnapshotTakeRequest(BaseModel):
    vm_id: uuid.UUID
    name: str = Field(min_length=1, max_length=50)
    description: str = Field(default="", max_length=200)


class SnapshotActionRequest(BaseModel):
    vm_id: uuid.UUID
    name: str = Field(min_length=1)


class SnapshotResponse(BaseModel):
    id: uuid.UUID
    vm_id: uuid.UUID
    name: str
    description: str | None
    created_at: datetime


class VMCloneRequest(BaseModel):
    vm_id: uuid.UUID
    new_name: str = Field(min_length=1, max_length=50)

    @field_validator("new_name")
    @classmethod
    def validate_new_name(cls, v: str) -> str:
        if not _VM_NAME_RE.match(v):
            raise ValueError(
                "Name must be 1-50 characters: alphanumeric, hyphens, and spaces only"
            )
        return v


class OVAExportRequest(BaseModel):
    vm_id: uuid.UUID
    output_path: str

    @field_validator("output_path")
    @classmethod
    def validate_output_path(cls, v: str) -> str:
        if not os.path.isabs(v):
            raise ValueError("output_path must be an absolute path")
        if not v.lower().endswith(".ova"):
            raise ValueError("output_path must end with .ova")
        return v


class OVAImportRequest(BaseModel):
    source_path: str
    name: str = Field(min_length=1, max_length=50)
    ram: int = Field(ge=512, le=16384, default=1024)
    cpu: int = Field(ge=1, le=32, default=2)

    @field_validator("source_path")
    @classmethod
    def validate_source_path(cls, v: str) -> str:
        if not os.path.isabs(v):
            raise ValueError("source_path must be an absolute path")
        if not v.lower().endswith((".ova", ".ovf")):
            raise ValueError("source_path must end with .ova or .ovf")
        return v

    @field_validator("name")
    @classmethod
    def validate_import_name(cls, v: str) -> str:
        if not _VM_NAME_RE.match(v):
            raise ValueError(
                "Name must be 1-50 characters: alphanumeric, hyphens, and spaces only"
            )
        return v


class OVAExportResponse(BaseModel):
    message: str


class LogResponse(BaseModel):
    id: uuid.UUID
    user_id: uuid.UUID | None
    action: LogAction
    target: str
    status: LogStatus
    message: str
    created_at: datetime


class AIUsageResponse(BaseModel):
    id: uuid.UUID
    user_id: uuid.UUID | None
    prompt: str
    response: str
    tokens: int
    created_at: datetime


class UserProfile(BaseModel):
    id: uuid.UUID
    is_admin: bool
    created_at: datetime


# --- AI Command schemas ---


class AICommandRequest(BaseModel):
    prompt: str = Field(min_length=1, max_length=2000)


class AICommandResponse(BaseModel):
    action: str
    result: str
    ai_response: dict[str, Any]


class AICreateVM(BaseModel):
    action: Literal["create_vm"]
    name: str = Field(min_length=1, max_length=50)
    os: str = Field(min_length=1)
    ram: int = Field(ge=512, le=16384)
    cpu: int = Field(ge=1, le=32, default=2)
    disk_size: int = Field(ge=5120, le=512000, default=20480)

    @field_validator("name")
    @classmethod
    def validate_name(cls, v: str) -> str:
        if not _VM_NAME_RE.match(v):
            raise ValueError(
                "Name must be 1-50 characters: alphanumeric, hyphens, and spaces only"
            )
        return v


class AIStartVM(BaseModel):
    action: Literal["start_vm"]
    vm_id: uuid.UUID


class AIStopVM(BaseModel):
    action: Literal["stop_vm"]
    vm_id: uuid.UUID


class AIDeleteVM(BaseModel):
    action: Literal["delete_vm"]
    vm_id: uuid.UUID


class AIListVMs(BaseModel):
    action: Literal["list_vms"]


class AIQueryAnalytics(BaseModel):
    action: Literal["query_analytics"]
    message: str = Field(min_length=1, max_length=2000)


class AIChat(BaseModel):
    action: Literal["chat"]
    message: str = Field(min_length=1, max_length=2000)


class AIModifyVM(BaseModel):
    action: Literal["modify_vm"]
    vm_id: uuid.UUID
    ram: int | None = Field(default=None, ge=512, le=16384)
    cpu: int | None = Field(default=None, ge=1, le=32)


class AIAttachISO(BaseModel):
    action: Literal["attach_iso"]
    vm_id: uuid.UUID
    iso_path: str = Field(min_length=1)


class AIDetachISO(BaseModel):
    action: Literal["detach_iso"]
    vm_id: uuid.UUID


class AIPauseVM(BaseModel):
    action: Literal["pause_vm"]
    vm_id: uuid.UUID


class AIResumeVM(BaseModel):
    action: Literal["resume_vm"]
    vm_id: uuid.UUID


# --- Analytics schemas ---


class VMMetrics(BaseModel):
    cpu_percent: float | None
    ram_used_mb: int | None


class UserAnalytics(BaseModel):
    total_vms: int
    running_vms: int
    stopped_vms: int
    error_vms: int
    total_ai_commands: int
    total_disk_used_mb: int
    disk_quota_mb: int


class AdminAnalytics(UserAnalytics):
    total_users: int


# --- Auth schemas ---


class LoginRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8)


class SignupRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8)


class UserInfo(BaseModel):
    id: uuid.UUID
    email: str
    is_admin: bool


class AuthResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserInfo


class SignupResponse(BaseModel):
    message: str
    user: UserInfo
    access_token: str | None = None
    token_type: str = "bearer"


class TimeSeriesPoint(BaseModel):
    date: str
    count: int


class AnalyticsTimeSeries(BaseModel):
    vms_created: list[TimeSeriesPoint]
    vms_by_day: list[TimeSeriesPoint]
    ai_commands_by_day: list[TimeSeriesPoint]


class ScheduleCreate(BaseModel):
    vm_id: uuid.UUID
    action: Literal["start", "stop"]
    cron_expr: str = Field(min_length=9, max_length=100)

    @field_validator("cron_expr")
    @classmethod
    def validate_cron(cls, v: str) -> str:
        parts = v.strip().split()
        if len(parts) < 5:
            raise ValueError("cron_expr must have at least 5 fields (minute hour day month weekday)")
        for p in parts[:5]:
            if not re.match(r"^[\d,\-\*/]+$", p):
                raise ValueError(f"Invalid cron field: '{p}'")
        return v.strip()


class ScheduleResponse(BaseModel):
    id: uuid.UUID
    user_id: uuid.UUID
    vm_id: uuid.UUID
    action: str
    cron_expr: str
    enabled: bool
    last_run: datetime | None
    created_at: datetime
