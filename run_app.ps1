$ErrorActionPreference = "Stop"
$ProjectRoot = "C:\Users\anilb\OneDrive\Attachments\Desktop\DAYANADA SAGAR CLG PROJECTS"
Set-Location $ProjectRoot

Write-Host "=== 1. Running Automated Tests (TC-01 to TC-42) ===" -ForegroundColor Cyan
python -m pytest "$ProjectRoot\backend\tests" -v

Write-Host "`n=== 2. Starting Backend Server on http://localhost:8000 ===" -ForegroundColor Green
Start-Process powershell -ArgumentList "-NoExit", "-Command", "Set-Location '$ProjectRoot'; python -m uvicorn backend.app.main:app --host 0.0.0.0 --port 8000"

Write-Host "=== 3. Starting Frontend Server on http://localhost:5173 ===" -ForegroundColor Green
Start-Process powershell -ArgumentList "-NoExit", "-Command", "Set-Location '$ProjectRoot\frontend'; npm.cmd run dev"

Write-Host "`nBoth servers launched! Open http://localhost:5173 in your browser." -ForegroundColor Yellow
