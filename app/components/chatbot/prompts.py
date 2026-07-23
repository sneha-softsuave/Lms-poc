"""Grounded tutor prompts (PRD 4.5).

The assistant answers ONLY from retrieved course material and cites it. It does
not use outside knowledge. Abstention is enforced in code (retrieval threshold),
and reinforced here so the model stays within the provided context.
"""

TUTOR_SYSTEM_PROMPT = """You are the doubt-clearing assistant for a military training course.
Answer the learner's question using ONLY the provided material below. Rules:
- Use only facts present in the material. Do not use outside knowledge.
- Be concise and accurate. Refer to components/procedures by their names in the material.
- You are given two kinds of material: COURSE MATERIAL (reviewed and approved) and
  SOURCE DOCUMENT (raw text from the original manual the course was built from).
  Prefer the course material. Use the source document to add detail it omits, or to
  answer when it is silent — the source is authoritative but unsummarised.
- Earlier conversation turns, when shown, are only for resolving what the learner is
  referring to ("it", "that one", "the second one"). Never treat them as facts.
- If neither contains the answer, reply exactly: NOT_COVERED
- Do not fabricate. Do not speculate beyond the material."""


def build_tutor_prompt(
    question: str,
    context_blocks: list[str],
    lesson_context: str | None,
    source_blocks: list[str] | None = None,
    history: list[tuple[str, str]] | None = None,
) -> str:
    material = "\n\n".join(f"[{i + 1}] {b}" for i, b in enumerate(context_blocks))
    lesson_line = f"\nCurrent lesson context: {lesson_context}\n" if lesson_context else ""
    history_section = ""
    if history:
        turns = "\n".join(
            f"{'Learner' if role == 'user' else 'Assistant'}: {text}" for role, text in history
        )
        history_section = (
            "\nEarlier in this conversation (for resolving references like "
            f'"it" or "that one" — not a source of facts):\n{turns}\n'
        )
    source_section = ""
    if source_blocks:
        start = len(context_blocks)
        blocks = "\n\n".join(f"[{start + i + 1}] {b}" for i, b in enumerate(source_blocks))
        source_section = f"\nSource document (original manual, unsummarised):\n{blocks}\n"
    return (
        f"Course material:\n{material}\n{source_section}{lesson_line}{history_section}\n"
        f"Learner question: {question}\n\n"
        f"Answer using only the material above. If not answerable, reply NOT_COVERED."
    )
