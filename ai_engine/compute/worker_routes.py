"""Owner-controlled worker enrollment and authenticated heartbeats."""
from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Header, HTTPException
from pydantic import BaseModel, ConfigDict, Field, field_validator

from . import worker_registry as registry

router = APIRouter(prefix="/api/compute/workers", tags=["Jon2 Compute Workers"])


def _validate_label_list(value):
    if not isinstance(value, list) or len(value) > 8:
        raise ValueError("Accelerator fields must be lists with at most 8 entries.")
    cleaned = []
    for item in value:
        if not isinstance(item, str) or not item.strip() or len(item) > 100:
            raise ValueError("Accelerator entries must be non-empty strings up to 100 characters.")
        if "," in item or any(ord(char) < 32 or ord(char) == 127 for char in item):
            raise ValueError("Accelerator entries cannot contain commas or control characters.")
        cleaned.append(item.strip())
    return cleaned


class EnrollmentRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    node_id: str = Field(min_length=3, max_length=64, pattern=r"^[A-Za-z0-9][A-Za-z0-9._-]{2,63}$")
    display_name: str = Field(default="Jon2 worker", min_length=1, max_length=80)
    platform: str = Field(min_length=1, max_length=80)
    cpu_count: int = Field(ge=1, le=4096)
    memory_total_bytes: int = Field(ge=0, le=2**60)
    accelerator_types: list[str] = Field(default_factory=list, max_length=8)
    accelerator_names: list[str] = Field(default_factory=list, max_length=8)

    @field_validator("accelerator_types", "accelerator_names", mode="before")
    @classmethod
    def validate_accelerator_labels(cls, value):
        return _validate_label_list(value)


class HeartbeatRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    cpu_count: int = Field(ge=1, le=4096)
    memory_total_bytes: int = Field(ge=0, le=2**60)
    accelerator_types: list[str] = Field(default_factory=list, max_length=8)
    accelerator_names: list[str] = Field(default_factory=list, max_length=8)

    @field_validator("accelerator_types", "accelerator_names", mode="before")
    @classmethod
    def validate_accelerator_labels(cls, value):
        return _validate_label_list(value)


def _owner(candidate: str | None) -> None:
    if not registry.verify_owner_token(candidate):
        raise HTTPException(status_code=503 if not registry.owner_token_configured() else 401,
                            detail="Worker owner authentication failed or is not configured.")


@router.post("/enroll")
def enroll_worker(
    request: EnrollmentRequest,
    authorization: Annotated[str | None, Header()] = None,
):
    candidate = authorization.removeprefix("Bearer ").strip() if authorization else None
    _owner(candidate)
    try:
        token = registry.enroll(**request.model_dump())
    except ValueError as error:
        raise HTTPException(status_code=422, detail=str(error))
    return {
        "node_id": request.node_id,
        "worker_token": token,
        "token_display": "shown_once",
        "message": "Store this worker token securely. It cannot be retrieved again."
    }


@router.post("/{node_id}/heartbeat")
def worker_heartbeat(
    node_id: str,
    request: HeartbeatRequest,
    authorization: Annotated[str | None, Header()] = None,
):
    token = authorization.removeprefix("Bearer ").strip() if authorization else ""
    try:
        ok = registry.heartbeat(node_id, token, **request.model_dump())
    except ValueError as error:
        raise HTTPException(status_code=422, detail=str(error))
    if not ok:
        raise HTTPException(status_code=401, detail="Unknown worker or invalid worker token.")
    return {"node_id": node_id, "accepted": True, "status": "online"}


@router.get("")
def workers(
    authorization: Annotated[str | None, Header()] = None,
):
    candidate = authorization.removeprefix("Bearer ").strip() if authorization else None
    _owner(candidate)
    return {"workers": registry.list_workers(), "dispatch_enabled": False}


@router.delete("/{node_id}")
def revoke_worker(
    node_id: str,
    authorization: Annotated[str | None, Header()] = None,
):
    candidate = authorization.removeprefix("Bearer ").strip() if authorization else None
    _owner(candidate)
    if not registry.revoke(node_id):
        raise HTTPException(status_code=404, detail="Worker not found.")
    return {"node_id": node_id, "revoked": True}


@router.on_event("startup")
def initialize_worker_registry():
    registry.initialize()
