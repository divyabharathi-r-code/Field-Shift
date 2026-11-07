"""Engine purity guard (docs/00 rule: scientific layer must NOT depend on LLM/network).

Two layers of enforcement:
  - static contract via import-linter (`lint-imports`, run in CI), and
  - this runtime test, which scans every engine/data-source file for banned
    imports so a violation fails `pytest` even where import-linter isn't run.

Phase 1: engine/ is intentionally empty except package markers; the test
still guards the directory so future phases cannot silently break purity.
"""

from __future__ import annotations

import re
from pathlib import Path

# tests/unit/test_engine_purity.py -> parents[2] == backend/
BACKEND_ROOT = Path(__file__).resolve().parents[2]

BANNED_MODULES = {
    "httpx", "requests", "urllib3", "aiohttp", "socket", "urllib",
    "openai", "anthropic", "ollama", "google.generativeai", "boto3",
}
# explain/ is the only place allowed to talk to an LLM; engine must not touch it.
BANNED_LOCAL = {"explain", "app"}

_IMPORT_RE = re.compile(
    r"^\s*(?:from|import)\s+([A-Za-z_][\w.]*)", re.MULTILINE
)


def _python_files(pkg: str) -> list[Path]:
    return sorted((BACKEND_ROOT / pkg).rglob("*.py"))


def test_engine_package_exists() -> None:
    assert (BACKEND_ROOT / "engine" / "__init__.py").is_file()


def test_engine_sources_import_nothing_banned() -> None:
    offenders: list[str] = []
    for path in _python_files("engine"):
        text = path.read_text(encoding="utf-8")
        for match in _IMPORT_RE.finditer(text):
            top = match.group(1).split(".")[0]
            if top in BANNED_MODULES or top in BANNED_LOCAL:
                offenders.append(f"{path.relative_to(BACKEND_ROOT)}: {match.group(1)}")
    assert offenders == [], "engine/ must stay network- and LLM-free:\n" + "\n".join(offenders)
