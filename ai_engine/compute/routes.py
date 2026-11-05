"""Read-only Jon2 Compute API routes."""
from fastapi import APIRouter, HTTPException, Query

from .resource_probe import assess_task, inspect_resources

router = APIRouter(prefix="/api/compute", tags=["Jon2 Compute"])


@router.get("/health")
def compute_health():
    snapshot = inspect_resources()
    return {
        "service": "Jon2 Compute Control Plane",
        "status": "online",
        "capacity_class": snapshot["capacity_class"],
        "provisioning_status": snapshot["provisioning_status"],
    }


@router.get("/resources")
def compute_resources():
    return inspect_resources()


@router.get("/admission")
def compute_admission(
    min_memory_gib: float = Query(default=2.0, gt=0, le=1024),
    require_gpu: bool = False,
):
    try:
        return assess_task(min_memory_gib=min_memory_gib, require_gpu=require_gpu)
    except ValueError as error:
        raise HTTPException(status_code=422, detail=str(error))


# Authenticated worker registry endpoints (task dispatch remains disabled).
from .worker_routes import router as worker_router
router.include_router(worker_router)
