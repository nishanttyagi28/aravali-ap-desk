# Start API + UI against the real offline stack (Windows).
$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $PSScriptRoot
Set-Location $Root

$venvPy = Join-Path $Root ".venv\Scripts\python.exe"
if (-not (Test-Path $venvPy)) {
    py -3.12 -m venv (Join-Path $Root ".venv")
}
& $venvPy -m pip install -q -e ".[dev,synth,ocr]" 2>$null
if ($LASTEXITCODE -ne 0) { & $venvPy -m pip install -e ".[dev,synth,ocr]" }

$env:DATABASE_URL = "sqlite:///data/ap_desk.db"
$dataDir = Join-Path $Root "data"
if (-not (Test-Path $dataDir)) { New-Item -ItemType Directory -Path $dataDir | Out-Null }
& $venvPy -m api.seed

$api = Start-Process -FilePath $venvPy -ArgumentList "-m","api.serve" -PassThru -WorkingDirectory $Root
Start-Sleep -Seconds 2

Push-Location (Join-Path $Root "ui")
if (-not (Test-Path "node_modules")) { npm ci }
$env:VITE_API_BASE = "http://127.0.0.1:8000"
$ui = Start-Process -FilePath "npm" -ArgumentList "run","dev","--","--host","127.0.0.1" -PassThru
Pop-Location

Write-Host "API pid $($api.Id) on http://127.0.0.1:8000"
Write-Host "UI pid $($ui.Id) on http://127.0.0.1:5173"
Write-Host "Press Ctrl+C to stop (kill PIDs manually if this script exits)."

try {
    Wait-Process -Id $api.Id, $ui.Id
} finally {
    if (-not $api.HasExited) { Stop-Process -Id $api.Id -Force -ErrorAction SilentlyContinue }
    if (-not $ui.HasExited) { Stop-Process -Id $ui.Id -Force -ErrorAction SilentlyContinue }
}
