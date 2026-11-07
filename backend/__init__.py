"""FieldShift backend package root.

Layer map (docs/01_ARCHITECTURE_AND_FOLDERS.md):
  app/      HTTP layer only (FastAPI routers, validation, error envelope)
  engine/   PURE science: deterministic, no network, no LLM, no I/O
  schemas/  Pydantic v2 wire contract
  data/     providers + cache + curated tables (below the engine)
  explain/  optional LLM sidecar (never imported by engine/)
"""

__version__ = "0.1.0"
