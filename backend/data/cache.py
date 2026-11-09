"""Atomic, time-limited JSON response cache for data providers."""

from __future__ import annotations

import json
import os
import re
import tempfile
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any


class CacheError(RuntimeError):
    """Raised when a cached response cannot be read or written safely."""


@dataclass(frozen=True)
class CachedResponse:
    payload: dict[str, Any]
    retrieved_at: datetime


class JsonResponseCache:
    def __init__(self, directory: Path, ttl: timedelta) -> None:
        if ttl <= timedelta(0):
            raise ValueError("cache TTL must be positive")
        self.directory = directory
        self.ttl = ttl

    def load(self, key: str) -> CachedResponse | None:
        path = self._path_for(key)
        if not path.exists():
            return None

        try:
            envelope = json.loads(path.read_text(encoding="utf-8"))
            retrieved_at = datetime.fromisoformat(envelope["retrieved_at"])
            payload = envelope["payload"]
        except (OSError, KeyError, TypeError, ValueError, json.JSONDecodeError) as exc:
            raise CacheError(f"Unable to read cached response {path.name}") from exc

        if retrieved_at.tzinfo is None or not isinstance(payload, dict):
            raise CacheError(f"Cached response {path.name} has an invalid format")
        if datetime.now(UTC) - retrieved_at.astimezone(UTC) > self.ttl:
            return None
        return CachedResponse(payload=payload, retrieved_at=retrieved_at)

    def save(self, key: str, payload: dict[str, Any], retrieved_at: datetime) -> None:
        if retrieved_at.tzinfo is None:
            raise ValueError("retrieved_at must include a timezone")
        path = self._path_for(key)
        envelope = {
            "retrieved_at": retrieved_at.isoformat(),
            "payload": payload,
        }
        temporary_path: Path | None = None
        try:
            path.parent.mkdir(parents=True, exist_ok=True)
            with tempfile.NamedTemporaryFile(
                mode="w",
                encoding="utf-8",
                dir=path.parent,
                delete=False,
                suffix=".tmp",
            ) as temporary_file:
                temporary_path = Path(temporary_file.name)
                json.dump(envelope, temporary_file, allow_nan=False, separators=(",", ":"))
            os.replace(temporary_path, path)
        except (OSError, TypeError, ValueError) as exc:
            raise CacheError(f"Unable to write cached response {path.name}") from exc
        finally:
            if temporary_path is not None:
                try:
                    temporary_path.unlink(missing_ok=True)
                except OSError as exc:
                    raise CacheError(
                        f"Unable to clean up temporary cached response {path.name}"
                    ) from exc

    def _path_for(self, key: str) -> Path:
        if re.fullmatch(r"[a-f0-9]{64}", key) is None:
            raise ValueError("cache key must be a lowercase SHA-256 digest")
        return self.directory / f"{key}.json"
