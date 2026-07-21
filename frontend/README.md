# Defense LMS — Frontend (thin demo shell)

A minimal React + TypeScript + React Three Fiber UI that proves the backend loop
end to end: sign in → browse catalog → open a lesson with an interactive **3D
model** (rotate/pan/zoom, clickable hotspots → grounded component explainer) and
a **doubt-clearing chatbot** (grounded, cited, abstains).

This is intentionally thin (backend-first). It is a scaffold to build the full
learner/admin UX on.

## Run
```bash
cd frontend
npm install
npm run dev          # http://localhost:3000  (proxies /api -> http://localhost:8000)
```
Start the backend first (`uvicorn app.main:app --reload` from the repo root).

## Notes
- **No CDN**: three.js and all deps are bundled locally by Vite (air-gap friendly).
- GLB assets are served by the backend object store. The 5 preloaded models seed
  automatically; drop the optimized `.glb` files into the object store under
  `models3d/<model_key>.glb` and expose them at `/media/...` for the viewer.
- If a lesson has no associated model the viewer degrades gracefully to a note
  (PRD FR-5.4.5); wire an image/diagram fallback here for production.
