"""Seed a ready-to-demo published course (no AI calls, instant, free).

Inserts a fully-published course with modules, lessons (with provenance), a
glossary, an approved quiz bank, a 3D model attached to a lesson, and a demo
learner account — so the UI has real content the moment you open it. Themed to
the sample military-studies material.

Also does a best-effort vector sync so the chatbot works (needs a working
gateway / API key; skipped gracefully if unavailable).

Run (server stopped): .venv/Scripts/python.exe scripts/seed_demo.py
Then start the server and log in.
"""

import asyncio
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import select  # noqa: E402

from app.components.auth.db_models import ROLE_LEARNER, User  # noqa: E402
from app.components.content.db_models import (  # noqa: E402
    REVIEW_APPROVED,
    STATUS_PUBLISHED,
    Course,
    GlossaryTerm,
    Lesson,
    Module,
    Question,
    Quiz,
    Subject,
)
from app.components.models3d.seed import seed_models  # noqa: E402
from app.core.security import hash_password  # noqa: E402
from app.database import Base, async_session, engine  # noqa: E402

# Import all component tables so create_all() below builds the full schema
# (enrolments, chatbot kb_content, quiz, audit, certificates, models3d).
from app.components.auth import db_models as _m_auth  # noqa: E402,F401
from app.components.ingestion import db_models as _m_ing  # noqa: E402,F401
from app.components.enrolment import db_models as _m_enr  # noqa: E402,F401
from app.components.chatbot import db_models as _m_chat  # noqa: E402,F401
from app.components.quiz import db_models as _m_quiz  # noqa: E402,F401
from app.components.audit import db_models as _m_audit  # noqa: E402,F401
from app.components.certificates import db_models as _m_cert  # noqa: E402,F401
from app.components.models3d import db_models as _m_3d  # noqa: E402,F401

DOC = "MIL-STUDIES-01"


def ref(section, page):
    return {"doc": DOC, "section": section, "page": page}


async def main() -> None:
    # Ensure tables exist + 3D library seeded.
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async with async_session() as db:
        await seed_models(db)

        # Demo learner (matches the login screen's "Use learner" button).
        existing = (await db.execute(select(User).where(User.email == "cadet@defense-lms.org"))).scalar_one_or_none()
        if not existing:
            db.add(User(email="cadet@defense-lms.org", full_name="Cadet Rao",
                        hashed_password=hash_password("cadet12345"), role=ROLE_LEARNER))

        # Skip if already seeded.
        if (await db.execute(select(Subject).where(Subject.title == "Indian Armed Forces — Weapons & Equipment"))).scalar_one_or_none():
            await db.commit()
            print("Demo course already present — nothing to do.")
            return

        subject = Subject(
            title="Indian Armed Forces — Weapons & Equipment",
            description="Roles, small arms and support weapons of the Indian Army.",
        )
        course = Course(
            subject=subject,
            title="Weapons & War Equipment — Fundamentals",
            description="Introduction to the roles of the armed forces and their infantry weapons.",
            objectives=["Describe the role of the infantry",
                        "Identify standard-issue small arms and support weapons",
                        "State the effective range and role of each weapon"],
            status=STATUS_PUBLISHED,
            version=1,
        )

        # Module 1 — Role of the armed forces
        m1 = Module(title="Role of the Armed Forces", order_index=0)
        m1.lessons.append(Lesson(order_index=0, title="Role of the infantry",
            body="The infantry is the primary arm of the Indian Army, tasked with closing in on the "
                 "enemy to physically assault and capture ground, and to man and defend the borders.",
            source_ref=ref("Role of the Armed Forces", 2)))
        m1.lessons.append(Lesson(order_index=1, title="Terrain and readiness",
            body="India maintains a well-equipped force ready to operate across all terrain — from the "
                 "icy heights of Siachen to the deserts of Rajasthan and the forests of the North East.",
            source_ref=ref("Role and Equipment", 1)))

        # Module 2 — Small arms & support weapons (gets the 3D rifle model)
        m2 = Module(title="Small Arms & Support Weapons", order_index=1)
        rifle_lesson = Lesson(order_index=0, title="Assault rifles",
            body="The AK-203 is a new assault rifle being introduced into the army. Assault rifles are "
                 "the standard individual weapon of the infantry soldier.",
            source_ref=ref("Small Arms", 3), model3d_id="rifle-trainer")
        m2.lessons.append(rifle_lesson)
        m2.lessons.append(Lesson(order_index=1, title="Light Machine Gun",
            body="The 5.56mm Light Machine Gun fires effectively up to 700m. It is automatic with a higher "
                 "rate of fire than an assault rifle, useful for breaking an enemy's final charge.",
            source_ref=ref("Small Arms", 3)))

        course.modules.extend([m1, m2])
        course.glossary.extend([
            GlossaryTerm(term="Infantry", definition="The arm of close combat that assaults and captures ground.", source_ref=ref("Role", 2)),
            GlossaryTerm(term="LMG", definition="Light Machine Gun — automatic support weapon effective to ~700m.", source_ref=ref("Small Arms", 3)),
            GlossaryTerm(term="AK-203", definition="New assault rifle being introduced into the Indian Army.", source_ref=ref("Small Arms", 3)),
        ])
        db.add(subject)
        db.add(course)
        await db.flush()

        # Approved quiz banks per module.
        def q(module_id, qtype, stem, options, correct, rationale, difficulty, page):
            return Question(module_id=module_id, qtype=qtype, stem=stem, options=options,
                            correct_answer=correct, rationale=rationale, difficulty=difficulty,
                            review_status=REVIEW_APPROVED, quality_score=88, source_ref=ref("Small Arms", page))

        db.add(Quiz(module_id=m1.id, title="Role of the Armed Forces — Quiz"))
        db.add(q(m1.id, "mcq", "What is the primary task of the infantry?",
                 ["Close with and capture ground", "Operate radar", "Fly aircraft", "Command ships"],
                 "Close with and capture ground", "The infantry closes in to assault and capture ground.", "basic", 2))
        db.add(q(m1.id, "tf", "The infantry defends the national borders.",
                 ["true", "false"], "true", "Stated in the material.", "basic", 2))

        db.add(Quiz(module_id=m2.id, title="Small Arms & Support Weapons — Quiz"))
        db.add(q(m2.id, "mcq", "What is the effective range of the 5.56mm LMG?",
                 ["300m", "500m", "700m", "1000m"], "700m", "The LMG fires effectively up to 700m.", "intermediate", 3))
        db.add(q(m2.id, "mcq", "Which assault rifle is being introduced into the army?",
                 ["AK-203", "INSAS", "M16", "SLR"], "AK-203", "The AK-203 is the new assault rifle.", "basic", 3))

        await db.commit()
        course_id = course.id
        print(f"Seeded published course #{course_id}: {course.title}")

    # Best-effort chatbot indexing (needs a working gateway / API key).
    try:
        from app.components.chatbot.sync_service import SyncService
        from app.gateway import get_gateway

        async with async_session() as db:
            stats = await SyncService.sync_course(course_id, get_gateway(), db)
        print(f"Chatbot index: {stats}")
    except Exception as exc:  # noqa: BLE001
        print(f"Chatbot index skipped (set an API key to enable): {type(exc).__name__}: {exc}")

    print("\nDONE. Start the server and log in:")
    print("  Admin   : admin@defense-lms.org / admin12345")
    print("  Learner : cadet@defense-lms.org / cadet12345")


if __name__ == "__main__":
    asyncio.run(main())
