"""
Communication drafting service — generate professional letters, advisories,
notice responses, and engagement letters using LLM.
"""

from __future__ import annotations

import logging
from typing import List

from app.services.openrouter import OpenRouterClient

logger = logging.getLogger(__name__)

# ── System prompts ───────────────────────────────────────────────────────────

_ADVISORY_SYSTEM = (
    "You are a senior Chartered Accountant at a reputable Indian CA firm. "
    "Draft a professional advisory letter for a client. "
    "The letter should:\n"
    "1. Have a clear subject line\n"
    "2. Open with context and purpose\n"
    "3. Present the analysis with citations to relevant sections of law\n"
    "4. Clearly state the recommendation\n"
    "5. Include any caveats or assumptions\n"
    "6. List action items with deadlines\n"
    "7. Close professionally\n\n"
    "Tone: Professional, clear, and authoritative. Avoid jargon where simpler language works. "
    "Always cite specific sections, rules, or circulars when making legal statements."
)

_NOTICE_RESPONSE_SYSTEM = (
    "You are a senior Chartered Accountant drafting a formal reply to a tax/GST notice "
    "on behalf of a client. The response must:\n\n"
    "1. Be addressed to the correct authority with proper references\n"
    "2. Quote the notice reference, DIN, PAN, and assessment year\n"
    "3. Address each issue point-by-point in the order raised\n"
    "4. Cite specific sections, rules, CBDT circulars, and relevant case laws\n"
    "5. Attach a list of supporting documents being submitted\n"
    "6. Include a prayer clause requesting disposal/dropping of proceedings\n"
    "7. Request a personal hearing opportunity\n"
    "8. End with 'Yours faithfully' and placeholder for CA signature\n\n"
    "Tone: Respectful but firm. Do NOT concede any point that can be legitimately contested. "
    "Be conservative in admissions."
)

_ENGAGEMENT_LETTER_SYSTEM = (
    "You are drafting a standard engagement letter for a Chartered Accountant's practice in India. "
    "The letter must follow ICAI guidelines and include:\n\n"
    "1. Date and client details\n"
    "2. Scope of engagement — services to be provided\n"
    "3. Responsibilities of the CA firm\n"
    "4. Responsibilities of the client (providing information, access, etc.)\n"
    "5. Fee structure and payment terms\n"
    "6. Timeline and deliverables\n"
    "7. Confidentiality clause\n"
    "8. Limitation of liability clause\n"
    "9. Termination provisions\n"
    "10. Governing law (Indian law)\n"
    "11. Signature blocks for both parties\n\n"
    "Use professional, legally sound language. Follow the format prescribed by "
    "ICAI Standard on Quality Control (SQC) 1."
)

_EMAIL_SYSTEM = (
    "You are a Chartered Accountant drafting a professional email. "
    "Keep it concise, professional, and action-oriented. "
    "Include a clear subject line, greeting, body, and closing. "
    "If there are deadlines or action items, highlight them clearly."
)


class CommunicationDrafter:
    """Draft professional communications for CA practice management."""

    def __init__(self, openrouter: OpenRouterClient) -> None:
        self.llm = openrouter

    # ── Advisory letter ──────────────────────────────────────────────────

    async def draft_advisory(
        self, topic: str, client_name: str, details: str
    ) -> str:
        """
        Draft a professional advisory letter.

        Parameters
        ----------
        topic : str
            The advisory topic (e.g., "Section 80C tax planning for FY 2025-26").
        client_name : str
            Name of the client/firm being advised.
        details : str
            Specific details, facts, or queries from the client.
        """
        messages = [
            {"role": "system", "content": _ADVISORY_SYSTEM},
            {
                "role": "user",
                "content": (
                    f"Draft an advisory letter for the following:\n\n"
                    f"CLIENT: {client_name}\n"
                    f"TOPIC: {topic}\n"
                    f"DETAILS/FACTS:\n{details}\n\n"
                    "Generate a complete advisory letter with proper formatting, "
                    "legal citations, and actionable recommendations."
                ),
            },
        ]

        result = await self.llm.chat_completion(
            messages=messages,
            model=self.llm.select_model("advisory"),
            temperature=0.3,
            max_tokens=4096,
        )

        logger.info(
            "Advisory drafted for '%s' — %d tokens", topic, result["tokens"]["total"]
        )
        return result["text"].strip()

    # ── Notice response ──────────────────────────────────────────────────

    async def draft_notice_response(
        self,
        notice_summary: str,
        client_details: str,
        legal_position: str,
    ) -> str:
        """
        Draft a formal response to a tax/GST notice.

        Parameters
        ----------
        notice_summary : str
            Summary of the notice including type, section, issues, and deadline.
        client_details : str
            Client PAN, name, assessment year, and relevant facts.
        legal_position : str
            The legal position/arguments to be made in the response.
        """
        messages = [
            {"role": "system", "content": _NOTICE_RESPONSE_SYSTEM},
            {
                "role": "user",
                "content": (
                    f"NOTICE SUMMARY:\n{notice_summary}\n\n"
                    f"CLIENT DETAILS:\n{client_details}\n\n"
                    f"OUR LEGAL POSITION:\n{legal_position}\n\n"
                    "Draft a complete formal response letter addressing all issues raised "
                    "in the notice. Include proper legal citations and supporting arguments."
                ),
            },
        ]

        result = await self.llm.chat_completion(
            messages=messages,
            model=self.llm.select_model("drafting"),
            temperature=0.3,
            max_tokens=4096,
        )

        logger.info("Notice response drafted — %d tokens", result["tokens"]["total"])
        return result["text"].strip()

    # ── Engagement letter ────────────────────────────────────────────────

    async def draft_engagement_letter(
        self,
        client_name: str,
        services: List[str],
        fees: str,
    ) -> str:
        """
        Draft a standard engagement letter.

        Parameters
        ----------
        client_name : str
            Name of the client/firm being engaged.
        services : list[str]
            List of services to be provided (e.g., ["ITR filing", "Tax audit", "GST return"]).
        fees : str
            Fee description (e.g., "INR 50,000 plus GST, payable in two instalments").
        """
        services_text = "\n".join(f"  - {svc}" for svc in services)

        messages = [
            {"role": "system", "content": _ENGAGEMENT_LETTER_SYSTEM},
            {
                "role": "user",
                "content": (
                    f"Draft an engagement letter for:\n\n"
                    f"CLIENT: {client_name}\n"
                    f"SERVICES:\n{services_text}\n"
                    f"FEES: {fees}\n\n"
                    "Generate a complete engagement letter following ICAI guidelines. "
                    "Include all standard clauses."
                ),
            },
        ]

        result = await self.llm.chat_completion(
            messages=messages,
            model=self.llm.select_model("drafting"),
            temperature=0.2,
            max_tokens=4096,
        )

        logger.info(
            "Engagement letter drafted for '%s' — %d tokens",
            client_name,
            result["tokens"]["total"],
        )
        return result["text"].strip()

    # ── Email drafting ───────────────────────────────────────────────────

    async def draft_email(
        self,
        recipient: str,
        purpose: str,
        details: str,
        tone: str = "professional",
    ) -> str:
        """
        Draft a professional email.

        Parameters
        ----------
        recipient : str
            Who the email is for (e.g., "client", "tax officer", "colleague").
        purpose : str
            Purpose of the email.
        details : str
            Key details to include.
        tone : str
            Tone of the email (professional, formal, friendly).
        """
        messages = [
            {"role": "system", "content": _EMAIL_SYSTEM},
            {
                "role": "user",
                "content": (
                    f"Draft an email with the following:\n\n"
                    f"TO: {recipient}\n"
                    f"PURPOSE: {purpose}\n"
                    f"DETAILS: {details}\n"
                    f"TONE: {tone}\n\n"
                    "Include a subject line, greeting, body, and closing."
                ),
            },
        ]

        result = await self.llm.chat_completion(
            messages=messages,
            model=self.llm.select_model("drafting"),
            temperature=0.4,
            max_tokens=2048,
        )

        return result["text"].strip()

    # ── Client circular ──────────────────────────────────────────────────

    async def draft_client_circular(
        self,
        topic: str,
        key_changes: str,
        effective_date: str,
    ) -> str:
        """
        Draft a circular to clients about regulatory changes.

        Useful for Finance Act amendments, new CBDT circulars, GST rate changes, etc.
        """
        messages = [
            {
                "role": "system",
                "content": (
                    "You are a CA firm partner drafting a circular to all clients about "
                    "an important regulatory change. The circular should:\n"
                    "1. Have a clear title and date\n"
                    "2. Explain WHAT changed in plain language\n"
                    "3. Explain WHO is affected\n"
                    "4. Explain WHAT action clients need to take\n"
                    "5. Include the effective date prominently\n"
                    "6. Cite the specific notification/circular/section\n"
                    "7. Offer the firm's assistance\n"
                    "Keep it concise (under 500 words) and easy to understand."
                ),
            },
            {
                "role": "user",
                "content": (
                    f"TOPIC: {topic}\n"
                    f"KEY CHANGES: {key_changes}\n"
                    f"EFFECTIVE DATE: {effective_date}\n\n"
                    "Draft a client circular about this change."
                ),
            },
        ]

        result = await self.llm.chat_completion(
            messages=messages,
            model=self.llm.select_model("drafting"),
            temperature=0.3,
            max_tokens=2048,
        )

        return result["text"].strip()
