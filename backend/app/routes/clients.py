"""Client management routes — CRUD, compliance calendar, linked entities."""

from __future__ import annotations

import uuid
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.database import get_db
from app.dependencies import get_current_user, require_role
from app.middleware.audit import get_client_ip, log_action
from app.models.client import Client
from app.models.compliance import ComplianceStatus, ComplianceTask
from app.models.computation import TaxComputation
from app.models.document import Document
from app.models.user import User
from app.schemas.client import (
    ClientCreate,
    ClientListResponse,
    ClientResponse,
    ClientUpdate,
    ComplianceStats,
)
from app.schemas.compliance import ComplianceCalendarResponse, ComplianceTaskResponse
from app.schemas.computation import IncomeTaxResponse
from app.schemas.document import DocumentResponse

router = APIRouter(tags=["clients"])


# --------------------------------------------------------------------------- #
#  Helpers
# --------------------------------------------------------------------------- #


def _build_client_response(client: Client, stats: ComplianceStats | None = None) -> ClientResponse:
    """Map a Client ORM instance to the response schema."""
    return ClientResponse(
        id=client.id,
        firm_name=client.firm_name,
        contact_person=client.contact_person,
        email=client.email,
        phone=client.phone,
        pan=client.pan,
        gstin=client.gstin,
        cin=client.cin,
        entity_type=client.entity_type.value,
        address=client.address_json.get("address") if client.address_json else None,
        assigned_to=client.assigned_to,
        assigned_to_name=(
            client.assigned_user.full_name
            if client.assigned_user
            else None
        ),
        compliance_stats=stats,
        is_active=client.is_active,
        created_at=client.created_at,
        updated_at=client.updated_at,
    )


async def _get_compliance_stats(
    db: AsyncSession, client_id: uuid.UUID
) -> ComplianceStats:
    """Compute compliance statistics for a client."""
    result = await db.execute(
        select(
            func.count(ComplianceTask.id).label("total"),
            func.count(ComplianceTask.id).filter(
                ComplianceTask.status == ComplianceStatus.completed
            ).label("completed"),
            func.count(ComplianceTask.id).filter(
                ComplianceTask.status == ComplianceStatus.overdue
            ).label("overdue"),
            func.count(ComplianceTask.id).filter(
                ComplianceTask.status == ComplianceStatus.pending
            ).label("pending"),
        ).where(ComplianceTask.client_id == client_id)
    )
    row = result.one()
    return ComplianceStats(
        total_tasks=row.total,
        completed_tasks=row.completed,
        overdue_tasks=row.overdue,
        pending_tasks=row.pending,
    )


async def _get_client_or_404(
    db: AsyncSession, client_id: uuid.UUID
) -> Client:
    """Fetch a client by ID or raise 404."""
    result = await db.execute(
        select(Client)
        .options(selectinload(Client.assigned_user))
        .where(Client.id == client_id)
    )
    client = result.scalar_one_or_none()
    if client is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Client not found",
        )
    return client


# --------------------------------------------------------------------------- #
#  GET / — List clients
# --------------------------------------------------------------------------- #


@router.get(
    "/",
    response_model=ClientListResponse,
    summary="List all clients with pagination and search",
)
async def list_clients(
    page: int = Query(1, ge=1, description="Page number"),
    size: int = Query(20, ge=1, le=100, description="Items per page"),
    search: Optional[str] = Query(None, description="Search by firm name or PAN"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> ClientListResponse:
    """Return a paginated list of active clients. Supports search by name or PAN."""

    query = select(Client).options(selectinload(Client.assigned_user)).where(Client.is_active.is_(True))

    if search:
        # Escape LIKE wildcards to prevent injection of % and _
        safe_search = search.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
        pattern = f"%{safe_search}%"
        query = query.where(
            Client.firm_name.ilike(pattern, escape="\\") | Client.pan.ilike(pattern, escape="\\")
        )

    # Total count
    count_q = select(func.count()).select_from(query.subquery())
    total = (await db.execute(count_q)).scalar_one()

    # Paginate
    offset = (page - 1) * size
    query = query.order_by(Client.firm_name).offset(offset).limit(size)
    result = await db.execute(query)
    clients = result.scalars().all()

    # Batch compliance stats to avoid N+1 queries
    client_ids = [c.id for c in clients]
    stats_map: dict[uuid.UUID, ComplianceStats] = {}
    if client_ids:
        stats_result = await db.execute(
            select(
                ComplianceTask.client_id,
                func.count(ComplianceTask.id).label("total"),
                func.count(ComplianceTask.id).filter(
                    ComplianceTask.status == ComplianceStatus.completed
                ).label("completed"),
                func.count(ComplianceTask.id).filter(
                    ComplianceTask.status == ComplianceStatus.overdue
                ).label("overdue"),
                func.count(ComplianceTask.id).filter(
                    ComplianceTask.status == ComplianceStatus.pending
                ).label("pending"),
            )
            .where(ComplianceTask.client_id.in_(client_ids))
            .group_by(ComplianceTask.client_id)
        )
        for row in stats_result.all():
            stats_map[row.client_id] = ComplianceStats(
                total_tasks=row.total,
                completed_tasks=row.completed,
                overdue_tasks=row.overdue,
                pending_tasks=row.pending,
            )

    items = []
    for c in clients:
        stats = stats_map.get(c.id, ComplianceStats(
            total_tasks=0, completed_tasks=0, overdue_tasks=0, pending_tasks=0,
        ))
        items.append(_build_client_response(c, stats))

    return ClientListResponse(items=items, total=total)


# --------------------------------------------------------------------------- #
#  POST / — Create client
# --------------------------------------------------------------------------- #


@router.post(
    "/",
    response_model=ClientResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new client",
)
async def create_client(
    body: ClientCreate,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> ClientResponse:
    """Create a new client entity. PAN must be unique."""

    # Check duplicate PAN
    existing = await db.execute(select(Client).where(Client.pan == body.pan))
    if existing.scalar_one_or_none() is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="A client with this PAN already exists",
        )

    client = Client(
        firm_name=body.firm_name,
        contact_person=body.contact_person,
        email=body.email,
        phone=body.phone,
        pan=body.pan,
        gstin=body.gstin,
        cin=body.cin,
        entity_type=body.entity_type.value,
        address_json={"address": body.address} if body.address else None,
        assigned_to=current_user.id,
    )
    db.add(client)
    await db.flush()

    await log_action(
        db,
        user_id=current_user.id,
        action="client.create",
        entity_type="client",
        entity_id=client.id,
        details={"firm_name": body.firm_name, "pan": body.pan},
        ip_address=get_client_ip(request),
    )

    return _build_client_response(client)


# --------------------------------------------------------------------------- #
#  GET /{client_id} — Get client details
# --------------------------------------------------------------------------- #


@router.get(
    "/{client_id}",
    response_model=ClientResponse,
    summary="Get client details",
)
async def get_client(
    client_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> ClientResponse:
    """Retrieve full details for a single client."""
    client = await _get_client_or_404(db, client_id)
    stats = await _get_compliance_stats(db, client_id)
    return _build_client_response(client, stats)


# --------------------------------------------------------------------------- #
#  PUT /{client_id} — Update client
# --------------------------------------------------------------------------- #


@router.put(
    "/{client_id}",
    response_model=ClientResponse,
    summary="Update client details",
)
async def update_client(
    client_id: uuid.UUID,
    body: ClientUpdate,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> ClientResponse:
    """Update an existing client's details."""
    client = await _get_client_or_404(db, client_id)

    MUTABLE_FIELDS = {
        "firm_name", "contact_person", "email", "phone",
        "pan", "gstin", "cin", "entity_type", "address",
    }

    update_data = body.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        if field not in MUTABLE_FIELDS:
            continue
        if field == "address":
            client.address_json = {"address": value} if value else None
        elif field == "entity_type" and value is not None:
            client.entity_type = value
        else:
            setattr(client, field, value)

    await db.flush()

    await log_action(
        db,
        user_id=current_user.id,
        action="client.update",
        entity_type="client",
        entity_id=client.id,
        details={"updated_fields": list(update_data.keys())},
        ip_address=get_client_ip(request),
    )

    stats = await _get_compliance_stats(db, client_id)
    return _build_client_response(client, stats)


# --------------------------------------------------------------------------- #
#  DELETE /{client_id} — Soft delete
# --------------------------------------------------------------------------- #


@router.delete(
    "/{client_id}",
    status_code=status.HTTP_200_OK,
    summary="Soft-delete a client (admin only)",
)
async def delete_client(
    client_id: uuid.UUID,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role(["admin"])),
) -> dict:
    """Soft-delete a client by setting is_active to False. Admin only."""
    client = await _get_client_or_404(db, client_id)

    if not client.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Client is already deactivated",
        )

    client.is_active = False
    await db.flush()

    await log_action(
        db,
        user_id=current_user.id,
        action="client.delete",
        entity_type="client",
        entity_id=client.id,
        details={"firm_name": client.firm_name},
        ip_address=get_client_ip(request),
    )

    return {"detail": "Client deactivated successfully"}


# --------------------------------------------------------------------------- #
#  GET /{client_id}/calendar — Compliance calendar
# --------------------------------------------------------------------------- #


@router.get(
    "/{client_id}/calendar",
    response_model=ComplianceCalendarResponse,
    summary="Get compliance calendar for a client",
)
async def get_client_calendar(
    client_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> ComplianceCalendarResponse:
    """Return all compliance tasks for a client, with overdue/upcoming counts."""
    await _get_client_or_404(db, client_id)

    from datetime import date

    result = await db.execute(
        select(ComplianceTask)
        .where(ComplianceTask.client_id == client_id)
        .order_by(ComplianceTask.due_date)
    )
    tasks = result.scalars().all()

    today = date.today()
    overdue_count = sum(
        1 for t in tasks
        if t.due_date < today and t.status.value not in ("completed",)
    )
    upcoming_count = sum(
        1 for t in tasks
        if t.due_date >= today and t.status.value not in ("completed",)
    )

    task_responses = [
        ComplianceTaskResponse(
            id=t.id,
            client_id=t.client_id,
            task_type=t.task_type.value,
            description=t.description or "",
            status=t.status.value,
            due_date=t.due_date,
            assessment_year=t.assessment_year or "",
            assigned_to=t.assigned_to,
            created_at=t.created_at,
            updated_at=t.updated_at,
        )
        for t in tasks
    ]

    return ComplianceCalendarResponse(
        tasks=task_responses,
        overdue_count=overdue_count,
        upcoming_count=upcoming_count,
    )


# --------------------------------------------------------------------------- #
#  GET /{client_id}/documents — Client documents
# --------------------------------------------------------------------------- #


@router.get(
    "/{client_id}/documents",
    response_model=list[DocumentResponse],
    summary="Get all documents for a client",
)
async def get_client_documents(
    client_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[DocumentResponse]:
    """Return all documents associated with a client."""
    await _get_client_or_404(db, client_id)

    result = await db.execute(
        select(Document)
        .where(Document.client_id == client_id)
        .order_by(Document.uploaded_at.desc())
    )
    docs = result.scalars().all()
    return [DocumentResponse.model_validate(d) for d in docs]


# --------------------------------------------------------------------------- #
#  GET /{client_id}/computations — Client computations
# --------------------------------------------------------------------------- #


@router.get(
    "/{client_id}/computations",
    response_model=list[dict],
    summary="Get all tax computations for a client",
)
async def get_client_computations(
    client_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[dict]:
    """Return all tax computations associated with a client."""
    await _get_client_or_404(db, client_id)

    result = await db.execute(
        select(TaxComputation)
        .where(TaxComputation.client_id == client_id)
        .order_by(TaxComputation.created_at.desc())
    )
    comps = result.scalars().all()

    return [
        {
            "id": str(c.id),
            "client_id": str(c.client_id),
            "assessment_year": c.assessment_year,
            "regime": c.regime.value,
            "gross_income": str(c.gross_income) if c.gross_income else None,
            "tax_liability": str(c.tax_liability) if c.tax_liability else None,
            "computation_json": c.computation_json,
            "created_at": c.created_at.isoformat(),
        }
        for c in comps
    ]
