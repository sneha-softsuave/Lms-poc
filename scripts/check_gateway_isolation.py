"""Gateway isolation gate (PRD 4.9).

Fails if any module OUTSIDE app/gateway/ imports a provider SDK directly. This
is what makes cloud<->local a config change, not a code change. Wire into CI.

Run: .venv/Scripts/python.exe scripts/check_gateway_isolation.py
"""

import pathlib
import re
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
APP = ROOT / "app"
GATEWAY = APP / "gateway"

# Provider SDKs that only the gateway may import.
FORBIDDEN = re.compile(r"^\s*(?:import|from)\s+(anthropic|openai|sentence_transformers)\b", re.M)

violations: list[str] = []
for path in APP.rglob("*.py"):
    if GATEWAY in path.parents:
        continue
    text = path.read_text(encoding="utf-8")
    for m in FORBIDDEN.finditer(text):
        line_no = text[: m.start()].count("\n") + 1
        violations.append(f"{path.relative_to(ROOT)}:{line_no}: {m.group(0).strip()}")

if violations:
    print("GATEWAY ISOLATION VIOLATIONS (move these behind app/gateway/):")
    for v in violations:
        print("  -", v)
    sys.exit(1)

print("gateway isolation: PASS (no provider SDK imports outside app/gateway/)")
