"""Phase 3 smoke test: catalog, enrolment, delivery, progress/resume.

Builds on Phases 1-2 (FakeGateway) to publish a course, then drives the learner
loop: browse catalog -> enrol -> view lesson -> complete lessons -> assert
progress % and resume point advance, ending at 100% completion.

Run: .venv/Scripts/python.exe scripts/smoke_phase3.py
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

import httpx  # noqa: E402

from app.gateway.factory import get_gateway  # noqa: E402
from app.main import app  # noqa: E402

# Reuse the FakeGateway + docx helper from the phase 2 smoke.
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from smoke_phase2 import FakeGateway, make_docx  # noqa: E402


async def publish_course(c, H) -> dict:
    doc = (await c.post("/api/v1/ingestion/upload", headers=H,
           files={"file": ("veh.docx", make_docx(),
                  "application/vnd.openxmlformats-officedocument.wordprocessingml.document")})).json()
    course = (await c.post(f"/api/v1/course-generation/documents/{doc['id']}/generate",
                           headers=H)).json()
    qs = (await c.get(f"/api/v1/review/courses/{course['id']}/questions", headers=H)).json()
    for q in qs:
        await c.post(f"/api/v1/review/questions/{q['id']}/approve", headers=H)
    await c.post(f"/api/v1/review/courses/{course['id']}/publish", headers=H)
    return course


async def main() -> None:
    app.dependency_overrides[get_gateway] = lambda: FakeGateway()
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as c:
        async with app.router.lifespan_context(app):
            admin = (await c.post("/api/v1/auth/login",
                     json={"email": "admin@defense-lms.org", "password": "admin12345"})).json()["access_token"]
            AH = {"Authorization": f"Bearer {admin}"}
            course = await publish_course(c, AH)
            course_id = course["id"]
            print("published course id", course_id)

            # learner
            await c.post("/api/v1/auth/register",
                         json={"email": "cadet@x.com", "password": "cadet123", "full_name": "Cadet"})
            lt = (await c.post("/api/v1/auth/login",
                  json={"email": "cadet@x.com", "password": "cadet123"})).json()["access_token"]
            H = {"Authorization": f"Bearer {lt}"}

            # catalog grouped by subject
            cat = (await c.get("/api/v1/catalog/subjects", headers=H)).json()
            assert len(cat) == 1 and cat[0]["subject_title"] == "Vehicle Mechanics", cat
            assert cat[0]["courses"][0]["id"] == course_id
            print("catalog by subject: ok")

            # cannot view lesson before enrolling
            lessons = [l for m in course["modules"] for l in m["lessons"]]
            r = await c.get(f"/api/v1/learning/lessons/{lessons[0]['id']}", headers=H)
            assert r.status_code == 403, f"expected 403, got {r.status_code}"

            # enrol
            r = await c.post(f"/api/v1/enrolments/courses/{course_id}", headers=H)
            assert r.status_code == 201 and r.json()["progress_pct"] == 0
            assert r.json()["resume_lesson_id"] == lessons[0]["id"]
            print("enrol: ok, progress 0, resume=first lesson")

            # dashboard shows it
            dash = (await c.get("/api/v1/enrolments/me", headers=H)).json()
            assert dash[0]["course_title"].startswith("Vehicle Mechanics")

            # view + complete first lesson
            r = await c.get(f"/api/v1/learning/lessons/{lessons[0]['id']}", headers=H)
            assert r.status_code == 200 and r.json()["has_3d"] is False
            r = await c.post(f"/api/v1/learning/lessons/{lessons[0]['id']}/complete", headers=H)
            pct1 = r.json()["progress_pct"]
            assert pct1 == 50, pct1  # 1 of 2 lessons
            assert r.json()["resume_lesson_id"] == lessons[1]["id"]
            print("complete lesson 1: progress", pct1, "resume advanced")

            # idempotent re-complete does not exceed
            r = await c.post(f"/api/v1/learning/lessons/{lessons[0]['id']}/complete", headers=H)
            assert r.json()["progress_pct"] == 50

            # complete last lesson -> 100% + completed
            r = await c.post(f"/api/v1/learning/lessons/{lessons[1]['id']}/complete", headers=H)
            assert r.json()["progress_pct"] == 100, r.json()
            assert r.json()["status"] == "completed"
            assert r.json()["completed_at"] is not None
            assert r.json()["resume_lesson_id"] is None
            print("complete lesson 2: progress 100, course completed")

    app.dependency_overrides.clear()
    print("\nPHASE 3 SMOKE: PASS")


if __name__ == "__main__":
    asyncio.run(main())
