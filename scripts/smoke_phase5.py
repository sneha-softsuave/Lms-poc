"""Phase 5 smoke test: quiz take + auto-grade, analytics, audit.

Publishes a course (FakeGateway), enrols a learner, takes the module quiz
(answering correctly), checks auto-grade + pass, then verifies admin analytics
(cohort progress, subject mastery, weakest topics) and the immutable audit log.

Run: .venv/Scripts/python.exe scripts/smoke_phase5.py
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

import httpx  # noqa: E402

from app.gateway.factory import get_gateway  # noqa: E402
from app.main import app  # noqa: E402
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
            module_id = course["modules"][0]["id"]

            # learner enrols
            await c.post("/api/v1/auth/register", json={"email": "cadet@x.com", "password": "cadet123"})
            lt = (await c.post("/api/v1/auth/login",
                  json={"email": "cadet@x.com", "password": "cadet123"})).json()["access_token"]
            H = {"Authorization": f"Bearer {lt}"}
            await c.post(f"/api/v1/enrolments/courses/{course_id}", headers=H)

            # fetch quiz (approved questions, no answers exposed)
            quiz = (await c.get(f"/api/v1/quiz/modules/{module_id}", headers=H)).json()
            assert len(quiz["questions"]) == 2, quiz
            assert "correct_answer" not in quiz["questions"][0], "must not leak answers"
            print("quiz delivered:", len(quiz["questions"]), "approved questions, answers hidden")

            # answer correctly (from the canned quiz: mcq 'Cools the engine', tf 'true')
            answers = {str(quiz["questions"][0]["id"]): "Cools the engine",
                       str(quiz["questions"][1]["id"]): "true"}
            res = (await c.post(f"/api/v1/quiz/modules/{module_id}/submit",
                                headers=H, json={"answers": answers})).json()
            assert res["score_pct"] == 100 and res["passed"] is True, res
            assert res["results"][0]["rationale"], "feedback should include rationale"
            print("quiz auto-grade:", res["score_pct"], "% passed=", res["passed"])

            # answer one wrong -> 50%
            wrong = {str(quiz["questions"][0]["id"]): "Ignites fuel",
                     str(quiz["questions"][1]["id"]): "true"}
            res2 = (await c.post(f"/api/v1/quiz/modules/{module_id}/submit",
                                 headers=H, json={"answers": wrong})).json()
            assert res2["score_pct"] == 50 and res2["passed"] is False, res2
            print("wrong answer graded: 50% fail")

            # analytics (admin)
            cohort = (await c.get("/api/v1/admin/analytics/cohort-progress", headers=AH)).json()
            assert cohort and cohort[0]["enrolled"] == 1, cohort
            mastery = (await c.get("/api/v1/admin/analytics/subject-mastery", headers=AH)).json()
            assert mastery and mastery[0]["subject_title"] == "Vehicle Mechanics", mastery
            weakest = (await c.get("/api/v1/admin/analytics/weakest-topics", headers=AH)).json()
            assert weakest and weakest[0]["module_title"] == "Powerpack", weakest
            print("analytics: cohort/mastery/weakest ok; avg score",
                  mastery[0]["avg_score_pct"], "%")

            # audit log populated + append-only (admin read)
            audit = (await c.get("/api/v1/admin/audit", headers=AH)).json()
            actions = {e["action"] for e in audit}
            assert {"course.publish", "enrolment.create", "quiz.submit"} <= actions, actions
            print("audit events:", sorted(actions))

            # learner cannot read audit / analytics
            r = await c.get("/api/v1/admin/audit", headers=H)
            assert r.status_code == 403
            print("rbac: learner blocked from audit")

    app.dependency_overrides.clear()
    print("\nPHASE 5 SMOKE: PASS")


if __name__ == "__main__":
    asyncio.run(main())
