"""
RAG (Retrieval-Augmented Generation) pipeline — the intelligence core of OperatorOS.

Handles query classification, vector search, context assembly, and structured
response generation for Indian tax/compliance questions.
"""

from __future__ import annotations

import logging
import re
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from uuid import UUID

from sqlalchemy import text as sql_text
from sqlalchemy.ext.asyncio import AsyncSession

from app.services.embedding import EmbeddingService
from app.services.openrouter import OpenRouterClient

logger = logging.getLogger(__name__)

# ── System prompts per query type ────────────────────────────────────────────

_BASE_PERSONA = (
    "You are AuditMind, an expert AI assistant for Indian Chartered Accountants. "
    "You specialise in Indian income tax (Income Tax Act, 1961), GST (CGST/SGST/IGST Acts), "
    "company law (Companies Act, 2013), and professional compliance. "
    "You work inside OperatorOS, a practice management platform for CA firms.\n\n"
    "RULES:\n"
    "1. ALWAYS cite specific sections, rules, circulars, or notifications (e.g., Section 80C, "
    "Rule 12, Circular No. 3/2024).\n"
    "2. When provisions were recently amended (Finance Act 2024/2025), explicitly flag the change "
    "and its effective date.\n"
    "3. Be CONSERVATIVE in interpretation — when in doubt, adopt the interpretation that favours "
    "compliance and reduces risk for the assessee.\n"
    "4. Never invent case law citations. If you are unsure of a specific case, say so.\n"
    "5. Suggest concrete action items with deadlines where applicable.\n"
    "6. If the question involves numbers, show step-by-step computation working.\n"
    "7. Structure your answer with clear headings and bullet points.\n"
)

_QUERY_PROMPTS: Dict[str, str] = {
    "factual": (
        _BASE_PERSONA
        + "This is a FACTUAL question — the user wants a clear, definitive answer about tax law, "
        "rates, due dates, or provisions. Be precise and cite the exact section/rule.\n"
    ),
    "computation": (
        _BASE_PERSONA
        + "This is a COMPUTATION question — the user needs you to calculate tax, interest, penalty, "
        "or another financial figure. Show every step of working, state the applicable rates, "
        "and present the final answer clearly. Use tables where helpful.\n"
    ),
    "advisory": (
        _BASE_PERSONA
        + "This is an ADVISORY question — the user is seeking professional guidance on a tax "
        "planning, structuring, or compliance matter. Present multiple options where relevant, "
        "weigh pros and cons, highlight risks, and give a clear recommendation. "
        "Flag any anti-avoidance provisions (GAAR, SAAR) that may apply.\n"
    ),
    "procedural": (
        _BASE_PERSONA
        + "This is a PROCEDURAL question — the user wants to know the process, forms, portals, "
        "or steps to complete a compliance task. Give a numbered step-by-step guide with the "
        "relevant form numbers, portal URLs, and timelines.\n"
    ),
}

# ── Similarity threshold and limits ──────────────────────────────────────────

_SIMILARITY_THRESHOLD = 0.7
_MAX_CONTEXT_DOCS = 5
_MAX_CONTEXT_CHARS = 12_000


class RAGService:
    """End-to-end retrieval-augmented generation for tax queries."""

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

    async def answer_query(
        self,
        question: str,
        client_id: Optional[UUID] = None,
        context: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Full RAG pipeline:
          1. Classify query type
          2. Generate question embedding
          3. Vector-search relevant documents
          4. Build context
          5. Call LLM
          6. Parse response (citations, action items)
          7. Return structured result
        """
        start = datetime.now(timezone.utc)

        # Step 1: Classify query
        query_type = await self._classify_query(question)
        logger.info("Query classified as: %s", query_type)

        # Step 2: Generate embedding for the question
        question_embedding = await self.embedding.generate_embedding(question)

        # Step 3: Vector search
        relevant_docs = await self._vector_search(
            question_embedding, client_id=client_id
        )
        logger.info("Retrieved %d relevant documents", len(relevant_docs))

        # Step 4: Build context
        assembled_context = self._build_context(relevant_docs, extra_context=context)

        # Step 5: Build messages
        system_prompt = self.build_system_prompt(query_type)
        messages = [
            {"role": "system", "content": system_prompt},
        ]

        if assembled_context:
            messages.append({
                "role": "system",
                "content": (
                    "RELEVANT CONTEXT FROM CLIENT DOCUMENTS AND KNOWLEDGE BASE:\n"
                    "---\n"
                    f"{assembled_context}\n"
                    "---\n"
                    "Use the above context to ground your answer. Cite document names "
                    "when referencing specific information from client documents."
                ),
            })

        messages.append({"role": "user", "content": question})

        # Step 6: Call LLM with task-appropriate model
        model = self.llm.select_model(query_type)
        llm_result = await self.llm.chat_completion(
            messages=messages,
            model=model,
            temperature=0.2 if query_type == "computation" else 0.3,
            max_tokens=4096,
        )

        # Step 7: Parse response
        response_text = llm_result["text"]
        citations = self._extract_citations(response_text)
        action_items = self._extract_action_items(response_text)

        # Build sources list from retrieved docs
        sources = [
            {
                "document_id": str(doc["id"]),
                "filename": doc["filename"],
                "similarity": round(doc["similarity"], 4),
                "excerpt": doc["excerpt"][:300],
            }
            for doc in relevant_docs
        ]

        elapsed_ms = (datetime.now(timezone.utc) - start).total_seconds() * 1000

        return {
            "response": response_text,
            "query_type": query_type,
            "model_used": llm_result["model"],
            "tokens_used": llm_result["tokens"]["total"],
            "latency_ms": round(elapsed_ms, 2),
            "sources": sources,
            "citations": citations,
            "action_items": action_items,
            "cost_usd": llm_result["cost_usd"],
        }

    # ── System prompt builder ────────────────────────────────────────────

    def build_system_prompt(self, query_type: str) -> str:
        """Return the specialised system prompt for *query_type*."""
        return _QUERY_PROMPTS.get(query_type, _QUERY_PROMPTS["factual"])

    # ── Query classification ─────────────────────────────────────────────

    async def _classify_query(self, question: str) -> str:
        """Classify the question into factual / computation / advisory / procedural."""
        categories = ["factual", "computation", "advisory", "procedural"]
        return await self.llm.quick_classify(question, categories)

    # ── Vector search ────────────────────────────────────────────────────

    async def _vector_search(
        self,
        query_embedding: List[float],
        client_id: Optional[UUID] = None,
    ) -> List[Dict[str, Any]]:
        """
        Search the documents table for semantically similar content.

        Uses pgvector's cosine distance operator ``<=>``.
        """
        embedding_str = "[" + ",".join(str(v) for v in query_embedding) + "]"

        if client_id is not None:
            query = sql_text("""
                SELECT
                    id,
                    original_filename,
                    summary,
                    doc_type,
                    1 - (embedding <=> :embedding ::vector) AS similarity
                FROM documents
                WHERE embedding IS NOT NULL
                  AND client_id = :client_id
                  AND 1 - (embedding <=> :embedding ::vector) > :threshold
                ORDER BY similarity DESC
                LIMIT :limit
            """)
            params = {
                "embedding": embedding_str,
                "client_id": str(client_id),
                "threshold": _SIMILARITY_THRESHOLD,
                "limit": _MAX_CONTEXT_DOCS,
            }
        else:
            query = sql_text("""
                SELECT
                    id,
                    original_filename,
                    summary,
                    doc_type,
                    1 - (embedding <=> :embedding ::vector) AS similarity
                FROM documents
                WHERE embedding IS NOT NULL
                  AND 1 - (embedding <=> :embedding ::vector) > :threshold
                ORDER BY similarity DESC
                LIMIT :limit
            """)
            params = {
                "embedding": embedding_str,
                "threshold": _SIMILARITY_THRESHOLD,
                "limit": _MAX_CONTEXT_DOCS,
            }

        try:
            result = await self.db.execute(query, params)
            rows = result.fetchall()
        except Exception as exc:
            logger.error("Vector search failed: %s", exc)
            return []

        return [
            {
                "id": row.id,
                "filename": row.original_filename,
                "summary": row.summary or "",
                "doc_type": row.doc_type,
                "similarity": float(row.similarity),
                "excerpt": (row.summary or "")[:500],
            }
            for row in rows
        ]

    # ── Context assembly ─────────────────────────────────────────────────

    @staticmethod
    def _build_context(
        docs: List[Dict[str, Any]],
        extra_context: Optional[str] = None,
    ) -> str:
        """Combine retrieved documents and optional extra context into a prompt block."""
        parts: List[str] = []

        if extra_context:
            parts.append(f"USER-PROVIDED CONTEXT:\n{extra_context}\n")

        for i, doc in enumerate(docs, 1):
            parts.append(
                f"[Document {i}: {doc['filename']} (type: {doc['doc_type']}, "
                f"relevance: {doc['similarity']:.2f})]\n"
                f"{doc['excerpt']}\n"
            )

        combined = "\n".join(parts)
        # Truncate if too long
        if len(combined) > _MAX_CONTEXT_CHARS:
            combined = combined[:_MAX_CONTEXT_CHARS] + "\n... [context truncated]"

        return combined

    # ── Response parsing ─────────────────────────────────────────────────

    @staticmethod
    def _extract_citations(text: str) -> List[str]:
        """
        Extract legal citations from the LLM response.

        Matches patterns like:
          - Section 80C
          - Section 143(1)
          - Rule 12
          - Circular No. 3/2024
          - Notification No. 18/2024
          - CGST Act
          - Finance Act 2024
        """
        patterns = [
            r"Section\s+\d+[A-Z]*(?:\(\d+\))?(?:\([a-z]+\))?",
            r"Rule\s+\d+[A-Z]*(?:\(\d+\))?",
            r"Circular\s+No\.\s*\d+/\d{4}",
            r"Notification\s+No\.\s*\d+/\d{4}",
            r"(?:CGST|SGST|IGST|UTGST)\s+(?:Act|Rules?)",
            r"Finance\s+Act[,\s]+\d{4}",
            r"Companies\s+Act[,\s]+\d{4}",
            r"Income\s+Tax\s+Act[,\s]+\d{4}",
        ]
        citations: List[str] = []
        seen: set = set()
        for pattern in patterns:
            for match in re.finditer(pattern, text, re.IGNORECASE):
                citation = match.group(0).strip()
                normalised = citation.lower()
                if normalised not in seen:
                    seen.add(normalised)
                    citations.append(citation)
        return citations

    @staticmethod
    def _extract_action_items(text: str) -> List[str]:
        """
        Extract action items from the LLM response.

        Looks for bullet points under headers containing 'action', 'next steps',
        'to-do', 'deadline', or numbered items with action verbs.
        """
        items: List[str] = []

        # Look for lines starting with action verbs after "Action" headers
        action_section = False
        for line in text.split("\n"):
            stripped = line.strip()
            lower = stripped.lower()

            # Detect action-item section headers
            if any(
                kw in lower
                for kw in ["action item", "next step", "to-do", "todo", "recommended action"]
            ):
                action_section = True
                continue

            # Detect other section headers (end of action section)
            if action_section and stripped.startswith("#"):
                action_section = False
                continue

            # Collect bullet/numbered items in action sections
            if action_section and stripped and (
                stripped.startswith(("-", "*", "+"))
                or re.match(r"^\d+[\.\)]\s", stripped)
            ):
                # Clean the bullet/number prefix
                cleaned = re.sub(r"^[-*+]\s*|^\d+[\.\)]\s*", "", stripped).strip()
                if cleaned:
                    items.append(cleaned)

        # Also look for standalone deadline mentions
        deadline_pattern = r"(?:deadline|due date|must be filed by|file before)\s*[:\-]?\s*(.+)"
        for match in re.finditer(deadline_pattern, text, re.IGNORECASE):
            deadline_text = match.group(0).strip()
            if deadline_text not in items:
                items.append(deadline_text)

        return items
