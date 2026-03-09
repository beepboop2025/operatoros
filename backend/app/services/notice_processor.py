"""
Notice processing service — classify, extract, summarise, and draft responses
for Indian income-tax and GST notices.
"""

from __future__ import annotations

import json
import logging
import re
from datetime import date, datetime, timezone
from typing import Any, Dict, List, Optional
from uuid import UUID

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.notice import Notice, NoticeStatus
from app.services.openrouter import OpenRouterClient

logger = logging.getLogger(__name__)

# ── Urgency matrix (days until deadline -> urgency) ──────────────────────────

_URGENCY_MAP = {
    "critical": 0,   # deadline passed or today
    "high": 3,        # <= 3 days
    "medium": 10,     # <= 10 days
    "low": 999,       # > 10 days
}

# ── Notice classification prompt ─────────────────────────────────────────────

_CLASSIFY_PROMPT = (
    "You are an expert on Indian income tax and GST notices. "
    "Classify this notice into one of the following types:\n"
    "- intimation_143_1 (Section 143(1) intimation)\n"
    "- scrutiny_143_2 (Section 143(2) scrutiny)\n"
    "- reassessment_148 (Section 148/148A reassessment)\n"
    "- demand (demand notice)\n"
    "- rectification_154 (Section 154 rectification)\n"
    "- penalty (penalty proceedings)\n"
    "- gst_asmt10 (GST ASMT-10)\n"
    "- gst_drc01 (GST DRC-01)\n"
    "- gst_drc07 (GST DRC-07)\n"
    "- other\n\n"
    "Respond with ONLY the type code, nothing else."
)

# ── Notice extraction prompt ─────────────────────────────────────────────────

_EXTRACT_PROMPT = (
    "You are an expert Indian tax notice analyst. Extract the following from this notice. "
    "Return a JSON object with:\n"
    "- notice_type: type of notice\n"
    "- section: the section under which notice is issued (e.g., '143(1)', '148')\n"
    "- demand_amount: total demand in INR (number or null)\n"
    "- tax_demand: tax portion of demand (number or null)\n"
    "- interest_demand: interest portion (number or null)\n"
    "- penalty_demand: penalty portion (number or null)\n"
    "- assessment_year: AY mentioned (e.g., '2023-24')\n"
    "- financial_year: FY mentioned (e.g., '2022-23')\n"
    "- period: period covered\n"
    "- deadline: response deadline in YYYY-MM-DD format (or null)\n"
    "- sections_cited: list of all sections, rules, circulars cited\n"
    "- issues_raised: list of specific issues/discrepancies\n"
    "- officer_details: {name, designation, jurisdiction}\n"
    "- pan: PAN mentioned\n"
    "- din: DIN (Document Identification Number) if present\n"
    "Return ONLY valid JSON."
)

# ── Summary prompt ───────────────────────────────────────────────────────────

_SUMMARY_PROMPT = (
    "You are a tax notice analyst for Indian CA firms. "
    "Summarise this notice in 4-6 bullet points covering:\n"
    "1. Type and section of the notice\n"
    "2. Key demand/issue amount\n"
    "3. Period/Assessment Year\n"
    "4. Specific issues raised\n"
    "5. Response deadline and consequences of non-response\n"
    "6. Recommended immediate actions\n"
    "Be concise and professional."
)

# ── Response drafting prompt ─────────────────────────────────────────────────

_RESPONSE_PROMPT = (
    "You are a senior Indian Chartered Accountant drafting a formal response to a tax notice. "
    "Draft a COMPLETE reply letter in the following format:\n\n"
    "1. Start with 'To, The [Officer Designation], [Jurisdiction]'\n"
    "2. Include 'Subject: Reply to Notice u/s [Section] dated [Date]'\n"
    "3. Include 'Ref: PAN - [PAN], AY - [AY], DIN - [DIN if available]'\n"
    "4. Address each issue raised in the notice point by point\n"
    "5. Cite relevant sections, rules, case laws, and circulars\n"
    "6. Maintain a respectful but firm professional tone\n"
    "7. Request for personal hearing if applicable\n"
    "8. End with 'Yours faithfully,\\n[Placeholder for CA Signature]\\n"
    "[CA Name]\\nMembership No. [XXXXX]'\n\n"
    "IMPORTANT: Be conservative — do not concede any point that can be legitimately contested. "
    "Cite specific sections and provisions for every argument. "
    "Include prayer clause requesting dropping of proceedings if the response addresses all issues."
)


class NoticeProcessor:
    """Process and respond to income-tax and GST notices."""

    def __init__(
        self,
        db: AsyncSession,
        openrouter: OpenRouterClient,
    ) -> None:
        self.db = db
        self.llm = openrouter

    # ── Main processing ──────────────────────────────────────────────────

    async def process_notice(
        self,
        notice_id: UUID,
        document_text: str,
        notice_type: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Full notice processing pipeline:
          1. Classify notice type (if not provided)
          2. Extract structured data (demand, sections, deadline)
          3. Generate summary
          4. Assess urgency
          5. Return structured result with recommended timeline
        """
        if not document_text or not document_text.strip():
            return {"error": "No text provided for notice processing."}

        # Step 1: Classify
        if not notice_type:
            notice_type = await self._classify_notice(document_text)
        logger.info("Notice %s classified as: %s", notice_id, notice_type)

        # Step 2: Extract structured data
        extracted = await self._extract_notice_data(document_text)

        # Step 3: Generate summary
        summary = await self._generate_summary(document_text)

        # Step 4: Assess urgency
        deadline_str = extracted.get("deadline")
        urgency = self._assess_urgency(deadline_str)
        response_timeline = self._recommended_timeline(urgency, notice_type)

        # Step 5: Update notice in DB
        await self._update_notice(
            notice_id,
            notice_type=notice_type,
            summary=summary,
            extracted=extracted,
        )

        return {
            "notice_id": str(notice_id),
            "notice_type": notice_type,
            "summary": summary,
            "extracted_data": extracted,
            "urgency": urgency,
            "response_timeline": response_timeline,
            "demand_amount": extracted.get("demand_amount"),
            "deadline": deadline_str,
            "sections_cited": extracted.get("sections_cited", []),
            "issues_raised": extracted.get("issues_raised", []),
        }

    # ── Response drafting ────────────────────────────────────────────────

    async def generate_response_draft(
        self,
        notice_id: UUID,
        client_context: str,
    ) -> str:
        """
        Draft a formal response letter for a notice.

        Parameters
        ----------
        notice_id : UUID
            The notice to respond to (fetches summary from DB).
        client_context : str
            Additional context about the client's position, documents, and facts.
        """
        # Fetch notice
        result = await self.db.execute(select(Notice).where(Notice.id == notice_id))
        notice = result.scalar_one_or_none()
        if notice is None:
            raise ValueError(f"Notice {notice_id} not found")

        notice_summary = notice.summary or "No summary available"

        messages = [
            {"role": "system", "content": _RESPONSE_PROMPT},
            {
                "role": "user",
                "content": (
                    f"NOTICE SUMMARY:\n{notice_summary}\n\n"
                    f"NOTICE TYPE: {notice.notice_type.value}\n"
                    f"RESPONSE DEADLINE: {notice.response_deadline}\n\n"
                    f"CLIENT CONTEXT AND POSITION:\n{client_context}\n\n"
                    "Draft a complete reply to this notice addressing all issues."
                ),
            },
        ]

        result = await self.llm.chat_completion(
            messages=messages,
            model=self.llm.select_model("drafting"),
            temperature=0.3,
            max_tokens=4096,
        )

        draft = result["text"].strip()

        # Save draft to DB
        try:
            stmt = (
                update(Notice)
                .where(Notice.id == notice_id)
                .values(
                    response_draft=draft,
                    status=NoticeStatus.response_drafted,
                )
            )
            await self.db.execute(stmt)
            await self.db.flush()
        except Exception as exc:
            logger.error("Failed to save notice response draft: %s", exc)

        return draft

    # ── Classification ───────────────────────────────────────────────────

    async def _classify_notice(self, text: str) -> str:
        """Classify the notice type using LLM."""
        text_chunk = text[:3000]
        messages = [
            {"role": "system", "content": _CLASSIFY_PROMPT},
            {"role": "user", "content": text_chunk},
        ]

        try:
            result = await self.llm.chat_completion(
                messages=messages,
                model=self.llm.select_model("classification"),
                temperature=0.0,
                max_tokens=32,
            )
            raw = result["text"].strip().lower().replace(" ", "_")
            # Validate against known types
            valid_types = {
                "intimation_143_1", "scrutiny_143_2", "reassessment_148",
                "demand", "rectification_154", "penalty",
                "gst_asmt10", "gst_drc01", "gst_drc07", "other",
            }
            if raw in valid_types:
                return raw
            # Fuzzy match
            for vt in valid_types:
                if vt in raw or raw in vt:
                    return vt
            return "other"
        except Exception as exc:
            logger.warning("Notice classification failed: %s", exc)
            return "other"

    # ── Data extraction ──────────────────────────────────────────────────

    async def _extract_notice_data(self, text: str) -> Dict[str, Any]:
        """Extract structured data from notice text."""
        text_chunk = text[:5000]
        messages = [
            {"role": "system", "content": _EXTRACT_PROMPT},
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
            raw_json = re.sub(r"^```(?:json)?\s*", "", raw_json)
            raw_json = re.sub(r"\s*```$", "", raw_json)
            return json.loads(raw_json)
        except (json.JSONDecodeError, Exception) as exc:
            logger.warning("Notice data extraction failed: %s", exc)
            return {"parse_error": str(exc), "raw_preview": text[:500]}

    # ── Summary ──────────────────────────────────────────────────────────

    async def _generate_summary(self, text: str) -> str:
        """Generate a concise notice summary."""
        text_chunk = text[:4000]
        messages = [
            {"role": "system", "content": _SUMMARY_PROMPT},
            {"role": "user", "content": text_chunk},
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
            logger.error("Notice summary generation failed: %s", exc)
            return text[:500]

    # ── Urgency assessment ───────────────────────────────────────────────

    @staticmethod
    def _assess_urgency(deadline_str: Optional[str]) -> str:
        """Determine urgency level from the deadline date."""
        if not deadline_str:
            return "medium"

        try:
            deadline = date.fromisoformat(deadline_str)
        except (ValueError, TypeError):
            return "medium"

        days_remaining = (deadline - date.today()).days

        if days_remaining <= 0:
            return "critical"
        elif days_remaining <= 3:
            return "high"
        elif days_remaining <= 10:
            return "medium"
        else:
            return "low"

    @staticmethod
    def _recommended_timeline(urgency: str, notice_type: str) -> Dict[str, str]:
        """Provide recommended action timeline based on urgency and notice type."""
        timelines = {
            "critical": {
                "immediate": "File adjournment request if deadline has passed",
                "within_24h": "Gather all supporting documents",
                "within_48h": "Draft and review response",
                "note": "Consider applying for condonation of delay u/s 119(2)(b) if deadline is missed",
            },
            "high": {
                "immediate": "Acknowledge notice and assign to team member",
                "within_24h": "Review notice and identify key issues",
                "within_48h": "Gather supporting documents",
                "within_72h": "Draft response for review",
                "note": "Prioritise this notice — deadline is very close",
            },
            "medium": {
                "within_24h": "Acknowledge and assign",
                "within_3_days": "Detailed analysis of issues raised",
                "within_5_days": "Gather documents and draft response",
                "within_7_days": "Internal review and filing",
                "note": "Standard processing timeline",
            },
            "low": {
                "within_48h": "Acknowledge and schedule for processing",
                "within_1_week": "Detailed analysis",
                "within_2_weeks": "Draft response",
                "before_deadline": "Final review and filing",
                "note": "Comfortable timeline — ensure it does not slip through the cracks",
            },
        }

        timeline = timelines.get(urgency, timelines["medium"])

        # Add notice-specific guidance
        if "scrutiny" in notice_type or "143_2" in notice_type:
            timeline["special"] = (
                "Scrutiny assessment — consider engaging senior counsel. "
                "Ensure all books of account and documents are in order."
            )
        elif "148" in notice_type:
            timeline["special"] = (
                "Reassessment proceedings — verify if notice is time-barred. "
                "Check if mandatory conditions of Section 148A are met."
            )
        elif "penalty" in notice_type:
            timeline["special"] = (
                "Penalty proceedings — check if reasonable cause u/s 273B can be established. "
                "Review if penalty is mandatory or discretionary."
            )

        return timeline

    # ── DB update ────────────────────────────────────────────────────────

    async def _update_notice(
        self,
        notice_id: UUID,
        notice_type: str,
        summary: str,
        extracted: Dict[str, Any],
    ) -> None:
        """Update the notice record with processing results."""
        try:
            values: Dict[str, Any] = {
                "summary": summary,
                "status": NoticeStatus.under_review,
            }

            # Update response_deadline if extracted
            deadline_str = extracted.get("deadline")
            if deadline_str:
                try:
                    values["response_deadline"] = date.fromisoformat(deadline_str)
                except (ValueError, TypeError):
                    pass

            stmt = update(Notice).where(Notice.id == notice_id).values(**values)
            await self.db.execute(stmt)
            await self.db.flush()

        except Exception as exc:
            logger.error("Failed to update notice %s: %s", notice_id, exc)
