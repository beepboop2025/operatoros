"""
OpenRouter API client — unified gateway to LLM providers.

Handles model routing, retries with exponential backoff, token counting,
cost tracking, and structured response parsing.
"""

from __future__ import annotations

import asyncio
import logging
import time
from typing import Any, Dict, List, Optional

import httpx

from app.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()

# ── Model routing table ─────────────────────────────────────────────────────

_MODEL_ROUTING: Dict[str, str] = {
    "factual": "anthropic/claude-haiku-4-5-20251001",
    "advisory": "anthropic/claude-sonnet-4-20250514",
    "computation": "anthropic/claude-sonnet-4-20250514",
    "drafting": "anthropic/claude-sonnet-4-20250514",
    "summarization": "anthropic/claude-sonnet-4-20250514",
    "bulk": "anthropic/claude-haiku-4-5-20251001",
    "classification": "anthropic/claude-haiku-4-5-20251001",
}

# ── Approximate cost per 1M tokens (input/output) ──────────────────────────

_COST_PER_MILLION: Dict[str, Dict[str, float]] = {
    "anthropic/claude-haiku-4-5-20251001": {"input": 1.00, "output": 5.00},
    "anthropic/claude-sonnet-4-20250514": {"input": 3.00, "output": 15.00},
}

MAX_RETRIES = 3
BASE_BACKOFF = 1.0  # seconds


class OpenRouterClient:
    """Async client for the OpenRouter chat-completions API."""

    def __init__(self) -> None:
        self._client: Optional[httpx.AsyncClient] = None
        self._total_tokens_used: int = 0
        self._total_cost_usd: float = 0.0

    # ── Lifecycle ────────────────────────────────────────────────────────

    async def _get_client(self) -> httpx.AsyncClient:
        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient(
                base_url=settings.OPENROUTER_BASE_URL,
                headers={
                    "Authorization": f"Bearer {settings.OPENROUTER_API_KEY}",
                    "Content-Type": "application/json",
                    "HTTP-Referer": "https://operatoros.app",
                    "X-Title": "OperatorOS",
                },
                timeout=httpx.Timeout(60.0, connect=10.0),
            )
        return self._client

    async def close(self) -> None:
        if self._client and not self._client.is_closed:
            await self._client.aclose()
            self._client = None

    # ── Model selection ──────────────────────────────────────────────────

    @staticmethod
    def select_model(task_type: str) -> str:
        """
        Pick the best model for *task_type*.

        Falls back to ``settings.DEFAULT_LLM_MODEL`` for unknown types.
        """
        return _MODEL_ROUTING.get(task_type, settings.DEFAULT_LLM_MODEL)

    # ── Chat completion ──────────────────────────────────────────────────

    async def chat_completion(
        self,
        messages: List[Dict[str, str]],
        model: Optional[str] = None,
        temperature: float = 0.3,
        max_tokens: int = 4096,
    ) -> Dict[str, Any]:
        """
        Send a chat-completion request to OpenRouter with retry logic.

        Returns
        -------
        dict with keys:
            text       – the assistant's response content
            model      – actual model used
            tokens     – dict of prompt/completion/total token counts
            latency_ms – round-trip time in milliseconds
            cost_usd   – estimated cost of this call
        """
        resolved_model = model or settings.DEFAULT_LLM_MODEL
        payload = {
            "model": resolved_model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
        }

        last_error: Optional[Exception] = None

        for attempt in range(1, MAX_RETRIES + 1):
            try:
                client = await self._get_client()
                start = time.monotonic()
                resp = await client.post("/chat/completions", json=payload)
                latency_ms = (time.monotonic() - start) * 1000

                if resp.status_code == 429:
                    retry_after = float(resp.headers.get("Retry-After", BASE_BACKOFF * attempt))
                    logger.warning(
                        "OpenRouter rate-limited (attempt %d/%d), backing off %.1fs",
                        attempt, MAX_RETRIES, retry_after,
                    )
                    await asyncio.sleep(retry_after)
                    continue

                resp.raise_for_status()
                data = resp.json()

                # Parse response
                choice = data["choices"][0]
                text = choice["message"]["content"]
                usage = data.get("usage", {})
                prompt_tokens = usage.get("prompt_tokens", 0)
                completion_tokens = usage.get("completion_tokens", 0)
                total_tokens = usage.get("total_tokens", prompt_tokens + completion_tokens)
                actual_model = data.get("model", resolved_model)

                # Track cost
                cost_usd = self._estimate_cost(actual_model, prompt_tokens, completion_tokens)
                self._total_tokens_used += total_tokens
                self._total_cost_usd += cost_usd

                logger.info(
                    "OpenRouter call: model=%s tokens=%d latency=%.0fms cost=$%.4f",
                    actual_model, total_tokens, latency_ms, cost_usd,
                )

                return {
                    "text": text,
                    "model": actual_model,
                    "tokens": {
                        "prompt": prompt_tokens,
                        "completion": completion_tokens,
                        "total": total_tokens,
                    },
                    "latency_ms": round(latency_ms, 2),
                    "cost_usd": round(cost_usd, 6),
                }

            except httpx.HTTPStatusError as exc:
                last_error = exc
                if exc.response.status_code >= 500:
                    wait = BASE_BACKOFF * (2 ** (attempt - 1))
                    logger.warning(
                        "OpenRouter server error %d (attempt %d/%d), retrying in %.1fs",
                        exc.response.status_code, attempt, MAX_RETRIES, wait,
                    )
                    await asyncio.sleep(wait)
                    continue
                # Client errors (4xx except 429) are not retried
                logger.error("OpenRouter client error: %s", exc)
                raise

            except (httpx.ConnectError, httpx.ReadTimeout) as exc:
                last_error = exc
                wait = BASE_BACKOFF * (2 ** (attempt - 1))
                logger.warning(
                    "OpenRouter connection error (attempt %d/%d): %s — retrying in %.1fs",
                    attempt, MAX_RETRIES, exc, wait,
                )
                await asyncio.sleep(wait)

        raise RuntimeError(
            f"OpenRouter request failed after {MAX_RETRIES} attempts: {last_error}"
        )

    # ── Quick helpers ────────────────────────────────────────────────────

    async def quick_classify(self, text: str, categories: List[str]) -> str:
        """
        Use a fast, cheap model to classify *text* into one of *categories*.
        """
        cat_list = ", ".join(categories)
        messages = [
            {
                "role": "system",
                "content": (
                    f"You are a classifier. Respond with EXACTLY one of these categories: {cat_list}. "
                    "No explanation, no punctuation, just the category."
                ),
            },
            {"role": "user", "content": text},
        ]
        result = await self.chat_completion(
            messages=messages,
            model=self.select_model("classification"),
            temperature=0.0,
            max_tokens=32,
        )
        raw = result["text"].strip().lower()
        # Fuzzy match against categories
        for cat in categories:
            if cat.lower() in raw:
                return cat
        return categories[0]  # fallback to first category

    # ── Internal helpers ─────────────────────────────────────────────────

    @staticmethod
    def _estimate_cost(model: str, prompt_tokens: int, completion_tokens: int) -> float:
        rates = _COST_PER_MILLION.get(model)
        if rates is None:
            # Default to Sonnet pricing for unknown models
            rates = {"input": 3.0, "output": 15.0}
        input_cost = (prompt_tokens / 1_000_000) * rates["input"]
        output_cost = (completion_tokens / 1_000_000) * rates["output"]
        return input_cost + output_cost

    # ── Stats ────────────────────────────────────────────────────────────

    @property
    def total_tokens_used(self) -> int:
        return self._total_tokens_used

    @property
    def total_cost_usd(self) -> float:
        return round(self._total_cost_usd, 6)
