"""Phase 6 smoke test: 3D model backend (registry, hotspots, association, viewer).

Verifies the 5-model library seeds, an admin associates a model with a lesson,
the viewer payload (glb + hotspots) is enrolment-gated, and a hotspot drives the
grounded component explainer.

Run: .venv/Scripts/python.exe scripts/smoke_phase6.py
"""

import asyncio
import os
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
from app.gateway.factory import get_gateway  # noqa: E402
from app.main import app  # noqa: E402
from smoke_phase4 import HashGateway  # noqa: E402
from smoke_phase2 import make_docx  # noqa: E402


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
    await c.post(f"/api/v1/admin/chatbot/courses/{course['id']}/sync", headers=H)
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

            # library of 5 seeded on startup
            models = (await c.get("/api/v1/models3d", headers=AH)).json()
            keys = {m["model_key"] for m in models}
            assert len(models) == 5 and "engine-cutaway" in keys, keys
            assert all(m["glb_uri"].endswith(".glb") and "local://" in m["glb_uri"] for m in models)
            print("seeded 3D library:", sorted(keys))

            # model detail carries hotspots
            detail = (await c.get("/api/v1/models3d/engine-cutaway", headers=AH)).json()
            assert detail["hotspots"][0]["component"] == "Coolant pump", detail
            print("hotspots: ok (", detail["hotspots"][0]["component"], ")")

            course = await publish_and_sync(c, AH)
            course_id = course["id"]
            lesson = course["modules"][0]["lessons"][0]

            # associate engine-cutaway with the engine lesson
            r = await c.post(f"/api/v1/models3d/lessons/{lesson['id']}/associate",
                             headers=AH, json={"model_key": "engine-cutaway"})
            assert r.status_code == 200 and r.json()["model3d_id"] == "engine-cutaway"
            # unknown key rejected
            r = await c.post(f"/api/v1/models3d/lessons/{lesson['id']}/associate",
                             headers=AH, json={"model_key": "does-not-exist"})
            assert r.status_code == 404
            print("associate model to lesson: ok (bad key rejected)")

            # learner enrols and gets the viewer payload
            await c.post("/api/v1/auth/register", json={"email": "cadet@x.com", "password": "cadet123"})
            lt = (await c.post("/api/v1/auth/login",
                  json={"email": "cadet@x.com", "password": "cadet123"})).json()["access_token"]
            H = {"Authorization": f"Bearer {lt}"}

            # gated before enrol
            r = await c.get(f"/api/v1/models3d/lessons/{lesson['id']}/viewer", headers=H)
            assert r.status_code == 403, r.status_code
            await c.post(f"/api/v1/enrolments/courses/{course_id}", headers=H)

            viewer = (await c.get(f"/api/v1/models3d/lessons/{lesson['id']}/viewer", headers=H)).json()
            assert viewer["model_key"] == "engine-cutaway"
            assert viewer["glb_uri"].endswith("engine-cutaway.glb")
            assert viewer["hotspots"][0]["component"] == "Coolant pump"
            print("viewer payload (enrolment-gated): glb + hotspots ok")

            # hotspot click -> grounded component explainer
            r = await c.post("/api/v1/chat/explain-component", headers=H,
                             json={"course_id": course_id, "lesson_id": lesson["id"],
                                   "component": viewer["hotspots"][0]["component"]})
            body = r.json()
            assert body["grounded"] is True and body["answer"], body
            print("hotspot -> component explainer: grounded=True")

            # learning lesson view reflects has_3d
            lv = (await c.get(f"/api/v1/learning/lessons/{lesson['id']}", headers=H)).json()
            assert lv["has_3d"] is True
            print("lesson view has_3d: True")

    app.dependency_overrides.clear()
    print("\nPHASE 6 SMOKE: PASS")


if __name__ == "__main__":
    asyncio.run(main())
