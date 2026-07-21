"""OpenAI gateway binding: GPT for generation + OpenAI embeddings.

Uses OpenAI for BOTH generation and embeddings, so the whole app runs with just
the ``openai`` package and an API key — no local ML models (PyTorch /
sentence-transformers) required. This is the ONLY module (with cloud.py /
local.py) allowed to import a provider SDK.

Also works with any OpenAI-compatible endpoint (Azure OpenAI, OpenRouter, a
local vLLM/Ollama server) by setting OPENAI_BASE_URL.
"""

from __future__ import annotations

import logging

from app.gateway.base import Completion

logger = logging.getLogger(__name__)

# Output dimensionality per embedding model (drives the Qdrant collection size).
_EMBED_DIMS = {
    "text-embedding-3-small": 1536,
    "text-embedding-3-large": 3072,
    "text-embedding-ada-002": 1536,
}


class OpenAIGateway:
    def __init__(
        self,
        *,
        api_key: str,
        model: str,
        embedding_model: str,
        base_url: str | None = None,
        default_max_tokens: int = 2048,
        default_temperature: float = 0.0,
    ) -> None:
        self._api_key = api_key
        self._model = model
        self._embedding_model = embedding_model
        self._base_url = base_url or None
        self._default_max_tokens = default_max_tokens
        self._default_temperature = default_temperature
        self._client = None  # AsyncOpenAI, lazy

    def _get_client(self):
        if self._client is None:
            from openai import AsyncOpenAI

            self._client = AsyncOpenAI(api_key=self._api_key, base_url=self._base_url)
        return self._client

    # ── generation ────────────────────────────────────────────────────────────
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
        messages = []
        if system:
            messages.append({"role": "system", "content": system})
        messages.append({"role": "user", "content": prompt})
        resp = await client.chat.completions.create(
            model=self._model,
            messages=messages,
            max_tokens=max_tokens or self._default_max_tokens,
            temperature=temperature,
            stop=stop or None,
        )
        text = resp.choices[0].message.content or ""
        usage = resp.usage
        return Completion(
            text=text,
            model=self._model,
            input_tokens=getattr(usage, "prompt_tokens", 0) if usage else 0,
            output_tokens=getattr(usage, "completion_tokens", 0) if usage else 0,
        )

    # ── embeddings ──────────────────────────────────────────────────────────────
    @property
    def embedding_dim(self) -> int:
        return _EMBED_DIMS.get(self._embedding_model, 1536)

    async def embed(self, texts: list[str]) -> list[list[float]]:
        if not texts:
            return []
        client = self._get_client()
        resp = await client.embeddings.create(model=self._embedding_model, input=texts)
        # API returns items in input order, but sort by index defensively.
        ordered = sorted(resp.data, key=lambda d: d.index)
        return [d.embedding for d in ordered]

    # ── rerank ──────────────────────────────────────────────────────────────────
    async def rerank(self, query: str, passages: list[str]) -> list[float]:
        if not passages:
            return []
        vectors = await self.embed([query, *passages])
        q = vectors[0]
        return [sum(a * b for a, b in zip(q, p, strict=True)) for p in vectors[1:]]
