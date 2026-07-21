# PRD Compliance — Defense AI LMS POC

Mapping of PRD functional requirements to implementation status.
✅ implemented & verified · ⚠️ partial · ⏸ deferred (infra, out of code-POC scope)

## 5.1 Admin console, users, auth
| FR | Requirement | Status |
|----|-------------|--------|
| 5.1.1 | Admin creates org / cohorts / role assignments | ⚠️ roles + admin-assign implemented; formal "cohort" entity not modelled |
| 5.1.2 | Upload materials; manage subjects/courses/quizzes | ✅ |
| 5.1.3 | Select model provider (cloud/local) without code change | ✅ model gateway (`cloud`/`openai`/`local` by config) |
| 5.1.4 | Associate a preloaded 3D model with a lesson; no 3D upload | ✅ (also editable after publish) |
| 5.1.5 | OIDC/SAML SSO with local-account fallback | ⏸ local JWT accounts done; Keycloak SSO deferred |
| 5.1.6 | Two roles (admin / learner) | ✅ |

## 5.2 Material upload & AI course generation
| FR | Requirement | Status |
|----|-------------|--------|
| 5.2.1 | Ingest PDF/DOCX/PPTX, OCR scanned pages | ✅ (Tesseract OCR fallback) |
| 5.2.2 | Split content into subjects | ✅ |
| 5.2.3 | Generate structured course per subject | ✅ |
| 5.2.4 | Generate quiz bank per module | ✅ |
| 5.2.5 | Review/edit/approve before publish; provenance; versioning | ✅ |

## 5.3 Catalog, subjects & enrolment
| FR | Requirement | Status |
|----|-------------|--------|
| 5.3.1 | Catalog of published courses grouped by subject | ✅ |
| 5.3.2 | Self-enrol; admin assign | ✅ |
| 5.3.3 | Course page: modules, lessons, objectives, progress, resume | ✅ |

## 5.4 Learning delivery & 3D
| FR | Requirement | Status |
|----|-------------|--------|
| 5.4.1 | Guided lesson flow; completion; resume | ✅ |
| 5.4.2 | Render 3D where a preloaded model is associated | ✅ |
| 5.4.3 | Rotate/pan/zoom, hotspot selection, component highlight, preset views | ✅ in-scene hotspots, click-to-highlight + camera focus, Front/Side/Top/Iso presets |
| 5.4.4 | ≥5 preloaded, licence-clear models | ✅ 5 GLBs (self-authored → licence-clear), served locally |
| 5.4.5 | Degrade gracefully to images/diagrams | ✅ 2D schematic fallback when WebGL unavailable |

## 5.5 Doubt-clearing chatbot
| FR | Requirement | Status |
|----|-------------|--------|
| 5.5.1 | Grounded answers, citations, multi-turn | ✅ |
| 5.5.2 | Uses current course/lesson as context | ✅ |
| 5.5.3 | Component explainer with citation | ✅ (hotspot → grounded, cited answer) |
| 5.5.4 | Abstain/redirect when uncovered | ✅ |

## 5.6 Quizzes & assessment
| FR | Requirement | Status |
|----|-------------|--------|
| 5.6.1 | MCQ/TF/short with difficulty, answer, grounded rationale | ✅ |
| 5.6.2 | Review/edit/approve/reject before delivery | ✅ |
| 5.6.3 | Auto-grade objective; record scores | ✅ |

## 5.7 Progress, analytics & audit
| FR | Requirement | Status |
|----|-------------|--------|
| 5.7.1 | Progress: lessons, quiz scores, **time on task**, completion %, subject mastery | ✅ (time-on-task via heartbeat) |
| 5.7.2 | Learner dashboard: enrolled, progress, resume | ✅ |
| 5.7.3 | Mark complete; issue **completion record/certificate** | ✅ (auto-issued certificate + printable view) |
| 5.7.4 | Admin cohort analytics, weakest topics, **exportable** | ✅ (+ CSV export) |
| 5.7.5 | Immutable audit log | ✅ |

## 4.9 Model gateway (cloud ↔ local)
| Requirement | Status |
|-------------|--------|
| Single interface for all AI ops; provider by config | ✅ `app/gateway/` — `generate/embed/rerank` |
| Cloud provider | ✅ Anthropic Claude **and** OpenAI |
| Local (vLLM/Ollama + BGE/E5) | ⏸ interface stubbed; wiring deferred to air-gap phase |
| No SDK imports outside gateway (enforced) | ✅ CI gate `scripts/check_gateway_isolation.py` |

## Deferred (infrastructure / hardening — beyond a code POC)
| Item | PRD ref | Why deferred |
|------|---------|--------------|
| OIDC/SAML via Keycloak | 4.10, 5.1.5 | needs a running identity provider; local JWT covers the demo |
| Local LLM server (vLLM/Ollama) + BGE/E5 | 4.9 | needs GPU/model hosting; OpenAI/Claude cover the demo, gateway makes it a config swap |
| Kubernetes/Helm, internal registry | Deployment | ops concern; `docker-compose` provided for the demo |
| glTF Draco compression + LODs | 4.4.3 | models are small; optimisation unnecessary at POC scale |
| Formal cohort entity | 5.1.1 | admin-assign to individuals implemented; cohort grouping is a schema add |

## How to verify
- Offline backend suite: `scripts/smoke_phase{0..6}.py` (all PASS) + `check_gateway_isolation.py`
- Frontend: `cd frontend && npm run build` (passes)
- Live: `python scripts/seed_demo.py` → `uvicorn app.main:app` → `frontend: npm run dev`
