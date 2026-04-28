# DeepSeekChat packaging

Run this in PowerShell:

```powershell
.\build_exe.ps1
```

The portable folder will be:

```text
dist/
  DeepSeekChat/
    DeepSeekChat.exe
    config.json
    prompts.txt
    conversations/
    _internal/
```

Edit `config.json` to set the API key or default model. Edit `prompts.txt` to change the system prompt.

Feature changes still require editing the Python source files and rebuilding.
