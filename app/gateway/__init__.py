"""Model Gateway — the ONLY place the app talks to AI providers (PRD 4.9).

Import the gateway via ``get_gateway()`` / ``build_gateway()``. No other module
may import ``anthropic``, ``openai`` or ``sentence_transformers`` directly — a CI
grep gate enforces this so cloud↔local is a config change, never a code change.
"""

from app.gateway.base import Completion, ModelGateway
from app.gateway.factory import build_gateway, get_gateway

__all__ = ["Completion", "ModelGateway", "build_gateway", "get_gateway"]
