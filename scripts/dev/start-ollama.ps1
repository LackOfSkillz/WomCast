$env:OLLAMA_HOST = "127.0.0.1:11435"
Start-Process -FilePath "$env:LOCALAPPDATA\Programs\Ollama\ollama.exe" -ArgumentList 'serve' -WindowStyle Minimized
