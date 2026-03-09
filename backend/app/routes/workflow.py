"""Workflow routes — trigger and monitor n8n workflows."""

from __future__ import annotations

import httpx
from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.database import get_db
from app.dependencies import get_current_user
from app.middleware.audit import get_client_ip, log_action
from app.models.user import User

router = APIRouter(tags=["workflow"])

settings = get_settings()


# --------------------------------------------------------------------------- #
#  Request / Response schemas
# --------------------------------------------------------------------------- #


class WorkflowTriggerRequest(BaseModel):
    workflow_name: str = Field(..., min_length=1, max_length=256, description="Name or path of the n8n workflow webhook")
    payload: dict = Field(default_factory=dict, description="Data to send to the workflow")


class WorkflowTriggerResponse(BaseModel):
    success: bool
    execution_id: str | None = None
    message: str
    webhook_response: dict | None = None


class WorkflowStatusResponse(BaseModel):
    execution_id: str
    status: str
    finished: bool
    data: dict | None = None


# --------------------------------------------------------------------------- #
#  POST /trigger — Trigger an n8n workflow
# --------------------------------------------------------------------------- #


@router.post(
    "/trigger",
    response_model=WorkflowTriggerResponse,
    summary="Trigger an n8n workflow via webhook",
)
async def trigger_workflow(
    body: WorkflowTriggerRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> WorkflowTriggerResponse:
    """Trigger an n8n workflow by sending a payload to its webhook endpoint.

    The workflow_name is appended to the base n8n webhook URL configured in
    the application settings.
    """

    webhook_url = f"{settings.N8N_WEBHOOK_URL}/webhook/{body.workflow_name}"

    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                webhook_url,
                json={
                    **body.payload,
                    "triggered_by": str(current_user.id),
                    "user_email": current_user.email,
                },
            )

        webhook_response = None
        try:
            webhook_response = response.json()
        except Exception:
            webhook_response = {"raw": response.text[:500]}

        # Try to extract execution_id from n8n response
        execution_id = None
        if isinstance(webhook_response, dict):
            execution_id = webhook_response.get("executionId") or webhook_response.get("execution_id")

        await log_action(
            db,
            user_id=current_user.id,
            action="workflow.trigger",
            entity_type="workflow",
            details={
                "workflow_name": body.workflow_name,
                "status_code": response.status_code,
                "execution_id": execution_id,
            },
            ip_address=get_client_ip(request),
        )

        if response.status_code >= 400:
            return WorkflowTriggerResponse(
                success=False,
                execution_id=execution_id,
                message=f"Workflow returned HTTP {response.status_code}",
                webhook_response=webhook_response,
            )

        return WorkflowTriggerResponse(
            success=True,
            execution_id=execution_id,
            message="Workflow triggered successfully",
            webhook_response=webhook_response,
        )

    except httpx.ConnectError:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Cannot connect to n8n. Ensure n8n is running and accessible.",
        )
    except httpx.TimeoutException:
        raise HTTPException(
            status_code=status.HTTP_504_GATEWAY_TIMEOUT,
            detail="n8n webhook timed out after 30 seconds.",
        )
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Workflow trigger failed: {str(exc)}",
        )


# --------------------------------------------------------------------------- #
#  GET /status/{execution_id} — Check workflow status
# --------------------------------------------------------------------------- #


@router.get(
    "/status/{execution_id}",
    response_model=WorkflowStatusResponse,
    summary="Check n8n workflow execution status",
)
async def get_workflow_status(
    execution_id: str,
    current_user: User = Depends(get_current_user),
) -> WorkflowStatusResponse:
    """Proxy request to the n8n API to check the status of a workflow execution.

    Requires the n8n REST API to be accessible from the backend.
    """

    n8n_api_url = f"{settings.N8N_WEBHOOK_URL}/api/v1/executions/{execution_id}"

    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            response = await client.get(n8n_api_url)

        if response.status_code == 404:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Execution not found in n8n",
            )

        if response.status_code >= 400:
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail=f"n8n API returned HTTP {response.status_code}",
            )

        data = response.json()

        return WorkflowStatusResponse(
            execution_id=execution_id,
            status=data.get("status", "unknown"),
            finished=data.get("finished", False),
            data=data.get("data"),
        )

    except httpx.ConnectError:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Cannot connect to n8n API.",
        )
    except httpx.TimeoutException:
        raise HTTPException(
            status_code=status.HTTP_504_GATEWAY_TIMEOUT,
            detail="n8n API request timed out.",
        )
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to check workflow status: {str(exc)}",
        )
