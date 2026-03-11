"""Document routes — upload, retrieve, search, and delete."""

from __future__ import annotations

import uuid
from pathlib import Path

from fastapi import APIRouter, Depends, File, Form, HTTPException, Request, UploadFile, status
from sqlalchemy import select
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

    content = await file.read()

    # Verify actual content size
    if len(content) > MAX_FILE_SIZE:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"File too large. Maximum allowed size is {MAX_FILE_SIZE // (1024 * 1024)} MB",
        )
    import aiofiles
    async with aiofiles.open(file_path, "wb") as f:
        await f.write(content)

    # Create database record
    document = Document(
        id=doc_id,
        client_id=client_id,
        doc_type=model_doc_type,
        original_filename=file.filename or "unknown",
        file_url=str(file_path),
        file_size=len(content),
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
            "file_size": len(content),
        },
        ip_address=get_client_ip(request),
    )

    return DocumentResponse.model_validate(document)


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
