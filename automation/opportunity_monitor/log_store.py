"""Append-only JSON-lines log of every scored opportunity. This is the
Reception-Pattern Log data source (design doc section 5) — never
written into the Excel tracker directly; Evan promotes entries into
that himself."""

import json
from pathlib import Path


def append_entry(log_path: Path, entry: dict) -> None:
    log_path.parent.mkdir(parents=True, exist_ok=True)
    with open(log_path, "a", encoding="utf-8") as f:
        f.write(json.dumps(entry) + "\n")


def read_all_entries(log_path: Path) -> list[dict]:
    if not log_path.exists():
        return []
    with open(log_path, "r", encoding="utf-8") as f:
        return [json.loads(line) for line in f if line.strip()]
