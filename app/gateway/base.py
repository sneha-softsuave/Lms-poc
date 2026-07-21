"""Gateway interface (PRD 4.9).

    class ModelGateway(Protocol):
        def generate(...) -> Completion
        def embed(texts) -> list[list[float]]
        def rerank(query, passages) -> list[float]

Every AI capability in the app — course generation, chatbot answers, component
explanations, quiz generation, embeddings, reranking — goes through this one
interface. Provider binding is configuration only (see factory.build_gateway).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol, runtime_checkable


@dataclass
class Completion:
    """Result of a text generation call."""

    text: str
    model: str = ""
    input_tokens: int = 0
    output_tokens: int = 0


@runtime_checkable
class ModelGateway(Protocol):
    """The single interface the application uses for all model operations."""

    @property
    def embedding_dim(self) -> int:
        """Dimensionality of vectors returned by ``embed`` (drives Qdrant collection size)."""
        ...

    async def generate(
        self,
        prompt: str,
        *,
        system: str | None = None,
        max_tokens: int = 1024,
        temperature: float = 0.0,
        stop: list[str] | None = None,
    ) -> Completion: ...

    async def embed(self, texts: list[str]) -> list[list[float]]: ...

    async def rerank(self, query: str, passages: list[str]) -> list[float]: ...
