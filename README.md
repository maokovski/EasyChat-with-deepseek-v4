# DeepSeek Chat Desktop

A small Tkinter desktop chat client for DeepSeek's OpenAI-compatible API.

## Local Setup

Clone the project and enter the folder:

```powershell
git clone <your-repo-url>
cd DeepSeekChatProject
```

Install the Python dependency:

```powershell
pip install openai
```

Create your local config file:

```powershell
copy config.example.json config.json
```

Open `config.json` and fill in your own DeepSeek API key:

```json
{
  "DEEPSEEK_API_KEY": "sk-your-api-key",
  "DEEPSEEK_BASE_URL": "https://api.deepseek.com",
  "default_model": "deepseek-v4-pro",
  "theme": "light",
  "window_geometry": "980x680"
}
```

Run the app:

```powershell
python ds_v4.py
```

## Notes

This repository does not include an API key. Each user must create their own
`config.json` from `config.example.json`.

Local chat history is saved in `conversations/`. This folder is ignored by Git.

## Optional Portable Build

To build a copyable Windows folder with an `.exe`:

```powershell
.\build_exe.ps1
```

The output will be:

```text
dist/DeepSeekChat/
```
