"""Document routes — upload, retrieve, search, and delete."""

from __future__ import annotations

import uuid
from pathlib import Path

from typing import Optional

from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, Request, UploadFile, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.dependencies import get_current_user, require_role
from app.middleware.audit import get_client_ip, log_action
from app.models.client import Client
from app.models.document import DocType as ModelDocType, Document, DocumentStatus
from app.models.user import User
from app.schemas.document import (
    DocType,
    DocumentResponse,
    DocumentSearchRequest,
    DocumentSearchResult,
)
from app.schemas.pagination import paginated_response

router = APIRouter(tags=["documents"])

# Storage directory for uploaded files
UPLOAD_DIR = Path("/app/uploads")

# Maximum allowed file size: 50 MB
MAX_FILE_SIZE = 50 * 1024 * 1024


# --------------------------------------------------------------------------- #
#  POST /upload — Upload a document
# --------------------------------------------------------------------------- #


@router.post(
    "/upload",
    response_model=DocumentResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Upload a document",
)
async def upload_document(
    request: Request,
    file: UploadFile = File(...),
    client_id: uuid.UUID = Form(...),
    doc_type: str = Form(...),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> DocumentResponse:
    """Upload a document file, save it to storage, and create a database record.

    The document status starts as 'uploaded' and will transition to 'processing'
    once the background parsing pipeline picks it up.
    """

    # Validate client exists
    result = await db.execute(select(Client).where(Client.id == client_id))
    client = result.scalar_one_or_none()
    if client is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Client not found",
        )

    # Validate doc_type
    try:
        model_doc_type = ModelDocType(doc_type)
    except ValueError:
        valid_types = [t.value for t in ModelDocType]
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid doc_type. Must be one of: {valid_types}",
        )

    # Check file size before reading the full file
    # First try Content-Length header for an early check
    if file.size is not None and file.size > MAX_FILE_SIZE:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"File too large. Maximum allowed size is {MAX_FILE_SIZE // (1024 * 1024)} MB",
        )

    # Save file to disk
    doc_id = uuid.uuid4()
    upload_dir = UPLOAD_DIR / str(client_id)
    upload_dir.mkdir(parents=True, exist_ok=True)

    # Sanitize filename to prevent path traversal
    safe_name = Path(file.filename or "upload").name
    file_ext = Path(safe_name).suffix
    file_path = upload_dir / f"{doc_id}{file_ext}"

    # Read file in chunks to enforce size limit during streaming.
    # This prevents loading the entire payload into memory when file.size is
    # not available (e.g. chunked transfer encoding).
    import aiofiles

    _CHUNK_SIZE = 256 * 1024  # 256 KB per chunk
    total_read = 0
    async with aiofiles.open(file_path, "wb") as f:
        while True:
            chunk = await file.read(_CHUNK_SIZE)
            if not chunk:
                break
            total_read += len(chunk)
            if total_read > MAX_FILE_SIZE:
                # Clean up the partial file before raising
                await f.close()
                try:
                    file_path.unlink(missing_ok=True)
                except OSError:
                    pass
                raise HTTPException(
                    status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                    detail=f"File too large. Maximum allowed size is {MAX_FILE_SIZE // (1024 * 1024)} MB",
                )
            await f.write(chunk)

    content_size = total_read

    # Create database record
    document = Document(
        id=doc_id,
        client_id=client_id,
        doc_type=model_doc_type,
        original_filename=file.filename or "unknown",
        file_url=str(file_path),
        file_size=content_size,
        status=DocumentStatus.uploaded,
        uploaded_by=current_user.id,
    )
    db.add(document)
    await db.flush()

    await log_action(
        db,
        user_id=current_user.id,
        action="document.upload",
        entity_type="document",
        entity_id=document.id,
        details={
            "filename": file.filename,
            "doc_type": doc_type,
            "client_id": str(client_id),
            "file_size": content_size,
        },
        ip_address=get_client_ip(request),
    )

    return DocumentResponse.model_validate(document)


# --------------------------------------------------------------------------- #
#  POST /bulk-upload — Upload multiple documents
# --------------------------------------------------------------------------- #


@router.post(
    "/bulk-upload",
    status_code=status.HTTP_201_CREATED,
    summary="Upload multiple documents at once (max 100)",
)
async def bulk_upload_documents(
    request: Request,
    files: list[UploadFile] = File(...),
    client_id: uuid.UUID = Form(...),
    doc_type: str = Form("other"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict:
    """Upload multiple files in a single request.

    Returns per-file results with success_count and error_count.
    Max 100 files per request.
    """
    if len(files) > 100:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Maximum 100 files per bulk upload",
        )

    # Validate client
    result = await db.execute(select(Client).where(Client.id == client_id))
    client = result.scalar_one_or_none()
    if client is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Client not found",
        )

    try:
        model_doc_type = ModelDocType(doc_type)
    except ValueError:
        model_doc_type = ModelDocType.other

    import asyncio
    import aiofiles

    _CHUNK_SIZE = 256 * 1024
    semaphore = asyncio.Semaphore(10)
    results_list = []

    async def process_file(file: UploadFile) -> dict:
        async with semaphore:
            try:
                doc_id = uuid.uuid4()
                upload_dir = UPLOAD_DIR / str(client_id)
                upload_dir.mkdir(parents=True, exist_ok=True)

                safe_name = Path(file.filename or "upload").name
                file_ext = Path(safe_name).suffix
                file_path = upload_dir / f"{doc_id}{file_ext}"

                total_read = 0
                async with aiofiles.open(file_path, "wb") as f:
                    while True:
                        chunk = await file.read(_CHUNK_SIZE)
                        if not chunk:
                            break
                        total_read += len(chunk)
                        if total_read > MAX_FILE_SIZE:
                            await f.close()
                            try:
                                file_path.unlink(missing_ok=True)
                            except OSError:
                                pass
                            return {
                                "filename": file.filename,
                                "success": False,
                                "error": f"File too large (max {MAX_FILE_SIZE // (1024 * 1024)} MB)",
                            }
                        await f.write(chunk)

                document = Document(
                    id=doc_id,
                    client_id=client_id,
                    doc_type=model_doc_type,
                    original_filename=file.filename or "unknown",
                    file_url=str(file_path),
                    file_size=total_read,
                    status=DocumentStatus.uploaded,
                    uploaded_by=current_user.id,
                )
                db.add(document)
                await db.flush()

                return {
                    "filename": file.filename,
                    "success": True,
                    "document_id": str(doc_id),
                }
            except Exception as exc:
                return {
                    "filename": file.filename,
                    "success": False,
                    "error": str(exc),
                }

    results_list = await asyncio.gather(*[process_file(f) for f in files])

    success_count = sum(1 for r in results_list if r["success"])
    error_count = sum(1 for r in results_list if not r["success"])

    await log_action(
        db,
        user_id=current_user.id,
        action="document.bulk_upload",
        entity_type="document",
        details={
            "client_id": str(client_id),
            "file_count": len(files),
            "success_count": success_count,
            "error_count": error_count,
        },
        ip_address=get_client_ip(request),
    )

    return {
        "success_count": success_count,
        "error_count": error_count,
        "results": results_list,
    }


# --------------------------------------------------------------------------- #
#  GET / — List documents with pagination
# --------------------------------------------------------------------------- #


@router.get(
    "/",
    summary="List documents with pagination and optional filters",
)
async def list_documents(
    page: int = Query(1, ge=1, description="Page number"),
    size: int = Query(20, ge=1, le=100, description="Items per page"),
    client_id: Optional[uuid.UUID] = Query(None, description="Filter by client"),
    document_type: Optional[str] = Query(None, description="Filter by doc type"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict:
    """Return a paginated list of documents, most recent first."""

    base_query = select(Document).order_by(Document.uploaded_at.desc())

    if client_id is not None:
        base_query = base_query.where(Document.client_id == client_id)

    if document_type is not None:
        try:
            model_dt = ModelDocType(document_type)
            base_query = base_query.where(Document.doc_type == model_dt)
        except ValueError:
            pass  # ignore invalid filter gracefully

    # Total count
    count_q = select(func.count()).select_from(base_query.subquery())
    total = (await db.execute(count_q)).scalar_one()

    offset = (page - 1) * size
    paged_query = base_query.offset(offset).limit(size)
    result = await db.execute(paged_query)
    docs = result.scalars().all()

    items = [DocumentResponse.model_validate(d) for d in docs]
    return paginated_response(items, total, page, size)


# --------------------------------------------------------------------------- #
#  GET /{document_id} — Get document details
# --------------------------------------------------------------------------- #


@router.get(
    "/{document_id}",
    response_model=DocumentResponse,
    summary="Get document details",
)
async def get_document(
    document_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> DocumentResponse:
    """Retrieve details for a specific document."""

    result = await db.execute(
        select(Document).where(Document.id == document_id)
    )
    document = result.scalar_one_or_none()
    if document is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Document not found",
        )

    return DocumentResponse.model_validate(document)


# --------------------------------------------------------------------------- #
#  POST /search — Semantic search across documents
# --------------------------------------------------------------------------- #


@router.post(
    "/search",
    response_model=list[DocumentSearchResult],
    summary="Search across documents (semantic)",
)
async def search_documents(
    body: DocumentSearchRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[DocumentSearchResult]:
    """Semantic search across document content.

    **Note:** This endpoint currently performs keyword-based search on summaries.
    Full vector-based semantic search will be enabled once the embedding service
    is integrated.
    """

    query = select(Document).where(Document.status == DocumentStatus.processed)

    if body.client_id is not None:
        query = query.where(Document.client_id == body.client_id)

    if body.doc_type is not None:
        try:
            model_dt = ModelDocType(body.doc_type.value)
            query = query.where(Document.doc_type == model_dt)
        except ValueError:
            pass

    # Keyword-based fallback: search in summary field
    # Escape LIKE wildcards to prevent unexpected pattern matching
    safe_query = body.query.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
    query = query.where(
        Document.summary.ilike(f"%{safe_query}%", escape="\\")
    ).limit(body.limit)

    result = await db.execute(query)
    docs = result.scalars().all()

    return [
        DocumentSearchResult(
            document=DocumentResponse.model_validate(doc),
            relevance_score=0.5,  # Placeholder until vector search is active
            excerpt=doc.summary[:200] if doc.summary else "",
        )
        for doc in docs
    ]


# --------------------------------------------------------------------------- #
#  DELETE /{document_id} — Delete document
# --------------------------------------------------------------------------- #


@router.delete(
    "/{document_id}",
    status_code=status.HTTP_200_OK,
    summary="Delete a document",
)
async def delete_document(
    document_id: uuid.UUID,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role(["admin", "partner"])),
) -> dict:
    """Delete a document record and its associated file. Restricted to admin and partner roles."""

    result = await db.execute(
        select(Document).where(Document.id == document_id)
    )
    document = result.scalar_one_or_none()
    if document is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Document not found",
        )

    # Attempt to remove file from disk
    try:
        file_path = Path(document.file_url)
        if file_path.exists():
            file_path.unlink()
    except OSError as exc:
        import logging
        logging.getLogger("operatoros.documents").warning(
            "Failed to delete file %s for document %s: %s",
            document.file_url, document.id, exc,
        )

    await log_action(
        db,
        user_id=current_user.id,
        action="document.delete",
        entity_type="document",
        entity_id=document.id,
        details={"filename": document.original_filename},
        ip_address=get_client_ip(request),
    )

    await db.delete(document)
    await db.flush()

    return {"detail": "Document deleted successfully"}
