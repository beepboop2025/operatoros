"""
Document processing service — OCR, text extraction, parsing, summarisation, and embedding.

Handles PDFs, images, and text files.  Extracts structured data from Indian tax
documents (Form 26AS, GST notices, bank statements, financial statements) and
updates the database with parsed JSON, summary, and vector embedding.
"""

from __future__ import annotations

import logging
import os
import re
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from uuid import UUID

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.document import Document, DocumentStatus
from app.services.embedding import EmbeddingService
from app.services.openrouter import OpenRouterClient

logger = logging.getLogger(__name__)

# ── Extraction prompts ───────────────────────────────────────────────────────

_PARSE_PROMPTS: Dict[str, str] = {
    "form26as": (
        "Extract ALL structured data from this Form 26AS text. Return a JSON object with:\n"
        "- tds_entries: list of {deductor_name, tan, amount_paid, tds_deducted, date, section}\n"
        "- sft_entries: list of {reporting_entity, transaction_type, amount}\n"
        "- tax_paid: list of {challan_no, bsr_code, date, amount, type}\n"
        "- refunds: list of {assessment_year, amount, date}\n"
        "- total_tds: sum of all TDS\n"
        "- total_tax_paid: sum of all tax payments\n"
        "Return ONLY valid JSON, no explanation."
    ),
    "notice": (
        "Extract structured data from this tax/GST notice. Return a JSON object with:\n"
        "- notice_type: the type of notice (e.g., u/s 143(1), u/s 148, DRC-01)\n"
        "- section: the section under which notice is issued\n"
        "- demand_amount: total demand in INR (null if not applicable)\n"
        "- assessment_year: the AY in question\n"
        "- period: the period covered\n"
        "- deadline: response deadline date (YYYY-MM-DD)\n"
        "- issues_raised: list of specific issues/discrepancies mentioned\n"
        "- sections_cited: list of sections cited in the notice\n"
        "Return ONLY valid JSON, no explanation."
    ),
    "bank_statement": (
        "Analyse this bank statement text. Return a JSON object with:\n"
        "- account_holder: name\n"
        "- account_number: masked account number\n"
        "- bank_name: name of bank\n"
        "- period: {from: 'YYYY-MM-DD', to: 'YYYY-MM-DD'}\n"
        "- opening_balance: amount\n"
        "- closing_balance: amount\n"
        "- total_credits: sum of credits\n"
        "- total_debits: sum of debits\n"
        "- categories: {salary: amount, rent: amount, investments: amount, "
        "business_receipts: amount, loans: amount, other: amount}\n"
        "- high_value_transactions: list of {date, description, amount, type} "
        "for transactions above INR 50,000\n"
        "Return ONLY valid JSON, no explanation."
    ),
    "financial_statement": (
        "Extract key financial figures from this financial statement. Return a JSON object with:\n"
        "- entity_name: name of the company/firm\n"
        "- period: {from: 'YYYY-MM-DD', to: 'YYYY-MM-DD'}\n"
        "- revenue: total revenue/turnover\n"
        "- net_profit: profit after tax\n"
        "- total_assets: total assets\n"
        "- total_liabilities: total liabilities\n"
        "- equity: shareholders' equity\n"
        "- key_ratios: {current_ratio, debt_equity, roe, pat_margin}\n"
        "- depreciation: total depreciation\n"
        "- tax_provision: provision for income tax\n"
        "Return ONLY valid JSON, no explanation."
    ),
}

_SUMMARY_PROMPT = (
    "You are a tax document analyst for Indian CA firms. "
    "Summarise the following document in 3-5 bullet points. "
    "Highlight: (1) key financial figures, (2) compliance implications, "
    "(3) any red flags or action items. Be concise and professional."
)

# ── Chunking defaults ────────────────────────────────────────────────────────

_DEFAULT_CHUNK_SIZE = 1000
_DEFAULT_OVERLAP = 200


class DocumentProcessor:
    """Process uploaded documents: extract text, parse, summarise, embed."""

    def __init__(
        self,
        db: AsyncSession,
        embedding_service: EmbeddingService,
        openrouter: OpenRouterClient,
    ) -> None:
        self.db = db
        self.embedding = embedding_service
        self.llm = openrouter

    # ── Main entry point ─────────────────────────────────────────────────

    async def process_document(
        self, document_id: UUID, file_path: str, doc_type: str
    ) -> Dict[str, Any]:
        """
        Full processing pipeline for a document.

        1. Mark status as processing
        2. Extract text (PDF / image / plain text)
        3. Parse structured data based on doc_type
        4. Generate summary via LLM
        5. Generate embedding
        6. Update database record
        7. Return summary and action items
        """
        # Mark processing
        await self._update_status(document_id, DocumentStatus.processing)

        try:
            # Step 1: Extract text
            raw_text = await self._extract_text(file_path)
            if not raw_text or not raw_text.strip():
                await self._update_status(document_id, DocumentStatus.failed)
                return {"error": "No text could be extracted from the document."}

            logger.info(
                "Extracted %d characters from document %s", len(raw_text), document_id
            )

            # Step 2: Parse structured data
            parsed_json = await self._parse_document(raw_text, doc_type)

            # Step 3: Generate summary
            summary = await self._generate_summary(raw_text, doc_type)

            # Step 4: Generate embedding (from summary + key text)
            embedding_text = f"{summary}\n\n{raw_text[:3000]}"
            embedding = await self.embedding.generate_embedding(embedding_text)

            # Step 5: Extract action items from summary
            action_items = self._extract_action_items(summary)

            # Step 6: Update database
            await self._update_document(
                document_id,
                parsed_json=parsed_json,
                summary=summary,
                embedding=embedding,
            )

            logger.info("Document %s processed successfully", document_id)

            return {
                "document_id": str(document_id),
                "status": "processed",
                "summary": summary,
                "parsed_fields": list(parsed_json.keys()) if parsed_json else [],
                "action_items": action_items,
                "text_length": len(raw_text),
            }

        except Exception as exc:
            logger.error("Document processing failed for %s: %s", document_id, exc)
            await self._update_status(document_id, DocumentStatus.failed)
            return {
                "document_id": str(document_id),
                "status": "failed",
                "error": str(exc),
            }

    # ── Text extraction ──────────────────────────────────────────────────

    async def _extract_text(self, file_path: str) -> str:
        """Route to the appropriate text extractor based on file extension."""
        if not os.path.isfile(file_path):
            raise FileNotFoundError(f"File not found: {file_path}")

        ext = os.path.splitext(file_path)[1].lower()

        if ext == ".pdf":
            return self.extract_text_from_pdf(file_path)
        elif ext in (".png", ".jpg", ".jpeg", ".tiff", ".bmp", ".webp"):
            return self.extract_text_from_image(file_path)
        elif ext in (".txt", ".csv", ".json", ".xml"):
            return self._read_text_file(file_path)
        else:
            # Try reading as text; fall back to PDF
            try:
                return self._read_text_file(file_path)
            except UnicodeDecodeError:
                return self.extract_text_from_pdf(file_path)

    @staticmethod
    def extract_text_from_pdf(file_path: str) -> str:
        """Extract text from a PDF file using PyPDF2."""
        try:
            from PyPDF2 import PdfReader
        except ImportError:
            raise RuntimeError(
                "PyPDF2 is required for PDF processing. Install with: pip install PyPDF2"
            )

        reader = PdfReader(file_path)
        pages: List[str] = []
        for page in reader.pages:
            text = page.extract_text()
            if text:
                pages.append(text)

        combined = "\n\n".join(pages)

        # If very little text extracted, the PDF might be scanned
        if len(combined.strip()) < 100 and len(reader.pages) > 0:
            logger.warning(
                "PDF %s yielded very little text (%d chars), may need OCR",
                file_path,
                len(combined),
            )

        return combined

    @staticmethod
    def extract_text_from_image(file_path: str) -> str:
        """Extract text from an image using pytesseract OCR."""
        try:
            import pytesseract
            from PIL import Image
        except ImportError:
            raise RuntimeError(
                "pytesseract and Pillow are required for image OCR. "
                "Install with: pip install pytesseract Pillow"
            )

        image = Image.open(file_path)
        text = pytesseract.image_to_string(image, lang="eng")
        return text

    @staticmethod
    def _read_text_file(file_path: str) -> str:
        """Read a plain text file."""
        with open(file_path, "r", encoding="utf-8") as f:
            return f.read()

    # ── Document parsing ─────────────────────────────────────────────────

    async def _parse_document(
        self, text: str, doc_type: str
    ) -> Dict[str, Any]:
        """Use LLM to parse structured data from document text."""
        parse_prompt = _PARSE_PROMPTS.get(doc_type)
        if parse_prompt is None:
            # Generic parsing for unknown types
            parse_prompt = (
                "Extract any structured data from this document. Return a JSON object "
                "with relevant key-value pairs. Include dates, amounts, names, and "
                "reference numbers. Return ONLY valid JSON, no explanation."
            )

        # Use a chunk of the text (first 6000 chars) to avoid token limits
        text_chunk = text[:6000]

        messages = [
            {"role": "system", "content": parse_prompt},
            {"role": "user", "content": text_chunk},
        ]

        try:
            result = await self.llm.chat_completion(
                messages=messages,
                model=self.llm.select_model("factual"),
                temperature=0.0,
                max_tokens=2048,
            )
            raw_json = result["text"].strip()
            # Strip markdown code fences if present
            raw_json = re.sub(r"^```(?:json)?\s*", "", raw_json)
            raw_json = re.sub(r"\s*```$", "", raw_json)

            import json
            return json.loads(raw_json)

        except (json.JSONDecodeError, KeyError) as exc:
            logger.warning("Failed to parse document JSON: %s", exc)
            return {"raw_text_preview": text[:500], "parse_error": str(exc)}
        except Exception as exc:
            logger.error("Document parsing LLM call failed: %s", exc)
            return {"raw_text_preview": text[:500], "parse_error": str(exc)}

    # ── Summary generation ───────────────────────────────────────────────

    async def _generate_summary(self, text: str, doc_type: str) -> str:
        """Generate a concise summary of the document content."""
        text_chunk = text[:4000]

        messages = [
            {"role": "system", "content": _SUMMARY_PROMPT},
            {
                "role": "user",
                "content": f"Document type: {doc_type}\n\n{text_chunk}",
            },
        ]

        try:
            result = await self.llm.chat_completion(
                messages=messages,
                model=self.llm.select_model("summarization"),
                temperature=0.2,
                max_tokens=1024,
            )
            return result["text"].strip()

        except Exception as exc:
            logger.error("Summary generation failed: %s", exc)
            # Fall back to first 500 chars
            return text[:500] + "..." if len(text) > 500 else text

    # ── Text chunking ────────────────────────────────────────────────────

    @staticmethod
    def chunk_text(
        text: str,
        chunk_size: int = _DEFAULT_CHUNK_SIZE,
        overlap: int = _DEFAULT_OVERLAP,
    ) -> List[str]:
        """
        Split text into overlapping chunks for embedding or processing.

        Tries to break on sentence boundaries where possible.
        """
        if len(text) <= chunk_size:
            return [text]

        chunks: List[str] = []
        start = 0

        while start < len(text):
            end = start + chunk_size

            # Try to break at a sentence boundary
            if end < len(text):
                # Look for sentence-ending punctuation near the end
                search_start = max(end - 200, start)
                last_period = text.rfind(". ", search_start, end)
                last_newline = text.rfind("\n", search_start, end)
                break_at = max(last_period, last_newline)
                if break_at > start:
                    end = break_at + 1

            chunk = text[start:end].strip()
            if chunk:
                chunks.append(chunk)

            start = end - overlap

        return chunks

    # ── Database updates ─────────────────────────────────────────────────

    async def _update_status(self, document_id: UUID, status: DocumentStatus) -> None:
        """Update document processing status."""
        try:
            stmt = (
                update(Document)
                .where(Document.id == document_id)
                .values(status=status)
            )
            await self.db.execute(stmt)
            await self.db.flush()
        except Exception as exc:
            logger.error("Failed to update document status: %s", exc)

    async def _update_document(
        self,
        document_id: UUID,
        parsed_json: Dict[str, Any],
        summary: str,
        embedding: List[float],
    ) -> None:
        """Update document with parsed data, summary, and embedding."""
        try:
            stmt = (
                update(Document)
                .where(Document.id == document_id)
                .values(
                    parsed_json=parsed_json,
                    summary=summary,
                    embedding=embedding,
                    status=DocumentStatus.processed,
                    processed_at=datetime.now(timezone.utc),
                )
            )
            await self.db.execute(stmt)
            await self.db.flush()
        except Exception as exc:
            logger.error("Failed to update document record: %s", exc)
            raise

    # ── Action item extraction ───────────────────────────────────────────

    @staticmethod
    def _extract_action_items(summary: str) -> List[str]:
        """Pull action items from the summary text."""
        items: List[str] = []
        action_keywords = [
            "file", "submit", "pay", "verify", "reconcile", "respond",
            "check", "review", "ensure", "deposit", "upload", "report",
        ]
        for line in summary.split("\n"):
            stripped = line.strip().lstrip("-*+ ").strip()
            lower = stripped.lower()
            if any(kw in lower for kw in action_keywords) and len(stripped) > 10:
                items.append(stripped)
        return items
