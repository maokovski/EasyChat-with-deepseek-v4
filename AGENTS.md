# AI Agent Project Notes

Last updated: 2026-04-28

This file is intended for AI coding agents that need to understand the current
state of this repository before making changes.

Before making edits, also read `WORKFLOW.md` for the expected agent workflow.

## Project Summary

This is a small Windows-friendly Tkinter desktop chat client for DeepSeek's
OpenAI-compatible chat API. The user-facing entrypoint is `ds_v4.py`, which
re-exports and runs the implementation in `deepseek_api_client.py`.

## Current Features

- Tkinter desktop chat UI.
- DeepSeek API access through the `openai` Python SDK.
- Runtime configuration from `config.json`, created from defaults when missing.
- Optional environment fallback for `DEEPSEEK_API_KEY` and `DEEPSEEK_BASE_URL`.
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
- Portable Windows build flow through `build_exe.ps1` and PyInstaller.

## Important Files

- `deepseek_api_client.py`: Main application code. Contains runtime file setup,
  config loading/saving, `DeepSeekClient`, formatting helpers, and
  `DeepSeekChatApp`.
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

- Source run: the directory containing `deepseek_api_client.py`.
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
- Current repository state observed:
  - Main implementation is concentrated in `deepseek_api_client.py`.
  - `ds_v4.py` is only a compatibility entrypoint.
  - User secrets and generated runtime/build output are ignored by Git.
  - Packaging is documented and automated through `build_exe.ps1`.

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
