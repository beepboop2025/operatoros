"""Query routes — RAG Q&A endpoint and query history."""

from __future__ import annotations

import uuid
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.dependencies import get_current_user
from app.middleware.audit import get_client_ip, log_action
from app.models.client import Client
from app.models.query import Query as QueryModel
from app.models.user import User
from app.schemas.query import QueryRequest, QueryResponse

router = APIRouter(tags=["queries"])


# --------------------------------------------------------------------------- #
#  POST / — Submit a query
# --------------------------------------------------------------------------- #


@router.post(
    "/",
    response_model=QueryResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Submit a tax/compliance query",
)
async def submit_query(
    body: QueryRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> QueryResponse:
    """Submit a tax or compliance query for processing.

    This is the main RAG endpoint. Currently operates in placeholder mode:
    the query is saved to the database and a structured response indicates
    that the RAG pipeline will process it asynchronously.
    """

    # Validate client if provided
    if body.client_id is not None:
        result = await db.execute(
            select(Client).where(Client.id == body.client_id)
        )
        if result.scalar_one_or_none() is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Client not found",
            )

    # Create the query record with placeholder response
    query_record = QueryModel(
        client_id=body.client_id,
        asked_by=current_user.id,
        question=body.question,
        response=(
            "Your query has been received and will be processed by the RAG pipeline. "
            "The system will analyze relevant documents, tax laws, and compliance "
            "guidelines to provide a comprehensive response. Please check back shortly."
        ),
        sources_cited=[],
        query_type="general",
        model_used="placeholder",
        tokens_used=0,
    )
    db.add(query_record)
    await db.flush()

    await log_action(
        db,
        user_id=current_user.id,
        action="query.create",
        entity_type="query",
        entity_id=query_record.id,
        details={
            "question_preview": body.question[:100],
            "client_id": str(body.client_id) if body.client_id else None,
        },
        ip_address=get_client_ip(request),
    )

    return QueryResponse(
        id=query_record.id,
        question=query_record.question,
        response=query_record.response,
        sources_cited=[],
        query_type="general",
        model_used="placeholder",
        tokens_used=0,
        asked_by=query_record.asked_by,
        client_id=query_record.client_id,
        created_at=query_record.created_at,
    )


# --------------------------------------------------------------------------- #
#  GET / — List recent queries
# --------------------------------------------------------------------------- #


@router.get(
    "/",
    response_model=list[QueryResponse],
    summary="List recent queries with pagination",
)
async def list_queries(
    page: int = Query(1, ge=1, description="Page number"),
    size: int = Query(20, ge=1, le=100, description="Items per page"),
    client_id: Optional[uuid.UUID] = Query(None, description="Filter by client"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[QueryResponse]:
    """Return a paginated list of queries, most recent first."""

    query = select(QueryModel).order_by(QueryModel.created_at.desc())

    if client_id is not None:
        query = query.where(QueryModel.client_id == client_id)

    offset = (page - 1) * size
    query = query.offset(offset).limit(size)

    result = await db.execute(query)
    records = result.scalars().all()

    return [
        QueryResponse(
            id=r.id,
            question=r.question,
            response=r.response or "",
            sources_cited=r.sources_cited or [],
            query_type=r.query_type.value if r.query_type else "general",
            model_used=r.model_used or "unknown",
            tokens_used=r.tokens_used or 0,
            asked_by=r.asked_by,
            client_id=r.client_id,
            created_at=r.created_at,
        )
        for r in records
    ]


# --------------------------------------------------------------------------- #
#  GET /{query_id} — Get query details
# --------------------------------------------------------------------------- #


@router.get(
    "/{query_id}",
    response_model=QueryResponse,
    summary="Get query details",
)
async def get_query(
    query_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> QueryResponse:
    """Retrieve full details for a specific query, including response and sources."""

    result = await db.execute(
        select(QueryModel).where(QueryModel.id == query_id)
    )
    record = result.scalar_one_or_none()

    if record is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Query not found",
        )

    return QueryResponse(
        id=record.id,
        question=record.question,
        response=record.response or "",
        sources_cited=record.sources_cited or [],
        query_type=record.query_type.value if record.query_type else "general",
        model_used=record.model_used or "unknown",
        tokens_used=record.tokens_used or 0,
        asked_by=record.asked_by,
        client_id=record.client_id,
        created_at=record.created_at,
    )
