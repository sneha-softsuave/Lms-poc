"""Grounded tutor prompts (PRD 4.5).

The assistant answers ONLY from retrieved course material and cites it. It does
not use outside knowledge. Abstention is enforced in code (retrieval threshold),
and reinforced here so the model stays within the provided context.
"""

TUTOR_SYSTEM_PROMPT = """You are the doubt-clearing assistant for a military training course.
Answer the learner's question using ONLY the provided course material below. Rules:
- Use only facts present in the material. Do not use outside knowledge.
- Be concise and accurate. Refer to components/procedures by their names in the material.
- If the material does not contain the answer, reply exactly: NOT_COVERED
- Do not fabricate. Do not speculate beyond the material."""


def build_tutor_prompt(question: str, context_blocks: list[str], lesson_context: str | None) -> str:
    material = "\n\n".join(f"[{i + 1}] {b}" for i, b in enumerate(context_blocks))
    lesson_line = f"\nCurrent lesson context: {lesson_context}\n" if lesson_context else ""
    return (
        f"Course material:\n{material}\n{lesson_line}\n"
        f"Learner question: {question}\n\n"
        f"Answer using only the material above. If not answerable, reply NOT_COVERED."
    )
