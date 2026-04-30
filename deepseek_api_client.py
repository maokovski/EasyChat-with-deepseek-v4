#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
DeepSeek V4 API wrapper using the OpenAI-compatible SDK.

Install dependency:
    pip install openai

Set API key before running:
    Open API Settings in the app, or edit config.json next to the program.
"""

from __future__ import annotations

import json
import queue
import re
import sys
import threading
import tkinter as tk
import time
import webbrowser
from pathlib import Path
from tkinter import filedialog, messagebox, scrolledtext, ttk
from typing import Any, Dict, Iterator, List, Literal, Optional
from ctypes import windll

from openai import OpenAI


Message = Dict[str, Any]
ThinkingType = Literal["enabled", "disabled"]
ReasoningEffort = Literal["high", "max"]


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


def configure_windows_dpi_awareness() -> None:
    if sys.platform != "win32":
        return
    try:
        windll.shcore.SetProcessDpiAwareness(1)
    except Exception:
        try:
            windll.user32.SetProcessDPIAware()
        except Exception:
            pass


def configure_tk_scaling(root: tk.Tk) -> None:
    pixels_per_inch = root.winfo_fpixels("1i")
    if pixels_per_inch > 0:
        root.tk.call("tk", "scaling", pixels_per_inch / 72.0)


class DeepSeekClient:
    """Small client for DeepSeek's OpenAI-compatible Chat API."""

    DEFAULT_BASE_URL = "https://api.deepseek.com"
    DEFAULT_MODEL = "deepseek-v4-pro"
    FLASH_MODEL = "deepseek-v4-flash"

    def __init__(
        self,
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
    ) -> None:
        config = load_config()
        self.api_key = api_key or str(config.get("DEEPSEEK_API_KEY") or "").strip()
        if not self.api_key:
            raise ValueError(
                f"Missing DeepSeek API key. Open API Settings or fill {CONFIG_PATH.name}."
            )

        self.base_url = (
            base_url
            or str(config.get("DEEPSEEK_BASE_URL") or "").strip()
            or self.DEFAULT_BASE_URL
        )
        self.client = OpenAI(api_key=self.api_key, base_url=self.base_url)

    def chat(
        self,
        messages: List[Message],
        model: str = DEFAULT_MODEL,
        thinking: Optional[ThinkingType] = None,
        reasoning_effort: ReasoningEffort = "high",
        temperature: Optional[float] = None,
        top_p: Optional[float] = None,
        max_tokens: Optional[int] = None,
        stream: bool = False,
        **kwargs: Any,
    ) -> Any:
        """Create a chat completion."""
        if not messages:
            raise ValueError("messages must contain at least one message.")

        params: Dict[str, Any] = {
            "model": model,
            "messages": messages,
            "stream": stream,
            **kwargs,
        }

        if temperature is not None:
            params["temperature"] = temperature
        if top_p is not None:
            params["top_p"] = top_p
        if max_tokens is not None:
            params["max_tokens"] = max_tokens

        if thinking is not None:
            if thinking not in ("enabled", "disabled"):
                raise ValueError('thinking must be "enabled", "disabled", or None.')
            if reasoning_effort not in ("high", "max"):
                raise ValueError('reasoning_effort must be "high" or "max".')

            extra_body = dict(params.pop("extra_body", {}) or {})
            extra_body["thinking"] = {"type": thinking}
            params["extra_body"] = extra_body

            if thinking == "enabled":
                params["reasoning_effort"] = reasoning_effort

        return self.client.chat.completions.create(**params)

    def simple_chat(
        self,
        user_message: str,
        system_message: str = "You are a helpful assistant.",
        **kwargs: Any,
    ) -> str:
        """Send one user message and return assistant text."""
        response = self.chat(
            messages=[
                {"role": "system", "content": system_message},
                {"role": "user", "content": user_message},
            ],
            **kwargs,
        )
        return response.choices[0].message.content or ""

    def stream_chat(
        self,
        messages: List[Message],
        include_reasoning: bool = False,
        **kwargs: Any,
    ) -> Iterator[str]:
        """Stream assistant text chunks."""
        response = self.chat(messages=messages, stream=True, **kwargs)
        for chunk in response:
            if not chunk.choices:
                continue

            delta = chunk.choices[0].delta
            reasoning = getattr(delta, "reasoning_content", None)
            content = getattr(delta, "content", None)

            if include_reasoning and reasoning:
                yield reasoning
            if content:
                yield content


DeepSeekV4Client = DeepSeekClient


CHAT_BODY_FONT = ("Microsoft YaHei UI", 12)
CHAT_BODY_BOLD_FONT = ("Microsoft YaHei UI", 12, "bold")
CHAT_BODY_ITALIC_FONT = ("Microsoft YaHei UI", 12, "italic")
CHAT_BODY_BOLD_ITALIC_FONT = ("Microsoft YaHei UI", 12, "bold italic")
CHAT_HEADING_FONT = ("Microsoft YaHei UI", 14, "bold")
CHAT_CODE_FONT = ("Cascadia Mono", 11)
CHAT_TABLE_FONT = ("Cascadia Mono", 11)
CHAT_SUPSUB_FONT = ("Microsoft YaHei UI", 9)
CHAT_EMOJI_FONT = ("Segoe UI Emoji", 12)
CHAT_META_FONT = ("Microsoft YaHei UI", 9)
INPUT_FONT = ("Microsoft YaHei UI", 12)
UI_FONT = ("Microsoft YaHei UI", 10)
CONTEXT_RECENT_MESSAGE_COUNT = 10
SUMMARY_BATCH_MIN_MESSAGES = 4
SUMMARY_SYSTEM_PROMPT = (
    "You organize conversation memory. Compress older messages into a concise "
    "but complete summary. Preserve user goals, key decisions, project "
    "constraints, completed changes, todos, important facts, and preferences. "
    "Do not add information that is not present in the original messages."
)
UI_TEXT = {
    "en": {
        "new_chat": "New Chat",
        "current_model": "Current Model",
        "thinking": "Thinking",
        "thinking_off": "Off",
        "history": "History",
        "theme_light": "Light",
        "theme_dark": "Dark",
        "api_settings": "API Settings",
        "regenerate": "Regenerate",
        "save_txt": "Save .txt",
        "clear": "Clear",
        "initial_hint": "Type below. Enter sends, Shift+Enter inserts a new line.",
        "image": "Image",
        "new_session_title": "New chat",
        "untitled_chat": "Untitled chat",
        "new_chat_started": "New chat started. Enter sends, Shift+Enter inserts a new line.",
        "please_wait": "Please Wait",
        "api_busy": "A request is still running. Change API settings after it finishes.",
        "api_key_missing_title": "DeepSeek API Key Missing",
        "api_key_missing_body": "Please open API Settings or fill config.json next to this program.",
        "api_saved_title": "API Settings Saved",
        "api_saved_error": "Settings were saved, but the client could not start:",
        "api_saved_ok": "API settings saved and applied.",
        "api_required": "API Key is required before requests can be sent.",
        "show_api_key": "Show API Key",
        "cancel": "Cancel",
        "save": "Save",
        "cannot_regenerate": "Cannot Regenerate",
        "no_regenerate_chat": "There is no conversation to regenerate yet.",
        "send_first": "Please send a question first.",
        "regenerate_notice": "Regenerating the previous answer.",
        "nothing_to_save": "Nothing To Save",
        "empty_session": "The current session has no content.",
        "save_current_session": "Save Current Session",
        "this_conversation": "this conversation",
        "delete_history": "Delete History",
        "delete_confirm": "Delete \"{title}\"?\n\nThis cannot be undone.",
        "history_deleted": "History deleted. Enter sends, Shift+Enter inserts a new line.",
        "cannot_delete": "Cannot Delete",
        "select_history": "Select a history item on the left first.",
        "cleared": "Cleared. Enter sends, Shift+Enter inserts a new line.",
        "summary_none": "None.",
        "summary_prompt": "Existing summary:\n{old_summary}\n\nOlder messages to merge:\n{new_context}\n\nOutput the updated summary.",
        "summary_context": "A compressed summary of earlier messages follows. Use it as long-term context, while prioritizing the recent full messages:\n{summary}",
        "language": "Language",
    },
    "zh": {
        "new_chat": "\u65b0\u5bf9\u8bdd",
        "current_model": "\u5f53\u524d\u6a21\u578b",
        "thinking": "\u601d\u8003",
        "thinking_off": "\u5173\u95ed",
        "history": "\u5bf9\u8bdd\u8bb0\u5f55",
        "theme_light": "\u6d45\u8272",
        "theme_dark": "\u6df1\u8272",
        "api_settings": "API \u8bbe\u7f6e",
        "regenerate": "\u91cd\u65b0\u751f\u6210",
        "save_txt": "\u4fdd\u5b58 .txt",
        "clear": "\u6e05\u5c4f",
        "initial_hint": "\u5728\u4e0b\u65b9\u8f93\u5165\u95ee\u9898\u3002Enter \u53d1\u9001\uff0cShift+Enter \u6362\u884c\u3002",
        "image": "\u56fe\u7247",
        "new_session_title": "\u65b0\u5bf9\u8bdd",
        "untitled_chat": "\u672a\u547d\u540d\u5bf9\u8bdd",
        "new_chat_started": "\u65b0\u5bf9\u8bdd\u5df2\u5f00\u59cb\u3002Enter \u53d1\u9001\uff0cShift+Enter \u6362\u884c\u3002",
        "please_wait": "\u8bf7\u7a0d\u5019",
        "api_busy": "\u5f53\u524d\u8bf7\u6c42\u8fd8\u5728\u8fdb\u884c\u4e2d\uff0c\u8bf7\u7ed3\u675f\u540e\u518d\u4fee\u6539 API \u8bbe\u7f6e\u3002",
        "api_key_missing_title": "DeepSeek API Key \u7f3a\u5931",
        "api_key_missing_body": "\u8bf7\u6253\u5f00 API \u8bbe\u7f6e\uff0c\u6216\u586b\u5199\u7a0b\u5e8f\u65c1\u7684 config.json\u3002",
        "api_saved_title": "API \u8bbe\u7f6e\u5df2\u4fdd\u5b58",
        "api_saved_error": "\u914d\u7f6e\u5df2\u4fdd\u5b58\uff0c\u4f46\u5ba2\u6237\u7aef\u521d\u59cb\u5316\u5931\u8d25\uff1a",
        "api_saved_ok": "API \u8bbe\u7f6e\u5df2\u4fdd\u5b58\u5e76\u751f\u6548\u3002",
        "api_required": "\u53d1\u9001\u8bf7\u6c42\u524d\u5fc5\u987b\u586b\u5199 API Key\u3002",
        "show_api_key": "\u663e\u793a API Key",
        "cancel": "\u53d6\u6d88",
        "save": "\u4fdd\u5b58",
        "cannot_regenerate": "\u65e0\u6cd5\u91cd\u65b0\u751f\u6210",
        "no_regenerate_chat": "\u8fd8\u6ca1\u6709\u53ef\u4ee5\u91cd\u65b0\u751f\u6210\u7684\u5bf9\u8bdd\u3002",
        "send_first": "\u8bf7\u5148\u53d1\u9001\u4e00\u4e2a\u95ee\u9898\u3002",
        "regenerate_notice": "\u91cd\u65b0\u751f\u6210\u4e0a\u4e00\u6761\u56de\u590d\u3002",
        "nothing_to_save": "\u65e0\u9700\u4fdd\u5b58",
        "empty_session": "\u5f53\u524d\u4f1a\u8bdd\u6ca1\u6709\u5185\u5bb9\u3002",
        "save_current_session": "\u4fdd\u5b58\u5f53\u524d\u4f1a\u8bdd",
        "this_conversation": "\u8fd9\u6761\u5bf9\u8bdd",
        "delete_history": "\u5220\u9664\u5386\u53f2\u8bb0\u5f55",
        "delete_confirm": "\u786e\u5b9a\u5220\u9664\u300c{title}\u300d\u5417\uff1f\n\n\u6b64\u64cd\u4f5c\u4e0d\u53ef\u6062\u590d\u3002",
        "history_deleted": "\u5386\u53f2\u8bb0\u5f55\u5df2\u5220\u9664\u3002Enter \u53d1\u9001\uff0cShift+Enter \u6362\u884c\u3002",
        "cannot_delete": "\u65e0\u6cd5\u5220\u9664",
        "select_history": "\u8bf7\u5148\u5728\u5de6\u4fa7\u9009\u62e9\u4e00\u6761\u5386\u53f2\u8bb0\u5f55\u3002",
        "cleared": "\u5df2\u6e05\u5c4f\u3002Enter \u53d1\u9001\uff0cShift+Enter \u6362\u884c\u3002",
        "summary_none": "\u65e0\u3002",
        "summary_prompt": "\u5df2\u6709\u6458\u8981\uff1a\n{old_summary}\n\n\u9700\u8981\u5e76\u5165\u6458\u8981\u7684\u65e7\u5bf9\u8bdd\uff1a\n{new_context}\n\n\u8bf7\u8f93\u51fa\u66f4\u65b0\u540e\u7684\u6458\u8981\u3002",
        "summary_context": "\u6b64\u524d\u8f83\u65e9\u5bf9\u8bdd\u7684\u538b\u7f29\u6458\u8981\u5982\u4e0b\u3002\u56de\u7b54\u65f6\u8bf7\u628a\u5b83\u4f5c\u4e3a\u957f\u671f\u4e0a\u4e0b\u6587\u53c2\u8003\uff0c\u540c\u65f6\u4f18\u5148\u9075\u5faa\u6700\u8fd1\u539f\u6587\u6d88\u606f\uff1a\n{summary}",
        "language": "\u8bed\u8a00",
    },
}
EMOJI_PATTERN = re.compile(
    "["
    "\U0001f1e6-\U0001f1ff"
    "\U0001f300-\U0001f5ff"
    "\U0001f600-\U0001f64f"
    "\U0001f680-\U0001f6ff"
    "\U0001f700-\U0001f77f"
    "\U0001f780-\U0001f7ff"
    "\U0001f800-\U0001f8ff"
    "\U0001f900-\U0001f9ff"
    "\U0001fa70-\U0001faff"
    "\u2600-\u27bf"
    "]+"
)
CHAT_LINE_SPACING = {
    "message_before": 5,
    "message_wrap": 3,
    "message_after": 10,
    "system_before": 3,
    "system_wrap": 2,
    "system_after": 8,
    "input_before": 1,
    "input_wrap": 2,
    "input_after": 1,
}


def format_latex_for_text_widget(text: str) -> str:
    """Make common Markdown/LaTeX math output easier to read in Tk text."""
    replacements = {
        r"\times": "×",
        r"\cdot": "·",
        r"\div": "÷",
        r"\pm": "±",
        r"\leq": "≤",
        r"\geq": "≥",
        r"\neq": "≠",
        r"\approx": "≈",
        r"\infty": "∞",
        r"\rightarrow": "→",
        r"\to": "→",
        r"\alpha": "α",
        r"\beta": "β",
        r"\gamma": "γ",
        r"\delta": "δ",
        r"\epsilon": "ε",
        r"\theta": "θ",
        r"\lambda": "λ",
        r"\mu": "μ",
        r"\pi": "π",
        r"\sigma": "σ",
        r"\omega": "ω",
        r"\sum": "Σ",
        r"\prod": "Π",
        r"\int": "∫",
        r"\left": "",
        r"\right": "",
    }

    def display_formula(match: re.Match[str]) -> str:
        formula = match.group(1).strip()
        return f"\n[Formula]\n{formula}\n"

    def inline_formula(match: re.Match[str]) -> str:
        formula = match.group(1).strip()
        return f" {formula} "

    def fraction(match: re.Match[str]) -> str:
        numerator = match.group(1).strip()
        denominator = match.group(2).strip()
        return f"({numerator})/({denominator})"

    def sqrt(match: re.Match[str]) -> str:
        return f"sqrt({match.group(1).strip()})"

    def protect_inline_code(segment: str) -> tuple[str, Dict[str, str]]:
        protected: Dict[str, str] = {}

        def replace(match: re.Match[str]) -> str:
            key = f"@@INLINE_CODE_{len(protected)}@@"
            protected[key] = match.group(0)
            return key

        return re.sub(r"`[^`\n]+`", replace, segment), protected

    def restore_inline_code(segment: str, protected: Dict[str, str]) -> str:
        for key, value in protected.items():
            segment = segment.replace(key, value)
        return segment

    def format_segment(segment: str) -> str:
        segment, protected = protect_inline_code(segment)
        segment = re.sub(r"\\\[(.*?)\\\]", display_formula, segment, flags=re.DOTALL)
        segment = re.sub(r"\$\$(.*?)\$\$", display_formula, segment, flags=re.DOTALL)
        segment = re.sub(r"\\\((.*?)\\\)", inline_formula, segment, flags=re.DOTALL)
        segment = re.sub(r"(?<!\\)\$(.+?)(?<!\\)\$", inline_formula, segment, flags=re.DOTALL)
        segment = re.sub(r"\\frac\{([^{}]+)\}\{([^{}]+)\}", fraction, segment)
        segment = re.sub(r"\\sqrt\{([^{}]+)\}", sqrt, segment)

        for raw, formatted in replacements.items():
            segment = segment.replace(raw, formatted)

        return restore_inline_code(segment, protected)

    parts = re.split(r"(```.*?```)", text, flags=re.DOTALL)
    text = "".join(part if part.startswith("```") else format_segment(part) for part in parts)
    return re.sub(r"\n{3,}", "\n\n", text).strip()


def format_paragraphs_for_reading(text: str, indent: bool = True) -> str:
    """Normalize prose paragraphs into a Chinese-paper-like reading rhythm."""
    lines = [line.rstrip() for line in text.strip().splitlines()]
    blocks: List[str] = []
    current: List[str] = []
    in_code_block = False

    def is_markdown_block_line(stripped: str) -> bool:
        return any(
            (
                re.match(r"#{1,6}\s+", stripped),
                re.match(r"[-*_]{3,}$", stripped),
                re.match(r"[-*+]\s+", stripped),
                re.match(r"\d+[.)]\s+", stripped),
                re.match(r">\s?", stripped),
                re.match(r"\|.*\|$", stripped),
                re.match(r":?-{3,}:?(\s*\|\s*:?-{3,}:?)+$", stripped),
                stripped.startswith("[Formula]"),
            )
        )

    def flush_current() -> None:
        if current:
            paragraph = " ".join(part.strip() for part in current if part.strip())
            if paragraph:
                blocks.append(f"　　{paragraph}" if indent else paragraph)
            current.clear()

    for line in lines:
        stripped = line.strip()
        if stripped.startswith("```"):
            flush_current()
            in_code_block = not in_code_block
            blocks.append(line)
            continue

        if in_code_block:
            blocks.append(line)
            continue

        if not stripped:
            flush_current()
            continue

        if is_markdown_block_line(stripped):
            flush_current()
            blocks.append(stripped)
            continue

        current.append(stripped)

    flush_current()
    return "\n".join(blocks).strip("\n")


class DeepSeekChatApp:
    """Small desktop chat window for manually asking DeepSeek questions."""

    def __init__(self, root: tk.Tk) -> None:
        ensure_runtime_files()
        self.app_config = load_config()
        self.system_prompt = load_system_prompt()
        self.root = root
        self.root.title("DeepSeek Chat")
        self.root.geometry(str(self.app_config.get("window_geometry") or "980x680"))
        self.root.minsize(640, 460)

        self.client: Optional[DeepSeekClient] = None
        self.messages: List[Message] = [
            {"role": "system", "content": self.system_prompt}
        ]
        self.model_name = str(
            self.app_config.get("default_model") or DeepSeekClient.DEFAULT_MODEL
        )
        if self.model_name not in (DeepSeekClient.DEFAULT_MODEL, DeepSeekClient.FLASH_MODEL):
            self.model_name = DeepSeekClient.DEFAULT_MODEL
        self.thinking_modes = self._load_thinking_modes()
        self.conversation_count = 0
        self.result_queue: "queue.Queue[tuple[str, int, str, float, str, str, int]]" = queue.Queue()
        self.is_waiting = False
        self.dark_mode = str(self.app_config.get("theme") or "light") == "dark"
        self.language = self._normalize_language(str(self.app_config.get("language") or "en"))
        self.sidebar_visible = True
        self.sidebar_width = self._normalize_sidebar_width(
            self.app_config.get("sidebar_width")
        )
        self.sidebar_drag_start_x = 0
        self.sidebar_drag_start_width = self.sidebar_width
        self.transcript: List[str] = []
        self.display_entries: List[tuple[str, str, str]] = []
        self.sessions: List[Dict[str, Any]] = self._load_sessions_from_disk()
        self.active_session_index: Optional[int] = None
        self.conversation_summary = ""
        self.summarized_message_count = 0
        self.link_count = 0
        self.history_rows: List[tuple[tk.Frame, tk.Button, tk.Button]] = []
        self.api_settings_window: Optional[tk.Toplevel] = None
        self.style = ttk.Style()

        self._build_ui()
        self._refresh_history_list()
        self._poll_results()

        try:
            self.client = DeepSeekClient()
        except Exception as exc:
            messagebox.showerror(
                "DeepSeek API Key Missing",
                f"{self._text('api_key_missing_body')}\n\n"
                f"Details: {exc}",
            )

    def _build_ui(self) -> None:
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)

        self.main_frame = tk.Frame(self.root, bd=0, highlightthickness=0)
        self.main_frame.grid(row=0, column=0, sticky="nsew")
        self.main_frame.columnconfigure(2, weight=1)
        self.main_frame.rowconfigure(0, weight=1)

        self.sidebar = tk.Frame(
            self.main_frame,
            width=self.sidebar_width,
            bd=0,
            highlightthickness=0,
        )
        self.sidebar.grid(row=0, column=0, sticky="ns")
        self.sidebar.grid_propagate(False)
        self.sidebar.columnconfigure(0, weight=1)

        self.sidebar_header = tk.Frame(self.sidebar, bd=0, highlightthickness=0)
        self.sidebar_header.grid(row=0, column=0, sticky="ew", padx=14, pady=(16, 12))
        self.sidebar_header.columnconfigure(0, weight=1)

        self.brand_label = tk.Label(
            self.sidebar_header,
            text="EasyChat",
            anchor="w",
            font=("Segoe UI", 18, "bold"),
        )
        self.brand_label.grid(row=0, column=0, sticky="ew", padx=(2, 4))

        self.brand_subtitle = tk.Label(
            self.sidebar_header,
            text="DeepSeek V4",
            anchor="w",
            font=("Segoe UI", 9),
        )
        self.brand_subtitle.grid(row=1, column=0, sticky="ew", padx=(2, 4), pady=(1, 0))

        self.sidebar_close_button = tk.Button(
            self.sidebar_header,
            text="×",
            width=3,
            relief=tk.FLAT,
            bd=0,
            command=self.toggle_sidebar,
        )
        self.sidebar_close_button.grid(row=0, column=1, rowspan=2, sticky="ne")

        self.new_chat_button = tk.Button(
            self.sidebar,
            text=f"+  {self._text('new_chat')}",
            relief=tk.FLAT,
            bd=0,
            anchor="w",
            command=self.new_chat,
        )
        self.new_chat_button.grid(row=1, column=0, sticky="ew", padx=14, pady=(0, 14), ipady=10)

        self.model_panel = tk.Frame(self.sidebar, bd=0, highlightthickness=1)
        self.model_panel.grid(row=2, column=0, sticky="ew", padx=14, pady=(0, 14))
        self.model_panel.columnconfigure(0, weight=1)

        self.model_title = tk.Label(
            self.model_panel,
            text=self._text("current_model"),
            anchor="w",
            font=("Microsoft YaHei UI", 9),
        )
        self.model_title.grid(row=0, column=0, sticky="ew", padx=12, pady=(10, 2))

        self.model_label = tk.Label(
            self.model_panel,
            text=self.model_name,
            anchor="w",
            font=("Segoe UI", 10, "bold"),
        )
        self.model_label.grid(row=1, column=0, sticky="ew", padx=12, pady=(0, 10))

        self.pro_button = tk.Button(
            self.model_panel,
            text="V4 Pro",
            relief=tk.FLAT,
            bd=0,
            anchor="w",
            command=lambda: self.set_model(DeepSeekClient.DEFAULT_MODEL),
        )
        self.pro_button.grid(row=2, column=0, sticky="ew", padx=8, pady=(0, 6), ipady=8)

        self.flash_button = tk.Button(
            self.model_panel,
            text="V4 Flash",
            relief=tk.FLAT,
            bd=0,
            anchor="w",
            command=lambda: self.set_model(DeepSeekClient.FLASH_MODEL),
        )
        self.flash_button.grid(row=3, column=0, sticky="ew", padx=8, pady=(0, 6), ipady=8)

        self.thinking_button = tk.Button(
            self.model_panel,
            text=f"Thinking: {self._thinking_mode_label()}",
            relief=tk.FLAT,
            bd=0,
            anchor="w",
            command=self.toggle_thinking_mode,
        )
        self.thinking_button.grid(row=4, column=0, sticky="ew", padx=8, pady=(0, 8), ipady=8)

        self.history_title = tk.Label(
            self.sidebar,
            text=self._text("history"),
            anchor="w",
            font=("Microsoft YaHei UI", 9),
        )
        self.history_title.grid(row=3, column=0, sticky="ew", padx=18, pady=(0, 6))

        self.history_frame = tk.Frame(
            self.sidebar,
            bd=0,
            highlightthickness=0,
            relief=tk.FLAT,
        )
        self.history_frame.grid(row=4, column=0, sticky="nsew", padx=14, pady=(0, 12))
        self.history_frame.columnconfigure(0, weight=1)

        self.sidebar_spacer = tk.Frame(self.sidebar, bd=0, highlightthickness=0)
        self.sidebar_spacer.grid(row=5, column=0, sticky="nsew")
        self.sidebar.rowconfigure(4, weight=1)

        self.sidebar_actions = tk.Frame(self.sidebar, bd=0, highlightthickness=1)
        self.sidebar_actions.grid(row=6, column=0, sticky="ew", padx=14, pady=(0, 16))
        self.sidebar_actions.columnconfigure(0, weight=1)

        self.theme_button = tk.Button(
            self.sidebar_actions,
            text=self._text("theme_dark"),
            relief=tk.FLAT,
            bd=0,
            anchor="w",
            command=self.toggle_theme,
        )
        self.theme_button.grid(row=0, column=0, sticky="ew", padx=8, pady=(8, 6), ipady=8)

        self.regenerate_button = tk.Button(
            self.sidebar_actions,
            text=f"R  {self._text('regenerate')}",
            relief=tk.FLAT,
            bd=0,
            anchor="w",
            command=self.regenerate_last,
        )
        self.regenerate_button.grid(row=1, column=0, sticky="ew", padx=8, pady=(0, 6), ipady=8)

        self.save_button = tk.Button(
            self.sidebar_actions,
            text=f"S  {self._text('save_txt')}",
            relief=tk.FLAT,
            bd=0,
            anchor="w",
            command=self.save_transcript,
        )
        self.save_button.grid(row=2, column=0, sticky="ew", padx=8, pady=(0, 6), ipady=8)

        self.clear_button = tk.Button(
            self.sidebar_actions,
            text=f"C  {self._text('clear')}",
            relief=tk.FLAT,
            bd=0,
            anchor="w",
            command=self.clear_chat,
        )
        self.clear_button.grid(row=3, column=0, sticky="ew", padx=8, pady=(0, 8), ipady=8)

        self.sidebar_resize_handle = tk.Frame(
            self.main_frame,
            width=5,
            bd=0,
            highlightthickness=0,
            cursor="sb_h_double_arrow",
        )
        self.sidebar_resize_handle.grid(row=0, column=1, sticky="ns")
        self.sidebar_resize_handle.bind("<ButtonPress-1>", self._start_sidebar_resize)
        self.sidebar_resize_handle.bind("<B1-Motion>", self._drag_sidebar_resize)
        self.sidebar_resize_handle.bind("<ButtonRelease-1>", self._finish_sidebar_resize)

        self.content_frame = tk.Frame(self.main_frame, bd=0, highlightthickness=0)
        self.content_frame.grid(row=0, column=2, sticky="nsew")
        self.content_frame.columnconfigure(0, weight=1)
        self.content_frame.rowconfigure(1, weight=1)

        self.topbar = tk.Frame(self.content_frame, bd=0, highlightthickness=1)
        self.topbar.grid(row=0, column=0, sticky="ew", padx=24, pady=(18, 12))
        self.topbar.columnconfigure(1, weight=1)

        self.sidebar_open_button = tk.Button(
            self.topbar,
            text="☰",
            width=3,
            relief=tk.FLAT,
            bd=0,
            command=self.toggle_sidebar,
        )
        self.sidebar_open_button.grid(row=0, column=0, sticky="w", padx=(10, 10), pady=8)

        self.title_label = tk.Label(
            self.topbar,
            text="DeepSeek",
            anchor="w",
            font=("Segoe UI", 14, "bold"),
        )
        self.title_label.grid(row=0, column=1, sticky="w", pady=8)

        self.model_badge = tk.Label(
            self.topbar,
            text=self.model_name,
            font=("Segoe UI", 9),
            padx=10,
            pady=4,
        )
        self.model_badge.grid(row=0, column=2, sticky="e", pady=8)

        self.language_label = tk.Label(
            self.topbar,
            text=self._text("language"),
            anchor="e",
            font=("Segoe UI", 9),
        )
        self.language_label.grid(row=0, column=3, sticky="e", padx=(14, 6), pady=8)

        self.language_var = tk.StringVar(value=self._language_display_name(self.language))
        self.language_menu = tk.OptionMenu(
            self.topbar,
            self.language_var,
            "English",
            "Chinese",
            command=lambda _value: self.set_language_from_menu(),
        )
        self.language_menu.configure(relief=tk.FLAT, bd=0, highlightthickness=0)
        self.language_menu.grid(row=0, column=4, sticky="e", padx=(0, 8), pady=8)

        self.api_settings_button = tk.Button(
            self.topbar,
            text=self._text("api_settings"),
            relief=tk.FLAT,
            bd=0,
            padx=10,
            pady=4,
            command=self.open_api_settings,
        )
        self.api_settings_button.grid(row=0, column=5, sticky="e", padx=(0, 10), pady=8)

        self.chat_panel = tk.Frame(self.content_frame, bd=0, highlightthickness=1)
        self.chat_panel.grid(row=1, column=0, sticky="nsew", padx=24, pady=(0, 10))
        self.chat_panel.columnconfigure(0, weight=1)
        self.chat_panel.rowconfigure(0, weight=1)

        self.chat_area = scrolledtext.ScrolledText(
            self.chat_panel,
            wrap=tk.WORD,
            state=tk.DISABLED,
            font=CHAT_BODY_FONT,
            bd=0,
            relief=tk.FLAT,
            padx=28,
            pady=20,
        )
        self.chat_area.grid(row=0, column=0, sticky="nsew", padx=1, pady=1)
        self.chat_area.tag_configure(
            "user",
            justify=tk.RIGHT,
            rmargin=22,
            lmargin1=120,
            lmargin2=120,
            spacing1=CHAT_LINE_SPACING["message_before"],
            spacing2=CHAT_LINE_SPACING["message_wrap"],
            spacing3=CHAT_LINE_SPACING["message_after"],
            font=CHAT_BODY_FONT,
        )
        self.chat_area.tag_configure(
            "assistant",
            justify=tk.LEFT,
            lmargin1=22,
            lmargin2=22,
            rmargin=72,
            spacing1=CHAT_LINE_SPACING["message_before"],
            spacing2=CHAT_LINE_SPACING["message_wrap"],
            spacing3=CHAT_LINE_SPACING["message_after"],
            font=CHAT_BODY_FONT,
        )
        self.chat_area.tag_configure(
            "system",
            justify=tk.CENTER,
            spacing1=CHAT_LINE_SPACING["system_before"],
            spacing2=CHAT_LINE_SPACING["system_wrap"],
            spacing3=CHAT_LINE_SPACING["system_after"],
            font=CHAT_META_FONT,
        )
        self.chat_area.tag_configure(
            "error",
            justify=tk.LEFT,
            lmargin1=22,
            lmargin2=22,
            rmargin=72,
            spacing1=CHAT_LINE_SPACING["message_before"],
            spacing2=CHAT_LINE_SPACING["message_wrap"],
            spacing3=CHAT_LINE_SPACING["message_after"],
            font=CHAT_BODY_FONT,
        )
        self.chat_area.tag_configure("md_speaker", font=CHAT_META_FONT)
        self.chat_area.tag_configure("md_heading", font=CHAT_HEADING_FONT)
        self.chat_area.tag_configure("md_bold", font=CHAT_BODY_BOLD_FONT)
        self.chat_area.tag_configure("md_italic", font=CHAT_BODY_ITALIC_FONT)
        self.chat_area.tag_configure("md_bold_italic", font=CHAT_BODY_BOLD_ITALIC_FONT)
        self.chat_area.tag_configure("md_strike", overstrike=1)
        self.chat_area.tag_configure("md_code", font=CHAT_CODE_FONT)
        self.chat_area.tag_configure("md_table", font=CHAT_TABLE_FONT)
        self.chat_area.tag_configure("md_sup", font=CHAT_SUPSUB_FONT, offset=5)
        self.chat_area.tag_configure("md_sub", font=CHAT_SUPSUB_FONT, offset=-3)
        self.chat_area.tag_configure("md_link", underline=1)
        self.chat_area.tag_configure("md_emoji", font=CHAT_EMOJI_FONT)
        self.chat_area.tag_configure("md_separator", font=CHAT_META_FONT)

        self.status_label = tk.Label(
            self.content_frame,
            text="Ready",
            anchor="w",
            font=("Segoe UI", 9),
        )
        self.status_label.grid(row=2, column=0, sticky="ew", padx=32, pady=(0, 8))

        self.composer_frame = tk.Frame(self.content_frame, bd=0, highlightthickness=1)
        self.composer_frame.grid(row=3, column=0, sticky="ew", padx=24, pady=(0, 24))
        self.composer_frame.columnconfigure(0, weight=1)
        self.input_box = tk.Text(
            self.composer_frame,
            height=4,
            wrap=tk.WORD,
            font=INPUT_FONT,
            bd=0,
            relief=tk.FLAT,
            padx=14,
            pady=12,
            spacing1=CHAT_LINE_SPACING["input_before"],
            spacing2=CHAT_LINE_SPACING["input_wrap"],
            spacing3=CHAT_LINE_SPACING["input_after"],
        )
        self.input_box.grid(row=0, column=0, sticky="ew")
        self.input_box.bind("<Control-Return>", self._send_from_event)
        self.input_box.bind("<Return>", self._send_from_event)
        self.input_box.bind("<Shift-Return>", self._insert_newline)

        self.send_button = tk.Button(
            self.composer_frame,
            text="↑",
            width=3,
            relief=tk.FLAT,
            bd=0,
            font=("Segoe UI", 13, "bold"),
            command=self.send_message,
        )
        self.send_button.grid(row=0, column=1, sticky="ns", padx=(0, 10), pady=10)

        self._append_chat(
            "System",
            self._text("initial_hint"),
        )
        self._refresh_model_display()
        self.apply_theme()

    def _append_chat(self, speaker: str, text: str, tag: str = "assistant") -> None:
        if speaker.startswith("Conversation") and "DeepSeek" in speaker:
            text = format_latex_for_text_widget(text)
            text = format_paragraphs_for_reading(text, indent=True)
        elif tag == "user":
            text = format_paragraphs_for_reading(text, indent=False)
        elif tag == "error":
            text = format_paragraphs_for_reading(text, indent=False)

        entry = f"{speaker}:\n{text.strip()}\n\n"
        self.transcript.append(entry.strip())
        self.display_entries.append((speaker, text.strip(), tag))
        self._insert_chat_entry(speaker, text, tag)

    def _insert_with_tags(self, text: str, base_tag: str, *extra_tags: str) -> None:
        tags = tuple(tag for tag in (base_tag, *extra_tags) if tag)
        if "md_emoji" in tags or "md_code" in tags:
            self.chat_area.insert(tk.END, text, tags)
            return

        position = 0
        for match in EMOJI_PATTERN.finditer(text):
            if match.start() > position:
                self.chat_area.insert(tk.END, text[position : match.start()], tags)
            self.chat_area.insert(tk.END, match.group(0), (*tags, "md_emoji"))
            position = match.end()
        if position < len(text):
            self.chat_area.insert(tk.END, text[position:], tags)

    def _insert_link(self, label: str, url: str, base_tag: str, *extra_tags: str) -> None:
        if url.startswith("www."):
            url = f"https://{url}"
        self.link_count += 1
        link_tag = f"md_link_{self.link_count}"
        self._insert_with_tags(label, base_tag, *extra_tags, "md_link", link_tag)
        self.chat_area.tag_bind(link_tag, "<Button-1>", lambda _event, target=url: webbrowser.open(target))
        self.chat_area.tag_bind(link_tag, "<Enter>", lambda _event: self.chat_area.configure(cursor="hand2"))
        self.chat_area.tag_bind(link_tag, "<Leave>", lambda _event: self.chat_area.configure(cursor=""))

    def _display_width(self, text: str) -> int:
        width = 0
        for char in text:
            code = ord(char)
            if EMOJI_PATTERN.match(char):
                width += 2
            elif (
                0x1100 <= code <= 0x11FF
                or 0x2E80 <= code <= 0xA4CF
                or 0xAC00 <= code <= 0xD7A3
                or 0xF900 <= code <= 0xFAFF
                or 0xFE10 <= code <= 0xFE19
                or 0xFE30 <= code <= 0xFE6F
                or 0xFF00 <= code <= 0xFF60
                or 0xFFE0 <= code <= 0xFFE6
            ):
                width += 2
            else:
                width += 1
        return width

    def _pad_display(self, text: str, width: int) -> str:
        return text + " " * max(0, width - self._display_width(text))

    def _is_table_separator(self, line: str) -> bool:
        cells = [cell.strip() for cell in line.strip().strip("|").split("|")]
        return bool(cells) and all(re.match(r"^:?-{3,}:?$", cell) for cell in cells)

    def _is_table_line(self, line: str) -> bool:
        stripped = line.strip()
        return stripped.startswith("|") and stripped.endswith("|") and stripped.count("|") >= 2

    def _format_table_lines(self, lines: List[str]) -> List[str]:
        rows = [[cell.strip() for cell in line.strip().strip("|").split("|")] for line in lines]
        if not rows:
            return []

        column_count = max(len(row) for row in rows)
        for row in rows:
            row.extend([""] * (column_count - len(row)))

        widths = [0] * column_count
        for row in rows:
            if all(re.match(r"^:?-{3,}:?$", cell) for cell in row):
                continue
            for index, cell in enumerate(row):
                widths[index] = max(widths[index], self._display_width(cell))

        formatted: List[str] = []
        for row in rows:
            if all(re.match(r"^:?-{3,}:?$", cell) for cell in row):
                formatted.append("| " + " | ".join("-" * widths[index] for index in range(column_count)) + " |")
            else:
                formatted.append(
                    "| "
                    + " | ".join(
                        self._pad_display(cell, widths[index]) for index, cell in enumerate(row)
                    )
                    + " |"
                )
        return formatted

    def _insert_table(self, lines: List[str], base_tag: str) -> None:
        for line in self._format_table_lines(lines):
            self._insert_with_tags(f"{line}\n", base_tag, "md_table")

    def _insert_inline_markdown(self, line: str, base_tag: str, *extra_tags: str) -> None:
        pattern = re.compile(
            r"!\[([^\]]*)\]\(([^)\s]+)(?:\s+\"[^\"]*\")?\)"
            r"|\[([^\]]+)\]\(([^)\s]+)(?:\s+\"[^\"]*\")?\)"
            r"|<((?:https?|mailto):[^>\s]+)>"
            r"|(?<![<(\"])\b((?:https?://|www\.)[^\s<>()]+)"
            r"|(?<![@\w:/.-])((?:[a-zA-Z0-9-]+\.)+(?:com|org|net|edu|gov|io|ai|cn|dev|app|co|uk|jp|de|fr|ru|info|me|xyz|site|tech|top|wiki|news|blog)(?:/[^\s<>()]*)?)"
            r"|<sup>(.*?)</sup>"
            r"|<sub>(.*?)</sub>"
            r"|`([^`\n]+)`"
            r"|\*\*\*(.+?)\*\*\*"
            r"|\*\*(.+?)\*\*"
            r"|(?<!\*)\*(?!\s)(.+?)(?<!\s)\*(?!\*)"
            r"|~~(.+?)~~",
            re.IGNORECASE,
        )
        position = 0
        for match in pattern.finditer(line):
            if match.start() > position:
                self._insert_with_tags(line[position : match.start()], base_tag, *extra_tags)

            if match.group(1) is not None:
                label = match.group(1).strip() or self._text("image")
                self._insert_link(f"{self._text('image')}: {label}", match.group(2), base_tag, *extra_tags)
            elif match.group(3) is not None:
                self._insert_link(match.group(3), match.group(4), base_tag, *extra_tags)
            elif match.group(5) is not None:
                self._insert_link(match.group(5), match.group(5), base_tag, *extra_tags)
            elif match.group(6) is not None:
                raw_url = match.group(6)
                trailing = ""
                while raw_url and raw_url[-1] in ".,;:!?)]}，。；：！？）】":
                    trailing = raw_url[-1] + trailing
                    raw_url = raw_url[:-1]
                self._insert_link(raw_url, raw_url, base_tag, *extra_tags)
                if trailing:
                    self._insert_with_tags(trailing, base_tag, *extra_tags)
            elif match.group(7) is not None:
                raw_url = match.group(7)
                trailing = ""
                while raw_url and raw_url[-1] in ".,;:!?)]}，。；：！？）】":
                    trailing = raw_url[-1] + trailing
                    raw_url = raw_url[:-1]
                self._insert_link(raw_url, raw_url, base_tag, *extra_tags)
                if trailing:
                    self._insert_with_tags(trailing, base_tag, *extra_tags)
            elif match.group(8) is not None:
                self._insert_with_tags(match.group(8), base_tag, *extra_tags, "md_sup")
            elif match.group(9) is not None:
                self._insert_with_tags(match.group(9), base_tag, *extra_tags, "md_sub")
            elif match.group(10) is not None:
                self._insert_with_tags(match.group(10), base_tag, *extra_tags, "md_code")
            elif match.group(11) is not None:
                self._insert_with_tags(match.group(11), base_tag, *extra_tags, "md_bold_italic")
            elif match.group(12) is not None:
                self._insert_with_tags(match.group(12), base_tag, *extra_tags, "md_bold")
            elif match.group(13) is not None:
                self._insert_with_tags(match.group(13), base_tag, *extra_tags, "md_italic")
            elif match.group(14) is not None:
                self._insert_with_tags(match.group(14), base_tag, *extra_tags, "md_strike")
            position = match.end()

        if position < len(line):
            self._insert_with_tags(line[position:], base_tag, *extra_tags)

    def _insert_chat_entry(self, speaker: str, text: str, tag: str) -> None:
        self.chat_area.configure(state=tk.NORMAL)
        self._insert_with_tags(f"{speaker}:\n", tag, "md_speaker")

        in_code_block = False
        table_lines: List[str] = []

        def flush_table() -> None:
            if table_lines:
                self._insert_table(table_lines, tag)
                table_lines.clear()

        for line in text.strip().splitlines():
            stripped = line.strip()
            if stripped.startswith("```"):
                flush_table()
                in_code_block = not in_code_block
                continue

            if in_code_block:
                self._insert_with_tags(f"{line}\n", tag, "md_code")
                continue

            if self._is_table_line(stripped):
                table_lines.append(stripped)
                continue

            flush_table()

            heading = re.match(r"#{1,6}\s+(.+)$", stripped)
            if heading:
                self._insert_inline_markdown(heading.group(1), tag, "md_heading")
                self._insert_with_tags("\n", tag, "md_heading")
                continue

            if re.match(r"[-*_]{3,}$", stripped):
                self._insert_with_tags("─" * 42 + "\n", tag, "md_separator")
                continue

            self._insert_inline_markdown(line, tag)
            self._insert_with_tags("\n", tag)

        flush_table()
        self._insert_with_tags("\n", tag)
        self.chat_area.configure(state=tk.DISABLED)
        self.chat_area.see(tk.END)

    def _render_current_chat(self) -> None:
        self.chat_area.configure(state=tk.NORMAL)
        self.chat_area.delete("1.0", tk.END)
        self.chat_area.configure(state=tk.DISABLED)
        for speaker, text, tag in self.display_entries:
            self._insert_chat_entry(speaker, text, tag)

    def _configure_hover_button(
        self,
        button: tk.Button,
        normal_bg: str,
        hover_bg: str,
        normal_fg: str,
        hover_fg: Optional[str] = None,
    ) -> None:
        hover_fg = hover_fg or normal_fg
        button.configure(
            bg=normal_bg,
            fg=normal_fg,
            activebackground=hover_bg,
            activeforeground=hover_fg,
        )

        def on_enter(_event: tk.Event) -> None:
            if str(button.cget("state")) != tk.DISABLED:
                button.configure(bg=hover_bg, fg=hover_fg, cursor="hand2")

        def on_leave(_event: tk.Event) -> None:
            button.configure(bg=normal_bg, fg=normal_fg, cursor="")

        button.bind("<Enter>", on_enter)
        button.bind("<Leave>", on_leave)

    def _normalize_language(self, language: str) -> str:
        return language if language in UI_TEXT else "en"

    def _text(self, key: str) -> str:
        language = self._normalize_language(getattr(self, "language", "en"))
        return UI_TEXT.get(language, UI_TEXT["en"]).get(key, UI_TEXT["en"].get(key, key))

    def _language_display_name(self, language: str) -> str:
        return "Chinese" if self._normalize_language(language) == "zh" else "English"

    def _normalize_sidebar_width(self, value: Any) -> int:
        try:
            width = int(value)
        except (TypeError, ValueError):
            width = 218
        return max(168, min(width, 360))

    def set_language_from_menu(self) -> None:
        selected = self.language_var.get()
        self.language = "zh" if selected == "Chinese" else "en"
        self.app_config["language"] = self.language
        save_config(self.app_config)
        self._refresh_language_text()
        self.status_label.configure(text=f"Language changed to {selected}")

    def _refresh_language_text(self) -> None:
        self.new_chat_button.configure(text=f"+  {self._text('new_chat')}")
        self.model_title.configure(text=self._text("current_model"))
        self.history_title.configure(text=self._text("history"))
        self.regenerate_button.configure(text=f"R  {self._text('regenerate')}")
        self.save_button.configure(text=f"S  {self._text('save_txt')}")
        self.clear_button.configure(text=f"C  {self._text('clear')}")
        self.api_settings_button.configure(text=self._text("api_settings"))
        self.language_label.configure(text=self._text("language"))
        self.language_var.set(self._language_display_name(self.language))
        self._refresh_model_display()

    def _set_sidebar_width(self, width: int) -> None:
        self.sidebar_width = self._normalize_sidebar_width(width)
        self.sidebar.configure(width=self.sidebar_width)
        if self.sidebar_visible:
            self.main_frame.columnconfigure(0, minsize=self.sidebar_width)

    def _start_sidebar_resize(self, event: tk.Event) -> None:
        self.sidebar_drag_start_x = int(event.x_root)
        self.sidebar_drag_start_width = self.sidebar_width

    def _drag_sidebar_resize(self, event: tk.Event) -> None:
        delta = int(event.x_root) - self.sidebar_drag_start_x
        self._set_sidebar_width(self.sidebar_drag_start_width + delta)

    def _finish_sidebar_resize(self, _event: tk.Event) -> None:
        self.app_config["sidebar_width"] = self.sidebar_width
        save_config(self.app_config)

    def _has_real_chat(self) -> bool:
        return any(message.get("role") != "system" for message in self.messages)

    def _session_title(self) -> str:
        for message in self.messages:
            if message.get("role") == "user":
                title = str(message.get("content", "")).strip().replace("\n", " ")
                return title[:22] + ("..." if len(title) > 22 else "")
        return f"{self._text('new_session_title')} {len(self.sessions) + 1}"

    def _save_current_session(self) -> None:
        if not self._has_real_chat():
            return

        session = {
            "title": self._session_title(),
            "messages": [dict(message) for message in self.messages],
            "transcript": list(self.transcript),
            "display_entries": list(self.display_entries),
            "conversation_count": self.conversation_count,
            "model_name": self.model_name,
            "conversation_summary": self.conversation_summary,
            "summarized_message_count": self.summarized_message_count,
        }
        if self.active_session_index is None:
            self.sessions.insert(0, session)
            self.active_session_index = 0
        else:
            self.sessions[self.active_session_index] = session
        self._refresh_history_list()
        self._write_sessions_to_disk()

    def _load_sessions_from_disk(self) -> List[Dict[str, Any]]:
        ensure_runtime_files()
        if not SESSIONS_PATH.exists():
            return []
        try:
            data = json.loads(SESSIONS_PATH.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return []
        if not isinstance(data, list):
            return []
        return [session for session in data if isinstance(session, dict)]

    def _load_thinking_modes(self) -> Dict[str, str]:
        raw_modes = self.app_config.get("thinking_modes")
        modes = raw_modes if isinstance(raw_modes, dict) else {}
        return {
            DeepSeekClient.DEFAULT_MODEL: self._normalize_thinking_mode(
                str(modes.get(DeepSeekClient.DEFAULT_MODEL) or "disabled")
            ),
            DeepSeekClient.FLASH_MODEL: self._normalize_thinking_mode(
                str(modes.get(DeepSeekClient.FLASH_MODEL) or "disabled")
            ),
        }

    def _normalize_thinking_mode(self, mode: str) -> str:
        return mode if mode in ("disabled", "high", "max") else "disabled"

    def _current_thinking_mode(self) -> str:
        return self._normalize_thinking_mode(
            self.thinking_modes.get(self.model_name, "disabled")
        )

    def _thinking_mode_label(self) -> str:
        mode = self._current_thinking_mode()
        labels = {
            "disabled": self._text("thinking_off"),
            "high": "High",
            "max": "Max",
        }
        return labels[mode]

    def toggle_thinking_mode(self) -> None:
        if self.is_waiting:
            return

        next_modes = {
            "disabled": "high",
            "high": "max",
            "max": "disabled",
        }
        self.thinking_modes[self.model_name] = next_modes[self._current_thinking_mode()]
        self.app_config["thinking_modes"] = dict(self.thinking_modes)
        save_config(self.app_config)
        self._refresh_model_display()
        self.status_label.configure(
            text=f"{self.model_name} thinking mode: {self._thinking_mode_label()}"
        )

    def _write_sessions_to_disk(self) -> None:
        ensure_runtime_files()
        SESSIONS_PATH.write_text(
            json.dumps(self.sessions, ensure_ascii=True, indent=2),
            encoding="utf-8",
        )

    def _refresh_history_list(self) -> None:
        for row, _title_button, _delete_button in self.history_rows:
            row.destroy()
        self.history_rows = []

        for index, session in enumerate(self.sessions):
            row = tk.Frame(self.history_frame, bd=0, highlightthickness=0)
            row.grid(row=index, column=0, sticky="ew", pady=(0, 4))
            row.columnconfigure(0, weight=1)
            marker = "● " if index == self.active_session_index else ""
            title_button = tk.Button(
                row,
                text=f"{marker}{session.get('title', self._text('untitled_chat'))}",
                relief=tk.FLAT,
                bd=0,
                anchor="w",
                font=("Microsoft YaHei UI", 10),
                command=lambda session_index=index: self.load_session_by_index(session_index),
            )
            title_button.grid(row=0, column=0, sticky="ew")
            delete_button = tk.Button(
                row,
                text="×",
                width=2,
                relief=tk.FLAT,
                bd=0,
                font=("Segoe UI", 10, "bold"),
                command=lambda session_index=index: self.delete_session_by_index(session_index),
            )
            delete_button.grid(row=0, column=1, sticky="e")
            self.history_rows.append((row, title_button, delete_button))
        self.apply_theme()

    def new_chat(self) -> None:
        if self.is_waiting:
            return

        self._save_current_session()
        self.active_session_index = None
        self.messages = [{"role": "system", "content": self.system_prompt}]
        self.transcript = []
        self.display_entries = []
        self.conversation_summary = ""
        self.summarized_message_count = 0
        self.conversation_count = 0
        self.status_label.configure(text="Ready")
        self._append_chat("System", self._text("new_chat_started"), "system")
        self._refresh_history_list()
        self._render_current_chat()

    def load_session_by_index(self, target_index: int) -> None:
        if self.is_waiting:
            return

        if target_index < 0 or target_index >= len(self.sessions):
            return

        if target_index == self.active_session_index:
            return

        inserted_current = self.active_session_index is None and self._has_real_chat()
        self._save_current_session()
        if inserted_current:
            target_index += 1
        self.active_session_index = target_index
        session = self.sessions[target_index]
        self.messages = [dict(message) for message in session["messages"]]
        self.transcript = list(session["transcript"])
        self.display_entries = list(session["display_entries"])
        self.conversation_count = int(session["conversation_count"])
        self.model_name = str(session["model_name"])
        self.conversation_summary = str(session.get("conversation_summary") or "")
        self.summarized_message_count = int(session.get("summarized_message_count") or 0)
        self.status_label.configure(text=f"Loaded - {session['title']}")
        self._refresh_history_list()
        self._refresh_model_display()
        self._render_current_chat()

    def load_selected_session(self, _event: tk.Event) -> None:
        return

    def apply_theme(self) -> None:
        if self.dark_mode:
            page_bg = "#171a1f"
            sidebar_bg = "#111418"
            panel_bg = "#1f242b"
            chat_bg = "#1b2026"
            input_bg = "#222831"
            fg = "#f2f3ef"
            muted = "#a8b0b6"
            border = "#343c46"
            button_bg = "#20262e"
            button_hover = "#2b343f"
            selected_bg = "#29453f"
            accent_bg = "#3dd6b3"
            accent_hover = "#66e4c9"
            send_fg = "#061613"
            accent_fg = "#071613"
            insert = "#ffffff"
        else:
            page_bg = "#f5f6f2"
            sidebar_bg = "#e8ece5"
            panel_bg = "#fbfcf8"
            chat_bg = "#fffefa"
            input_bg = "#ffffff"
            fg = "#1c211f"
            muted = "#65706b"
            border = "#cdd6ce"
            button_bg = "#f2f5ef"
            button_hover = "#e0e8df"
            selected_bg = "#d6eee6"
            accent_bg = "#0f8f75"
            accent_hover = "#0a755f"
            send_fg = "#ffffff"
            accent_fg = "#ffffff"
            insert = "#111111"

        self.root.configure(bg=page_bg)
        self.main_frame.configure(bg=page_bg)
        self.sidebar.configure(bg=sidebar_bg)
        self.sidebar_resize_handle.configure(bg=border)
        self.sidebar_header.configure(bg=sidebar_bg)
        self.sidebar_spacer.configure(bg=sidebar_bg)
        self.model_panel.configure(
            bg=panel_bg,
            highlightbackground=border,
            highlightcolor=border,
        )
        self.sidebar_actions.configure(
            bg=panel_bg,
            highlightbackground=border,
            highlightcolor=border,
        )
        self.content_frame.configure(bg=page_bg)
        self.topbar.configure(
            bg=panel_bg,
            highlightbackground=border,
            highlightcolor=border,
        )
        self.chat_panel.configure(
            bg=border,
            highlightbackground=border,
            highlightcolor=border,
        )
        self.composer_frame.configure(bg=input_bg, highlightbackground=border, highlightcolor=border)

        self.brand_label.configure(bg=sidebar_bg, fg=fg)
        self.brand_subtitle.configure(bg=sidebar_bg, fg=muted)
        self._configure_hover_button(self.sidebar_close_button, button_bg, button_hover, fg)
        self.sidebar_close_button.configure(
            highlightbackground=sidebar_bg,
            highlightcolor=fg,
        )
        self._configure_hover_button(self.sidebar_open_button, panel_bg, button_hover, fg)
        self.sidebar_open_button.configure(
            highlightbackground=panel_bg,
            highlightcolor=fg,
        )
        self.model_title.configure(bg=panel_bg, fg=muted)
        self.model_label.configure(bg=panel_bg, fg=fg)
        self.history_title.configure(bg=sidebar_bg, fg=muted)
        self.history_frame.configure(bg=sidebar_bg)
        for index, (row, title_button, delete_button) in enumerate(self.history_rows):
            selected = index == self.active_session_index
            row_bg = selected_bg if selected else sidebar_bg
            row.configure(bg=row_bg)
            self._configure_hover_button(
                title_button,
                row_bg,
                button_hover,
                fg,
            )
            title_button.configure(
                highlightbackground=row_bg,
                highlightcolor=fg,
            )
            self._configure_hover_button(
                delete_button,
                row_bg,
                button_hover,
                muted,
                fg,
            )
            delete_button.configure(
                highlightbackground=row_bg,
                highlightcolor=fg,
            )
        self.title_label.configure(bg=panel_bg, fg=fg)
        self.model_badge.configure(bg=selected_bg, fg=muted)
        self.language_label.configure(bg=panel_bg, fg=muted)
        self.language_menu.configure(
            bg=button_bg,
            fg=fg,
            activebackground=button_hover,
            activeforeground=fg,
            highlightbackground=panel_bg,
        )
        self.language_menu["menu"].configure(bg=button_bg, fg=fg, activebackground=button_hover)
        self._configure_hover_button(self.api_settings_button, button_bg, button_hover, fg)
        self.api_settings_button.configure(
            highlightbackground=panel_bg,
            highlightcolor=fg,
        )
        self.status_label.configure(bg=page_bg, fg=muted)

        self.style.configure("TFrame", background=page_bg)
        self.style.configure("TLabel", background=page_bg, foreground=fg)
        self.style.configure("TButton", padding=4)
        self._configure_hover_button(self.theme_button, button_bg, button_hover, fg)
        self.theme_button.configure(
            text=f"Light  {self._text('theme_light')}" if self.dark_mode else f"Dark  {self._text('theme_dark')}",
            highlightbackground=panel_bg,
            highlightcolor=fg,
        )
        self._configure_hover_button(self.new_chat_button, accent_bg, accent_hover, accent_fg)
        self.new_chat_button.configure(
            highlightbackground=sidebar_bg,
            highlightcolor=accent_bg,
        )
        self._configure_hover_button(self.thinking_button, button_bg, button_hover, fg)
        self.thinking_button.configure(
            highlightbackground=panel_bg,
            highlightcolor=fg,
        )
        for button in (self.pro_button, self.flash_button):
            selected = (
                button is self.pro_button
                and self.model_name == DeepSeekClient.DEFAULT_MODEL
            ) or (
                button is self.flash_button
                and self.model_name == DeepSeekClient.FLASH_MODEL
            )
            self._configure_hover_button(
                button,
                selected_bg if selected else button_bg,
                button_hover,
                fg,
            )
            button.configure(
                disabledforeground="#777777",
                highlightbackground=panel_bg,
                highlightcolor=fg,
            )
        for button in (
            self.regenerate_button,
            self.save_button,
            self.clear_button,
        ):
            self._configure_hover_button(button, button_bg, button_hover, fg)
            button.configure(
                disabledforeground="#777777",
                highlightbackground=panel_bg,
                highlightcolor=fg,
            )
        self._configure_hover_button(
            self.send_button,
            accent_bg,
            accent_hover,
            send_fg,
            send_fg,
        )
        self.send_button.configure(
            disabledforeground="#c7ccd4",
            highlightbackground=input_bg,
            highlightcolor=accent_bg,
        )
        self.chat_area.configure(bg=chat_bg, fg=fg, insertbackground=insert)
        self.chat_area.tag_configure("md_speaker", foreground=muted)
        self.chat_area.tag_configure("md_heading", foreground=fg)
        self.chat_area.tag_configure("md_bold", foreground=fg)
        self.chat_area.tag_configure("md_italic", foreground=fg)
        self.chat_area.tag_configure("md_bold_italic", foreground=fg)
        self.chat_area.tag_configure("md_strike", foreground=muted)
        self.chat_area.tag_configure(
            "md_code",
            foreground=fg,
            background=selected_bg,
        )
        self.chat_area.tag_configure(
            "md_table",
            foreground=fg,
            background=selected_bg,
        )
        self.chat_area.tag_configure("md_sup", foreground=fg)
        self.chat_area.tag_configure("md_sub", foreground=fg)
        self.chat_area.tag_configure("md_link", foreground="#8ab4f8" if self.dark_mode else "#0969da")
        self.chat_area.tag_configure("md_emoji", foreground=fg)
        self.chat_area.tag_configure("md_separator", foreground=muted)
        self.input_box.configure(bg=input_bg, fg=fg, insertbackground=insert)
        self._sync_sidebar_visibility()

    def toggle_theme(self) -> None:
        self.dark_mode = not self.dark_mode
        self.app_config["theme"] = "dark" if self.dark_mode else "light"
        save_config(self.app_config)
        self.apply_theme()

    def toggle_sidebar(self) -> None:
        self.sidebar_visible = not self.sidebar_visible
        self._sync_sidebar_visibility()

    def _sync_sidebar_visibility(self) -> None:
        if self.sidebar_visible:
            if not self.sidebar.winfo_ismapped():
                self.sidebar.grid(row=0, column=0, sticky="ns")
            if not self.sidebar_resize_handle.winfo_ismapped():
                self.sidebar_resize_handle.grid(row=0, column=1, sticky="ns")
            self.sidebar_open_button.grid_remove()
            self.sidebar.configure(width=self.sidebar_width)
            self.main_frame.columnconfigure(0, minsize=self.sidebar_width)
        else:
            self.sidebar.grid_remove()
            self.sidebar_resize_handle.grid_remove()
            self.sidebar_open_button.grid()
            self.main_frame.columnconfigure(0, minsize=0)

    def _refresh_model_display(self) -> None:
        self.model_label.configure(text=self.model_name)
        self.model_badge.configure(text=self.model_name)
        self.thinking_button.configure(
            text=f"{self._text('thinking')}: {self._thinking_mode_label()}"
        )
        self.pro_button.configure(
            state=tk.DISABLED if self.model_name == DeepSeekClient.DEFAULT_MODEL else tk.NORMAL
        )
        self.flash_button.configure(
            state=tk.DISABLED if self.model_name == DeepSeekClient.FLASH_MODEL else tk.NORMAL
        )
        if self.is_waiting:
            self.pro_button.configure(state=tk.DISABLED)
            self.flash_button.configure(state=tk.DISABLED)
            self.new_chat_button.configure(state=tk.DISABLED)
            self.thinking_button.configure(state=tk.DISABLED)
            self.api_settings_button.configure(state=tk.DISABLED)
            self.regenerate_button.configure(state=tk.DISABLED)
            self.clear_button.configure(state=tk.DISABLED)
        else:
            self.new_chat_button.configure(state=tk.NORMAL)
            self.thinking_button.configure(state=tk.NORMAL)
            self.api_settings_button.configure(state=tk.NORMAL)
            self.regenerate_button.configure(state=tk.NORMAL)
            self.clear_button.configure(state=tk.NORMAL)
        self.apply_theme()

    def open_api_settings(self) -> None:
        if self.is_waiting:
            messagebox.showinfo(self._text("please_wait"), self._text("api_busy"))
            return

        if self.api_settings_window is not None and self.api_settings_window.winfo_exists():
            self.api_settings_window.lift()
            self.api_settings_window.focus_force()
            return

        window = tk.Toplevel(self.root)
        self.api_settings_window = window
        window.title(self._text("api_settings"))
        window.resizable(False, False)
        window.transient(self.root)

        page_bg = "#202124" if self.dark_mode else "#f4f6f8"
        panel_bg = "#30343a" if self.dark_mode else "#ffffff"
        fg = "#ececec" if self.dark_mode else "#111111"
        muted = "#b4b4b4" if self.dark_mode else "#676767"
        border = "#41464d" if self.dark_mode else "#cfd7e2"
        button_bg = "#202328" if self.dark_mode else "#eef2f6"
        button_hover = "#343941" if self.dark_mode else "#dfe7f0"
        accent_bg = "#ececec" if self.dark_mode else "#111111"
        accent_hover = "#ffffff" if self.dark_mode else "#2d3748"
        accent_fg = "#111111" if self.dark_mode else "#ffffff"

        window.configure(bg=page_bg)
        form = tk.Frame(window, bg=panel_bg, bd=0, highlightthickness=1, highlightbackground=border)
        form.grid(row=0, column=0, sticky="nsew", padx=14, pady=14)
        form.columnconfigure(1, weight=1)

        title = tk.Label(
            form,
            text=self._text("api_settings"),
            bg=panel_bg,
            fg=fg,
            anchor="w",
            font=("Microsoft YaHei UI", 12, "bold"),
        )
        title.grid(row=0, column=0, columnspan=2, sticky="ew", padx=14, pady=(12, 10))

        key_label = tk.Label(form, text="API Key", bg=panel_bg, fg=muted, anchor="w")
        key_label.grid(row=1, column=0, sticky="w", padx=(14, 10), pady=(0, 8))
        api_key_var = tk.StringVar(value=str(self.app_config.get("DEEPSEEK_API_KEY") or ""))
        api_key_entry = tk.Entry(
            form,
            textvariable=api_key_var,
            width=42,
            show="*",
            bg=page_bg,
            fg=fg,
            insertbackground=fg,
            relief=tk.FLAT,
            highlightthickness=1,
            highlightbackground=border,
            highlightcolor=border,
        )
        api_key_entry.grid(row=1, column=1, sticky="ew", padx=(0, 14), pady=(0, 8), ipady=5)

        base_label = tk.Label(form, text="Base URL", bg=panel_bg, fg=muted, anchor="w")
        base_label.grid(row=2, column=0, sticky="w", padx=(14, 10), pady=(0, 8))
        base_url_var = tk.StringVar(
            value=str(self.app_config.get("DEEPSEEK_BASE_URL") or DeepSeekClient.DEFAULT_BASE_URL)
        )
        base_url_entry = tk.Entry(
            form,
            textvariable=base_url_var,
            width=42,
            bg=page_bg,
            fg=fg,
            insertbackground=fg,
            relief=tk.FLAT,
            highlightthickness=1,
            highlightbackground=border,
            highlightcolor=border,
        )
        base_url_entry.grid(row=2, column=1, sticky="ew", padx=(0, 14), pady=(0, 8), ipady=5)

        reveal_var = tk.BooleanVar(value=False)

        def toggle_reveal() -> None:
            api_key_entry.configure(show="" if reveal_var.get() else "*")

        reveal_check = tk.Checkbutton(
            form,
            text=self._text("show_api_key"),
            variable=reveal_var,
            command=toggle_reveal,
            bg=panel_bg,
            fg=muted,
            activebackground=panel_bg,
            activeforeground=fg,
            selectcolor=panel_bg,
        )
        reveal_check.grid(row=3, column=1, sticky="w", padx=(0, 14), pady=(0, 12))

        actions = tk.Frame(form, bg=panel_bg, bd=0, highlightthickness=0)
        actions.grid(row=4, column=0, columnspan=2, sticky="e", padx=14, pady=(0, 14))

        def close_window() -> None:
            self.api_settings_window = None
            window.destroy()

        def save_api_settings() -> None:
            api_key = api_key_var.get().strip()
            base_url = base_url_var.get().strip() or DeepSeekClient.DEFAULT_BASE_URL
            if not api_key:
                self.client = None
                self.status_label.configure(text="API key required")
                messagebox.showerror(
                    self._text("api_key_missing_title"),
                    self._text("api_required"),
                    parent=window,
                )
                return
            self.app_config["DEEPSEEK_API_KEY"] = api_key
            self.app_config["DEEPSEEK_BASE_URL"] = base_url
            save_config(self.app_config)

            try:
                self.client = DeepSeekClient(api_key=api_key or None, base_url=base_url)
            except Exception as exc:
                self.client = None
                self.status_label.configure(text="API settings saved, but DeepSeek is not ready")
                messagebox.showerror(
                    self._text("api_saved_title"),
                    f"{self._text('api_saved_error')}\n\n{exc}",
                    parent=window,
                )
                return

            self.status_label.configure(text="API settings saved")
            messagebox.showinfo(
                self._text("api_settings"),
                self._text("api_saved_ok"),
                parent=window,
            )
            close_window()

        cancel_button = tk.Button(
            actions,
            text=self._text("cancel"),
            relief=tk.FLAT,
            bd=0,
            padx=14,
            pady=6,
            command=close_window,
        )
        cancel_button.grid(row=0, column=0, padx=(0, 8))
        self._configure_hover_button(cancel_button, button_bg, button_hover, fg)

        save_button = tk.Button(
            actions,
            text=self._text("save"),
            relief=tk.FLAT,
            bd=0,
            padx=16,
            pady=6,
            command=save_api_settings,
        )
        save_button.grid(row=0, column=1)
        self._configure_hover_button(save_button, accent_bg, accent_hover, accent_fg, accent_fg)

        window.protocol("WM_DELETE_WINDOW", close_window)
        window.update_idletasks()
        x = self.root.winfo_rootx() + max(0, (self.root.winfo_width() - window.winfo_width()) // 2)
        y = self.root.winfo_rooty() + max(0, (self.root.winfo_height() - window.winfo_height()) // 3)
        window.geometry(f"+{x}+{y}")
        api_key_entry.focus_set()

    def set_model(self, model_name: str) -> None:
        if self.is_waiting:
            messagebox.showinfo(
                "Please Wait",
                "A request is still running. Change the model after it finishes.",
            )
            return

        self.model_name = model_name
        self.app_config["default_model"] = self.model_name
        save_config(self.app_config)
        self._refresh_model_display()
        self.status_label.configure(text=f"Model changed to {self.model_name}")

    def _send_from_event(self, _event: tk.Event) -> str:
        self.send_message()
        return "break"

    def _insert_newline(self, _event: tk.Event) -> str:
        self.input_box.insert(tk.INSERT, "\n")
        return "break"

    def send_message(self) -> None:
        if self.is_waiting:
            return
        if self.client is None:
            messagebox.showerror(
                "DeepSeek Not Ready",
                "DEEPSEEK_API_KEY is not set, so the app cannot send requests.",
            )
            return

        user_text = self.input_box.get("1.0", tk.END).strip()
        if not user_text:
            return

        self.conversation_count += 1
        turn_number = self.conversation_count
        model_name = self.model_name
        self._refresh_model_display()

        self.input_box.delete("1.0", tk.END)
        self._append_chat(f"Conversation {turn_number} - You", user_text, "user")
        self.messages.append({"role": "user", "content": user_text})

        self._start_request(
            turn_number,
            model_name,
            self._current_thinking_mode(),
            list(self.messages),
            self.conversation_summary,
            self.summarized_message_count,
        )

    def _start_request(
        self,
        turn_number: int,
        model_name: str,
        thinking_mode: str,
        messages: List[Message],
        conversation_summary: str,
        summarized_message_count: int,
    ) -> None:
        self.is_waiting = True
        self.send_button.configure(state=tk.DISABLED)
        self._refresh_model_display()
        self.status_label.configure(
            text=f"Conversation {turn_number}: waiting for {model_name}..."
        )

        worker = threading.Thread(
            target=self._request_answer,
            args=(
                turn_number,
                model_name,
                thinking_mode,
                messages,
                conversation_summary,
                summarized_message_count,
            ),
            daemon=True,
        )
        worker.start()

    def regenerate_last(self) -> None:
        if self.is_waiting:
            return

        if len(self.messages) < 2:
            messagebox.showinfo(
                self._text("cannot_regenerate"),
                self._text("no_regenerate_chat"),
            )
            return

        if self.messages[-1]["role"] == "assistant":
            self.messages.pop()
            self.summarized_message_count = min(
                self.summarized_message_count,
                max(0, len(self.messages) - 1),
            )

        if self.messages[-1]["role"] != "user":
            messagebox.showinfo(self._text("cannot_regenerate"), self._text("send_first"))
            return

        self.conversation_count += 1
        turn_number = self.conversation_count
        model_name = self.model_name
        self._append_chat(
            f"Conversation {turn_number} - Regenerate",
            self._text("regenerate_notice"),
            "system",
        )
        self._start_request(
            turn_number,
            model_name,
            self._current_thinking_mode(),
            list(self.messages),
            self.conversation_summary,
            self.summarized_message_count,
        )

    def save_transcript(self) -> None:
        if not self.transcript:
            messagebox.showinfo(self._text("nothing_to_save"), self._text("empty_session"))
            return

        path = filedialog.asksaveasfilename(
            parent=self.root,
            title=self._text("save_current_session"),
            defaultextension=".txt",
            filetypes=[("Text files", "*.txt"), ("All files", "*.*")],
        )
        if not path:
            return

        with open(path, "w", encoding="utf-8") as file:
            file.write("\n\n".join(self.transcript))
            file.write("\n")
        self.status_label.configure(text=f"Saved to {path}")

    def delete_session_by_index(self, target_index: int) -> None:
        if self.is_waiting:
            return

        if target_index < 0 or target_index >= len(self.sessions):
            return

        title = str(self.sessions[target_index].get("title") or self._text("this_conversation"))
        confirmed = messagebox.askyesno(
            self._text("delete_history"),
            self._text("delete_confirm").format(title=title),
            parent=self.root,
        )
        if not confirmed:
            return

        deleting_active = target_index == self.active_session_index
        del self.sessions[target_index]

        if deleting_active:
            self.active_session_index = None
            self.messages = [{"role": "system", "content": self.system_prompt}]
            self.transcript = []
            self.display_entries = []
            self.conversation_summary = ""
            self.summarized_message_count = 0
            self.conversation_count = 0
            self.chat_area.configure(state=tk.NORMAL)
            self.chat_area.delete("1.0", tk.END)
            self.chat_area.configure(state=tk.DISABLED)
            self._append_chat("System", self._text("history_deleted"), "system")
            self.status_label.configure(text="Deleted selected conversation")
        elif self.active_session_index is not None and target_index < self.active_session_index:
            self.active_session_index -= 1
            self.status_label.configure(text=f"Deleted - {title}")
        else:
            self.status_label.configure(text=f"Deleted - {title}")

        self._write_sessions_to_disk()
        self._refresh_history_list()
        self._refresh_model_display()

    def delete_selected_session(self) -> None:
        if self.active_session_index is None:
            messagebox.showinfo(self._text("cannot_delete"), self._text("select_history"))
            return
        self.delete_session_by_index(self.active_session_index)

    def clear_chat(self) -> None:
        if self.is_waiting:
            return

        self.messages = [{"role": "system", "content": self.system_prompt}]
        self.transcript = []
        self.display_entries = []
        self.conversation_summary = ""
        self.summarized_message_count = 0
        self.chat_area.configure(state=tk.NORMAL)
        self.chat_area.delete("1.0", tk.END)
        self.chat_area.configure(state=tk.DISABLED)
        self.status_label.configure(text="Ready")
        self._append_chat("System", self._text("cleared"), "system")

    def _format_messages_for_summary(self, messages: List[Message]) -> str:
        parts: List[str] = []
        for message in messages:
            role = str(message.get("role") or "unknown")
            content = str(message.get("content") or "").strip()
            if content:
                parts.append(f"{role}: {content}")
        return "\n\n".join(parts)

    def _summarize_context(
        self,
        model_name: str,
        existing_summary: str,
        messages_to_summarize: List[Message],
    ) -> str:
        assert self.client is not None
        old_summary = existing_summary.strip() or self._text("summary_none")
        new_context = self._format_messages_for_summary(messages_to_summarize)
        prompt = self._text("summary_prompt").format(
            old_summary=old_summary,
            new_context=new_context,
        )
        response = self.client.chat(
            messages=[
                {"role": "system", "content": SUMMARY_SYSTEM_PROMPT},
                {"role": "user", "content": prompt},
            ],
            model=model_name,
            thinking="disabled",
            temperature=0.2,
        )
        return (response.choices[0].message.content or existing_summary).strip()

    def _prepare_context_messages(
        self,
        model_name: str,
        messages: List[Message],
        summary: str,
        summarized_count: int,
    ) -> tuple[List[Message], str, int]:
        if not messages:
            return messages, summary, summarized_count

        system_message = messages[0]
        conversation_messages = messages[1:]
        summarize_until = max(0, len(conversation_messages) - CONTEXT_RECENT_MESSAGE_COUNT)

        if summarize_until - summarized_count >= SUMMARY_BATCH_MIN_MESSAGES:
            summary = self._summarize_context(
                model_name,
                summary,
                conversation_messages[summarized_count:summarize_until],
            )
            summarized_count = summarize_until

        context_messages: List[Message] = [dict(system_message)]
        if summary.strip():
            context_messages.append(
                {
                    "role": "system",
                    "content": self._text("summary_context").format(summary=summary.strip()),
                }
            )
        context_messages.extend(dict(message) for message in conversation_messages[summarized_count:])
        return context_messages, summary, summarized_count

    def _request_answer(
        self,
        turn_number: int,
        model_name: str,
        thinking_mode: str,
        messages: List[Message],
        conversation_summary: str,
        summarized_message_count: int,
    ) -> None:
        started_at = time.perf_counter()
        try:
            assert self.client is not None
            context_messages, updated_summary, updated_count = self._prepare_context_messages(
                model_name,
                messages,
                conversation_summary,
                summarized_message_count,
            )
            response = self.client.chat(
                messages=context_messages,
                model=model_name,
                thinking="disabled" if thinking_mode == "disabled" else "enabled",
                reasoning_effort="high" if thinking_mode == "disabled" else thinking_mode,
                temperature=0.7 if thinking_mode == "disabled" else None,
            )
            answer = response.choices[0].message.content or ""
            elapsed = time.perf_counter() - started_at
            self.result_queue.put(
                ("ok", turn_number, model_name, elapsed, answer, updated_summary, updated_count)
            )
        except Exception as exc:
            elapsed = time.perf_counter() - started_at
            self.result_queue.put(
                (
                    "error",
                    turn_number,
                    model_name,
                    elapsed,
                    str(exc),
                    conversation_summary,
                    summarized_message_count,
                )
            )

    def _poll_results(self) -> None:
        try:
            (
                status,
                turn_number,
                model_name,
                elapsed,
                payload,
                updated_summary,
                updated_count,
            ) = self.result_queue.get_nowait()
        except queue.Empty:
            self.root.after(100, self._poll_results)
            return

        if status == "ok":
            self.conversation_summary = str(updated_summary or "")
            self.summarized_message_count = int(updated_count or 0)
            self.messages.append({"role": "assistant", "content": payload})
            self._append_chat(
                f"Conversation {turn_number} - DeepSeek ({model_name}, {elapsed:.2f}s)",
                payload,
                "assistant",
            )
            self.status_label.configure(
                text=f"Ready - conversation {turn_number} took {elapsed:.2f}s"
            )
        else:
            self._append_chat(
                f"Conversation {turn_number} - Error ({model_name}, {elapsed:.2f}s)",
                payload,
                "error",
            )
            self.status_label.configure(
                text=f"Request failed - conversation {turn_number} took {elapsed:.2f}s"
            )

        self.is_waiting = False
        self.send_button.configure(state=tk.NORMAL)
        self._refresh_model_display()
        self._save_current_session()
        self.root.after(100, self._poll_results)


def launch_gui() -> None:
    configure_windows_dpi_awareness()
    ensure_runtime_files()
    root = tk.Tk()
    configure_tk_scaling(root)
    app = DeepSeekChatApp(root)

    def on_close() -> None:
        app._save_current_session()
        app.app_config["window_geometry"] = root.geometry()
        save_config(app.app_config)
        root.destroy()

    root.protocol("WM_DELETE_WINDOW", on_close)
    root.mainloop()


def main() -> None:
    launch_gui()


if __name__ == "__main__":
    main()
