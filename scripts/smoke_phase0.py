"""Phase 0 smoke test: boot the app on SQLite and exercise health + auth.

Run: .venv/Scripts/python.exe scripts/smoke_phase0.py
Uses an in-process ASGI transport (httpx) — no server or Postgres needed.
"""

import asyncio
import os
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Point the app at a throwaway SQLite DB BEFORE importing app modules.
_tmp = tempfile.mktemp(suffix=".db")
os.environ["DATABASE_URL"] = f"sqlite+aiosqlite:///{_tmp}"
os.environ["BOOTSTRAP_ADMIN_EMAIL"] = "admin@defense-lms.org"
os.environ["BOOTSTRAP_ADMIN_PASSWORD"] = "admin12345"

import httpx  # noqa: E402

from app.main import app  # noqa: E402


async def main() -> None:
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as c:
        # lifespan (create_all + bootstrap admin)
        async with app.router.lifespan_context(app):
            r = await c.get("/health")
            assert r.status_code == 200, r.text
            assert r.json()["status"] == "ok"
            print("health:", r.json())

            # bootstrap admin can log in
            r = await c.post(
                "/api/v1/auth/login",
                json={"email": "admin@defense-lms.org", "password": "admin12345"},
            )
            assert r.status_code == 200, r.text
            admin_token = r.json()["access_token"]
            print("admin login: ok")

            # self-register a learner
            r = await c.post(
                "/api/v1/auth/register",
                json={"email": "learner@x.com", "password": "learner123", "full_name": "Lee"},
            )
            assert r.status_code == 201, r.text
            assert r.json()["role"] == "learner"
            print("register learner: ok")

            # learner login + /me
            r = await c.post(
                "/api/v1/auth/login",
                json={"email": "learner@x.com", "password": "learner123"},
            )
            learner_token = r.json()["access_token"]
            r = await c.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {learner_token}"})
            assert r.status_code == 200 and r.json()["email"] == "learner@x.com", r.text
            print("me:", r.json())

            # RBAC: learner cannot create users
            r = await c.post(
                "/api/v1/auth/admin/users",
                headers={"Authorization": f"Bearer {learner_token}"},
                json={"email": "x@y.com", "password": "pass1234", "role": "admin"},
            )
            assert r.status_code == 403, f"expected 403, got {r.status_code}"
            print("rbac learner->admin blocked: ok")

            # RBAC: admin CAN create an admin
            r = await c.post(
                "/api/v1/auth/admin/users",
                headers={"Authorization": f"Bearer {admin_token}"},
                json={"email": "admin2@x.com", "password": "pass1234", "role": "admin"},
            )
            assert r.status_code == 201 and r.json()["role"] == "admin", r.text
            print("rbac admin creates admin: ok")

    print("\nPHASE 0 SMOKE: PASS")


if __name__ == "__main__":
    asyncio.run(main())
