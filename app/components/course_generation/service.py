"""AI structuring pipeline (PRD 4.1, 4.8).

document segments -> [LLM via gateway] -> draft Subject/Course/Module/Lesson/Glossary
                  -> [LLM via gateway] -> per-module draft Question bank + quality score

All model calls go through the injected ModelGateway (never a provider SDK). All
output is a DRAFT for admin review.
"""

from __future__ import annotations

import json
import logging
import re

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.components.content.db_models import (
    REVIEW_PENDING,
    Course,
    GlossaryTerm,
    Lesson,
    Module,
    Question,
    Quiz,
    Subject,
)
from app.components.course_generation.prompts import (
    COURSE_SYSTEM_PROMPT,
    COURSE_USER_TEMPLATE,
    QUALITY_SYSTEM_PROMPT,
    QUIZ_SYSTEM_PROMPT,
    QUIZ_USER_TEMPLATE,
)
from app.components.ingestion.db_models import Document, DocumentSegment
from app.gateway.base import ModelGateway

logger = logging.getLogger(__name__)


def _parse_json(text: str) -> dict:
    """Extract a JSON object from an LLM response (tolerates ```json fences / prose)."""
    text = text.strip()
    fence = re.search(r"```(?:json)?\s*(\{.*\})\s*```", text, re.S)
    if fence:
        text = fence.group(1)
    else:
        start, end = text.find("{"), text.rfind("}")
        if start != -1 and end != -1:
            text = text[start : end + 1]
    return json.loads(text)


def _segments_block(segments: list[DocumentSegment], limit: int = 40) -> str:
    lines = []
    for s in segments[:limit]:
        prov = f"[page {s.page}" + (f", section '{s.section}'" if s.section else "") + "]"
        lines.append(f"{s.ordinal}. {prov} {s.text}")
    return "\n".join(lines)


class CourseGenerationService:
    @staticmethod
    async def generate_from_document(
        doc_id: int, gateway: ModelGateway, db: AsyncSession, *, quiz_per_module: int = 3
    ) -> Course:
        doc = await db.get(Document, doc_id)
        if not doc:
            raise ValueError(f"Document {doc_id} not found")
        seg_result = await db.execute(
            select(DocumentSegment)
            .where(DocumentSegment.document_id == doc_id)
            .order_by(DocumentSegment.ordinal)
        )
        segments = list(seg_result.scalars().all())
        if not segments:
            raise ValueError(f"Document {doc_id} has no extracted segments")

        # ── 1) course structure ────────────────────────────────────────────────
        prompt = COURSE_USER_TEMPLATE.format(
            doc_code=doc.doc_code, segments=_segments_block(segments)
        )
        # Headroom matters: lesson bodies are the retrieval corpus (see the lesson
        # body rules in COURSE_USER_TEMPLATE), so the JSON is long by design and a
        # tight budget truncates it into unparseable output.
        completion = await gateway.generate(
            prompt, system=COURSE_SYSTEM_PROMPT, max_tokens=8000, temperature=0.0
        )
        data = _parse_json(completion.text)

        subj_d = data["subject"]
        course_d = data["course"]
        subject = Subject(
            title=subj_d["title"],
            description=subj_d.get("description", ""),
            source_doc_id=doc_id,
        )
        course = Course(
            subject=subject,
            title=course_d["title"],
            description=course_d.get("description", ""),
            objectives=course_d.get("objectives", []),
            status="draft",
        )
        for m_i, mod_d in enumerate(course_d.get("modules", [])):
            module = Module(title=mod_d["title"], order_index=m_i)
            for l_i, les_d in enumerate(mod_d.get("lessons", [])):
                module.lessons.append(
                    Lesson(
                        title=les_d["title"],
                        body=les_d.get("body", ""),
                        order_index=l_i,
                        source_ref=les_d.get("source_ref"),
                    )
                )
            course.modules.append(module)
        for term_d in course_d.get("glossary", []):
            course.glossary.append(
                GlossaryTerm(
                    term=term_d["term"],
                    definition=term_d.get("definition", ""),
                    source_ref=term_d.get("source_ref"),
                )
            )
        db.add(subject)
        db.add(course)
        await db.flush()  # assign ids for module quiz generation

        # ── 2) per-module quiz bank (drafts, pending review) ────────────────────
        for module in course.modules:
            await CourseGenerationService._generate_quiz_for_module(
                module=module,
                doc_code=doc.doc_code,
                gateway=gateway,
                db=db,
                num=quiz_per_module,
            )

        doc.status = "structured"
        await db.commit()
        await db.refresh(course)
        logger.info("Generated draft course '%s' from %s", course.title, doc.doc_code)
        return course

    @staticmethod
    async def _generate_quiz_for_module(
        *, module: Module, doc_code: str, gateway: ModelGateway, db: AsyncSession, num: int
    ) -> None:
        material = "\n".join(f"- {les.title}: {les.body}" for les in module.lessons)
        prompt = QUIZ_USER_TEMPLATE.format(
            module_title=module.title, doc_code=doc_code, material=material, num=num
        )
        completion = await gateway.generate(
            prompt, system=QUIZ_SYSTEM_PROMPT, max_tokens=2000, temperature=0.0
        )
        data = _parse_json(completion.text)
        db.add(Quiz(module_id=module.id, title=f"{module.title} — Quiz"))
        for q_d in data.get("questions", []):
            question = Question(
                module_id=module.id,
                qtype=q_d.get("qtype", "mcq"),
                stem=q_d["stem"],
                options=q_d.get("options"),
                correct_answer=str(q_d.get("correct_answer", "")),
                rationale=q_d.get("rationale", ""),
                difficulty=q_d.get("difficulty", "basic"),
                review_status=REVIEW_PENDING,
                source_ref=q_d.get("source_ref"),
            )
            question.quality_score = await CourseGenerationService._score_question(
                q_d, gateway
            )
            db.add(question)

    @staticmethod
    async def _score_question(q_d: dict, gateway: ModelGateway) -> int:
        try:
            completion = await gateway.generate(
                json.dumps(q_d), system=QUALITY_SYSTEM_PROMPT, max_tokens=300, temperature=0.0
            )
            score = _parse_json(completion.text).get("overall_score", 0)
            return int(score)
        except Exception as exc:  # noqa: BLE001
            logger.warning("Quality scoring failed: %s", exc)
            return 0
