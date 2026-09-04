param([int]$Port = 8281)
$ErrorActionPreference = 'Stop'
$backendRoot = Join-Path $PSScriptRoot '..\backend'
Set-Location $backendRoot
$venvPython = Join-Path $backendRoot '.venv\Scripts\python.exe'
if (Test-Path -LiteralPath $venvPython) {
    & $venvPython -m uvicorn app.main:app --host 127.0.0.1 --port $Port
} else {
    & py -3 -m uvicorn app.main:app --host 127.0.0.1 --port $Port
}
