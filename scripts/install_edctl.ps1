[CmdletBinding()]
param(
    [string]$GlobalHome = 'F:\environment'
)

$ErrorActionPreference = 'Stop'
$OutputEncoding = [System.Text.UTF8Encoding]::new($false)
[Console]::OutputEncoding = [System.Text.UTF8Encoding]::new($false)
$projectRoot = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path
$sourceScript = Join-Path $PSScriptRoot 'edctl.ps1'
$globalScript = Join-Path $GlobalHome 'edctl.ps1'
$globalCommand = Join-Path $GlobalHome 'edctl.cmd'

if (-not (Test-Path -LiteralPath $sourceScript -PathType Leaf)) {
    throw "找不到项目命令脚本: $sourceScript"
}
New-Item -ItemType Directory -Force -Path $GlobalHome | Out-Null

$wrapper = @"
[CmdletBinding()]
param(
    [Parameter(ValueFromRemainingArguments = `$true)]
    [string[]]`$Arguments
)
`$target = '$sourceScript'
if (-not (Test-Path -LiteralPath `$target -PathType Leaf)) { throw "edctl 项目脚本不存在: `$target" }
& powershell.exe -NoLogo -NoProfile -ExecutionPolicy Bypass -File `$target @Arguments
exit `$LASTEXITCODE
"@
[System.IO.File]::WriteAllText($globalScript, $wrapper, [System.Text.UTF8Encoding]::new($true))

$cmd = @"
@echo off
chcp 65001 >nul
powershell.exe -NoLogo -NoProfile -ExecutionPolicy Bypass -File "$globalScript" %*
"@
[System.IO.File]::WriteAllText($globalCommand, $cmd, [System.Text.UTF8Encoding]::new($true))

$userPath = [Environment]::GetEnvironmentVariable('Path', 'User')
$pathEntries = @($userPath -split ';' | Where-Object { -not [string]::IsNullOrWhiteSpace($_) })
if ($pathEntries -notcontains $GlobalHome) {
    $newPath = (($pathEntries + $GlobalHome) -join ';')
    [Environment]::SetEnvironmentVariable('Path', $newPath, 'User')
    $env:Path = "$GlobalHome;$env:Path"
    Write-Host "已将全局命令目录加入当前用户 PATH: $GlobalHome"
}
else {
    Write-Host "当前用户 PATH 已包含: $GlobalHome"
}

Write-Host "edctl 全局命令已安装: $globalCommand"
Write-Host '新开的 PowerShell 可直接运行: edctl help'
