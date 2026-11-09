"""FastAPI application factory (docs/02 §1: HTTP layer only, no science).

Mounted here:
  - CORS for the local Vite dev server
  - the single error envelope handlers (app/errors.py)
  - routers under /api/v1
Phase 1 registers `health` only; farm/knowledge/rotations/scenarios/explain
routers are added in their own phases — never stubbed with fake behaviour.
"""

from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import get_settings
from app.errors import install_handlers
from app.routers import environmental, health, knowledge


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(
        title="FieldShift API",
        version=settings.api_version,
        description=(
            "Transparent decision-support for resilient crop rotations. "
            "Engine results are deterministic and LLM-free; see docs/ in repo root."
        ),
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=False,
        allow_methods=["GET", "POST"],
        allow_headers=["Content-Type"],
    )

    install_handlers(app)

    api = "/api/v1"
    app.include_router(health.router, prefix=api)
    app.include_router(knowledge.router, prefix=api)
    app.include_router(environmental.router, prefix=api)
    # Phase 3+: farm   Phase 4+: knowledge   Phase 5+: rotations
    # Phase 6+: scenarios   Phase 10+: explain (only LLM route)

    return app


# Module-level ASGI app for `uvicorn app.main:app`
app = create_app()
