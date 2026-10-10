"""FastAPI app for the demo UI. Thin: every number comes from demo_app.service, which calls the existing engine.

    python -m demo_app            # http://127.0.0.1:8000
    python -m demo_app --offline  # safety net, no Azure
"""

from __future__ import annotations

import asyncio
import logging
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse, Response
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from .service import DemoService, UnknownCustomer

STATIC = Path(__file__).parent / "static"
log = logging.getLogger("demo_app")


class InvestigateRequest(BaseModel):
    customer_id: str
    use_agents: bool = True
    refresh: bool = False


def create_app(offline: bool = False, warm: bool = True, service: DemoService | None = None) -> FastAPI:
    svc = service or DemoService(offline=offline, warm=warm)
    app = FastAPI(title="Credit-Risk Investigation Agent (demo)", docs_url=None, redoc_url=None)
    app.state.service = svc

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    if (STATIC / "assets").exists():
        app.mount("/assets", StaticFiles(directory=STATIC / "assets"), name="assets")

    @app.get("/", include_in_schema=False)
    async def index():
        return FileResponse(STATIC / "index.html", media_type="text/html; charset=utf-8",
                            headers={"Cache-Control": "no-store"})

    @app.get("/favicon.ico", include_in_schema=False)
    async def favicon():
        return Response(status_code=204)

    @app.get("/api/health")
    async def health():
        try:
            return svc.health()
        except Exception as exc:  # noqa: BLE001 - the UI must always get an answer
            log.exception("health failed")
            return {"status": "degraded", "mode": "offline", "error": type(exc).__name__}

    @app.get("/api/personas")
    async def personas():
        return svc.personas()

    @app.post("/api/investigate")
    async def investigate(body: InvestigateRequest):
        try:
            return await asyncio.to_thread(svc.investigate, body.customer_id, body.use_agents, body.refresh)
        except UnknownCustomer:
            ids = [c["applicant_id"] for c in svc.cases]
            return JSONResponse(status_code=404, content={
                "ok": False, "error": "unknown_customer", "detail": f"No customer '{body.customer_id}'.", "available": ids})
        except Exception as exc:  # noqa: BLE001 - never a 500 to the UI
            log.exception("investigate failed")
            return JSONResponse(status_code=200, content={
                "ok": False, "error": "investigation_failed", "mode": svc.mode,
                "detail": f"The investigation could not be completed ({type(exc).__name__}). Try again or use offline mode."})

    return app
