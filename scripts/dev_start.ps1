# Dev start helper: launches frontend dev server (detached) and runs backend in foreground
Set-Location -Path (Split-Path -Parent $MyInvocation.MyCommand.Path)

Write-Host "Starting frontend dev server..."
Push-Location frontend
Start-Process -NoNewWindow -FilePath npm -ArgumentList 'run','dev'
Pop-Location

Write-Host "Installing Python requirements..."
python -m pip install -r requirements.txt

Write-Host "Starting backend (uvicorn)..."
Set-Location backend
python -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
