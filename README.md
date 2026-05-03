# EasyChat with DeepSeek V4

A small Windows-friendly Tkinter desktop chat client for DeepSeek's
OpenAI-compatible API.

## Features

- Desktop chat UI built with Python Tkinter.
- DeepSeek V4 Pro and V4 Flash model switching.
- Per-model thinking mode control: disabled, high, or max.
- Local conversation history with per-record delete controls.
- Summary memory for long chats: older turns are compressed into a saved
  summary while recent turns stay available as full context.
- Markdown-style chat rendering for headings, bold/italic text, code, tables,
  links, superscript/subscript, and emoji.
- Clickable links open in the system default browser.
- Light and dark themes.
- Small top-bar API settings window for editing the DeepSeek API key and base URL.
- Runtime language switching between English and Chinese.
- Microsoft Edge extension prototype under `edge_extension/` with a popup chat
  UI, local settings, transcript export, and current-page context capture.
- Optional one-folder Windows executable build with PyInstaller.

## Requirements

- Windows is the primary target.
- Python 3.10 or newer is recommended.
- A DeepSeek API key.
- Python dependency: `openai`.

## Quick Start

Clone the repository:

```powershell
git clone https://github.com/maokovski/EasyChat-with-deepseek-v4.git
cd EasyChat-with-deepseek-v4
```

Install the dependency:

```powershell
pip install openai
```

Create your local config:

```powershell
copy config.example.json config.json
```

Edit `config.json` and add your DeepSeek API key:

```json
{
  "DEEPSEEK_API_KEY": "sk-your-api-key",
  "DEEPSEEK_BASE_URL": "https://api.deepseek.com",
  "default_model": "deepseek-v4-pro",
  "thinking_modes": {
    "deepseek-v4-pro": "disabled",
    "deepseek-v4-flash": "disabled"
  },
  "theme": "light",
  "language": "en",
  "window_geometry": "980x680",
  "sidebar_width": 218
}
```

Run the app:

```powershell
python ds_v4.py
```

## Configuration

`config.json` is created locally from `config.example.json` and is ignored by
Git.

- `DEEPSEEK_API_KEY`: Your DeepSeek API key.
- `DEEPSEEK_BASE_URL`: DeepSeek API base URL.
- `default_model`: `deepseek-v4-pro` or `deepseek-v4-flash`.
- `thinking_modes`: Per-model thinking mode, one of `disabled`, `high`, `max`.
- `theme`: `light` or `dark`.
- `language`: `en` or `zh`.
- `window_geometry`: Initial Tkinter window size.
- `sidebar_width`: Saved sidebar width in pixels.

The same API key and base URL can also be edited from the top-bar API Settings
button.

The system prompt is stored in `prompts.txt`.

## Microsoft Edge Extension

The `edge_extension/` folder contains an unpacked Microsoft Edge extension that
offers a browser popup version of the chat client.

Load it locally:

```text
edge://extensions
```

Enable Developer mode, choose `Load unpacked`, and select:

```text
edge_extension/
```

Open the extension popup, click Settings, and add your DeepSeek API key. The
extension stores settings and conversation messages in `chrome.storage.local`;
API keys are not committed to this repository.

Extension capabilities:

- DeepSeek V4 Pro and V4 Flash model selection.
- Thinking mode selection: disabled, high, or max.
- Light/dark theme and English/Chinese UI selection.
- New chat, regenerate, clear, and transcript save actions.
- `Use Page` action that adds the active tab title, URL, selected text, visible
  page text, and common interactive elements to the composer.

## Local Data

This repository does not include an API key.

Local runtime data is not committed:

- `config.json`
- `conversations/`
- `dist/`
- `build/`

Conversation sessions are saved in `conversations/sessions.json`.

## Source Layout

Run the desktop app through:

```powershell
python ds_v4.py
```

Key source files:

- `ds_v4.py`: Stable compatibility entrypoint.
- `deepseek_api_client.py`: Tkinter desktop UI and chat workflow.
- `deepseek_client.py`: DeepSeek/OpenAI-compatible API wrapper.
- `config_store.py`: Runtime paths, config, prompt, and session file locations.
- `ui_text.py`: English and Chinese UI text.
- `edge_extension/`: Unpacked Microsoft Edge extension prototype.

## Portable Windows Build

To build a copyable Windows folder with an `.exe`:

```powershell
.\build_exe.ps1
```

The output folder is:

```text
dist/DeepSeekChat/
```

Before copying the portable build to another machine, fill in:

```text
dist/DeepSeekChat/config.json
```

## Notes

Feature changes require editing the Python source files and rebuilding the
portable app.

The compatibility entrypoint is `ds_v4.py`; keep `python ds_v4.py` as the
desktop launch command.
