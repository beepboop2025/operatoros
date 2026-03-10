"""
Embedding service — text-embedding-3-small via OpenRouter / OpenAI-compatible API.

Generates 1536-dimensional vectors for documents and queries, with Redis caching
and automatic chunking for long texts.
"""

from __future__ import annotations

import hashlib
import json
import logging
from typing import List, Optional

import httpx
import redis.asyncio as aioredis

from app.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()

# text-embedding-3-small has an ~8191 token limit; approximate as chars
_MAX_CHARS_PER_CHUNK = 24_000  # ~6000 tokens assuming ~4 chars/token
_CHUNK_OVERLAP_CHARS = 400
_EMBEDDING_DIM = 1536
_CACHE_TTL = 3600  # 1 hour


class EmbeddingService:
    """Generate and cache text embeddings."""

    def __init__(self, redis: Optional[aioredis.Redis] = None) -> None:
        self._client: Optional[httpx.AsyncClient] = None
        self._redis = redis

    # ── Lifecycle ────────────────────────────────────────────────────────

    async def _get_client(self) -> httpx.AsyncClient:
        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient(
                base_url=settings.OPENROUTER_BASE_URL,
                headers={
                    "Authorization": f"Bearer {settings.OPENROUTER_API_KEY}",
                    "Content-Type": "application/json",
                },
                timeout=httpx.Timeout(30.0, connect=10.0),
            )
        return self._client

    async def close(self) -> None:
        if self._client and not self._client.is_closed:
            await self._client.aclose()
            self._client = None

    # ── Single embedding ─────────────────────────────────────────────────

    async def generate_embedding(self, text: str) -> List[float]:
        """
        Generate a 1536-dim embedding for *text*.

        For texts exceeding the model token limit, the text is chunked and
        embeddings are mean-pooled.  Results are cached in Redis for 1 hour.
        """
        if not text or not text.strip():
            return [0.0] * _EMBEDDING_DIM

        text = text.strip()

        # Check cache
        cache_key = self._cache_key(text)
        cached = await self._get_cached(cache_key)
        if cached is not None:
            return cached

        # Chunk if necessary
        if len(text) > _MAX_CHARS_PER_CHUNK:
            chunks = self._chunk_text(text, _MAX_CHARS_PER_CHUNK, _CHUNK_OVERLAP_CHARS)
            embeddings = await self._request_embeddings(chunks)
            pooled = self._mean_pool(embeddings)
            await self._set_cached(cache_key, pooled)
            return pooled

        embeddings = await self._request_embeddings([text])
        embedding = embeddings[0]
        await self._set_cached(cache_key, embedding)
        return embedding

    # ── Batch embeddings ─────────────────────────────────────────────────

    async def generate_embeddings_batch(
        self, texts: List[str], batch_size: int = 32
    ) -> List[List[float]]:
        """
        Generate embeddings for multiple texts with batching.

        Texts that are individually too long are chunked and pooled.
        """
        results: List[List[float]] = []

        for i in range(0, len(texts), batch_size):
            batch = texts[i : i + batch_size]
            batch_results: List[List[float]] = []

            # Separate short and long texts
            short_texts: List[str] = []
            short_indices: List[int] = []
            long_texts: List[str] = []
            long_indices: List[int] = []

            for idx, txt in enumerate(batch):
                txt = (txt or "").strip()
                if not txt:
                    batch_results.append([0.0] * _EMBEDDING_DIM)
                    continue
                if len(txt) > _MAX_CHARS_PER_CHUNK:
                    long_indices.append(idx)
                    long_texts.append(txt)
                else:
                    short_indices.append(idx)
                    short_texts.append(txt)

            # Pre-fill batch_results to correct length
            while len(batch_results) < len(batch):
                batch_results.append([0.0] * _EMBEDDING_DIM)

            # Batch-embed short texts
            if short_texts:
                # Check cache for each
                uncached_texts: List[str] = []
                uncached_orig_indices: List[int] = []

                for j, txt in enumerate(short_texts):
                    cache_key = self._cache_key(txt)
                    cached = await self._get_cached(cache_key)
                    if cached is not None:
                        batch_results[short_indices[j]] = cached
                    else:
                        uncached_texts.append(txt)
                        uncached_orig_indices.append(short_indices[j])

                if uncached_texts:
                    embeddings = await self._request_embeddings(uncached_texts)
                    for k, emb in enumerate(embeddings):
                        orig_idx = uncached_orig_indices[k]
                        batch_results[orig_idx] = emb
                        await self._set_cached(self._cache_key(uncached_texts[k]), emb)

            # Handle long texts individually (chunk + pool)
            for j, txt in enumerate(long_texts):
                chunks = self._chunk_text(txt, _MAX_CHARS_PER_CHUNK, _CHUNK_OVERLAP_CHARS)
                embeddings = await self._request_embeddings(chunks)
                pooled = self._mean_pool(embeddings)
                batch_results[long_indices[j]] = pooled
                await self._set_cached(self._cache_key(txt), pooled)

            results.extend(batch_results)

        return results

    # ── HTTP request ─────────────────────────────────────────────────────

    async def _request_embeddings(self, texts: List[str]) -> List[List[float]]:
        """Call the embeddings API endpoint."""
        client = await self._get_client()
        payload = {
            "model": settings.EMBEDDING_MODEL,
            "input": texts,
        }

        try:
            resp = await client.post("/embeddings", json=payload)
            resp.raise_for_status()
            data = resp.json()

            # Sort by index (OpenAI API may return out of order)
            items = sorted(data["data"], key=lambda x: x["index"])
            return [item["embedding"] for item in items]

        except httpx.HTTPStatusError as exc:
            logger.error(
                "Embedding API error %d: %s",
                exc.response.status_code,
                exc.response.text[:500],
            )
            raise RuntimeError(f"Embedding API failed: {exc.response.status_code}") from exc
        except (httpx.ConnectError, httpx.ReadTimeout) as exc:
            logger.error("Embedding API connection error: %s", exc)
            raise RuntimeError(f"Embedding API unreachable: {exc}") from exc

    # ── Caching ──────────────────────────────────────────────────────────

    @staticmethod
    def _cache_key(text: str) -> str:
        digest = hashlib.sha256(text.encode("utf-8")).hexdigest()
        return f"emb:{settings.EMBEDDING_MODEL}:{digest}"

    async def _get_cached(self, key: str) -> Optional[List[float]]:
        if self._redis is None:
            return None
        try:
            raw = await self._redis.get(key)
            if raw:
                return json.loads(raw)
        except Exception as exc:
            logger.warning("Redis cache read error: %s", exc)
        return None

    async def _set_cached(self, key: str, embedding: List[float]) -> None:
        if self._redis is None:
            return
        try:
            await self._redis.set(key, json.dumps(embedding), ex=_CACHE_TTL)
        except Exception as exc:
            logger.warning("Redis cache write error: %s", exc)

    # ── Text chunking ────────────────────────────────────────────────────

    @staticmethod
    def _chunk_text(text: str, chunk_size: int, overlap: int) -> List[str]:
        """Split text into overlapping chunks."""
        chunks: List[str] = []
        start = 0
        while start < len(text):
            end = start + chunk_size
            chunk = text[start:end]
            if chunk.strip():
                chunks.append(chunk.strip())
            start = end - overlap
        return chunks or [text[:chunk_size]]

    # ── Mean pooling ─────────────────────────────────────────────────────

    @staticmethod
    def _mean_pool(embeddings: List[List[float]]) -> List[float]:
        """Average multiple embeddings into one vector."""
        if not embeddings:
            return [0.0] * _EMBEDDING_DIM
        if len(embeddings) == 1:
            return embeddings[0]

        dim = len(embeddings[0])
        pooled = [0.0] * dim
        for emb in embeddings:
            for i in range(dim):
                pooled[i] += emb[i]
        count = len(embeddings)
        return [v / count for v in pooled]
