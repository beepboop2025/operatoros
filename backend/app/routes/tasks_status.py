"""Task status routes — check background job progress."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status

from app.dependencies import get_current_user
from app.models.user import User

router = APIRouter(tags=["tasks"])


@router.get(
    "/{task_id}/status",
    summary="Get background task status",
)
async def get_task_status(
    task_id: str,
    current_user: User = Depends(get_current_user),
) -> dict:
    """Check the status of a Celery background task.

    Returns the task state (PENDING, STARTED, SUCCESS, FAILURE, RETRY)
    and result if available.
    """
    from app.celery_app import celery_app

    result = celery_app.AsyncResult(task_id)

    response = {
        "task_id": task_id,
        "status": result.state,
        "ready": result.ready(),
    }

    if result.ready():
        if result.successful():
            response["result"] = result.result
        else:
            response["error"] = str(result.result) if result.result else "Unknown error"
    elif result.state == "STARTED":
        response["info"] = result.info if result.info else {}

    return response
