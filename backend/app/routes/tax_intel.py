"""World Tax Radar routes — ingest and list tax intelligence feed items."""

from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.dependencies import require_api_key_or_admin
from app.models.tax_intel import TaxIntel
from app.schemas.pagination import paginated_response
from app.schemas.tax_intel import TaxIntelIngestRequest, TaxIntelResponse

router = APIRouter(tags=["tax-intel"])


# --------------------------------------------------------------------------- #
#  POST /ingest — Accept feed items from the social scraper connector
# --------------------------------------------------------------------------- #


@router.post(
    "/ingest",
    response_model=TaxIntelResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Ingest a tax intelligence feed item",
)
async def ingest_tax_intel(
    body: TaxIntelIngestRequest,
    db: AsyncSession = Depends(get_db),
    _=Depends(require_api_key_or_admin),
) -> TaxIntelResponse:
    """Ingest a World Tax Radar item from an upstream scraper.

    Requires either an admin bearer token or the configured ingest API key in
    the ``X-API-Key`` header.
    """
    item = TaxIntel(
        title=body.title,
        summary=body.summary,
        source_url=body.source_url,
        published_at=body.published_at,
        jurisdiction=body.jurisdiction,
        topic=body.topic,
        nri_impact_score=body.nri_impact_score,
        matched_terms=body.matched_terms or [],
    )
    db.add(item)
    await db.flush()

    return TaxIntelResponse.model_validate(item)


# --------------------------------------------------------------------------- #
#  GET / — List tax intelligence feed items with filters
# --------------------------------------------------------------------------- #


@router.get(
    "/",
    summary="List tax intelligence feed items",
)
async def list_tax_intel(
    jurisdiction: Optional[str] = Query(None, description="Filter by jurisdiction"),
    topic: Optional[str] = Query(None, description="Filter by topic"),
    impact_min: Optional[int] = Query(None, ge=0, le=100, description="Minimum NRI impact score"),
    impact_max: Optional[int] = Query(None, ge=0, le=100, description="Maximum NRI impact score"),
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Return a paginated list of tax intelligence items, newest first.

    Filters are case-insensitive substring matches for jurisdiction and topic.
    """
    filters = []
    if jurisdiction is not None:
        filters.append(TaxIntel.jurisdiction.ilike(f"%{jurisdiction}%"))
    if topic is not None:
        filters.append(TaxIntel.topic.ilike(f"%{topic}%"))
    if impact_min is not None:
        filters.append(TaxIntel.nri_impact_score >= impact_min)
    if impact_max is not None:
        filters.append(TaxIntel.nri_impact_score <= impact_max)

    base_query = select(TaxIntel).where(*filters).order_by(TaxIntel.created_at.desc())

    count_q = select(func.count()).select_from(base_query.subquery())
    total = (await db.execute(count_q)).scalar_one()

    offset = (page - 1) * size
    paged_query = base_query.offset(offset).limit(size)
    result = await db.execute(paged_query)
    items = [TaxIntelResponse.model_validate(item) for item in result.scalars().all()]

    return paginated_response(items, total, page, size)
