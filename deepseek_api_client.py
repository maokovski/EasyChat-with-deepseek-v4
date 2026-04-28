#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
DeepSeek V4 API wrapper using the OpenAI-compatible SDK.

Install dependency:
    pip install openai

Set API key before running:
    PowerShell: $env:DEEPSEEK_API_KEY = "sk-..."
    Bash:      export DEEPSEEK_API_KEY="sk-..."
"""

from __future__ import annotations

import json
import os
import queue
import re
import sys
import threading
import tkinter as tk
import time
from pathlib import Path
from tkinter import filedialog, messagebox, scrolledtext, ttk
from typing import Any, Dict, Iterator, List, Literal, Optional

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
    "theme": "light",
    "window_geometry": "980x680",
}


def ensure_runtime_files() -> None:
    CONVERSATIONS_DIR.mkdir(exist_ok=True)
    if not CONFIG_PATH.exists():
        CONFIG_PATH.write_text(
            json.dumps(DEFAULT_CONFIG, ensure_ascii=False, indent=2),
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
        json.dumps({**DEFAULT_CONFIG, **config}, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def load_system_prompt() -> str:
    ensure_runtime_files()
    prompt = PROMPTS_PATH.read_text(encoding="utf-8").strip()
    return prompt or "You are a helpful assistant."


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
        self.api_key = (
            api_key
            or str(config.get("DEEPSEEK_API_KEY") or "").strip()
            or os.environ.get("DEEPSEEK_API_KEY")
        )
        if not self.api_key:
            raise ValueError(
                f"Missing DeepSeek API key. Fill {CONFIG_PATH.name} or set DEEPSEEK_API_KEY."
            )

        self.base_url = (
            base_url
            or str(config.get("DEEPSEEK_BASE_URL") or "").strip()
            or os.environ.get("DEEPSEEK_BASE_URL")
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


CHAT_BODY_FONT = ("SimSun", 12)
CHAT_META_FONT = ("Microsoft YaHei UI", 9)
INPUT_FONT = ("SimSun", 12)
UI_FONT = ("Microsoft YaHei UI", 10)


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
        return f"\n[公式]\n{formula}\n"

    def inline_formula(match: re.Match[str]) -> str:
        formula = match.group(1).strip()
        return f" {formula} "

    def fraction(match: re.Match[str]) -> str:
        numerator = match.group(1).strip()
        denominator = match.group(2).strip()
        return f"({numerator})/({denominator})"

    def sqrt(match: re.Match[str]) -> str:
        return f"sqrt({match.group(1).strip()})"

    text = re.sub(r"\\\[(.*?)\\\]", display_formula, text, flags=re.DOTALL)
    text = re.sub(r"\$\$(.*?)\$\$", display_formula, text, flags=re.DOTALL)
    text = re.sub(r"\\\((.*?)\\\)", inline_formula, text, flags=re.DOTALL)
    text = re.sub(r"(?<!\\)\$(.+?)(?<!\\)\$", inline_formula, text, flags=re.DOTALL)
    text = re.sub(r"\\frac\{([^{}]+)\}\{([^{}]+)\}", fraction, text)
    text = re.sub(r"\\sqrt\{([^{}]+)\}", sqrt, text)

    for raw, formatted in replacements.items():
        text = text.replace(raw, formatted)

    return re.sub(r"\n{3,}", "\n\n", text).strip()


def format_paragraphs_for_reading(text: str, indent: bool = True) -> str:
    """Normalize prose paragraphs into a Chinese-paper-like reading rhythm."""
    lines = [line.rstrip() for line in text.strip().splitlines()]
    blocks: List[str] = []
    current: List[str] = []
    in_code_block = False

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

        if stripped.startswith(("[公式]", "-", "*", "1.", "2.", "3.", "4.", "5.", ">")):
            flush_current()
            blocks.append(stripped)
            continue

        current.append(stripped)

    flush_current()
    return "\n\n".join(blocks).strip("\n")


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
        self.conversation_count = 0
        self.result_queue: "queue.Queue[tuple[str, int, str, float, str]]" = queue.Queue()
        self.is_waiting = False
        self.dark_mode = str(self.app_config.get("theme") or "light") == "dark"
        self.sidebar_visible = True
        self.transcript: List[str] = []
        self.display_entries: List[tuple[str, str, str]] = []
        self.sessions: List[Dict[str, Any]] = self._load_sessions_from_disk()
        self.active_session_index: Optional[int] = None
        self.style = ttk.Style()

        self._build_ui()
        self._refresh_history_list()
        self._poll_results()

        try:
            self.client = DeepSeekClient()
        except Exception as exc:
            messagebox.showerror(
                "DeepSeek API Key Missing",
                f"Please fill {CONFIG_PATH.name} next to this program, or set DEEPSEEK_API_KEY.\n\n"
                f"Details: {exc}",
            )

    def _build_ui(self) -> None:
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)

        self.main_frame = tk.Frame(self.root, bd=0, highlightthickness=0)
        self.main_frame.grid(row=0, column=0, sticky="nsew")
        self.main_frame.columnconfigure(1, weight=1)
        self.main_frame.rowconfigure(0, weight=1)

        self.sidebar = tk.Frame(self.main_frame, width=218, bd=0, highlightthickness=0)
        self.sidebar.grid(row=0, column=0, sticky="ns")
        self.sidebar.grid_propagate(False)
        self.sidebar.columnconfigure(0, weight=1)

        self.sidebar_header = tk.Frame(self.sidebar, bd=0, highlightthickness=0)
        self.sidebar_header.grid(row=0, column=0, sticky="ew", padx=10, pady=(12, 8))
        self.sidebar_header.columnconfigure(0, weight=1)

        self.brand_label = tk.Label(
            self.sidebar_header,
            text="deepseek",
            anchor="w",
            font=("Segoe UI", 17, "bold"),
        )
        self.brand_label.grid(row=0, column=0, sticky="ew", padx=(6, 4))

        self.sidebar_close_button = tk.Button(
            self.sidebar_header,
            text="×",
            width=3,
            relief=tk.FLAT,
            bd=0,
            command=self.toggle_sidebar,
        )
        self.sidebar_close_button.grid(row=0, column=1, sticky="e")

        self.new_chat_button = tk.Button(
            self.sidebar,
            text="+  新对话",
            relief=tk.FLAT,
            bd=0,
            anchor="w",
            command=self.new_chat,
        )
        self.new_chat_button.grid(row=1, column=0, sticky="ew", padx=10, pady=(0, 12), ipady=9)

        self.model_title = tk.Label(
            self.sidebar,
            text="当前模型",
            anchor="w",
            font=("Microsoft YaHei UI", 9),
        )
        self.model_title.grid(row=2, column=0, sticky="ew", padx=16, pady=(4, 2))

        self.model_label = tk.Label(
            self.sidebar,
            text=self.model_name,
            anchor="w",
            font=("Segoe UI", 10, "bold"),
        )
        self.model_label.grid(row=3, column=0, sticky="ew", padx=16, pady=(0, 8))

        self.pro_button = tk.Button(
            self.sidebar,
            text="V4 Pro",
            relief=tk.FLAT,
            bd=0,
            anchor="w",
            command=lambda: self.set_model(DeepSeekClient.DEFAULT_MODEL),
        )
        self.pro_button.grid(row=4, column=0, sticky="ew", padx=10, pady=(2, 6), ipady=8)

        self.flash_button = tk.Button(
            self.sidebar,
            text="V4 Flash",
            relief=tk.FLAT,
            bd=0,
            anchor="w",
            command=lambda: self.set_model(DeepSeekClient.FLASH_MODEL),
        )
        self.flash_button.grid(row=5, column=0, sticky="ew", padx=10, pady=(0, 14), ipady=8)

        self.history_title = tk.Label(
            self.sidebar,
            text="对话记录",
            anchor="w",
            font=("Microsoft YaHei UI", 9),
        )
        self.history_title.grid(row=6, column=0, sticky="ew", padx=16, pady=(4, 6))

        self.history_list = tk.Listbox(
            self.sidebar,
            height=10,
            activestyle="none",
            bd=0,
            highlightthickness=0,
            relief=tk.FLAT,
            font=("Microsoft YaHei UI", 10),
        )
        self.history_list.grid(row=7, column=0, sticky="nsew", padx=10, pady=(0, 12))
        self.history_list.bind("<<ListboxSelect>>", self.load_selected_session)

        self.sidebar_spacer = tk.Frame(self.sidebar, bd=0, highlightthickness=0)
        self.sidebar_spacer.grid(row=8, column=0, sticky="nsew")
        self.sidebar.rowconfigure(7, weight=1)

        self.theme_button = tk.Button(
            self.sidebar,
            text="◐  主题",
            relief=tk.FLAT,
            bd=0,
            anchor="w",
            command=self.toggle_theme,
        )
        self.theme_button.grid(row=9, column=0, sticky="ew", padx=10, pady=(0, 8), ipady=8)

        self.regenerate_button = tk.Button(
            self.sidebar,
            text="↻  重新生成",
            relief=tk.FLAT,
            bd=0,
            anchor="w",
            command=self.regenerate_last,
        )
        self.regenerate_button.grid(row=10, column=0, sticky="ew", padx=10, pady=(0, 6), ipady=8)

        self.save_button = tk.Button(
            self.sidebar,
            text="⇩  保存 .txt",
            relief=tk.FLAT,
            bd=0,
            anchor="w",
            command=self.save_transcript,
        )
        self.save_button.grid(row=11, column=0, sticky="ew", padx=10, pady=(0, 6), ipady=8)

        self.clear_button = tk.Button(
            self.sidebar,
            text="⌧  清屏",
            relief=tk.FLAT,
            bd=0,
            anchor="w",
            command=self.clear_chat,
        )
        self.clear_button.grid(row=12, column=0, sticky="ew", padx=10, pady=(0, 18), ipady=8)

        self.content_frame = tk.Frame(self.main_frame, bd=0, highlightthickness=0)
        self.content_frame.grid(row=0, column=1, sticky="nsew")
        self.content_frame.columnconfigure(0, weight=1)
        self.content_frame.rowconfigure(1, weight=1)

        self.topbar = tk.Frame(self.content_frame, bd=0, highlightthickness=0)
        self.topbar.grid(row=0, column=0, sticky="ew", padx=28, pady=(18, 8))
        self.topbar.columnconfigure(1, weight=1)

        self.sidebar_open_button = tk.Button(
            self.topbar,
            text="☰",
            width=3,
            relief=tk.FLAT,
            bd=0,
            command=self.toggle_sidebar,
        )
        self.sidebar_open_button.grid(row=0, column=0, sticky="w", padx=(0, 10))

        self.title_label = tk.Label(
            self.topbar,
            text="DeepSeek",
            anchor="w",
            font=("Segoe UI", 14, "bold"),
        )
        self.title_label.grid(row=0, column=1, sticky="w")

        self.model_badge = tk.Label(
            self.topbar,
            text=self.model_name,
            font=("Segoe UI", 9),
            padx=10,
            pady=4,
        )
        self.model_badge.grid(row=0, column=2, sticky="e")

        self.chat_area = scrolledtext.ScrolledText(
            self.content_frame,
            wrap=tk.WORD,
            state=tk.DISABLED,
            font=CHAT_BODY_FONT,
            bd=0,
            relief=tk.FLAT,
            padx=26,
            pady=18,
        )
        self.chat_area.grid(row=1, column=0, sticky="nsew", padx=28, pady=(0, 8))
        self.chat_area.tag_configure(
            "user",
            justify=tk.RIGHT,
            rmargin=22,
            lmargin1=120,
            lmargin2=120,
            spacing1=8,
            spacing2=4,
            spacing3=18,
            font=CHAT_BODY_FONT,
        )
        self.chat_area.tag_configure(
            "assistant",
            justify=tk.LEFT,
            lmargin1=22,
            lmargin2=22,
            rmargin=72,
            spacing1=8,
            spacing2=5,
            spacing3=18,
            font=CHAT_BODY_FONT,
        )
        self.chat_area.tag_configure(
            "system",
            justify=tk.CENTER,
            spacing1=4,
            spacing3=12,
            font=CHAT_META_FONT,
        )
        self.chat_area.tag_configure(
            "error",
            justify=tk.LEFT,
            lmargin1=22,
            lmargin2=22,
            rmargin=72,
            spacing1=8,
            spacing2=5,
            spacing3=18,
            font=CHAT_BODY_FONT,
        )

        self.status_label = tk.Label(
            self.content_frame,
            text="Ready",
            anchor="w",
            font=("Segoe UI", 9),
        )
        self.status_label.grid(row=2, column=0, sticky="ew", padx=34, pady=(0, 6))

        self.composer_frame = tk.Frame(self.content_frame, bd=0, highlightthickness=1)
        self.composer_frame.grid(row=3, column=0, sticky="ew", padx=28, pady=(0, 22))
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
            "在下方输入问题。Enter 发送，Shift+Enter 换行。",
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
        self._insert_chat_entry(entry, tag)

    def _insert_chat_entry(self, entry: str, tag: str) -> None:
        self.chat_area.configure(state=tk.NORMAL)
        self.chat_area.insert(tk.END, entry, tag)
        self.chat_area.configure(state=tk.DISABLED)
        self.chat_area.see(tk.END)

    def _render_current_chat(self) -> None:
        self.chat_area.configure(state=tk.NORMAL)
        self.chat_area.delete("1.0", tk.END)
        self.chat_area.configure(state=tk.DISABLED)
        for speaker, text, tag in self.display_entries:
            entry = f"{speaker}:\n{text.strip()}\n\n"
            self._insert_chat_entry(entry, tag)

    def _has_real_chat(self) -> bool:
        return any(message.get("role") != "system" for message in self.messages)

    def _session_title(self) -> str:
        for message in self.messages:
            if message.get("role") == "user":
                title = str(message.get("content", "")).strip().replace("\n", " ")
                return title[:22] + ("..." if len(title) > 22 else "")
        return f"新对话 {len(self.sessions) + 1}"

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

    def _write_sessions_to_disk(self) -> None:
        ensure_runtime_files()
        SESSIONS_PATH.write_text(
            json.dumps(self.sessions, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

    def _refresh_history_list(self) -> None:
        self.history_list.delete(0, tk.END)
        for index, session in enumerate(self.sessions):
            marker = "● " if index == self.active_session_index else "  "
            self.history_list.insert(tk.END, f"{marker}{session['title']}")
        if self.active_session_index is not None and self.active_session_index < len(self.sessions):
            self.history_list.selection_clear(0, tk.END)
            self.history_list.selection_set(self.active_session_index)
            self.history_list.see(self.active_session_index)

    def new_chat(self) -> None:
        if self.is_waiting:
            return

        self._save_current_session()
        self.active_session_index = None
        self.messages = [{"role": "system", "content": self.system_prompt}]
        self.transcript = []
        self.display_entries = []
        self.conversation_count = 0
        self.status_label.configure(text="Ready")
        self._append_chat("System", "新对话已开始。Enter 发送，Shift+Enter 换行。", "system")
        self._refresh_history_list()
        self._render_current_chat()

    def load_selected_session(self, _event: tk.Event) -> None:
        if self.is_waiting:
            return

        selection = self.history_list.curselection()
        if not selection:
            return

        target_index = int(selection[0])
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
        self.status_label.configure(text=f"Loaded - {session['title']}")
        self._refresh_history_list()
        self._refresh_model_display()
        self._render_current_chat()

    def apply_theme(self) -> None:
        if self.dark_mode:
            page_bg = "#212121"
            sidebar_bg = "#171717"
            chat_bg = "#212121"
            input_bg = "#2f2f2f"
            fg = "#ececec"
            muted = "#b4b4b4"
            border = "#3f3f3f"
            button_bg = "#171717"
            button_hover = "#2f2f2f"
            selected_bg = "#2f2f2f"
            accent_bg = "#ececec"
            send_fg = "#111111"
            accent_fg = "#ffffff"
            insert = "#ffffff"
        else:
            page_bg = "#ffffff"
            sidebar_bg = "#f9f9f9"
            chat_bg = "#ffffff"
            input_bg = "#ffffff"
            fg = "#111111"
            muted = "#676767"
            border = "#d9d9d9"
            button_bg = "#f9f9f9"
            button_hover = "#ececec"
            selected_bg = "#ececec"
            accent_bg = "#111111"
            send_fg = "#ffffff"
            accent_fg = "#ffffff"
            insert = "#111111"

        self.root.configure(bg=page_bg)
        self.main_frame.configure(bg=page_bg)
        self.sidebar.configure(bg=sidebar_bg)
        self.sidebar_header.configure(bg=sidebar_bg)
        self.sidebar_spacer.configure(bg=sidebar_bg)
        self.content_frame.configure(bg=page_bg)
        self.topbar.configure(bg=page_bg)
        self.composer_frame.configure(bg=input_bg, highlightbackground=border, highlightcolor=border)

        self.brand_label.configure(bg=sidebar_bg, fg=fg)
        self.sidebar_close_button.configure(
            bg=button_bg,
            fg=fg,
            activebackground=button_hover,
            activeforeground=fg,
            highlightbackground=sidebar_bg,
            highlightcolor=fg,
        )
        self.sidebar_open_button.configure(
            bg=page_bg,
            fg=fg,
            activebackground=button_hover,
            activeforeground=fg,
            highlightbackground=page_bg,
            highlightcolor=fg,
        )
        self.model_title.configure(bg=sidebar_bg, fg=muted)
        self.model_label.configure(bg=sidebar_bg, fg=fg)
        self.history_title.configure(bg=sidebar_bg, fg=muted)
        self.history_list.configure(
            bg=sidebar_bg,
            fg=fg,
            selectbackground=selected_bg,
            selectforeground=fg,
        )
        self.title_label.configure(bg=page_bg, fg=fg)
        self.model_badge.configure(bg=selected_bg, fg=muted)
        self.status_label.configure(bg=page_bg, fg=muted)

        self.style.configure("TFrame", background=page_bg)
        self.style.configure("TLabel", background=page_bg, foreground=fg)
        self.style.configure("TButton", padding=4)
        self.theme_button.configure(
            text="☀  浅色" if self.dark_mode else "◐  深色",
            bg=button_bg,
            fg=fg,
            activebackground=button_hover,
            activeforeground=fg,
            highlightbackground=sidebar_bg,
            highlightcolor=fg,
        )
        self.new_chat_button.configure(
            bg=button_bg,
            fg=fg,
            activebackground=button_hover,
            activeforeground=fg,
            highlightbackground=sidebar_bg,
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
            button.configure(
                bg=selected_bg if selected else button_bg,
                fg=fg,
                activebackground=button_hover,
                activeforeground=fg,
                disabledforeground="#777777",
                highlightbackground=sidebar_bg,
                highlightcolor=fg,
            )
        for button in (
            self.regenerate_button,
            self.save_button,
            self.clear_button,
        ):
            button.configure(
                bg=button_bg,
                fg=fg,
                activebackground=button_hover,
                activeforeground=fg,
                disabledforeground="#777777",
                highlightbackground=sidebar_bg,
                highlightcolor=fg,
            )
        self.send_button.configure(
            bg=accent_bg,
            fg=send_fg,
            activebackground=button_hover,
            activeforeground=fg,
            disabledforeground="#c7ccd4",
            highlightbackground=input_bg,
            highlightcolor=accent_bg,
        )
        self.chat_area.configure(bg=chat_bg, fg=fg, insertbackground=insert)
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
            self.sidebar_open_button.grid_remove()
            self.main_frame.columnconfigure(0, minsize=218)
        else:
            self.sidebar.grid_remove()
            self.sidebar_open_button.grid()
            self.main_frame.columnconfigure(0, minsize=0)

    def _refresh_model_display(self) -> None:
        self.model_label.configure(text=self.model_name)
        self.model_badge.configure(text=self.model_name)
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
            self.regenerate_button.configure(state=tk.DISABLED)
            self.clear_button.configure(state=tk.DISABLED)
        else:
            self.new_chat_button.configure(state=tk.NORMAL)
            self.regenerate_button.configure(state=tk.NORMAL)
            self.clear_button.configure(state=tk.NORMAL)
        self.apply_theme()

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

        self._start_request(turn_number, model_name, list(self.messages))

    def _start_request(
        self,
        turn_number: int,
        model_name: str,
        messages: List[Message],
    ) -> None:
        self.is_waiting = True
        self.send_button.configure(state=tk.DISABLED)
        self._refresh_model_display()
        self.status_label.configure(
            text=f"Conversation {turn_number}: waiting for {model_name}..."
        )

        worker = threading.Thread(
            target=self._request_answer,
            args=(turn_number, model_name, messages),
            daemon=True,
        )
        worker.start()

    def regenerate_last(self) -> None:
        if self.is_waiting:
            return

        if len(self.messages) < 2:
            messagebox.showinfo("无法重新生成", "还没有可以重新生成的对话。")
            return

        if self.messages[-1]["role"] == "assistant":
            self.messages.pop()

        if self.messages[-1]["role"] != "user":
            messagebox.showinfo("无法重新生成", "请先发送一个问题。")
            return

        self.conversation_count += 1
        turn_number = self.conversation_count
        model_name = self.model_name
        self._append_chat(
            f"Conversation {turn_number} - Regenerate",
            "重新生成上一条回复。",
            "system",
        )
        self._start_request(turn_number, model_name, list(self.messages))

    def save_transcript(self) -> None:
        if not self.transcript:
            messagebox.showinfo("无需保存", "当前会话没有内容。")
            return

        path = filedialog.asksaveasfilename(
            parent=self.root,
            title="保存当前会话",
            defaultextension=".txt",
            filetypes=[("Text files", "*.txt"), ("All files", "*.*")],
        )
        if not path:
            return

        with open(path, "w", encoding="utf-8") as file:
            file.write("\n\n".join(self.transcript))
            file.write("\n")
        self.status_label.configure(text=f"Saved to {path}")

    def clear_chat(self) -> None:
        if self.is_waiting:
            return

        self.messages = [{"role": "system", "content": self.system_prompt}]
        self.transcript = []
        self.chat_area.configure(state=tk.NORMAL)
        self.chat_area.delete("1.0", tk.END)
        self.chat_area.configure(state=tk.DISABLED)
        self.status_label.configure(text="Ready")
        self._append_chat("System", "已清屏。Enter 发送，Shift+Enter 换行。", "system")

    def _request_answer(
        self,
        turn_number: int,
        model_name: str,
        messages: List[Message],
    ) -> None:
        started_at = time.perf_counter()
        try:
            assert self.client is not None
            response = self.client.chat(
                messages=messages,
                model=model_name,
                thinking="disabled",
                temperature=0.7,
            )
            answer = response.choices[0].message.content or ""
            elapsed = time.perf_counter() - started_at
            self.result_queue.put(("ok", turn_number, model_name, elapsed, answer))
        except Exception as exc:
            elapsed = time.perf_counter() - started_at
            self.result_queue.put(("error", turn_number, model_name, elapsed, str(exc)))

    def _poll_results(self) -> None:
        try:
            status, turn_number, model_name, elapsed, payload = self.result_queue.get_nowait()
        except queue.Empty:
            self.root.after(100, self._poll_results)
            return

        if status == "ok":
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
    ensure_runtime_files()
    root = tk.Tk()
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
