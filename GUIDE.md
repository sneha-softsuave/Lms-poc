# Beginner's Guide — Run & Test the Defense AI LMS POC

This guide assumes you know almost nothing about the project. Follow it top to
bottom. Every command is copy-paste ready for **Windows PowerShell**.

There are **two ways** to see this project working:

- **A. Test it (easiest)** — run the automated checks. No accounts, no API keys,
  no databases to install. ~2 minutes.
- **B. Run it live** — start the server and click around in your browser.

Start with A. It proves everything works. Then do B if you want to explore.

---

## 0. One-time setup

You need **Python 3.12** installed. Check it:

```powershell
python --version
```

If that prints `Python 3.12.x`, you're good. Now open PowerShell **in the project
folder** and create the isolated environment + install packages:

```powershell
cd C:\Users\softsuave\Documents\poc
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

> The `.venv` folder is a private copy of Python just for this project. After
> `Activate.ps1` your prompt shows `(.venv)` — that means it's active. If you
> open a new terminal later, run `.\.venv\Scripts\Activate.ps1` again.

> **If `Activate.ps1` is blocked** with a red "execution policy" error, run this
> once, then try again:
> ```powershell
> Set-ExecutionPolicy -Scope CurrentUser RemoteSigned
> ```

---

## A. Test it (the automated way) — do this first

The project ships **7 self-contained tests**, one per feature area. Each one
starts the whole app in memory, runs a real end-to-end scenario, and prints
`PASS`. They need **no API key and no database** — they use a tiny throwaway
SQLite file and a fake AI model, so they run fully offline.

Run them all:

```powershell
foreach ($p in 0..6) { python scripts\smoke_phase$p.py }
```

You should see each finish with `PHASE X SMOKE: PASS`. Here's what each proves:

| Test | What it checks |
|------|----------------|
| `smoke_phase0.py` | Sign-up / login / roles (admin vs learner) |
| `smoke_phase1.py` | Uploading a Word/PowerPoint/text file and pulling the text out |
| `smoke_phase2.py` | AI turns an uploaded doc into a draft course + quiz; admin approves & publishes |
| `smoke_phase3.py` | A learner browses the catalog, enrols, finishes lessons, progress hits 100% |
| `smoke_phase4.py` | The chatbot answers **only** from course material, cites sources, and says "not covered" for off-topic questions |
| `smoke_phase5.py` | Taking a quiz, auto-grading, analytics dashboards, audit log |
| `smoke_phase6.py` | The 3D model library, clickable hotspots, and hotspot → explanation |

Run just one (e.g. the chatbot) to read its output closely:

```powershell
python scripts\smoke_phase4.py
```

### One extra check — the "provider switch" guarantee

A key promise of this project is that swapping the AI provider (cloud ↔ local)
is a **settings change, not a code change**. This test enforces it:

```powershell
python scripts\check_gateway_isolation.py
```

It should print `gateway isolation: PASS`.

---

## B. Run it live (start the server, use your browser)

The project is already set up to run with **no external services** — it uses a
local SQLite file for the database, local disk for files, and in-memory search.
(The `.env` file is preconfigured for this.)

### B1. Start the server

With `(.venv)` active, in the project folder:

```powershell
uvicorn app.main:app --reload
```

Leave this window running. You'll see `Application startup complete`. On first
start it automatically creates an **admin account** and seeds the 5 demo 3D
models.

### B2. Open the interactive API page

In your browser go to:

```
http://localhost:8000/docs
```

This is **Swagger UI** — an auto-generated page listing every endpoint with a
"Try it out" button. This is the easiest way to poke the app without writing code.

### B3. Log in as the admin

1. On the `/docs` page, find **POST `/api/v1/auth/login`** and click it.
2. Click **Try it out**, and set the body to:
   ```json
   { "email": "admin@defense-lms.org", "password": "admin12345" }
   ```
3. Click **Execute**. In the response, copy the long `access_token` value.
4. Scroll to the top of the page, click the green **Authorize** button, paste the
   token, and confirm. Now every "Try it out" call runs as the admin.

### B4. Walk the main flow from `/docs`

Do these in order (each has a "Try it out" button):

1. **Upload material** — `POST /api/v1/ingestion/upload`. Choose any `.docx`,
   `.pdf`, `.pptx`, or `.txt` file. Note the `id` in the response.
2. **Generate a course** — `POST /api/v1/course-generation/documents/{doc_id}/generate`
   using that `id`. *(This step calls the real AI — see the note below.)*
3. **Review the questions** — `GET /api/v1/review/courses/{course_id}/questions`,
   then approve each with `POST /api/v1/review/questions/{id}/approve`.
4. **Publish** — `POST /api/v1/review/courses/{course_id}/publish`.
5. **Browse the catalog** — `GET /api/v1/catalog/subjects`.
6. **Ask the chatbot** — `POST /api/v1/chat` with a question about the material.

> ### ⚠️ Steps 2 and 6 need an AI key
> Course generation and the chatbot call a real AI model. Without a key they'll
> return an error (everything else — login, upload, catalog, enrolment, quizzes,
> 3D — works fine without one).
>
> To enable AI: open the `.env` file in the project folder, set
> `CLAUDE_API_KEY=sk-ant-...your key...`, save, and restart the server
> (Ctrl+C in the server window, then `uvicorn app.main:app --reload` again).
>
> **No key?** No problem — the automated tests in Section A already exercise the
> full AI flow using a stand-in model, so you can verify all the behavior there.

### B5. Stop the server

Click the server window and press **Ctrl + C**.

---

## C. (Optional) Run the whole real stack with Docker

If you have **Docker Desktop** installed and want the production-like setup
(PostgreSQL + Qdrant search + MinIO file storage), from the project folder:

```powershell
copy .env.example .env    # then edit .env and set CLAUDE_API_KEY
docker compose up --build
```

Then open `http://localhost:8000/docs` as before. Stop it with `Ctrl + C`, or
`docker compose down`.

---

## D. (Optional) The web UI

There's a thin React interface in the `frontend/` folder (sign in → catalog →
lesson with 3D viewer + chatbot). It needs **Node.js** installed:

```powershell
cd frontend
npm install
npm run dev
```

Then open `http://localhost:3000` (keep the backend from Section B running too).

---

## Troubleshooting

| Problem | Fix |
|---|---|
| `python` not found | Install Python 3.12 from python.org; re-open PowerShell. |
| `Activate.ps1 cannot be loaded` | Run `Set-ExecutionPolicy -Scope CurrentUser RemoteSigned`, then retry. |
| `ModuleNotFoundError` | You skipped `pip install -r requirements.txt`, or `(.venv)` isn't active. |
| Port 8000 already in use | Run `uvicorn app.main:app --reload --port 8001` and use `:8001`. |
| Course-gen / chat returns an error | You haven't set `CLAUDE_API_KEY` in `.env` (see step B4 note). |
| Want a clean slate | Delete the `*.sqlite` file in the project folder; it's recreated on next start. |

---

## What to remember

- **Section A (the smoke tests) is the real proof** — it runs the entire product
  end to end, offline, in about two minutes.
- **Section B** lets you click through it live; only the two AI steps need a key.
- Everything is self-contained: no cloud account required to see it work.
