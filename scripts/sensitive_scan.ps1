$ErrorActionPreference = 'Stop'
$root = Resolve-Path (Join-Path $PSScriptRoot '..')
$forbiddenName = [string]::Concat('y','a','t','o','r','i')
$patterns = @($forbiddenName, '-----BEGIN .*PRIVATE KEY-----', 'AKIA[0-9A-Z]{16}', 'password\s*[:=]\s*root')
Push-Location $root
try {
    $matches = rg -n -i ($patterns -join '|') . -g '!frontend/node_modules/**' -g '!frontend/dist/**' -g '!backend/__pycache__/**' -g '!scripts/sensitive_scan.ps1' 2>$null
    if ($LASTEXITCODE -eq 0) { $matches; throw '敏感信息扫描失败' }
}
finally {
    Pop-Location
}
Write-Output '敏感信息扫描通过'
