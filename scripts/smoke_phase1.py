"""Phase 1 smoke test: model gateway + content ingestion with provenance.

Run: .venv/Scripts/python.exe scripts/smoke_phase1.py
Builds real DOCX/PPTX/TXT in memory, uploads them through the admin endpoint,
and asserts segments carry page/section provenance. Uses SQLite + local storage.
"""

import asyncio
import io
import os
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

_tmp = tempfile.mktemp(suffix=".db")
os.environ["DATABASE_URL"] = f"sqlite+aiosqlite:///{_tmp}"
os.environ["STORAGE_PROVIDER"] = "local"
os.environ["LOCAL_STORAGE_PATH"] = tempfile.mkdtemp()
os.environ["MODEL_PROVIDER"] = "cloud"  # pin provider so conformance check is deterministic

import httpx  # noqa: E402

from app.gateway import build_gateway  # noqa: E402
from app.gateway.base import ModelGateway  # noqa: E402
from app.main import app  # noqa: E402


def make_docx() -> bytes:
    import docx

    d = docx.Document()
    d.add_heading("Engine Overview", level=1)
    d.add_paragraph("The powerpack is the vehicle's engine assembly.")
    d.add_heading("Cooling System", level=1)
    d.add_paragraph("The coolant pump circulates fluid to prevent overheating at idle.")
    buf = io.BytesIO()
    d.save(buf)
    return buf.getvalue()


def make_pptx() -> bytes:
    from pptx import Presentation
    from pptx.util import Inches

    prs = Presentation()
    slide = prs.slides.add_slide(prs.slide_layouts[1])
    slide.shapes.title.text = "Field Radio Controls"
    slide.placeholders[1].text = "The transceiver has a squelch knob and a PTT switch."
    buf = io.BytesIO()
    prs.save(buf)
    return buf.getvalue()


async def main() -> None:
    # ── gateway conformance (no network) ────────────────────────────────────────
    gw = build_gateway()
    assert isinstance(gw, ModelGateway), "gateway must satisfy the ModelGateway protocol"
    assert gw.embedding_dim == 384
    print("gateway conformance: ok (", type(gw).__name__, "dim", gw.embedding_dim, ")")

    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as c:
        async with app.router.lifespan_context(app):
            # login as bootstrap admin
            r = await c.post(
                "/api/v1/auth/login",
                json={"email": "admin@defense-lms.org", "password": "admin12345"},
            )
            token = r.json()["access_token"]
            H = {"Authorization": f"Bearer {token}"}

            # upload DOCX → expect section provenance
            r = await c.post(
                "/api/v1/ingestion/upload",
                headers=H,
                files={"file": ("veh.docx", make_docx(),
                                "application/vnd.openxmlformats-officedocument.wordprocessingml.document")},
            )
            assert r.status_code == 201, r.text
            docx_doc = r.json()
            sections = {s["section"] for s in docx_doc["segments"] if s["section"]}
            assert "Cooling System" in sections, sections
            assert docx_doc["doc_code"].startswith("VEH"), docx_doc["doc_code"]
            print("docx ingest:", docx_doc["method"], docx_doc["char_count"], "chars; sections:", sections)

            # upload PPTX → expect per-slide page numbers
            r = await c.post(
                "/api/v1/ingestion/upload",
                headers=H,
                files={"file": ("radio.pptx", make_pptx(),
                                "application/vnd.openxmlformats-officedocument.presentationml.presentation")},
            )
            assert r.status_code == 201, r.text
            pptx_doc = r.json()
            assert any(s["page"] == 1 for s in pptx_doc["segments"]), pptx_doc["segments"]
            assert "squelch" in pptx_doc["segments"][0]["text"], pptx_doc["segments"][0]["text"]
            print("pptx ingest:", pptx_doc["method"], "slides-to-pages ok")

            # upload TXT
            r = await c.post(
                "/api/v1/ingestion/upload",
                headers=H,
                files={"file": ("notes.txt", b"First-line checks on the utility vehicle.", "text/plain")},
            )
            assert r.status_code == 201, r.text
            print("txt ingest: ok")

            # list + detail
            r = await c.get("/api/v1/ingestion", headers=H)
            assert r.status_code == 200 and len(r.json()) == 3, r.text

            # RBAC: learner cannot upload
            await c.post("/api/v1/auth/register",
                         json={"email": "l@x.com", "password": "learner123"})
            lr = (await c.post("/api/v1/auth/login",
                               json={"email": "l@x.com", "password": "learner123"})).json()["access_token"]
            r = await c.post(
                "/api/v1/ingestion/upload",
                headers={"Authorization": f"Bearer {lr}"},
                files={"file": ("x.txt", b"hi", "text/plain")},
            )
            assert r.status_code == 403, f"expected 403, got {r.status_code}"
            print("rbac learner upload blocked: ok")

    print("\nPHASE 1 SMOKE: PASS")


if __name__ == "__main__":
    asyncio.run(main())
