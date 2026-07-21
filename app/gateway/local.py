"""Local gateway binding (air-gap phase): OpenAI-compatible LLM server
(vLLM / Ollama) + local BGE/E5 embeddings + local reranker.

Stubbed for the POC — the interface is implemented so callers compile and the
factory can select it, but the heavy local wiring lands in the hardening phase
(Phase 7). Selecting MODEL_PROVIDER=local today raises a clear NotImplemented.
"""

from __future__ import annotations

from app.gateway.base import Completion

_EMBED_DIMS = {"BAAI/bge-small-en-v1.5": 384, "BAAI/bge-base-en-v1.5": 768, "intfloat/e5-base-v2": 768}


class LocalGateway:
    def __init__(self, *, base_url: str, model: str, embedding_model: str) -> None:
        self._base_url = base_url
        self._model = model
        self._embedding_model = embedding_model

    @property
    def embedding_dim(self) -> int:
        return _EMBED_DIMS.get(self._embedding_model, 768)

    async def generate(
        self,
        prompt: str,
        *,
        system: str | None = None,
        max_tokens: int = 1024,
        temperature: float = 0.0,
        stop: list[str] | None = None,
    ) -> Completion:
        raise NotImplementedError(
            "LocalGateway (vLLM/Ollama) is implemented in the air-gap hardening phase. "
            "Set MODEL_PROVIDER=cloud for the POC demo."
        )

    async def embed(self, texts: list[str]) -> list[list[float]]:
        raise NotImplementedError("LocalGateway embeddings land in the air-gap hardening phase.")

    async def rerank(self, query: str, passages: list[str]) -> list[float]:
        raise NotImplementedError("LocalGateway rerank lands in the air-gap hardening phase.")
