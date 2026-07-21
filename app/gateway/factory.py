"""Gateway factory + process-wide singleton.

``build_gateway(settings)`` is the single switch: MODEL_PROVIDER=cloud|local.
The application obtains its gateway exclusively through ``get_gateway`` (FastAPI
dependency) so provider selection stays config-only.
"""

from __future__ import annotations

from functools import lru_cache

from app.core.config import settings
from app.gateway.base import ModelGateway


def build_gateway(cfg=settings) -> ModelGateway:
    provider = (cfg.MODEL_PROVIDER or "cloud").lower()
    if provider == "cloud":
        from app.gateway.cloud import CloudGateway

        return CloudGateway(
            anthropic_api_key=cfg.CLAUDE_API_KEY,
            claude_model=cfg.CLAUDE_MODEL,
            embedding_model=cfg.EMBEDDING_MODEL,
            default_max_tokens=cfg.GATEWAY_MAX_TOKENS,
            default_temperature=cfg.GATEWAY_TEMPERATURE,
        )
    if provider == "openai":
        from app.gateway.openai_provider import OpenAIGateway

        return OpenAIGateway(
            api_key=cfg.OPENAI_API_KEY,
            model=cfg.OPENAI_MODEL,
            embedding_model=cfg.OPENAI_EMBEDDING_MODEL,
            base_url=cfg.OPENAI_BASE_URL or None,
            default_max_tokens=cfg.GATEWAY_MAX_TOKENS,
            default_temperature=cfg.GATEWAY_TEMPERATURE,
        )
    if provider == "local":
        from app.gateway.local import LocalGateway

        return LocalGateway(
            base_url=cfg.LOCAL_LLM_BASE_URL,
            model=cfg.LOCAL_LLM_MODEL,
            embedding_model=cfg.EMBEDDING_MODEL,
        )
    raise ValueError(
        f"Unknown MODEL_PROVIDER: {cfg.MODEL_PROVIDER!r} (expected 'cloud', 'openai' or 'local')"
    )


@lru_cache(maxsize=1)
def get_gateway() -> ModelGateway:
    """FastAPI dependency: process-wide gateway singleton."""
    return build_gateway(settings)
