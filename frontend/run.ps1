param([int]$Port = 8601)
Set-Location (Split-Path $PSScriptRoot -Parent)
Write-Host "INGRES Console -> http://127.0.0.1:$Port" -ForegroundColor Cyan
& "$env:LOCALAPPDATA\Python\pythoncore-3.15-64\python.exe" -m uvicorn frontend.api.server:app --host 127.0.0.1 --port $Port
