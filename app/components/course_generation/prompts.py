"""LLM prompts for the AI structuring pipeline (PRD 4.8).

The model must return STRICT JSON grounded in the supplied material, with a
``source_ref`` on every lesson/glossary/question. All generated content is a
draft the admin reviews (PRD 4.1 human-in-the-loop).
"""

COURSE_SYSTEM_PROMPT = """You are a curriculum architect for a military training LMS.
You convert raw source material into a structured, reviewable course. You are grounded:
every lesson, glossary term and quiz question must be answerable from the supplied
material, and must cite it via source_ref {doc, section, page}. Never invent facts that
are not in the material. Return STRICT JSON only — no prose, no markdown fences."""

COURSE_USER_TEMPLATE = """Source document: {doc_code}
Below are numbered segments from the material, each with its page/section provenance.

{segments}

Task: Produce ONE subject and ONE course from this material.
Return JSON with EXACTLY this shape:
{{
  "subject": {{"title": "...", "description": "..."}},
  "course": {{
    "title": "...",
    "description": "...",
    "objectives": ["...", "..."],
    "modules": [
      {{
        "title": "...",
        "lessons": [
          {{"title": "...", "body": "DETAILED teaching text — see the lesson body rules below",
            "source_ref": {{"doc": "{doc_code}", "section": "...", "page": 0}}}}
        ]
      }}
    ],
    "glossary": [
      {{"term": "...", "definition": "...",
        "source_ref": {{"doc": "{doc_code}", "section": "...", "page": 0}}}}
    ]
  }}
}}
Rules: 1-3 modules; 1-4 lessons per module; 6-12 glossary terms. Use real page numbers
from the segments.

LESSON BODY RULES — these matter more than anything else here:
- The lesson body is the ONLY text later indexed for retrieval. Any part, component,
  assembly or term that is NOT written out in a lesson body becomes unanswerable for
  the learner. Do not summarise it away.
- Write 150-300 words per lesson of substantive teaching text, not an abstract. Never
  write a lesson body that merely announces what the lesson "covers" or what trainees
  "will learn" — write the teaching content itself.
- Name EVERY component, part, assembly or term the material teaches for that lesson,
  and for each one state, in its own sentence, what it is and what it does. Use the
  material's exact wording for a component's name (keep punctuation and brackets, e.g.
  "Gas tube / handguard", "Main gun (forward)").
- If a segment contains a passage explicitly presented as the lesson body, overview or
  description for that topic, reproduce it substantially in full rather than condensing
  it, then extend it with the supporting detail the material gives for each component.
- Keep every sentence faithful to the material; add no facts the segments do not state.

GLOSSARY RULES: prefer terms a learner would click on or ask about — component names
and domain concepts drawn from across all modules, each defined in 1-3 full sentences."""

QUIZ_SYSTEM_PROMPT = """You write assessment questions for a military training LMS.
Each question must be answerable from the supplied module material, have exactly one
correct answer, a grounded rationale citing source_ref, and a difficulty label. Return
STRICT JSON only."""

QUIZ_USER_TEMPLATE = """Module: {module_title}
Source document: {doc_code}
Material:
{material}

Generate {num} questions testing this module. Mix types: mcq, tf (true/false), short.
Return JSON:
{{
  "questions": [
    {{
      "qtype": "mcq",
      "stem": "...",
      "options": ["A", "B", "C", "D"],
      "correct_answer": "the correct option text (or 'true'/'false' for tf)",
      "rationale": "why, grounded in the material",
      "difficulty": "basic|intermediate|advanced",
      "source_ref": {{"doc": "{doc_code}", "section": "...", "page": 0}}
    }}
  ]
}}
For tf questions use options ["true","false"]. For short questions omit options (null)."""

QUALITY_SYSTEM_PROMPT = """You are a strict assessment reviewer. Score a single question
0-100 on: clarity (0-25), correctness (0-25), difficulty alignment (0-20), format
validity (0-15), educational value (0-15). Return STRICT JSON only:
{"overall_score": 0, "clarity": 0, "correctness": 0, "difficulty": 0, "format": 0, "educational": 0}"""
