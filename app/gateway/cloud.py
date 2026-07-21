"""Cloud gateway binding: Anthropic (Claude) for generation, local
sentence-transformers (MiniLM) for embeddings.

Clients are lazy-loaded so importing this module never requires the heavy deps
until an AI call is actually made — keeps import-time light for tests and tools.
This is the ONLY module (with local.py) allowed to import the provider SDKs.
"""

from __future__ import annotations

import asyncio
import logging

from app.gateway.base import Completion

logger = logging.getLogger(__name__)

# Known embedding dimensions by model (avoids loading the model just to ask).
_EMBED_DIMS = {"all-MiniLM-L6-v2": 384, "all-mpnet-base-v2": 768}


class CloudGateway:
    def __init__(
        self,
        *,
        anthropic_api_key: str,
        claude_model: str,
        embedding_model: str,
        default_max_tokens: int = 2048,
        default_temperature: float = 0.0,
    ) -> None:
        self._api_key = anthropic_api_key
        self._model = claude_model
        self._embedding_model_name = embedding_model
        self._default_max_tokens = default_max_tokens
        self._default_temperature = default_temperature
        self._client = None  # AsyncAnthropic, lazy
        self._embedder = None  # SentenceTransformer, lazy

    # ── generation ────────────────────────────────────────────────────────────
    def _get_client(self):
        if self._client is None:
            from anthropic import AsyncAnthropic

            self._client = AsyncAnthropic(api_key=self._api_key)
        return self._client

    async def generate(
        self,
        prompt: str,
        *,
        system: str | None = None,
        max_tokens: int = 1024,
        temperature: float = 0.0,
        stop: list[str] | None = None,
    ) -> Completion:
        client = self._get_client()
        kwargs: dict = {
            "model": self._model,
            "max_tokens": max_tokens or self._default_max_tokens,
            "temperature": temperature,
            "messages": [{"role": "user", "content": prompt}],
        }
        if system:
            kwargs["system"] = system
        if stop:
            kwargs["stop_sequences"] = stop
        resp = await client.messages.create(**kwargs)
        text = "".join(block.text for block in resp.content if getattr(block, "type", "") == "text")
        return Completion(
            text=text,
            model=self._model,
            input_tokens=getattr(resp.usage, "input_tokens", 0),
            output_tokens=getattr(resp.usage, "output_tokens", 0),
        )

    # ── embeddings ──────────────────────────────────────────────────────────────
    @property
    def embedding_dim(self) -> int:
        return _EMBED_DIMS.get(self._embedding_model_name, 384)

    def _get_embedder(self):
        if self._embedder is None:
            from sentence_transformers import SentenceTransformer

            logger.info("Loading embedding model %s", self._embedding_model_name)
            self._embedder = SentenceTransformer(self._embedding_model_name)
        return self._embedder

    async def embed(self, texts: list[str]) -> list[list[float]]:
        embedder = self._get_embedder()
        # SentenceTransformer.encode is CPU-bound/sync — run off the event loop.
        vectors = await asyncio.to_thread(
            embedder.encode, texts, normalize_embeddings=True, show_progress_bar=False
        )
        return [v.tolist() for v in vectors]

    # ── rerank ──────────────────────────────────────────────────────────────────
    async def rerank(self, query: str, passages: list[str]) -> list[float]:
        """Cosine similarity of query vs each passage using the embedding model.

        A dedicated cross-encoder reranker can drop in here later (local phase)
        without changing callers, since they only depend on the gateway interface.
        """
        if not passages:
            return []
        vectors = await self.embed([query, *passages])
        q = vectors[0]
        scores = []
        for p in vectors[1:]:
            scores.append(sum(a * b for a, b in zip(q, p, strict=True)))
        return scores
