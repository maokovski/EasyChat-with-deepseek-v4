$ErrorActionPreference = "Stop"

if (-not (Test-Path "config.json")) {
  Copy-Item "config.example.json" "config.json"
}

$PreferredPython = "$env:USERPROFILE\anaconda3\envs\torchmorph\python.exe"
if (Test-Path $PreferredPython) {
  $PythonExe = $PreferredPython
} else {
  $PythonExe = "python"
}

& $PythonExe -m pip install pyinstaller openai

& $PythonExe -m PyInstaller `
  --clean `
  --noconfirm `
  --onedir `
  --windowed `
  --name DeepSeekChat `
  --add-data "config.json;." `
  --add-data "prompts.txt;." `
  ds_v4.py

if (-not (Test-Path "dist\DeepSeekChat\DeepSeekChat.exe")) {
  throw "Build failed: dist\DeepSeekChat\DeepSeekChat.exe was not created."
}

New-Item -ItemType Directory -Force -Path "dist\DeepSeekChat\conversations" | Out-Null
Copy-Item -Force "config.json" "dist\DeepSeekChat\config.json"
Copy-Item -Force "prompts.txt" "dist\DeepSeekChat\prompts.txt"

Write-Host ""
Write-Host "Build complete: dist\DeepSeekChat\DeepSeekChat.exe"
Write-Host "Fill dist\DeepSeekChat\config.json with your DEEPSEEK_API_KEY before copying it to another computer."
