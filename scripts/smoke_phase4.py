"""Phase 4 smoke test: grounded chatbot + component explainer.

Uses a hashing-embedder fake gateway so retrieval similarity is meaningful
offline (no Qdrant, no API key). Verifies: sync -> in-scope question is grounded
and cited -> out-of-scope question abstains (grounded=false, answer=null, related
lessons) -> component explainer returns a grounded answer -> access control.

Run: .venv/Scripts/python.exe scripts/smoke_phase4.py
"""

import asyncio
import hashlib
import math
import os
import re
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

_tmp = tempfile.mktemp(suffix=".db")
os.environ["DATABASE_URL"] = f"sqlite+aiosqlite:///{_tmp}"
os.environ["STORAGE_PROVIDER"] = "local"
os.environ["LOCAL_STORAGE_PATH"] = tempfile.mkdtemp()
os.environ["VECTOR_BACKEND"] = "memory"

import httpx  # noqa: E402

from app.components.chatbot.vector_store import reset_vector_store  # noqa: E402
from app.gateway.base import Completion  # noqa: E402
from app.gateway.factory import get_gateway  # noqa: E402
from app.main import app  # noqa: E402
from smoke_phase2 import COURSE_JSON, QUALITY_JSON, QUIZ_JSON, make_docx  # noqa: E402

DIM = 384

# Toy embedder ignores stopwords so cosine reflects CONTENT overlap, approximating
# how a real semantic model (MiniLM) treats "capital of France" as unrelated to
# engine cooling. The product uses real embeddings via the gateway.
_STOP = {"the", "of", "is", "a", "an", "to", "what", "does", "do", "at", "why",
         "it", "in", "and", "for", "on", "with", "this", "that"}


def _embed_one(text: str) -> list[float]:
    vec = [0.0] * DIM
    for tok in re.findall(r"[a-z0-9]+", text.lower()):
        if tok in _STOP:
            continue
        h = int(hashlib.md5(tok.encode()).hexdigest(), 16) % DIM
        vec[h] += 1.0
    norm = math.sqrt(sum(v * v for v in vec)) or 1.0
    return [v / norm for v in vec]


class HashGateway:
    """Discriminative embeddings (hashed bag-of-words) + canned generations."""

    embedding_dim = DIM

    async def generate(self, prompt, *, system=None, max_tokens=1024, temperature=0.0, stop=None):
        s = system or ""
        if "curriculum architect" in s:
            return Completion(text=COURSE_JSON)
        if "assessment questions" in s:
            return Completion(text=QUIZ_JSON)
        if "assessment reviewer" in s:
            return Completion(text=QUALITY_JSON)
        if "doubt-clearing assistant" in s:
            # Grounded tutor: answer from the provided material.
            return Completion(text="Based on the course material, the coolant pump circulates "
                                   "fluid to cool the engine and prevent overheating at idle.")
        return Completion(text="{}")

    async def embed(self, texts):
        return [_embed_one(t) for t in texts]

    async def rerank(self, query, passages):
        qv = _embed_one(query)
        return [sum(a * b for a, b in zip(qv, _embed_one(p))) for p in passages]


async def publish_and_sync(c, H) -> dict:
    doc = (await c.post("/api/v1/ingestion/upload", headers=H,
           files={"file": ("veh.docx", make_docx(),
                  "application/vnd.openxmlformats-officedocument.wordprocessingml.document")})).json()
    course = (await c.post(f"/api/v1/course-generation/documents/{doc['id']}/generate",
                           headers=H)).json()
    qs = (await c.get(f"/api/v1/review/courses/{course['id']}/questions", headers=H)).json()
    for q in qs:
        await c.post(f"/api/v1/review/questions/{q['id']}/approve", headers=H)
    await c.post(f"/api/v1/review/courses/{course['id']}/publish", headers=H)
    # Publishing now indexes the course itself, so this explicit sync is a re-check
    # and correctly reports everything as skipped (hashes already match). Assert on
    # the total accounted-for content, which still fails if nothing was indexed.
    stats = (await c.post(f"/api/v1/admin/chatbot/courses/{course['id']}/sync", headers=H)).json()
    assert stats["synced"] + stats["skipped"] >= 2, stats
    return course


async def main() -> None:
    reset_vector_store()
    app.dependency_overrides[get_gateway] = lambda: HashGateway()
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as c:
        async with app.router.lifespan_context(app):
            admin = (await c.post("/api/v1/auth/login",
                     json={"email": "admin@defense-lms.org", "password": "admin12345"})).json()["access_token"]
            AH = {"Authorization": f"Bearer {admin}"}
            course = await publish_and_sync(c, AH)
            course_id = course["id"]
            print("published + synced course", course_id)

            # learner enrols
            await c.post("/api/v1/auth/register",
                         json={"email": "cadet@x.com", "password": "cadet123"})
            lt = (await c.post("/api/v1/auth/login",
                  json={"email": "cadet@x.com", "password": "cadet123"})).json()["access_token"]
            H = {"Authorization": f"Bearer {lt}"}

            # access control: not enrolled -> 403
            r = await c.post("/api/v1/chat", headers=H,
                             json={"course_id": course_id, "question": "what does the coolant pump do?"})
            assert r.status_code == 403, f"expected 403, got {r.status_code}"
            await c.post(f"/api/v1/enrolments/courses/{course_id}", headers=H)
            print("access control (enrol required): ok")

            # in-scope -> grounded + cited
            r = await c.post("/api/v1/chat", headers=H,
                             json={"course_id": course_id, "question": "what does the coolant pump do?"})
            assert r.status_code == 200, r.text
            body = r.json()
            assert body["grounded"] is True, body
            assert body["answer"] and "coolant pump" in body["answer"].lower()
            assert len(body["citations"]) >= 1 and body["citations"][0].get("page"), body["citations"]
            print("in-scope: grounded=True, citations:", body["citations"])
            thread_id = body["thread_id"]

            # follow-up in same thread (multi-turn)
            r = await c.post("/api/v1/chat", headers=H,
                             json={"course_id": course_id, "question": "why does it matter at idle?",
                                   "thread_id": thread_id})
            assert r.json()["thread_id"] == thread_id
            msgs = (await c.get(f"/api/v1/chat/threads/{thread_id}", headers=H)).json()
            assert len(msgs) == 4, msgs  # 2 user + 2 assistant
            print("multi-turn thread: ok (", len(msgs), "messages )")

            # out-of-scope -> abstain
            r = await c.post("/api/v1/chat", headers=H,
                             json={"course_id": course_id, "question": "what is the capital of France?"})
            body = r.json()
            assert body["grounded"] is False and body["answer"] is None, body
            assert len(body["related_lessons"]) >= 1, body
            print("out-of-scope: grounded=False, answer=None, related lessons pointed to")

            # component explainer (3D hotspot) -> grounded
            r = await c.post("/api/v1/chat/explain-component", headers=H,
                             json={"course_id": course_id, "component": "coolant pump"})
            body = r.json()
            assert body["grounded"] is True and body["answer"], body
            print("component explainer: grounded=True")

    app.dependency_overrides.clear()
    print("\nPHASE 4 SMOKE: PASS")


if __name__ == "__main__":
    asyncio.run(main())
