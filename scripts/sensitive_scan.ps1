$ErrorActionPreference = 'Stop'
$root = Resolve-Path (Join-Path $PSScriptRoot '..')
$scanTargets = @('backend', 'frontend/src', 'config', 'database', 'docs', 'README.md', 'CONTRIBUTING.md', 'SECURITY.md')
$patterns = @(
    '-----BEGIN .*PRIVATE KEY-----',
    'AKIA[0-9A-Z]{16}',
    'password\s*[:=]\s*root',
    'form\.value\.(account|password|openId)\s*=\s*[''"][^''"]+[''"]',
    '(?<!\d)1[3-9]\d{9}(?!\d)'
)
Push-Location $root
try {
    $scanFiles = @(git ls-files --cached --others --exclude-standard -- @scanTargets | Where-Object {
        $_ -match '\.(py|ps1|ts|tsx|vue|js|json|ya?ml|sql|md|txt|toml)$' -and (Test-Path -LiteralPath $_)
    })
    $patternMatches = @()
    $longIdMatches = @()
    if ($scanFiles.Count -gt 0) {
        $patternMatches = @(rg -n -i -P ($patterns -join '|') -- @scanFiles 2>$null)
        $longIdMatches = @(rg -n -P '(?<!\d)\d{16,20}(?!\d)' -- @scanFiles 2>$null)
    }

    $findings = @($patternMatches | ForEach-Object {
        if ($_ -match '^(.*?):(\d+):') {
            "$($Matches[1]):$($Matches[2])"
        }
    } | Sort-Object -Unique)

    $findings += @($longIdMatches | Where-Object {
        $_ -notmatch 'frontend[/\\]package-lock\.json:' -and
        $_ -notmatch '\.(svg|lock):' -and
        $_ -notmatch '900000000000000000\d' -and
        $_ -notmatch 'https?://'
    } | ForEach-Object {
        if ($_ -match '^(.*?):(\d+):') {
            "$($Matches[1]):$($Matches[2])"
        }
    })
    $findings = @($findings | Sort-Object -Unique)

    if ($findings.Count -gt 0) {
        $findings | ForEach-Object { Write-Output "发现疑似敏感信息：$_" }
        throw '敏感信息扫描失败'
    }
}
finally {
    Pop-Location
}
Write-Output '敏感信息扫描通过'
