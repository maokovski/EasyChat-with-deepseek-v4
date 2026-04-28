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
import webbrowser
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
    "thinking_modes": {
        "deepseek-v4-pro": "disabled",
        "deepseek-v4-flash": "disabled",
    },
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
CHAT_BODY_BOLD_FONT = ("SimSun", 12, "bold")
CHAT_BODY_ITALIC_FONT = ("SimSun", 12, "italic")
CHAT_BODY_BOLD_ITALIC_FONT = ("SimSun", 12, "bold italic")
CHAT_HEADING_FONT = ("Microsoft YaHei UI", 13, "bold")
CHAT_CODE_FONT = ("Consolas", 11)
CHAT_TABLE_FONT = ("Cascadia Mono", 10)
CHAT_SUPSUB_FONT = ("SimSun", 9)
CHAT_EMOJI_FONT = ("Segoe UI Emoji", 12)
CHAT_META_FONT = ("Microsoft YaHei UI", 9)
INPUT_FONT = ("SimSun", 12)
UI_FONT = ("Microsoft YaHei UI", 10)
CONTEXT_RECENT_MESSAGE_COUNT = 10
SUMMARY_BATCH_MIN_MESSAGES = 4
SUMMARY_SYSTEM_PROMPT = (
    "你是对话记忆整理器。请把旧对话压缩成一份简洁但信息充分的中文摘要，"
    "保留用户目标、关键决定、项目约束、已完成修改、待办事项、重要事实和偏好。"
    "不要添加原文中没有的信息。"
)
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
                stripped.startswith("[公式]"),
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
        self.sidebar_visible = True
        self.transcript: List[str] = []
        self.display_entries: List[tuple[str, str, str]] = []
        self.sessions: List[Dict[str, Any]] = self._load_sessions_from_disk()
        self.active_session_index: Optional[int] = None
        self.conversation_summary = ""
        self.summarized_message_count = 0
        self.link_count = 0
        self.history_rows: List[tuple[tk.Frame, tk.Button, tk.Button]] = []
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
            text="➕  新对话",
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

        self.thinking_button = tk.Button(
            self.sidebar,
            text="🧠  思考：关闭",
            relief=tk.FLAT,
            bd=0,
            anchor="w",
            command=self.toggle_thinking_mode,
        )
        self.thinking_button.grid(row=6, column=0, sticky="ew", padx=10, pady=(0, 14), ipady=8)

        self.history_title = tk.Label(
            self.sidebar,
            text="对话记录",
            anchor="w",
            font=("Microsoft YaHei UI", 9),
        )
        self.history_title.grid(row=7, column=0, sticky="ew", padx=16, pady=(4, 6))

        self.history_frame = tk.Frame(
            self.sidebar,
            bd=0,
            highlightthickness=0,
            relief=tk.FLAT,
        )
        self.history_frame.grid(row=8, column=0, sticky="nsew", padx=10, pady=(0, 12))
        self.history_frame.columnconfigure(0, weight=1)

        self.sidebar_spacer = tk.Frame(self.sidebar, bd=0, highlightthickness=0)
        self.sidebar_spacer.grid(row=9, column=0, sticky="nsew")
        self.sidebar.rowconfigure(8, weight=1)

        self.theme_button = tk.Button(
            self.sidebar,
            text="🌗  主题",
            relief=tk.FLAT,
            bd=0,
            anchor="w",
            command=self.toggle_theme,
        )
        self.theme_button.grid(row=10, column=0, sticky="ew", padx=10, pady=(0, 8), ipady=8)

        self.regenerate_button = tk.Button(
            self.sidebar,
            text="🔄  重新生成",
            relief=tk.FLAT,
            bd=0,
            anchor="w",
            command=self.regenerate_last,
        )
        self.regenerate_button.grid(row=11, column=0, sticky="ew", padx=10, pady=(0, 6), ipady=8)

        self.save_button = tk.Button(
            self.sidebar,
            text="💾  保存 .txt",
            relief=tk.FLAT,
            bd=0,
            anchor="w",
            command=self.save_transcript,
        )
        self.save_button.grid(row=12, column=0, sticky="ew", padx=10, pady=(0, 6), ipady=8)

        self.clear_button = tk.Button(
            self.sidebar,
            text="🧹  清屏",
            relief=tk.FLAT,
            bd=0,
            anchor="w",
            command=self.clear_chat,
        )
        self.clear_button.grid(row=13, column=0, sticky="ew", padx=10, pady=(0, 18), ipady=8)

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
                label = match.group(1).strip() or "图片"
                self._insert_link(f"图片: {label}", match.group(2), base_tag, *extra_tags)
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
            "disabled": "关闭",
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
            json.dumps(self.sessions, ensure_ascii=False, indent=2),
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
                text=f"{marker}{session.get('title', '未命名对话')}",
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
        self._append_chat("System", "新对话已开始。Enter 发送，Shift+Enter 换行。", "system")
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
            page_bg = "#202124"
            sidebar_bg = "#16181c"
            chat_bg = "#24262a"
            input_bg = "#30343a"
            fg = "#ececec"
            muted = "#b4b4b4"
            border = "#41464d"
            button_bg = "#202328"
            button_hover = "#343941"
            selected_bg = "#303640"
            accent_bg = "#ececec"
            accent_hover = "#ffffff"
            send_fg = "#111111"
            accent_fg = "#ffffff"
            insert = "#ffffff"
        else:
            page_bg = "#f4f6f8"
            sidebar_bg = "#e8edf3"
            chat_bg = "#ffffff"
            input_bg = "#eef2f6"
            fg = "#111111"
            muted = "#676767"
            border = "#cfd7e2"
            button_bg = "#eef2f6"
            button_hover = "#dfe7f0"
            selected_bg = "#d8e1ec"
            accent_bg = "#111111"
            accent_hover = "#2d3748"
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
        self._configure_hover_button(self.sidebar_close_button, button_bg, button_hover, fg)
        self.sidebar_close_button.configure(
            highlightbackground=sidebar_bg,
            highlightcolor=fg,
        )
        self._configure_hover_button(self.sidebar_open_button, page_bg, button_hover, fg)
        self.sidebar_open_button.configure(
            highlightbackground=page_bg,
            highlightcolor=fg,
        )
        self.model_title.configure(bg=sidebar_bg, fg=muted)
        self.model_label.configure(bg=sidebar_bg, fg=fg)
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
        self.title_label.configure(bg=page_bg, fg=fg)
        self.model_badge.configure(bg=selected_bg, fg=muted)
        self.status_label.configure(bg=page_bg, fg=muted)

        self.style.configure("TFrame", background=page_bg)
        self.style.configure("TLabel", background=page_bg, foreground=fg)
        self.style.configure("TButton", padding=4)
        self._configure_hover_button(self.theme_button, button_bg, button_hover, fg)
        self.theme_button.configure(
            text="☀️  浅色" if self.dark_mode else "🌙  深色",
            highlightbackground=sidebar_bg,
            highlightcolor=fg,
        )
        self._configure_hover_button(self.new_chat_button, button_bg, button_hover, fg)
        self.new_chat_button.configure(
            highlightbackground=sidebar_bg,
            highlightcolor=fg,
        )
        self._configure_hover_button(self.thinking_button, button_bg, button_hover, fg)
        self.thinking_button.configure(
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
            self._configure_hover_button(
                button,
                selected_bg if selected else button_bg,
                button_hover,
                fg,
            )
            button.configure(
                disabledforeground="#777777",
                highlightbackground=sidebar_bg,
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
                highlightbackground=sidebar_bg,
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
            self.sidebar_open_button.grid_remove()
            self.main_frame.columnconfigure(0, minsize=218)
        else:
            self.sidebar.grid_remove()
            self.sidebar_open_button.grid()
            self.main_frame.columnconfigure(0, minsize=0)

    def _refresh_model_display(self) -> None:
        self.model_label.configure(text=self.model_name)
        self.model_badge.configure(text=self.model_name)
        self.thinking_button.configure(text=f"🧠  思考：{self._thinking_mode_label()}")
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
            self.regenerate_button.configure(state=tk.DISABLED)
            self.clear_button.configure(state=tk.DISABLED)
        else:
            self.new_chat_button.configure(state=tk.NORMAL)
            self.thinking_button.configure(state=tk.NORMAL)
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
            messagebox.showinfo("无法重新生成", "还没有可以重新生成的对话。")
            return

        if self.messages[-1]["role"] == "assistant":
            self.messages.pop()
            self.summarized_message_count = min(
                self.summarized_message_count,
                max(0, len(self.messages) - 1),
            )

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

    def delete_session_by_index(self, target_index: int) -> None:
        if self.is_waiting:
            return

        if target_index < 0 or target_index >= len(self.sessions):
            return

        title = str(self.sessions[target_index].get("title") or "这条对话")
        confirmed = messagebox.askyesno(
            "删除历史记录",
            f"确定删除「{title}」吗？\n\n此操作不可恢复。",
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
            self._append_chat("System", "历史记录已删除。Enter 发送，Shift+Enter 换行。", "system")
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
            messagebox.showinfo("无法删除", "请先在左侧选择一条历史记录。")
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
        self._append_chat("System", "已清屏。Enter 发送，Shift+Enter 换行。", "system")

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
        old_summary = existing_summary.strip() or "无。"
        new_context = self._format_messages_for_summary(messages_to_summarize)
        prompt = (
            f"已有摘要：\n{old_summary}\n\n"
            f"需要并入摘要的旧对话：\n{new_context}\n\n"
            "请输出更新后的摘要。"
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
                    "content": (
                        "此前较早对话的压缩摘要如下。回答时请把它作为长期上下文参考，"
                        "同时优先遵循最近原文消息：\n"
                        f"{summary.strip()}"
                    ),
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
