"""Query routes — RAG Q&A endpoint and query history."""

from __future__ import annotations

import uuid
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy import func, select, Select
from sqlalchemy.ext.asyncio import AsyncSession

import logging

from app.database import get_db
from app.dependencies import get_current_user, get_redis
from app.middleware.audit import get_client_ip, log_action
from app.models.client import Client
from app.models.query import Query as QueryModel
from app.models.user import User
from app.schemas.query import QueryRequest, QueryResponse
from app.schemas.pagination import paginated_response
from app.services.embedding import EmbeddingService
from app.services.openrouter import OpenRouterClient
from app.services.rag import (
    RAGService,
    RAGEmbeddingError,
    RAGInvalidQueryError,
    RAGLLMError,
)

_logger = logging.getLogger(__name__)

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

    Runs the full RAG pipeline: classify -> embed -> vector search -> LLM.
    Falls back to a placeholder if the external services (embedding / LLM)
    are unavailable.
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

    # ── Attempt full RAG pipeline ────────────────────────────────────────
    rag_result = None
    try:
        # Build service instances (Redis is optional for embedding cache)
        redis_conn = None
        try:
            from app.dependencies import _redis_pool
            redis_conn = _redis_pool
        except Exception:
            pass

        embedding_svc = EmbeddingService(redis=redis_conn)
        openrouter_client = OpenRouterClient()
        rag_svc = RAGService(db=db, embedding_service=embedding_svc, openrouter=openrouter_client)

        rag_result = await rag_svc.answer_query(
            question=body.question,
            client_id=body.client_id,
            context=body.context if hasattr(body, "context") else None,
        )
    except RAGInvalidQueryError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        )
    except RAGEmbeddingError as exc:
        _logger.warning("RAG embedding failed, falling back to graceful response: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Embedding service unavailable: {exc}",
        )
    except RAGLLMError as exc:
        _logger.warning("RAG LLM failed, falling back to graceful response: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"LLM service unavailable: {exc}",
        )
    except Exception as exc:
        _logger.error(
            "RAG pipeline unexpected error for user=%s client=%s question='%s...': %s",
            current_user.id,
            body.client_id,
            body.question[:80],
            exc,
            exc_info=True,
        )
        # Graceful degradation: the query is still saved and the caller is told
        # explicitly that the AI service is unavailable (see ``fallback`` flag).
        rag_result = None

    # ── Build response fields ────────────────────────────────────────────
    fallback = rag_result is None
    if not fallback:
        response_text = rag_result["response"]
        sources_cited = rag_result.get("sources", [])
        query_type = rag_result.get("query_type", "general")
        model_used = rag_result.get("model_used", "unknown")
        tokens_used = rag_result.get("tokens_used", 0)
    else:
        response_text = (
            "The AI service is currently unavailable, so we could not generate "
            "an answer to your query. Your question has been saved; please try "
            "again once the service is back online."
        )
        sources_cited = []
        query_type = "general"
        model_used = "unavailable"
        tokens_used = 0

    # ── Persist ──────────────────────────────────────────────────────────
    query_record = QueryModel(
        client_id=body.client_id,
        asked_by=current_user.id,
        question=body.question,
        response=response_text,
        sources_cited=sources_cited,
        query_type=query_type,
        model_used=model_used,
        tokens_used=tokens_used,
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
            "rag_active": rag_result is not None,
        },
        ip_address=get_client_ip(request),
    )

    return QueryResponse(
        id=query_record.id,
        question=query_record.question,
        response=query_record.response,
        sources_cited=sources_cited if isinstance(sources_cited, list) else [],
        query_type=query_type,
        model_used=model_used,
        tokens_used=tokens_used,
        asked_by=query_record.asked_by,
        client_id=query_record.client_id,
        created_at=query_record.created_at,
        fallback=fallback,
    )


# --------------------------------------------------------------------------- #
#  GET / — List recent queries
# --------------------------------------------------------------------------- #


@router.get(
    "/",
    summary="List recent queries with pagination",
)
async def list_queries(
    page: int = Query(1, ge=1, description="Page number"),
    size: int = Query(20, ge=1, le=100, description="Items per page"),
    client_id: Optional[uuid.UUID] = Query(None, description="Filter by client"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict:
    """Return a paginated list of queries, most recent first."""

    base_query = select(QueryModel).order_by(QueryModel.created_at.desc())

    if client_id is not None:
        base_query = base_query.where(QueryModel.client_id == client_id)

    # Total count
    count_q = select(func.count()).select_from(base_query.subquery())
    total = (await db.execute(count_q)).scalar_one()

    offset = (page - 1) * size
    paginated_query = base_query.offset(offset).limit(size)

    result = await db.execute(paginated_query)
    records = result.scalars().all()

    items = [
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
            fallback=r.model_used in ("unavailable", "placeholder"),
        )
        for r in records
    ]

    return paginated_response(items, total, page, size)


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
        fallback=record.model_used in ("unavailable", "placeholder"),
    )
