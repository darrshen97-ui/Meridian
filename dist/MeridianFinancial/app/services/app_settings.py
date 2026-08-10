"""Small app-level runtime settings (model choice) persisted in DATA_DIR.

Env vars stay the source of truth for infrastructure config; this file holds
only the choices the Settings screen can change at runtime.
"""
from __future__ import annotations

import json

from app.core.config import get_settings

FILENAME = "app_settings.json"


def _path():
    return get_settings().data_dir / FILENAME


def read_app_settings() -> dict:
    try:
        return json.loads(_path().read_text())
    except (OSError, ValueError):
        return {}


def write_app_settings(values: dict) -> None:
    current = read_app_settings()
    current.update(values)
    _path().parent.mkdir(parents=True, exist_ok=True)
    _path().write_text(json.dumps(current, indent=1))
