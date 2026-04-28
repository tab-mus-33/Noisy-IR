"""
JSON-backed cache for NER results and synonym lookups.

Prevents re-running expensive NER inference or API calls on documents
that have already been processed. Cache is keyed by document ID (NER)
or normalised entity string (synonyms).
"""

import json
import threading
from pathlib import Path


class JsonCache:
    """Thread-safe, write-through JSON cache stored on disk."""

    def __init__(self, path: str | Path):
        self._path = Path(path)
        self._path.parent.mkdir(parents=True, exist_ok=True)
        self._lock = threading.Lock()
        self._data: dict = {}
        self._load()

    def _load(self) -> None:
        if self._path.exists():
            with open(self._path, encoding="utf-8") as f:
                self._data = json.load(f)

    def _save(self) -> None:
        with open(self._path, "w", encoding="utf-8") as f:
            json.dump(self._data, f, ensure_ascii=False, indent=2)

    def get(self, key: str):
        with self._lock:
            return self._data.get(key)

    def set(self, key: str, value) -> None:
        with self._lock:
            self._data[key] = value
            self._save()

    def __contains__(self, key: str) -> bool:
        with self._lock:
            return key in self._data

    def __len__(self) -> int:
        with self._lock:
            return len(self._data)

    def keys(self):
        with self._lock:
            return list(self._data.keys())
