import re
import uuid
from datetime import datetime

from pydantic import BaseModel, Field, field_validator

from app.models.enums import LogAction, LogStatus, VMStatus

_VM_NAME_RE = re.compile(r"^[a-zA-Z0-9][a-zA-Z0-9 \-]{0,49}$")


class VMCreate(BaseModel):
    name: str = Field(min_length=1, max_length=50)
    os: str
    ram: int = Field(ge=512, le=16384)

    @field_validator("name")
    @classmethod
    def validate_name(cls, v: str) -> str:
        if not _VM_NAME_RE.match(v):
            raise ValueError(
                "Name must be 1–50 characters: alphanumeric, hyphens, and spaces only"
            )
        return v


class VMResponse(BaseModel):
    id: uuid.UUID
    user_id: uuid.UUID
    name: str
    os: str
    ram: int
    status: VMStatus
    error_message: str | None
    created_at: datetime
    updated_at: datetime


class VMActionRequest(BaseModel):
    vm_id: str


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
