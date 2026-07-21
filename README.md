# Defense AI Training & Simulation LMS — POC

A self-contained AI Learning Management System: an admin uploads materials, the
platform auto-generates subjects → courses → modules → lessons + quizzes, learners
enrol and study self-paced, ask a **grounded doubt-clearing chatbot**, take
auto-generated quizzes, and progress is tracked. AI providers swap **cloud ↔ local**
behind a single **model gateway** with no application-code change (air-gap target).

See the build plan and the AI-workflow reuse analysis in `docs/`.

## Stack
- **Backend:** FastAPI (async), component architecture (`app/components/<name>/`)
- **DB:** PostgreSQL (asyncpg) via SQLAlchemy 2.0
- **Vector store:** Qdrant + sentence-transformers (MiniLM)
- **AI:** Anthropic (cloud) behind `app/gateway/` — local vLLM/Ollama + BGE/E5 later
- **Objects:** MinIO (S3 API), local-only
- **Auth:** JWT + two roles (admin / learner)

## Quick start (Docker)
```bash
cp .env.example .env      # set CLAUDE_API_KEY for AI features
docker compose up --build
# API:     http://localhost:8000/docs
# MinIO:   http://localhost:9001  (minioadmin / minioadmin)
```

## Local dev (no Docker; SQLite)
```bash
python -m venv .venv && .venv/Scripts/activate      # Windows
pip install -r requirements.txt
# Point DATABASE_URL at SQLite for a quick spin, or run Postgres.
uvicorn app.main:app --reload
```

## Verify (offline smoke tests — no API key, no external services)
Each phase has an end-to-end smoke test that boots the app on SQLite with an
injected fake gateway, so the whole loop is verifiable without Anthropic/Qdrant:
```bash
for p in 0 1 2 3 4 5 6; do .venv/Scripts/python.exe scripts/smoke_phase$p.py; done
.venv/Scripts/python.exe scripts/check_gateway_isolation.py   # PRD 4.9 gate
```
- phase0 — auth + RBAC + health
- phase1 — model gateway conformance + ingestion (DOCX/PPTX/TXT) with provenance
- phase2 — AI course generation + review/publish (pending-guard, version bump)
- phase3 — catalog → enrol → deliver → progress/resume → completion
- phase4 — grounded chatbot: cited answers, abstention, multi-turn, explainer
- phase5 — quiz auto-grade, analytics (cohort/mastery/weakest), audit log
- phase6 — 3D library, hotspots, lesson association, viewer, hotspot→explainer

`check_gateway_isolation.py` fails CI if any module outside `app/gateway/`
imports a provider SDK — this is what makes cloud↔local a config-only switch.

## Build phases
- **Phase 0–6** ✅ Full backend loop + thin React viewer scaffold (`frontend/`).
- **Phase 7** Air-gap hardening (local vLLM/Ollama + BGE/E5 via the gateway,
  Keycloak OIDC/SAML, Helm/k8s, no-outbound verification) — planned.
