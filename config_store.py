#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Runtime paths and local configuration storage."""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any, Dict


def runtime_dir() -> Path:
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parent


APP_DIR = runtime_dir()
CONFIG_PATH = APP_DIR / "config.json"
PROMPTS_PATH = APP_DIR / "prompts.txt"
CONVERSATIONS_DIR = APP_DIR / "conversations"
SESSIONS_PATH = CONVERSATIONS_DIR / "sessions.json"


DEFAULT_CONFIG: Dict[str, Any] = {
    "DEEPSEEK_API_KEY": "",
    "DEEPSEEK_BASE_URL": "https://api.deepseek.com",
    "default_model": "deepseek-v4-pro",
    "thinking_modes": {
        "deepseek-v4-pro": "disabled",
        "deepseek-v4-flash": "disabled",
    },
    "theme": "light",
    "language": "en",
    "window_geometry": "980x680",
    "sidebar_width": 218,
}


def ensure_runtime_files() -> None:
    CONVERSATIONS_DIR.mkdir(exist_ok=True)
    if not CONFIG_PATH.exists():
        CONFIG_PATH.write_text(
            json.dumps(DEFAULT_CONFIG, ensure_ascii=True, indent=2),
            encoding="utf-8",
        )
    if not PROMPTS_PATH.exists():
        PROMPTS_PATH.write_text("You are a helpful assistant.\n", encoding="utf-8")


def load_config() -> Dict[str, Any]:
    ensure_runtime_files()
    try:
        data = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        data = {}
    return {**DEFAULT_CONFIG, **data}


def save_config(config: Dict[str, Any]) -> None:
    ensure_runtime_files()
    CONFIG_PATH.write_text(
        json.dumps({**DEFAULT_CONFIG, **config}, ensure_ascii=True, indent=2),
        encoding="utf-8",
    )


def load_system_prompt() -> str:
    ensure_runtime_files()
    prompt = PROMPTS_PATH.read_text(encoding="utf-8").strip()
    return prompt or "You are a helpful assistant."
