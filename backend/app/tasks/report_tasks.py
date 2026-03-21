"""
Report generation background tasks — PDF tax reports and exports.
"""

from __future__ import annotations

import asyncio
import logging
from uuid import UUID

from app.celery_app import celery_app

logger = logging.getLogger("operatoros.tasks.report")


def _run_async(coro):
    """Run an async coroutine in a new event loop."""
    loop = asyncio.new_event_loop()
    try:
        return loop.run_until_complete(coro)
    finally:
        loop.close()


@celery_app.task(bind=True, max_retries=2, default_retry_delay=30)
def generate_tax_report_pdf(self, computation_id: str) -> dict:
    """Generate a PDF tax computation report for a saved computation.

    Args:
        computation_id: UUID string of the TaxComputation record.

    Returns:
        Dict with status and file_path of the generated PDF.
    """
    logger.info("Generating PDF report for computation %s", computation_id)

    async def _generate():
        from app.database import async_session_factory
        from app.services.pdf_generator import PDFGenerator
        from app.models.computation import TaxComputation
        from app.models.client import Client
        from sqlalchemy import select
        from sqlalchemy.orm import selectinload

        async with async_session_factory() as db:
            result = await db.execute(
                select(TaxComputation)
                .where(TaxComputation.id == UUID(computation_id))
            )
            comp = result.scalar_one_or_none()
            if comp is None:
                return {"status": "error", "error": "Computation not found"}

            client_result = await db.execute(
                select(Client).where(Client.id == comp.client_id)
            )
            client = client_result.scalar_one_or_none()

            generator = PDFGenerator()
            file_path = generator.generate_income_tax_report(
                computation=comp,
                client=client,
            )

            return {
                "status": "completed",
                "computation_id": computation_id,
                "file_path": file_path,
            }

    try:
        return _run_async(_generate())
    except Exception as exc:
        logger.error("PDF generation failed for %s: %s", computation_id, exc)
        raise self.retry(exc=exc)


@celery_app.task(bind=True, max_retries=1)
def generate_client_summary_pdf(self, client_id: str) -> dict:
    """Generate a comprehensive PDF summary for a client.

    Includes: client details, compliance status, recent computations,
    and document list.
    """
    logger.info("Generating client summary PDF for %s", client_id)

    async def _generate():
        from app.database import async_session_factory
        from app.services.pdf_generator import PDFGenerator
        from app.models.client import Client
        from app.models.compliance import ComplianceTask
        from app.models.computation import TaxComputation
        from sqlalchemy import select

        async with async_session_factory() as db:
            client_result = await db.execute(
                select(Client).where(Client.id == UUID(client_id))
            )
            client = client_result.scalar_one_or_none()
            if client is None:
                return {"status": "error", "error": "Client not found"}

            # Gather tasks and computations
            tasks_result = await db.execute(
                select(ComplianceTask)
                .where(ComplianceTask.client_id == UUID(client_id))
                .order_by(ComplianceTask.due_date)
                .limit(50)
            )
            tasks = tasks_result.scalars().all()

            comps_result = await db.execute(
                select(TaxComputation)
                .where(TaxComputation.client_id == UUID(client_id))
                .order_by(TaxComputation.created_at.desc())
                .limit(20)
            )
            computations = comps_result.scalars().all()

            generator = PDFGenerator()
            file_path = generator.generate_client_summary(
                client=client,
                tasks=tasks,
                computations=computations,
            )

            return {
                "status": "completed",
                "client_id": client_id,
                "file_path": file_path,
            }

    try:
        return _run_async(_generate())
    except Exception as exc:
        logger.error("Client summary PDF failed for %s: %s", client_id, exc)
        raise self.retry(exc=exc)
