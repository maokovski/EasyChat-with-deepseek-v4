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
from tkinter import filedialog, messagebox, scrolledtext, ttk
from typing import Any, Dict, List, Optional
from ctypes import windll

from config_store import (
    SESSIONS_PATH,
    ensure_runtime_files,
    load_config,
    load_system_prompt,
    save_config,
)
from deepseek_client import DeepSeekClient, DeepSeekV4Client, Message
from ui_text import UI_TEXT


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
    replacements = {
        r"\leftrightarrow": "\u2194",
        r"\rightarrow": "\u2192",
        r"\Rightarrow": "\u21d2",
        r"\leftarrow": "\u2190",
        r"\Leftarrow": "\u21d0",
        r"\mapsto": "\u21a6",
        r"\times": "\u00d7",
        r"\cdot": "\u00b7",
        r"\div": "\u00f7",
        r"\pm": "\u00b1",
        r"\leq": "\u2264",
        r"\le": "\u2264",
        r"\geq": "\u2265",
        r"\ge": "\u2265",
        r"\neq": "\u2260",
        r"\ne": "\u2260",
        r"\approx": "\u2248",
        r"\simeq": "\u2243",
        r"\infty": "\u221e",
        r"\top": "T",
        r"\to": "\u2192",
        r"\oslash": "\u2298",
        r"\oplus": "\u2295",
        r"\otimes": "\u2297",
        r"\ominus": "\u2296",
        r"\alpha": "\u03b1",
        r"\beta": "\u03b2",
        r"\gamma": "\u03b3",
        r"\delta": "\u03b4",
        r"\epsilon": "\u03b5",
        r"\varepsilon": "\u03b5",
        r"\epsilon": "\u03b5",
        r"\theta": "\u03b8",
        r"\lambda": "\u03bb",
        r"\mu": "\u03bc",
        r"\nu": "\u03bd",
        r"\pi": "\u03c0",
        r"\sigma": "\u03c3",
        r"\omega": "\u03c9",
        r"\sum": "\u2211",
        r"\prod": "\u220f",
        r"\int": "\u222b",
        r"\partial": "\u2202",
        r"\nabla": "\u2207",
        r"\forall": "\u2200",
        r"\exists": "\u2203",
        r"\notin": "\u2209",
        r"\in": "\u2208",
        r"\subseteq": "\u2286",
        r"\subset": "\u2282",
        r"\cup": "\u222a",
        r"\cap": "\u2229",
        r"\quad": "  ",
        r"\qquad": "    ",
        r"\bigl": "",
        r"\bigr": "",
        r"\Bigl": "",
        r"\Bigr": "",
        r"\big": "",
        r"\Big": "",
        r"\bigg": "",
        r"\Bigg": "",
        r"\left": "",
        r"\right": "",
        r"\,": " ",
        r"\;": " ",
        r"\:": " ",
        r"\!": "",
    }
    text_wrappers = {
        "mathbf",
        "mathrm",
        "mathit",
        "mathsf",
        "mathtt",
        "mathcal",
        "mathbb",
        "boldsymbol",
        "boxed",
        "operatorname",
        "text",
    }
    named_functions = {
        "argmax",
        "argmin",
        "cos",
        "det",
        "diag",
        "dim",
        "exp",
        "ker",
        "lim",
        "log",
        "LSE",
        "max",
        "min",
        "rank",
        "sin",
        "tan",
        "tr",
    }

    def display_formula(match: re.Match[str]) -> str:
        formula = format_math_text(match.group(1).strip())
        return f"\n{formula}\n"

    def inline_formula(match: re.Match[str]) -> str:
        formula = format_math_text(match.group(1).strip())
        return f" {formula} "

    def read_braced(segment: str, start: int) -> tuple[Optional[str], int]:
        if start >= len(segment) or segment[start] != "{":
            return None, start

        depth = 0
        for index in range(start, len(segment)):
            char = segment[index]
            if char == "{":
                depth += 1
            elif char == "}":
                depth -= 1
                if depth == 0:
                    return segment[start + 1 : index], index + 1
        return None, start

    def replace_fractions(segment: str) -> str:
        output: List[str] = []
        index = 0
        marker = r"\frac"
        while index < len(segment):
            if not segment.startswith(marker, index):
                output.append(segment[index])
                index += 1
                continue

            numerator, after_numerator = read_braced(segment, index + len(marker))
            if numerator is None:
                output.append(marker)
                index += len(marker)
                continue
            denominator, after_denominator = read_braced(segment, after_numerator)
            if denominator is None:
                output.append(segment[index:after_numerator])
                index = after_numerator
                continue

            numerator = replace_fractions(numerator.strip())
            denominator = replace_fractions(denominator.strip())
            output.append(f"({numerator})/({denominator})")
            index = after_denominator
        return "".join(output)

    def replace_text_wrappers(segment: str) -> str:
        output: List[str] = []
        index = 0
        while index < len(segment):
            if segment[index] != "\\":
                output.append(segment[index])
                index += 1
                continue

            command_match = re.match(r"\\([A-Za-z]+)", segment[index:])
            if not command_match:
                output.append(segment[index])
                index += 1
                continue

            command = command_match.group(1)
            after_command = index + len(command_match.group(0))
            if command in ("begin", "end"):
                _environment, after_environment = read_braced(segment, after_command)
                index = after_environment if after_environment != after_command else after_command
                continue
            if command not in text_wrappers:
                output.append(segment[index:after_command])
                index = after_command
                continue

            content, after_content = read_braced(segment, after_command)
            if content is None:
                output.append(segment[index:after_command])
                index = after_command
                continue

            output.append(format_math_text(content.strip()))
            index = after_content
        return "".join(output)

    def format_math_text(segment: str) -> str:
        def exponent(match: re.Match[str]) -> str:
            value = match.group(1).strip()
            return f"^{value}" if value.startswith("(") and value.endswith(")") else f"^({value})"

        def subscript(match: re.Match[str]) -> str:
            value = match.group(1).strip()
            return f"_{value}" if value.startswith("(") and value.endswith(")") else f"_({value})"

        segment = re.sub(r"\\begin\{[^{}]+\}", "", segment)
        segment = re.sub(r"\\end\{[^{}]+\}", "", segment)
        segment = re.sub(r"\\\\(?:\[[^\]]*\])?", "\n", segment)
        segment = segment.replace("&", "")
        segment = replace_fractions(segment)
        previous = None
        while previous != segment:
            previous = segment
            segment = replace_text_wrappers(segment)
        segment = re.sub(r"\\sqrt\{([^{}]+)\}", r"sqrt(\1)", segment)
        segment = re.sub(r"\^\{([^{}]+)\}", exponent, segment)
        segment = re.sub(r"_\{([^{}]+)\}", subscript, segment)
        for raw, formatted in sorted(replacements.items(), key=lambda item: len(item[0]), reverse=True):
            segment = segment.replace(raw, formatted)
        for function_name in sorted(named_functions, key=len, reverse=True):
            segment = re.sub(rf"\\{function_name}\b", function_name, segment)
        segment = re.sub(r"\\([A-Za-z]+)", r"\1", segment)
        segment = re.sub(r"\{([^{}]+)\}", r"\1", segment)
        return re.sub(r"[ \t]{2,}", " ", segment).strip()

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
        segment = format_math_text(segment)

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
        self.root.minsize(860, 520)

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
        self.request_started_at: Optional[float] = None
        self.quick_bar_last_timer_second = -1
        self.streaming_response_active = False
        self.dark_mode = str(self.app_config.get("theme") or "light") == "dark"
        self.language = self._normalize_language(str(self.app_config.get("language") or "en"))
        self.sidebar_visible = True
        self.sidebar_width = self._normalize_sidebar_width(
            self.app_config.get("sidebar_width")
        )
        self.sidebar_drag_start_x = 0
        self.sidebar_drag_start_width = self.sidebar_width
        self.inspector_visible = True
        self.transcript: List[str] = []
        self.display_entries: List[tuple[str, str, str]] = []
        self.sessions: List[Dict[str, Any]] = self._load_sessions_from_disk()
        self.active_session_index: Optional[int] = None
        self.conversation_summary = ""
        self.summarized_message_count = 0
        self.link_count = 0
        self.history_rows: List[tuple[tk.Frame, tk.Button, tk.Button]] = []
        self.api_settings_window: Optional[tk.Toplevel] = None
        self.quick_bar_enabled = bool(self.app_config.get("quick_bar_enabled", True))
        self.quick_bar: Optional[tk.Toplevel] = None
        self.quick_bar_frame: Optional[tk.Frame] = None
        self.quick_bar_canvas: Optional[tk.Canvas] = None
        self.quick_bar_label: Optional[tk.Label] = None
        self.quick_bar_hint: Optional[tk.Label] = None
        self.quick_bar_status: Optional[tk.Frame] = None
        self.quick_bar_menu: Optional[tk.Menu] = None
        self.quick_bar_side = self._normalize_quick_bar_side(self.app_config.get("quick_bar_side"))
        self.quick_bar_drag_start_x = 0
        self.quick_bar_drag_start_y = 0
        self.quick_bar_origin_x = 0
        self.quick_bar_origin_y = 0
        self.quick_bar_dragged = False
        self.quick_bar_animating = False
        self.main_window_hidden = False
        self.shutdown_requested = False
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

        self.history_title = tk.Label(
            self.sidebar,
            text=self._text("history"),
            anchor="w",
            font=("Microsoft YaHei UI", 9),
        )
        self.history_title.grid(row=2, column=0, sticky="ew", padx=18, pady=(0, 6))

        self.history_frame = tk.Frame(
            self.sidebar,
            bd=0,
            highlightthickness=0,
            relief=tk.FLAT,
        )
        self.history_frame.grid(row=3, column=0, sticky="nsew", padx=14, pady=(0, 12))
        self.history_frame.columnconfigure(0, weight=1)

        self.sidebar_spacer = tk.Frame(self.sidebar, bd=0, highlightthickness=0)
        self.sidebar_spacer.grid(row=4, column=0, sticky="nsew")
        self.sidebar.rowconfigure(3, weight=1)

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
        self.content_frame.columnconfigure(1, minsize=284)
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

        self.inspector_button = tk.Button(
            self.topbar,
            text=self._text("inspector"),
            relief=tk.FLAT,
            bd=0,
            padx=10,
            pady=4,
            command=self.toggle_inspector,
        )
        self.inspector_button.grid(row=0, column=3, sticky="e", padx=(12, 0), pady=8)

        self.quick_bar_button = tk.Button(
            self.topbar,
            text=self._text("quick_bar"),
            relief=tk.FLAT,
            bd=0,
            padx=10,
            pady=4,
            command=self.hide_main_window,
        )
        self.quick_bar_button.grid(row=0, column=4, sticky="e", padx=(8, 0), pady=8)

        self.language_label = tk.Label(
            self.topbar,
            text=self._text("language"),
            anchor="e",
            font=("Segoe UI", 9),
        )
        self.language_label.grid(row=0, column=5, sticky="e", padx=(14, 6), pady=8)

        self.language_var = tk.StringVar(value=self._language_display_name(self.language))
        self.language_menu = tk.OptionMenu(
            self.topbar,
            self.language_var,
            "English",
            "Chinese",
            command=lambda _value: self.set_language_from_menu(),
        )
        self.language_menu.configure(relief=tk.FLAT, bd=0, highlightthickness=0)
        self.language_menu.grid(row=0, column=6, sticky="e", padx=(0, 8), pady=8)

        self.api_settings_button = tk.Button(
            self.topbar,
            text=f"\u2699 {self._text('settings')}",
            relief=tk.FLAT,
            bd=0,
            padx=10,
            pady=4,
            command=self.open_api_settings,
        )
        self.api_settings_button.grid(row=0, column=7, sticky="e", padx=(0, 10), pady=8)

        self.chat_panel = tk.Frame(self.content_frame, bd=0, highlightthickness=1)
        self.chat_panel.grid(row=1, column=0, sticky="nsew", padx=(24, 0), pady=(0, 10))
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
        self.chat_area.bind("<Button-1>", lambda _event: self.chat_area.focus_set())
        self.chat_area.bind("<Control-c>", self._copy_chat_selection)
        self.chat_area.bind("<Control-C>", self._copy_chat_selection)
        self.chat_area.bind("<<Copy>>", self._copy_chat_selection)
        self.chat_area.bind("<Button-3>", self._show_chat_context_menu)
        self.chat_context_menu = tk.Menu(self.chat_area, tearoff=0)
        self._refresh_chat_context_menu()

        self.inspector = tk.Frame(
            self.content_frame,
            width=260,
            bd=0,
            highlightthickness=1,
        )
        self.inspector.grid(row=1, column=1, rowspan=3, sticky="nsew", padx=12, pady=(0, 24))
        self.inspector.grid_propagate(False)
        self.inspector.columnconfigure(0, weight=1)

        self.inspector_title = tk.Label(
            self.inspector,
            text=self._text("inspector"),
            anchor="w",
            font=("Segoe UI", 12, "bold"),
        )
        self.inspector_title.grid(row=0, column=0, sticky="ew", padx=14, pady=(14, 10))

        self.model_panel = tk.Frame(self.inspector, bd=0, highlightthickness=0)
        self.model_panel.grid(row=1, column=0, sticky="ew", padx=14, pady=(0, 14))
        self.model_panel.columnconfigure(0, weight=1)

        self.model_title = tk.Label(
            self.model_panel,
            text=self._text("current_model"),
            anchor="w",
            font=("Microsoft YaHei UI", 9),
        )
        self.model_title.grid(row=0, column=0, sticky="ew", pady=(0, 2))

        self.model_label = tk.Label(
            self.model_panel,
            text=self.model_name,
            anchor="w",
            font=("Segoe UI", 10, "bold"),
        )
        self.model_label.grid(row=1, column=0, sticky="ew", pady=(0, 10))

        self.pro_button = tk.Button(
            self.model_panel,
            text="V4 Pro",
            relief=tk.FLAT,
            bd=0,
            anchor="w",
            command=lambda: self.set_model(DeepSeekClient.DEFAULT_MODEL),
        )
        self.pro_button.grid(row=2, column=0, sticky="ew", pady=(0, 6), ipady=8)

        self.flash_button = tk.Button(
            self.model_panel,
            text="V4 Flash",
            relief=tk.FLAT,
            bd=0,
            anchor="w",
            command=lambda: self.set_model(DeepSeekClient.FLASH_MODEL),
        )
        self.flash_button.grid(row=3, column=0, sticky="ew", pady=(0, 6), ipady=8)

        self.thinking_button = tk.Button(
            self.model_panel,
            text=f"Thinking: {self._thinking_mode_label()}",
            relief=tk.FLAT,
            bd=0,
            anchor="w",
            command=self.toggle_thinking_mode,
        )
        self.thinking_button.grid(row=4, column=0, sticky="ew", pady=(0, 8), ipady=8)

        self.session_panel = tk.Frame(self.inspector, bd=0, highlightthickness=0)
        self.session_panel.grid(row=2, column=0, sticky="ew", padx=14, pady=(0, 14))
        self.session_panel.columnconfigure(0, weight=1)

        self.session_title_label = tk.Label(
            self.session_panel,
            text=self._text("session_state"),
            anchor="w",
            font=("Microsoft YaHei UI", 9),
        )
        self.session_title_label.grid(row=0, column=0, sticky="ew", pady=(0, 8))

        self.turns_label = tk.Label(
            self.session_panel,
            text="",
            anchor="w",
            justify=tk.LEFT,
            font=("Segoe UI", 9),
        )
        self.turns_label.grid(row=1, column=0, sticky="ew", pady=(0, 6))

        self.memory_label = tk.Label(
            self.session_panel,
            text="",
            anchor="w",
            justify=tk.LEFT,
            wraplength=220,
            font=("Segoe UI", 9),
        )
        self.memory_label.grid(row=2, column=0, sticky="ew")

        self.sidebar_actions = tk.Frame(self.inspector, bd=0, highlightthickness=0)
        self.sidebar_actions.grid(row=3, column=0, sticky="ew", padx=14, pady=(0, 14))
        self.sidebar_actions.columnconfigure(0, weight=1)

        self.theme_button = tk.Button(
            self.sidebar_actions,
            text=self._text("theme_dark"),
            relief=tk.FLAT,
            bd=0,
            anchor="w",
            command=self.toggle_theme,
        )
        self.theme_button.grid(row=0, column=0, sticky="ew", pady=(0, 6), ipady=8)

        self.regenerate_button = tk.Button(
            self.sidebar_actions,
            text=f"R  {self._text('regenerate')}",
            relief=tk.FLAT,
            bd=0,
            anchor="w",
            command=self.regenerate_last,
        )
        self.regenerate_button.grid(row=1, column=0, sticky="ew", pady=(0, 6), ipady=8)

        self.save_button = tk.Button(
            self.sidebar_actions,
            text=f"S  {self._text('save_txt')}",
            relief=tk.FLAT,
            bd=0,
            anchor="w",
            command=self.save_transcript,
        )
        self.save_button.grid(row=2, column=0, sticky="ew", pady=(0, 6), ipady=8)

        self.clear_button = tk.Button(
            self.sidebar_actions,
            text=f"C  {self._text('clear')}",
            relief=tk.FLAT,
            bd=0,
            anchor="w",
            command=self.clear_chat,
        )
        self.clear_button.grid(row=3, column=0, sticky="ew", pady=(0, 8), ipady=8)

        self.status_label = tk.Label(
            self.content_frame,
            text="Ready",
            anchor="w",
            font=("Segoe UI", 9),
        )
        self.status_label.grid(row=2, column=0, sticky="ew", padx=(32, 0), pady=(0, 8))

        self.composer_frame = tk.Frame(self.content_frame, bd=0, highlightthickness=1)
        self.composer_frame.grid(row=3, column=0, sticky="ew", padx=(24, 0), pady=(0, 24))
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
        self._build_quick_bar()
        self.apply_theme()

    def _build_quick_bar(self) -> None:
        if not self.quick_bar_enabled or self.quick_bar is not None:
            return

        bar = tk.Toplevel(self.root)
        self.quick_bar = bar
        bar.withdraw()
        bar.overrideredirect(True)
        bar.attributes("-topmost", True)
        try:
            bar.attributes("-toolwindow", True)
        except tk.TclError:
            pass
        bar.resizable(False, False)
        bar.columnconfigure(0, weight=1)
        bar.rowconfigure(0, weight=1)

        width, height = self._quick_bar_size()
        self.quick_bar_frame = tk.Frame(
            bar,
            width=width,
            height=height,
            bd=0,
            highlightthickness=1,
        )
        self.quick_bar_frame.grid(row=0, column=0, sticky="nsew")
        self.quick_bar_frame.grid_propagate(False)
        self.quick_bar_frame.columnconfigure(0, weight=1)
        self.quick_bar_frame.rowconfigure(0, weight=1)

        self.quick_bar_canvas = tk.Canvas(
            self.quick_bar_frame,
            width=width,
            height=height,
            bd=0,
            highlightthickness=0,
            relief=tk.FLAT,
        )
        self.quick_bar_canvas.grid(row=0, column=0, sticky="nsew")

        self.quick_bar_menu = tk.Menu(bar, tearoff=0)
        self._refresh_quick_bar_menu()

        quick_bar_widgets = (
            bar,
            self.quick_bar_frame,
            self.quick_bar_canvas,
        )
        for widget in quick_bar_widgets:
            widget.bind("<ButtonPress-1>", self._start_quick_bar_drag)
            widget.bind("<B1-Motion>", self._drag_quick_bar)
            widget.bind("<ButtonRelease-1>", self._finish_quick_bar_drag)
            widget.bind("<Button-3>", self._show_quick_bar_menu)
            widget.bind("<Enter>", self._quick_bar_enter)
            widget.bind("<Leave>", self._quick_bar_leave)

        self._position_quick_bar()
        bar.deiconify()

    def _position_quick_bar(self) -> None:
        if self.quick_bar is None:
            return

        self.quick_bar.update_idletasks()
        width, height = self._quick_bar_size()
        screen_width = self.root.winfo_screenwidth()
        screen_height = self.root.winfo_screenheight()
        side = self._normalize_quick_bar_side(self.app_config.get("quick_bar_side"))
        x = 2 if side == "left" else max(0, screen_width - width - 2)
        y = self._normalize_quick_bar_y(self.app_config.get("quick_bar_y"), screen_height, height)
        self.quick_bar.geometry(f"{width}x{height}+{x}+{y}")

    def _quick_bar_size(self) -> tuple[int, int]:
        brand_chars = len(self._quick_bar_brand())
        status_chars = max(
            len(self._text("quick_bar_ready")),
            len(self._text("quick_bar_running")),
        )
        width = max(54, min(74, 34 + status_chars * 5))
        height = max(392, 124 + brand_chars * 20 + 82)
        return width, height

    def _quick_bar_brand(self) -> str:
        return "EASYCHAT"

    def _quick_bar_elapsed_seconds(self) -> int:
        if not self.is_waiting or self.request_started_at is None:
            return 0
        return max(0, int(time.perf_counter() - self.request_started_at))

    def _format_quick_bar_elapsed(self) -> str:
        seconds = self._quick_bar_elapsed_seconds()
        minutes, seconds = divmod(seconds, 60)
        return f"{minutes:02d}:{seconds:02d}"

    def _draw_quick_bar(
        self,
        panel_bg: str,
        border: str,
        fg: str,
        muted: str,
        accent_bg: str,
        accent_fg: str,
    ) -> None:
        if self.quick_bar_canvas is None:
            return

        width, height = self._quick_bar_size()
        side = self._normalize_quick_bar_side(self.app_config.get("quick_bar_side"))
        status_fill = "#f0b429" if self.is_waiting else ("#6ee7b7" if self.dark_mode else "#0f8f75")
        stripe_x = width - 4 if side == "left" else 0
        state_text = self._text("quick_bar_running") if self.is_waiting else self._text("quick_bar_ready")
        elapsed_text = self._format_quick_bar_elapsed() if self.is_waiting else "--:--"

        canvas = self.quick_bar_canvas
        canvas.configure(width=width, height=height, bg=panel_bg)
        canvas.delete("all")
        canvas.create_rectangle(0, 0, width - 1, height - 1, fill=panel_bg, outline=border)
        canvas.create_rectangle(stripe_x, 0, stripe_x + 3, height, fill=accent_bg, outline=accent_bg)
        canvas.create_rectangle(15, 14, width - 15, 17, fill=muted, outline=muted)
        canvas.create_oval(width // 2 - 5, 30, width // 2 + 5, 40, fill=status_fill, outline=status_fill)
        canvas.create_text(
            width // 2,
            58,
            text=state_text,
            fill=fg,
            font=("Microsoft YaHei UI", 8, "bold"),
        )
        canvas.create_text(
            width // 2,
            78,
            text=elapsed_text,
            fill=muted if not self.is_waiting else fg,
            font=("Cascadia Mono", 8, "bold"),
        )
        canvas.create_line(13, 96, width - 13, 96, fill=border)
        brand = self._quick_bar_brand()
        brand_start_y = 128
        brand_step = max(18, min(22, (height - 206) // max(1, len(brand) - 1)))
        for index, char in enumerate(brand):
            canvas.create_text(
                width // 2,
                brand_start_y + index * brand_step,
                text=char,
                fill=fg,
                font=("Segoe UI", 9, "bold"),
            )
        canvas.create_rectangle(10, height - 48, width - 10, height - 20, fill=accent_bg, outline=accent_bg)
        canvas.create_text(
            width // 2,
            height - 34,
            text="AI",
            fill=accent_fg,
            font=("Segoe UI", 9, "bold"),
        )

    def _normalize_quick_bar_side(self, side: Any) -> str:
        return "left" if str(side) == "left" else "right"

    def _normalize_quick_bar_y(self, value: Any, screen_height: int, height: int) -> int:
        try:
            y = int(value)
        except (TypeError, ValueError):
            y = (screen_height - height) // 2
        return max(8, min(y, max(8, screen_height - height - 8)))

    def _parse_window_geometry(self, geometry: str) -> Optional[tuple[int, int, int, int]]:
        match = re.match(r"^(\d+)x(\d+)([+-]\d+)([+-]\d+)$", str(geometry).strip())
        if not match:
            return None
        return (
            int(match.group(1)),
            int(match.group(2)),
            int(match.group(3)),
            int(match.group(4)),
        )

    def _current_main_geometry(self) -> tuple[int, int, int, int]:
        self.root.update_idletasks()
        parsed = self._parse_window_geometry(self.root.geometry())
        if parsed is not None:
            return parsed
        return (
            max(860, self.root.winfo_width()),
            max(520, self.root.winfo_height()),
            self.root.winfo_x(),
            self.root.winfo_y(),
        )

    def _offscreen_x_for_quick_bar_side(self, width: int) -> int:
        side = self._normalize_quick_bar_side(self.app_config.get("quick_bar_side"))
        if side == "left":
            return 18 - width
        return self.root.winfo_screenwidth() - 18

    def _animate_main_window(
        self,
        start: tuple[int, int, int, int],
        end: tuple[int, int, int, int],
        on_done: Optional[Any] = None,
    ) -> None:
        if self.quick_bar_animating:
            return

        self.quick_bar_animating = True
        frames = 10
        interval_ms = 14

        def step(frame: int) -> None:
            if not self.root.winfo_exists():
                return

            t = min(1.0, frame / frames)
            eased = 1 - (1 - t) ** 3
            width = round(start[0] + (end[0] - start[0]) * eased)
            height = round(start[1] + (end[1] - start[1]) * eased)
            x = round(start[2] + (end[2] - start[2]) * eased)
            y = round(start[3] + (end[3] - start[3]) * eased)
            self.root.geometry(f"{width}x{height}+{x}+{y}")

            if frame >= frames:
                self.quick_bar_animating = False
                if on_done is not None:
                    on_done()
                return

            self.root.after(interval_ms, lambda: step(frame + 1))

        step(0)

    def _refresh_quick_bar_menu(self) -> None:
        if self.quick_bar_menu is None:
            return
        self.quick_bar_menu.delete(0, tk.END)
        self.quick_bar_menu.add_command(
            label=self._text("quick_bar_show") if self.main_window_hidden else self._text("quick_bar_hide"),
            command=self._toggle_main_window_from_bar,
        )
        self.quick_bar_menu.add_command(label=self._text("quick_bar_new"), command=self._new_chat_from_bar)
        self.quick_bar_menu.add_command(label=self._text("quick_bar_settings"), command=self._open_api_settings_from_bar)
        self.quick_bar_menu.add_command(label=self._text("quick_bar_theme"), command=self.toggle_theme)
        self.quick_bar_menu.add_separator()
        self.quick_bar_menu.add_command(label=self._text("quick_bar_exit"), command=self.exit_app)

    def _show_quick_bar_menu(self, event: tk.Event) -> str:
        self._refresh_quick_bar_menu()
        if self.quick_bar_menu is not None:
            self.quick_bar_menu.tk_popup(event.x_root, event.y_root)
        return "break"

    def _quick_bar_enter(self, _event: tk.Event) -> None:
        if self.quick_bar_frame is not None:
            self.quick_bar_frame.configure(cursor="fleur")

    def _quick_bar_leave(self, _event: tk.Event) -> None:
        if self.quick_bar_frame is not None:
            self.quick_bar_frame.configure(cursor="")

    def _toggle_main_window_from_bar(self, _event: Optional[tk.Event] = None) -> str:
        if self.main_window_hidden or not self.root.winfo_viewable():
            self.show_main_window()
        else:
            self.hide_main_window()
        return "break"

    def _new_chat_from_bar(self) -> None:
        self.show_main_window()
        self.new_chat()

    def _open_api_settings_from_bar(self) -> None:
        self.show_main_window()
        self.open_api_settings()

    def _start_quick_bar_drag(self, event: tk.Event) -> None:
        if self.quick_bar is None:
            return
        self.quick_bar_drag_start_x = int(event.x_root)
        self.quick_bar_drag_start_y = int(event.y_root)
        self.quick_bar_origin_x = self.quick_bar.winfo_x()
        self.quick_bar_origin_y = self.quick_bar.winfo_y()
        self.quick_bar_dragged = False

    def _drag_quick_bar(self, event: tk.Event) -> None:
        if self.quick_bar is None:
            return
        dx = int(event.x_root) - self.quick_bar_drag_start_x
        dy = int(event.y_root) - self.quick_bar_drag_start_y
        if abs(dx) > 3 or abs(dy) > 3:
            self.quick_bar_dragged = True
        width, height = self._quick_bar_size()
        screen_width = self.root.winfo_screenwidth()
        screen_height = self.root.winfo_screenheight()
        x = max(0, min(self.quick_bar_origin_x + dx, screen_width - width))
        y = max(8, min(self.quick_bar_origin_y + dy, max(8, screen_height - height - 8)))
        self.quick_bar.geometry(f"{width}x{height}+{x}+{y}")

    def _finish_quick_bar_drag(self, event: tk.Event) -> str:
        if self.quick_bar is None:
            return "break"
        if not self.quick_bar_dragged:
            return self._toggle_main_window_from_bar(event)

        width, height = self._quick_bar_size()
        screen_width = self.root.winfo_screenwidth()
        screen_height = self.root.winfo_screenheight()
        current_x = self.quick_bar.winfo_x()
        current_y = self.quick_bar.winfo_y()
        self.quick_bar_side = "left" if current_x < screen_width // 2 else "right"
        x = 2 if self.quick_bar_side == "left" else max(0, screen_width - width - 2)
        y = self._normalize_quick_bar_y(current_y, screen_height, height)
        self.quick_bar.geometry(f"{width}x{height}+{x}+{y}")
        self.app_config["quick_bar_side"] = self.quick_bar_side
        self.app_config["quick_bar_y"] = y
        save_config(self.app_config)
        return "break"

    def hide_main_window(self) -> None:
        if not self.quick_bar_enabled:
            self.root.iconify()
            return
        if self.quick_bar_animating:
            return

        self._save_current_session()
        saved_geometry = self.root.geometry()
        self.app_config["window_geometry"] = saved_geometry
        save_config(self.app_config)
        start = self._current_main_geometry()
        end = (start[0], start[1], self._offscreen_x_for_quick_bar_side(start[0]), start[3])

        def finish_hide() -> None:
            self.root.withdraw()
            self.root.geometry(saved_geometry)
            self.main_window_hidden = True
            self._refresh_quick_bar_menu()

        self._animate_main_window(start, end, finish_hide)

    def show_main_window(self) -> None:
        if self.quick_bar_animating:
            return

        target_geometry = str(self.app_config.get("window_geometry") or self.root.geometry())
        target = self._parse_window_geometry(target_geometry) or self._current_main_geometry()
        start = (target[0], target[1], self._offscreen_x_for_quick_bar_side(target[0]), target[3])
        self.root.geometry(f"{start[0]}x{start[1]}+{start[2]}+{start[3]}")
        self.root.deiconify()
        self.root.lift()

        def finish_show() -> None:
            self.root.focus_force()
            self.main_window_hidden = False
            self._refresh_quick_bar_menu()
            self.input_box.focus_set()

        self._animate_main_window(start, target, finish_show)

    def exit_app(self) -> None:
        self.shutdown_requested = True
        self._save_current_session()
        if self.root.winfo_exists():
            self.app_config["window_geometry"] = self.root.geometry()
        save_config(self.app_config)
        if self.quick_bar is not None and self.quick_bar.winfo_exists():
            self.quick_bar.destroy()
        self.root.destroy()

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
        if hasattr(self, "turns_label"):
            self._refresh_inspector()

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

    def _refresh_chat_context_menu(self) -> None:
        if not hasattr(self, "chat_context_menu"):
            return
        self.chat_context_menu.delete(0, tk.END)
        self.chat_context_menu.add_command(
            label=self._text("copy"),
            command=lambda: self._copy_chat_selection(None),
        )

    def _copy_chat_selection(self, _event: Optional[tk.Event] = None) -> str:
        try:
            selected = self.chat_area.get(tk.SEL_FIRST, tk.SEL_LAST)
        except tk.TclError:
            return "break"
        if selected:
            self.root.clipboard_clear()
            self.root.clipboard_append(selected)
        return "break"

    def _show_chat_context_menu(self, event: tk.Event) -> str:
        self.chat_area.focus_set()
        try:
            has_selection = bool(self.chat_area.get(tk.SEL_FIRST, tk.SEL_LAST))
        except tk.TclError:
            has_selection = False
        self.chat_context_menu.entryconfigure(
            0,
            state=tk.NORMAL if has_selection else tk.DISABLED,
        )
        self.chat_context_menu.tk_popup(event.x_root, event.y_root)
        return "break"

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

    def _start_streaming_chat_entry(self, speaker: str) -> None:
        self.streaming_response_active = True
        self.chat_area.configure(state=tk.NORMAL)
        self._insert_with_tags(f"{speaker}:\n", "assistant", "md_speaker")
        self.chat_area.configure(state=tk.DISABLED)
        self.chat_area.see(tk.END)

    def _append_streaming_chunk(self, chunk: str) -> None:
        if not chunk:
            return

        if not self.streaming_response_active:
            self._start_streaming_chat_entry("DeepSeek")

        self.chat_area.configure(state=tk.NORMAL)
        self._insert_with_tags(chunk, "assistant")
        self.chat_area.configure(state=tk.DISABLED)
        self.chat_area.see(tk.END)

    def _finish_streaming_chat_entry(self) -> None:
        if not self.streaming_response_active:
            return

        self.streaming_response_active = False
        self.chat_area.configure(state=tk.NORMAL)
        self._insert_with_tags("\n\n", "assistant")
        self.chat_area.configure(state=tk.DISABLED)
        self.chat_area.see(tk.END)

    def _render_current_chat(self) -> None:
        self.chat_area.configure(state=tk.NORMAL)
        self.chat_area.delete("1.0", tk.END)
        self.chat_area.configure(state=tk.DISABLED)
        for speaker, text, tag in self.display_entries:
            self._insert_chat_entry(speaker, text, tag)
        self._refresh_inspector()

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
        self.inspector_button.configure(text=self._text("inspector"))
        self.quick_bar_button.configure(text=self._text("quick_bar"))
        self.inspector_title.configure(text=self._text("inspector"))
        self.session_title_label.configure(text=self._text("session_state"))
        self.regenerate_button.configure(text=f"R  {self._text('regenerate')}")
        self.save_button.configure(text=f"S  {self._text('save_txt')}")
        self.clear_button.configure(text=f"C  {self._text('clear')}")
        self.api_settings_button.configure(text=f"\u2699 {self._text('settings')}")
        self.language_label.configure(text=self._text("language"))
        self.language_var.set(self._language_display_name(self.language))
        self._refresh_chat_context_menu()
        self._refresh_quick_bar_menu()
        self._refresh_model_display()
        self._refresh_inspector()

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
        if self.quick_bar is not None and self.quick_bar.winfo_exists():
            rail_bg = "#151a20" if self.dark_mode else "#f8faf7"
            self.quick_bar.configure(bg=rail_bg)
            if self.quick_bar_frame is not None:
                self.quick_bar_frame.configure(
                    bg=rail_bg,
                    highlightbackground=border,
                    highlightcolor=border,
                )
            self._draw_quick_bar(rail_bg, border, fg, muted, accent_bg, accent_fg)
            if self.quick_bar_menu is not None:
                self.quick_bar_menu.configure(
                    bg=button_bg,
                    fg=fg,
                    activebackground=button_hover,
                    activeforeground=fg,
                )
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
        self.inspector.configure(
            bg=panel_bg,
            highlightbackground=border,
            highlightcolor=border,
        )
        self.session_panel.configure(bg=panel_bg)
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
        self._configure_hover_button(self.inspector_button, button_bg, button_hover, fg)
        self.inspector_button.configure(
            highlightbackground=panel_bg,
            highlightcolor=fg,
        )
        self._configure_hover_button(self.quick_bar_button, button_bg, button_hover, fg)
        self.quick_bar_button.configure(
            highlightbackground=panel_bg,
            highlightcolor=fg,
        )
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
        self.inspector_title.configure(bg=panel_bg, fg=fg)
        self.session_title_label.configure(bg=panel_bg, fg=muted)
        self.turns_label.configure(bg=panel_bg, fg=fg)
        self.memory_label.configure(bg=panel_bg, fg=muted)

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
        self._sync_inspector_visibility()

    def toggle_theme(self) -> None:
        self.dark_mode = not self.dark_mode
        self.app_config["theme"] = "dark" if self.dark_mode else "light"
        save_config(self.app_config)
        self.apply_theme()

    def toggle_sidebar(self) -> None:
        self.sidebar_visible = not self.sidebar_visible
        self._sync_sidebar_visibility()

    def toggle_inspector(self) -> None:
        self.inspector_visible = not self.inspector_visible
        self._sync_inspector_visibility()

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

    def _sync_inspector_visibility(self) -> None:
        if self.inspector_visible:
            if not self.inspector.winfo_ismapped():
                self.inspector.grid(row=1, column=1, rowspan=3, sticky="nsew", padx=12, pady=(0, 24))
            self.content_frame.columnconfigure(1, minsize=284)
        else:
            self.inspector.grid_remove()
            self.content_frame.columnconfigure(1, minsize=0)

    def _refresh_inspector(self) -> None:
        if not hasattr(self, "turns_label"):
            return

        real_messages = [message for message in self.messages if message.get("role") != "system"]
        self.turns_label.configure(
            text=self._text("session_turns").format(
                turns=self.conversation_count,
                messages=len(real_messages),
            )
        )
        summary = self.conversation_summary.strip() or self._text("summary_none")
        summary_preview = summary if len(summary) <= 180 else f"{summary[:177]}..."
        self.memory_label.configure(
            text=self._text("memory_state").format(
                count=self.summarized_message_count,
                summary=summary_preview,
            )
        )

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
        self._refresh_inspector()
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
        window.title(self._text("settings"))
        window.geometry("760x520")
        window.minsize(700, 460)
        window.transient(self.root)

        page_bg = "#171a1f" if self.dark_mode else "#f5f6f2"
        sidebar_bg = "#111418" if self.dark_mode else "#e8ece5"
        panel_bg = "#1f242b" if self.dark_mode else "#fbfcf8"
        input_bg = "#222831" if self.dark_mode else "#ffffff"
        fg = "#f2f3ef" if self.dark_mode else "#1c211f"
        muted = "#a8b0b6" if self.dark_mode else "#65706b"
        border = "#343c46" if self.dark_mode else "#cdd6ce"
        button_bg = "#20262e" if self.dark_mode else "#f2f5ef"
        button_hover = "#2b343f" if self.dark_mode else "#e0e8df"
        selected_bg = "#29453f" if self.dark_mode else "#d6eee6"
        accent_bg = "#3dd6b3" if self.dark_mode else "#0f8f75"
        accent_hover = "#66e4c9" if self.dark_mode else "#0a755f"
        accent_fg = "#071613" if self.dark_mode else "#ffffff"

        window.configure(bg=page_bg)
        window.columnconfigure(1, weight=1)
        window.rowconfigure(0, weight=1)

        nav = tk.Frame(window, bg=sidebar_bg, bd=0, highlightthickness=0, width=172)
        nav.grid(row=0, column=0, sticky="ns")
        nav.grid_propagate(False)
        nav.columnconfigure(0, weight=1)

        content = tk.Frame(window, bg=page_bg, bd=0, highlightthickness=0)
        content.grid(row=0, column=1, sticky="nsew")
        content.columnconfigure(0, weight=1)
        content.rowconfigure(1, weight=1)

        title_label = tk.Label(
            content,
            text="",
            bg=page_bg,
            fg=fg,
            anchor="w",
            font=("Microsoft YaHei UI", 16, "bold"),
        )
        title_label.grid(row=0, column=0, sticky="ew", padx=22, pady=(20, 12))

        body = tk.Frame(content, bg=panel_bg, bd=0, highlightthickness=1, highlightbackground=border)
        body.grid(row=1, column=0, sticky="nsew", padx=22, pady=(0, 12))
        body.columnconfigure(0, minsize=260)
        body.columnconfigure(1, minsize=320)
        body.columnconfigure(2, weight=1)

        actions = tk.Frame(content, bg=page_bg, bd=0, highlightthickness=0)
        actions.grid(row=2, column=0, sticky="e", padx=22, pady=(0, 18))

        nav_title = tk.Label(
            nav,
            text=self._text("settings"),
            bg=sidebar_bg,
            fg=fg,
            anchor="w",
            font=("Microsoft YaHei UI", 13, "bold"),
        )
        nav_title.grid(row=0, column=0, sticky="ew", padx=16, pady=(18, 14))

        categories = [
            ("api", self._text("settings_api")),
            ("appearance", self._text("settings_appearance")),
            ("model", self._text("settings_model")),
            ("quick_bar", self._text("settings_quick_bar")),
        ]
        nav_buttons: Dict[str, tk.Button] = {}

        api_key_var = tk.StringVar(value=str(self.app_config.get("DEEPSEEK_API_KEY") or ""))
        base_url_var = tk.StringVar(
            value=str(self.app_config.get("DEEPSEEK_BASE_URL") or DeepSeekClient.DEFAULT_BASE_URL)
        )
        reveal_var = tk.BooleanVar(value=False)
        theme_var = tk.StringVar(value="dark" if self.dark_mode else "light")
        settings_language_var = tk.StringVar(value=self._language_display_name(self.language))
        default_model_var = tk.StringVar(value=self.model_name)
        pro_thinking_var = tk.StringVar(value=self.thinking_modes.get(DeepSeekClient.DEFAULT_MODEL, "disabled"))
        flash_thinking_var = tk.StringVar(value=self.thinking_modes.get(DeepSeekClient.FLASH_MODEL, "disabled"))
        quick_enabled_var = tk.BooleanVar(value=self.quick_bar_enabled)
        quick_side_var = tk.StringVar(value=self._normalize_quick_bar_side(self.app_config.get("quick_bar_side")))
        quick_y_value = self.app_config.get("quick_bar_y")
        quick_y_var = tk.StringVar(value="" if quick_y_value is None else str(quick_y_value))

        def clear_body() -> None:
            for child in body.winfo_children():
                child.destroy()

        def section_header(row: int, text: str) -> int:
            label = tk.Label(
                body,
                text=text,
                bg=panel_bg,
                fg=fg,
                anchor="w",
                font=("Microsoft YaHei UI", 12, "bold"),
            )
            label.grid(row=row, column=0, columnspan=2, sticky="w", padx=18, pady=(16, 10))
            return row + 1

        def setting_label(row: int, text: str, hint: str = "") -> None:
            label = tk.Label(
                body,
                text=text,
                bg=panel_bg,
                fg=fg,
                anchor="w",
                font=("Microsoft YaHei UI", 10, "bold"),
            )
            label.grid(row=row, column=0, sticky="nw", padx=(18, 16), pady=(6, 2))
            if hint:
                hint_label = tk.Label(
                    body,
                    text=hint,
                    bg=panel_bg,
                    fg=muted,
                    anchor="w",
                    justify=tk.LEFT,
                    wraplength=220,
                    font=("Microsoft YaHei UI", 9),
                )
                hint_label.grid(row=row + 1, column=0, sticky="nw", padx=(18, 16), pady=(0, 10))

        def styled_entry(row: int, variable: tk.StringVar, show: str = "") -> tk.Entry:
            entry = tk.Entry(
                body,
                textvariable=variable,
                show=show,
                width=34,
                bg=input_bg,
                fg=fg,
                insertbackground=fg,
                relief=tk.FLAT,
                highlightthickness=1,
                highlightbackground=border,
                highlightcolor=accent_bg,
            )
            entry.grid(row=row, column=1, sticky="w", padx=(0, 18), pady=(6, 10), ipady=6)
            return entry

        def styled_menu(row: int, variable: tk.StringVar, values: List[str]) -> tk.OptionMenu:
            menu = tk.OptionMenu(body, variable, *values)
            menu.configure(
                width=30,
                bg=input_bg,
                fg=fg,
                activebackground=button_hover,
                activeforeground=fg,
                relief=tk.FLAT,
                bd=0,
                highlightthickness=1,
                highlightbackground=border,
            )
            menu["menu"].configure(bg=input_bg, fg=fg, activebackground=button_hover)
            menu.grid(row=row, column=1, sticky="w", padx=(0, 18), pady=(6, 10))
            return menu

        def styled_check(row: int, variable: tk.BooleanVar, text: str) -> tk.Checkbutton:
            check = tk.Checkbutton(
                body,
                text=text,
                variable=variable,
                bg=panel_bg,
                fg=fg,
                activebackground=panel_bg,
                activeforeground=fg,
                selectcolor=panel_bg,
                anchor="w",
            )
            check.grid(row=row, column=1, sticky="w", padx=(0, 18), pady=(6, 10))
            return check

        def render_category(category: str) -> None:
            clear_body()
            for key, button in nav_buttons.items():
                selected = key == category
                self._configure_hover_button(button, selected_bg if selected else sidebar_bg, button_hover, fg)
                button.configure(highlightbackground=sidebar_bg)

            title_text = dict(categories).get(category, self._text("settings"))
            title_label.configure(text=title_text)
            row = 0

            if category == "api":
                row = section_header(row, self._text("api_settings"))
                setting_label(row, "API Key", "Stored in local config.json.")
                api_key_entry = styled_entry(row, api_key_var, show="" if reveal_var.get() else "*")
                row += 2

                def toggle_reveal() -> None:
                    api_key_entry.configure(show="" if reveal_var.get() else "*")

                reveal_check = styled_check(row, reveal_var, self._text("show_api_key"))
                reveal_check.configure(command=toggle_reveal)
                row += 1
                setting_label(row, "Base URL", "OpenAI-compatible DeepSeek endpoint.")
                styled_entry(row, base_url_var)
                row += 2
            elif category == "appearance":
                row = section_header(row, self._text("settings_appearance"))
                setting_label(row, self._text("theme_dark"), "Choose the application color theme.")
                styled_menu(row, theme_var, ["light", "dark"])
                row += 2
                setting_label(row, self._text("language"), "Switch UI language at runtime.")
                styled_menu(row, settings_language_var, ["English", "Chinese"])
                row += 2
            elif category == "model":
                row = section_header(row, self._text("settings_model"))
                setting_label(row, self._text("current_model"), "Default model for new requests.")
                styled_menu(row, default_model_var, [DeepSeekClient.DEFAULT_MODEL, DeepSeekClient.FLASH_MODEL])
                row += 2
                setting_label(row, "V4 Pro Thinking", "Persisted thinking mode for V4 Pro.")
                styled_menu(row, pro_thinking_var, ["disabled", "high", "max"])
                row += 2
                setting_label(row, "V4 Flash Thinking", "Persisted thinking mode for V4 Flash.")
                styled_menu(row, flash_thinking_var, ["disabled", "high", "max"])
                row += 2
            else:
                row = section_header(row, self._text("settings_quick_bar"))
                setting_label(row, "Enable", "Show the always-on-top edge bar.")
                styled_check(row, quick_enabled_var, self._text("settings_quick_bar"))
                row += 1
                setting_label(row, "Dock Side", "Side used when the bar snaps to the screen edge.")
                styled_menu(row, quick_side_var, ["right", "left"])
                row += 2
                setting_label(row, "Y Position", "Leave empty to center the bar automatically.")
                styled_entry(row, quick_y_var)
                row += 2

        for index, (key, label) in enumerate(categories, start=1):
            button = tk.Button(
                nav,
                text=label,
                relief=tk.FLAT,
                bd=0,
                anchor="w",
                padx=14,
                pady=9,
                command=lambda category_key=key: render_category(category_key),
            )
            button.grid(row=index, column=0, sticky="ew", padx=10, pady=(0, 4))
            nav_buttons[key] = button

        def close_window() -> None:
            self.api_settings_window = None
            window.destroy()

        def save_settings() -> None:
            api_key = api_key_var.get().strip()
            base_url = base_url_var.get().strip() or DeepSeekClient.DEFAULT_BASE_URL
            self.app_config["DEEPSEEK_API_KEY"] = api_key
            self.app_config["DEEPSEEK_BASE_URL"] = base_url
            self.dark_mode = theme_var.get() == "dark"
            self.app_config["theme"] = theme_var.get()
            self.language = "zh" if settings_language_var.get() == "Chinese" else "en"
            self.app_config["language"] = self.language
            self.model_name = default_model_var.get()
            if self.model_name not in (DeepSeekClient.DEFAULT_MODEL, DeepSeekClient.FLASH_MODEL):
                self.model_name = DeepSeekClient.DEFAULT_MODEL
            self.app_config["default_model"] = self.model_name
            self.thinking_modes = {
                DeepSeekClient.DEFAULT_MODEL: self._normalize_thinking_mode(pro_thinking_var.get()),
                DeepSeekClient.FLASH_MODEL: self._normalize_thinking_mode(flash_thinking_var.get()),
            }
            self.app_config["thinking_modes"] = dict(self.thinking_modes)
            self.quick_bar_enabled = bool(quick_enabled_var.get())
            self.quick_bar_side = self._normalize_quick_bar_side(quick_side_var.get())
            self.app_config["quick_bar_enabled"] = self.quick_bar_enabled
            self.app_config["quick_bar_side"] = self.quick_bar_side
            y_text = quick_y_var.get().strip()
            if y_text:
                try:
                    self.app_config["quick_bar_y"] = int(y_text)
                except ValueError:
                    self.app_config["quick_bar_y"] = None
            else:
                self.app_config["quick_bar_y"] = None
            save_config(self.app_config)

            if api_key:
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
            else:
                self.client = None

            if self.quick_bar_enabled and self.quick_bar is None:
                self._build_quick_bar()
            elif not self.quick_bar_enabled and self.quick_bar is not None and self.quick_bar.winfo_exists():
                self.quick_bar.destroy()
                self.quick_bar = None
                self.quick_bar_frame = None
                self.quick_bar_canvas = None
                self.quick_bar_menu = None
            elif self.quick_bar is not None and self.quick_bar.winfo_exists():
                self._position_quick_bar()

            self.status_label.configure(text="API settings saved")
            self._refresh_language_text()
            self._refresh_model_display()
            self.apply_theme()
            messagebox.showinfo(self._text("settings"), self._text("api_saved_ok"), parent=window)
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
            command=save_settings,
        )
        save_button.grid(row=0, column=1)
        self._configure_hover_button(save_button, accent_bg, accent_hover, accent_fg, accent_fg)

        window.protocol("WM_DELETE_WINDOW", close_window)
        render_category("api")
        window.update_idletasks()
        x = self.root.winfo_rootx() + max(0, (self.root.winfo_width() - window.winfo_width()) // 2)
        y = self.root.winfo_rooty() + max(0, (self.root.winfo_height() - window.winfo_height()) // 3)
        window.geometry(f"+{x}+{y}")
        window.focus_set()

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
        self.request_started_at = time.perf_counter()
        self.quick_bar_last_timer_second = -1
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
            self.result_queue.put(
                ("start", turn_number, model_name, 0.0, "", updated_summary, updated_count)
            )
            answer_parts: List[str] = []
            for chunk in self.client.stream_chat(
                messages=context_messages,
                model=model_name,
                thinking="disabled" if thinking_mode == "disabled" else "enabled",
                reasoning_effort="high" if thinking_mode == "disabled" else thinking_mode,
                temperature=0.7 if thinking_mode == "disabled" else None,
            ):
                answer_parts.append(chunk)
                self.result_queue.put(
                    ("chunk", turn_number, model_name, 0.0, chunk, updated_summary, updated_count)
                )
            answer = "".join(answer_parts)
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
        handled_final = False
        try:
            while True:
                (
                    status,
                    turn_number,
                    model_name,
                    elapsed,
                    payload,
                    updated_summary,
                    updated_count,
                ) = self.result_queue.get_nowait()

                if status == "start":
                    self._start_streaming_chat_entry(
                        f"Conversation {turn_number} - DeepSeek ({model_name}, streaming)"
                    )
                    self.status_label.configure(
                        text=f"Conversation {turn_number}: streaming from {model_name}..."
                    )
                    continue

                if status == "chunk":
                    self._append_streaming_chunk(payload)
                    continue

                if status == "ok":
                    self._finish_streaming_chat_entry()
                    self.conversation_summary = str(updated_summary or "")
                    self.summarized_message_count = int(updated_count or 0)
                    self.messages.append({"role": "assistant", "content": payload})
                    self._append_chat(
                        f"Conversation {turn_number} - DeepSeek ({model_name}, {elapsed:.2f}s)",
                        payload,
                        "assistant",
                    )
                    self._render_current_chat()
                    self.status_label.configure(
                        text=f"Ready - conversation {turn_number} took {elapsed:.2f}s"
                    )
                else:
                    self.streaming_response_active = False
                    self._append_chat(
                        f"Conversation {turn_number} - Error ({model_name}, {elapsed:.2f}s)",
                        payload,
                        "error",
                    )
                    self._render_current_chat()
                    self.status_label.configure(
                        text=f"Request failed - conversation {turn_number} took {elapsed:.2f}s"
                    )

                self.is_waiting = False
                self.request_started_at = None
                self.quick_bar_last_timer_second = -1
                self.send_button.configure(state=tk.NORMAL)
                self._refresh_model_display()
                self._save_current_session()
                handled_final = True
        except queue.Empty:
            pass

        if self.is_waiting:
            elapsed_second = self._quick_bar_elapsed_seconds()
            if elapsed_second != self.quick_bar_last_timer_second:
                self.quick_bar_last_timer_second = elapsed_second
                self.apply_theme()

        delay = 100 if handled_final else 50
        self.root.after(delay, self._poll_results)


def launch_gui() -> None:
    configure_windows_dpi_awareness()
    ensure_runtime_files()
    root = tk.Tk()
    configure_tk_scaling(root)
    app = DeepSeekChatApp(root)

    def on_close() -> None:
        if app.shutdown_requested or not app.quick_bar_enabled:
            app.exit_app()
        else:
            app.hide_main_window()

    root.protocol("WM_DELETE_WINDOW", on_close)
    root.mainloop()


def main() -> None:
    launch_gui()


if __name__ == "__main__":
    main()
