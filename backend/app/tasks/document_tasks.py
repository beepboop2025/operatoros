"""
Document processing background tasks — OCR, parsing, embedding generation.

These tasks are dispatched after a document is uploaded and run
asynchronously via Celery workers.
"""

from __future__ import annotations

import asyncio
import logging
from uuid import UUID

from app.celery_app import celery_app

logger = logging.getLogger("operatoros.tasks.document")


def _run_async(coro):
    """Run an async coroutine in a new event loop (Celery workers are sync)."""
    loop = asyncio.new_event_loop()
    try:
        return loop.run_until_complete(coro)
    finally:
        loop.close()


@celery_app.task(bind=True, max_retries=3, default_retry_delay=60)
def process_document(self, document_id: str, file_path: str, doc_type: str) -> dict:
    """Process a document: extract text, parse, summarise, generate embedding.

    Args:
        document_id: UUID string of the document record.
        file_path: Path to the uploaded file on disk.
        doc_type: Document type string (e.g. 'form_16', 'notice').

    Returns:
        Processing result dict with status, summary, and action items.
    """
    logger.info("Starting document processing for %s", document_id)

    async def _process():
        from app.database import async_session_factory
        from app.services.document_processor import DocumentProcessor
        from app.services.embedding import EmbeddingService
        from app.services.openrouter import OpenRouterClient

        async with async_session_factory() as db:
            embedding_svc = EmbeddingService()
            openrouter = OpenRouterClient()
            processor = DocumentProcessor(db, embedding_svc, openrouter)

            result = await processor.process_document(
                document_id=UUID(document_id),
                file_path=file_path,
                doc_type=doc_type,
            )
            await db.commit()
            return result

    try:
        return _run_async(_process())
    except Exception as exc:
        logger.error("Document processing failed for %s: %s", document_id, exc)
        raise self.retry(exc=exc)


@celery_app.task(bind=True, max_retries=2, default_retry_delay=30)
def generate_document_embedding(self, document_id: str, text: str) -> dict:
    """Generate or regenerate the vector embedding for a document.

    Args:
        document_id: UUID string of the document.
        text: Text content to embed.

    Returns:
        Dict with status and embedding dimension.
    """
    logger.info("Generating embedding for document %s", document_id)

    async def _embed():
        from app.database import async_session_factory
        from app.services.embedding import EmbeddingService
        from sqlalchemy import update
        from app.models.document import Document

        embedding_svc = EmbeddingService()
        embedding = await embedding_svc.generate_embedding(text[:8000])

        async with async_session_factory() as db:
            await db.execute(
                update(Document)
                .where(Document.id == UUID(document_id))
                .values(embedding=embedding)
            )
            await db.commit()

        return {
            "document_id": document_id,
            "status": "embedded",
            "dimensions": len(embedding),
        }

    try:
        return _run_async(_embed())
    except Exception as exc:
        logger.error("Embedding generation failed for %s: %s", document_id, exc)
        raise self.retry(exc=exc)
