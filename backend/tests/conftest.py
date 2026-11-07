"""Shared pytest fixtures for the backend test suite.

The FastAPI app lives in `backend/` with layer packages (`app`, `engine`,
`schemas`, `data`, `explain`) importable from the backend root — this fixture
makes `from app.main import create_app` work inside tests without installing
the project first.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))


@pytest.fixture()
def client() -> TestClient:
    # Import after sys.path setup so collection order never breaks it.
    from app.main import create_app

    return TestClient(create_app())
