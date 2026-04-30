# AI Agent Project Notes

Last updated: 2026-04-30

This file is intended for AI coding agents that need to understand the current
state of this repository before making changes.

Before making edits, also read `WORKFLOW.md` for the expected agent workflow.

## Project Summary

This is a small Windows-friendly Tkinter desktop chat client for DeepSeek's
OpenAI-compatible chat API. The user-facing entrypoint is `ds_v4.py`, which
re-exports the compatibility surface from `deepseek_api_client.py`.

## Current Features

- Tkinter desktop chat UI.
- DeepSeek API access through the `openai` Python SDK.
- Runtime configuration from `config.json`, created from defaults when missing.
- API credentials configured through `config.json` or the in-app API Settings
  window.
- System prompt loaded from `prompts.txt`.
- Local conversation persistence under `conversations/`.
- Session history list and session reload support.
- New chat, clear chat, regenerate last answer, and save transcript actions.
- Light/dark theme support.
- Sidebar visibility toggle.
- Model switching between DeepSeek model options exposed by the UI.
- Streaming response handling through a worker thread and UI polling queue.
- Basic formatting helpers for Markdown/LaTeX-like math text in the Tk text
  widget.
- Tuned chat and input text line spacing for compact, readable Chinese text.
- GUI buttons have hover feedback, and the sidebar, chat area, and input area
  use distinct light/dark surface colors.
- Markdown-aware reply formatting preserves headings, separators, lists, tables,
  quotes, code fences, and inline code examples without adding paragraph
  indentation.
- Chat output renders common Markdown styles in the Tk text widget, including
  headings, bold/italic/strikethrough text, inline code, fenced code,
  separators, superscript/subscript HTML tags, and clickable links including
  bare URLs.
- Long conversations use summary memory: older messages are compressed into a
  saved conversation summary while recent messages remain in full text for API
  requests.
- Sidebar history supports deleting a selected saved conversation with
  confirmation and current-session reset when needed. Delete controls are placed
  beside individual history rows.
- Each DeepSeek V4 model has an independent thinking mode setting, switchable
  between disabled, high, and max.
- Chat rendering uses a dedicated emoji font tag for Unicode emoji in normal
  message text.
- Markdown table blocks are normalized by display width and rendered with a
  dedicated table font for better Chinese/emoji column alignment.
- Sidebar action buttons use emoji-leading labels for a more consistent visual
  language.
- Portable Windows build flow through `build_exe.ps1` and PyInstaller.
- A compact API settings subwindow is available from the top bar for editing
  the DeepSeek API key and base URL without manually opening `config.json`.
- The UI language can be switched at runtime between English and Chinese; source
  files keep Chinese UI strings as escaped Unicode so literal Chinese characters
  do not appear in project files.
- Microsoft Edge extension prototype under `edge_extension/` with a Manifest V3
  popup chat UI, local settings storage, transcript download, and active-page
  context capture including visible page text and common interactive elements.

## Important Files

- `deepseek_api_client.py`: Main Tkinter application code. Keeps public exports
  for compatibility and contains `DeepSeekChatApp`, DPI setup, Markdown display
  helpers, summary-memory orchestration, and GUI behavior.
- `deepseek_client.py`: DeepSeek/OpenAI-compatible API wrapper, message typing,
  and `DeepSeekV4Client` alias.
- `config_store.py`: Runtime directory resolution, config loading/saving,
  system prompt loading, and session file paths.
- `ui_text.py`: English and Chinese UI text used by runtime language switching.
- `ds_v4.py`: Compatibility entrypoint. Imports from `deepseek_api_client.py`
  and calls `main()` when executed.
- `config.example.json`: Template config. Do not put real API keys in the repo.
- `prompts.txt`: Default system prompt used by the app.
- `build_exe.ps1`: Installs `pyinstaller` and `openai`, builds a one-folder
  Windows app, and copies runtime files into `dist/DeepSeekChat/`.
- `README.md`: User setup, local run, and portable build instructions.
- `PACKAGING.md`: Short packaging notes for the portable build.
- `.gitignore`: Ignores local secrets and generated/runtime output such as
  `config.json`, `dist/`, `build/`, `conversations/`, and Python caches.

## Runtime Behavior

On startup, the app resolves its runtime directory differently depending on
whether it is running from source or from a frozen executable:

- Source run: the directory containing `config_store.py`.
- PyInstaller build: the directory containing the executable.

The app ensures these runtime files exist:

- `config.json`
- `prompts.txt`
- `conversations/`

Conversation sessions are stored in `conversations/sessions.json`.

## Run And Build Commands

Install dependency:

```powershell
pip install openai
```

Run from source:

```powershell
python ds_v4.py
```

Build portable Windows folder:

```powershell
.\build_exe.ps1
```

Expected build output:

```text
dist/DeepSeekChat/DeepSeekChat.exe
```

## Modification Log

### 2026-04-28

- Added this `AGENTS.md` project notes file for future AI agents.
- Added `WORKFLOW.md` with the expected inspect, edit, verify, and documentation
  update process for future agents.
- Tuned GUI chat and input text line spacing in `deepseek_api_client.py` for
  compact, readable Chinese text, and reduced extra blank lines in formatted
  replies.
- Added button hover feedback and clearer surface contrast between the sidebar,
  chat display, and input composer.
- Updated `WORKFLOW.md` with GUI-specific implementation and verification
  guidance.
- Improved Markdown detection in reply formatting so Markdown structure and code
  examples are not mistaken for prose paragraphs.
- Added lightweight Markdown rendering for chat output, including headings,
  bold/italic/strikethrough text, inline code, fenced code, separators,
  superscript/subscript HTML tags, image/link labels, autolinks, and browser
  navigation for links.
- Added summary-memory context handling: API requests include the system prompt,
  a saved summary of older turns, and recent full messages instead of always
  sending the full conversation history.
- Added sidebar history deletion with confirmation and safe active-session
  cleanup; deletion is now available beside each history record row.
- Added Unicode emoji rendering support through a dedicated Tk text tag using
  the system emoji font.
- Added Markdown table block formatting that pads columns by display width and
  renders tables with a dedicated table tag.
- Added per-model thinking mode controls for `deepseek-v4-pro` and
  `deepseek-v4-flash`, persisted in config and passed through the API request.
- Updated sidebar action button labels to use emoji icons.
- Added bare URL autolinking so received websites can be clicked directly and
  opened in the default browser.
- Extended autolinking for source-style trailing website references such as
  `example.com/path` without an explicit protocol.
- Current repository state observed:
  - Main desktop UI implementation is concentrated in `deepseek_api_client.py`.
  - `ds_v4.py` is only a compatibility entrypoint.
  - `edge_extension/` contains the browser extension prototype for the `edge`
    branch.
  - User secrets and generated runtime/build output are ignored by Git.
  - Packaging is documented and automated through `build_exe.ps1`.

### 2026-04-30

- Added a top-bar API Settings button that opens a compact Tkinter child window
  for editing `DEEPSEEK_API_KEY` and `DEEPSEEK_BASE_URL`.
- API settings are saved back to `config.json` and the DeepSeek client is
  recreated immediately so the new credentials can be used without restarting.
- Removed environment-variable fallback for API credentials; the app now
  requires the API key from `config.json` or the API Settings window.
- Added runtime language selection for English and Chinese while keeping source
  and documentation files free of literal Chinese characters.
- Replaced the chat and input body font with `Microsoft YaHei UI`, kept code and
  tables on `Cascadia Mono`, and added Windows DPI/Tk scaling setup for clearer
  text rendering on scaled displays.
- Added a draggable sidebar resize handle and persisted the sidebar width in
  `config.json`.
- Refactored the Tkinter UI into a more polished workstation layout with
  grouped sidebar panels, a bordered top toolbar, a framed chat surface, and
  refreshed neutral/teal light and dark theme colors while preserving existing
  chat, history, model, thinking, API, language, theme, and resize behavior.
- Added an unpacked Microsoft Edge extension prototype in `edge_extension/`.
- The extension provides a popup chat UI with DeepSeek API settings, model and
  thinking controls, theme/language options, local message persistence,
  transcript export, and current-page context capture.
- Expanded the Edge extension `Use Page` action so it injects a script into the
  active tab and captures visible page text plus common interactive elements,
  not only the title, URL, and selected text.
- Split low-risk support code out of `deepseek_api_client.py`: runtime config
  and paths now live in `config_store.py`, the API wrapper lives in
  `deepseek_client.py`, and language text lives in `ui_text.py`.
- Updated `WORKFLOW.md` with the new source layout and expanded Python compile
  verification command.

## Agent Guidelines

- Keep real API keys out of committed files. Use `config.json` locally only.
- Preserve `ds_v4.py` as the stable entrypoint unless the user asks to change
  the launch command.
- Be careful with encoding. Existing Python files declare UTF-8, and UI text may
  include Chinese characters.
- Avoid deleting user conversations in `conversations/`; it is runtime data and
  ignored by Git.
- After feature changes, update this file's "Current Features" and
  "Modification Log" sections so the next agent can continue from the latest
  state.
- If packaging behavior changes, update both `PACKAGING.md` and this file.
