[CmdletBinding()]
param(
    [Parameter(Position = 0)]
    [string]$Command = 'help',
    [Parameter(Position = 1)]
    [string]$Target = '',
    [Parameter(Position = 2)]
    [string]$Action = '',
    [Alias('h')]
    [switch]$Help,
    [Alias('f')]
    [switch]$Follow,
    [Parameter(ValueFromRemainingArguments = $true)]
    [string[]]$Options
)

$ErrorActionPreference = 'Stop'
[Console]::InputEncoding = [System.Text.UTF8Encoding]::new($false)
[Console]::OutputEncoding = [System.Text.UTF8Encoding]::new($false)
$OutputEncoding = [System.Text.UTF8Encoding]::new($false)

$projectRoot = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path
$backendRoot = Join-Path $projectRoot 'backend'
$frontendRoot = Join-Path $projectRoot 'frontend'
$runtimeRoot = Join-Path $projectRoot '.edctl'
$logRoot = Join-Path $runtimeRoot 'logs'
$pidRoot = Join-Path $runtimeRoot 'pids'
$backendPort = 8281
$frontendPort = 5180

New-Item -ItemType Directory -Force -Path $logRoot, $pidRoot | Out-Null

function Import-EdEnvFile {
    $envPath = Join-Path $backendRoot '.env'
    if (-not (Test-Path -LiteralPath $envPath -PathType Leaf)) { return }
    foreach ($line in Get-Content -LiteralPath $envPath) {
        if ($line -match '^\s*#' -or $line -notmatch '^\s*([A-Za-z_][A-Za-z0-9_]*)\s*=\s*(.*)\s*$') { continue }
        $name = $Matches[1]
        $value = $Matches[2].Trim()
        if (($value.StartsWith('"') -and $value.EndsWith('"')) -or ($value.StartsWith("'") -and $value.EndsWith("'"))) {
            $value = $value.Substring(1, $value.Length - 2)
        }
        [Environment]::SetEnvironmentVariable($name, $value, 'Process')
    }
}

Import-EdEnvFile

function Show-EdHelp {
    Write-Host 'edctl - 教育业务系统本地开发统一入口'
    Write-Host ''
    Write-Host '用法:'
    Write-Host '  edctl help'
    Write-Host '  edctl project'
    Write-Host '  edctl service [backend|frontend|all] [status|start|stop|restart]'
    Write-Host '  edctl status'
    Write-Host '  edctl logs [backend|frontend] [-f]'
    Write-Host '  edctl browser [frontend]'
    Write-Host '  edctl doctor'
    Write-Host '  edctl install [全局目录]'
    Write-Host '  edctl test [backend|frontend|all]'
    Write-Host '  edctl worker [--limit N] [--runner-id ID] [--adapter NAME]'
    Write-Host ''
    Write-Host '常用命令:'
    Write-Host '  edctl project                  查看项目概览'
    Write-Host '  edctl service                  查看所有服务状态'
    Write-Host '  edctl service backend start    启动后端服务'
    Write-Host '  edctl service frontend start   启动前端服务'
    Write-Host '  edctl service all restart      重启全部服务'
    Write-Host '  edctl logs backend              查看后端日志'
    Write-Host '  edctl logs frontend             查看前端日志'
    Write-Host '  edctl browser                  打开前端页面'
    Write-Host '  edctl doctor                   检查本地环境'
    Write-Host '  edctl test all                 执行全部测试'
}

function Get-ServiceInfo {
    param([Parameter(Mandatory = $true)][string]$Service)
    switch ($Service) {
        'backend' {
            [pscustomobject]@{
                Name = 'backend'; DisplayName = 'Python 后端'; Port = $backendPort
                HealthUrl = "http://127.0.0.1:$backendPort/healthz"; ReadyUrl = "http://127.0.0.1:$backendPort/readyz"
                PidFile = Join-Path $pidRoot 'backend.pid'; LogFile = Join-Path $logRoot 'backend.log'; ErrorLogFile = Join-Path $logRoot 'backend.error.log'
            }
        }
        'frontend' {
            [pscustomobject]@{
                Name = 'frontend'; DisplayName = 'Vue 前端'; Port = $frontendPort
                HealthUrl = "http://127.0.0.1:$frontendPort/"; ReadyUrl = $null
                PidFile = Join-Path $pidRoot 'frontend.pid'; LogFile = Join-Path $logRoot 'frontend.log'; ErrorLogFile = Join-Path $logRoot 'frontend.error.log'
            }
        }
        default { throw "不支持的服务: $Service。可选值为 backend、frontend、all。" }
    }
}

function Get-ListeningPid {
    param([Parameter(Mandatory = $true)][int]$Port)
    $connection = Get-NetTCPConnection -LocalAddress 127.0.0.1 -LocalPort $Port -State Listen -ErrorAction SilentlyContinue | Select-Object -First 1
    if ($null -eq $connection) { return $null }
    return [int]$connection.OwningProcess
}

function Get-RecordedPid {
    param([Parameter(Mandatory = $true)]$Info)
    if (-not (Test-Path -LiteralPath $Info.PidFile)) { return $null }
    $raw = (Get-Content -LiteralPath $Info.PidFile -Raw).Trim()
    $pidValue = 0
    if ([int]::TryParse($raw, [ref]$pidValue) -and $pidValue -gt 0) { return $pidValue }
    return $null
}

function Get-EdServiceStatus {
    param([Parameter(Mandatory = $true)][string]$Service)
    $info = Get-ServiceInfo $Service
    $listeningPid = Get-ListeningPid $info.Port
    $recordedPid = Get-RecordedPid $info
    $process = if ($listeningPid) { Get-Process -Id $listeningPid -ErrorAction SilentlyContinue } else { $null }
    [pscustomobject]@{
        Service = $info.Name
        Port = $info.Port
        Status = if ($listeningPid) { '运行中' } else { '已停止' }
        ListeningPid = $listeningPid
        RecordedPid = $recordedPid
        Process = if ($process) { $process.ProcessName } else { '' }
    }
}

function Write-EdStatus {
    param([string[]]$Services = @('backend', 'frontend'))
    @($Services | ForEach-Object { Get-EdServiceStatus $_ }) | Format-Table -AutoSize
}

function Wait-EdHttp {
    param([Parameter(Mandatory = $true)][string]$Url, [int]$TimeoutSeconds = 2, [int[]]$ExpectedStatus = @(200))
    try {
        $requestParams = @{
            Uri = $Url
            UseBasicParsing = $true
            TimeoutSec = $TimeoutSeconds
            ErrorAction = 'Stop'
        }
        if ((Get-Command Invoke-WebRequest).Parameters.ContainsKey('NoProxy')) {
            $requestParams.NoProxy = $true
        }
        else {
            $requestParams.Proxy = $null
        }
        $response = Invoke-WebRequest @requestParams
        return $ExpectedStatus -contains [int]$response.StatusCode
    }
    catch {
        $response = $_.Exception.Response
        if ($null -ne $response) {
            try { return $ExpectedStatus -contains [int]$response.StatusCode.value__ } catch { }
        }
        return $false
    }
}

function Start-EdService {
    param([Parameter(Mandatory = $true)][string]$Service)
    $info = Get-ServiceInfo $Service
    $existingPid = Get-ListeningPid $info.Port
    if ($existingPid) {
        Set-Content -LiteralPath $info.PidFile -Value ([string]$existingPid) -Encoding ascii
        Write-Host "$($info.DisplayName) 已在端口 $($info.Port) 监听，PID $existingPid。"
        return
    }

    if ($Service -eq 'backend') {
        $python = Join-Path $backendRoot '.venv\Scripts\python.exe'
        if (-not (Test-Path -LiteralPath $python)) { $python = (Get-Command py -ErrorAction SilentlyContinue).Source }
        if ([string]::IsNullOrWhiteSpace($python)) { throw '未找到 Python。请先安装 Python 3.11+ 或创建 backend\.venv。' }
        $arguments = @('-m', 'uvicorn', 'app.main:app', '--host', '127.0.0.1', '--port', [string]$info.Port)
        $workingDirectory = $backendRoot
    }
    else {
        $npm = (Get-Command npm.cmd -ErrorAction SilentlyContinue).Source
        if ([string]::IsNullOrWhiteSpace($npm)) { throw '未找到 npm.cmd。请先安装 Node.js 18.18+。' }
        $python = $npm
        $arguments = @('run', 'dev', '--', '--host', '127.0.0.1', '--port', [string]$info.Port)
        $workingDirectory = $frontendRoot
    }

    $process = Start-Process -FilePath $python -ArgumentList $arguments -WorkingDirectory $workingDirectory -RedirectStandardOutput $info.LogFile -RedirectStandardError $info.ErrorLogFile -PassThru -WindowStyle Hidden
    Set-Content -LiteralPath $info.PidFile -Value ([string]$process.Id) -Encoding ascii
    $newPid = $null
    for ($attempt = 0; $attempt -lt 20; $attempt++) {
        Start-Sleep -Milliseconds 500
        $newPid = Get-ListeningPid $info.Port
        if ($newPid) { break }
    }
    if (-not $newPid) {
        $errorTail = if (Test-Path -LiteralPath $info.ErrorLogFile) { (Get-Content -LiteralPath $info.ErrorLogFile -Tail 8) -join ' ' } else { '' }
        Stop-Process -Id $process.Id -Force -ErrorAction SilentlyContinue
        Remove-Item -LiteralPath $info.PidFile -Force -ErrorAction SilentlyContinue
        throw "$($info.DisplayName) 启动失败，详见 $($info.ErrorLogFile)。$errorTail"
    }
    Set-Content -LiteralPath $info.PidFile -Value ([string]$newPid) -Encoding ascii
    Write-Host "$($info.DisplayName) 已启动，端口 $($info.Port)，PID $newPid。"
}

function Stop-EdService {
    param([Parameter(Mandatory = $true)][string]$Service)
    $info = Get-ServiceInfo $Service
    $portPid = Get-ListeningPid $info.Port
    $targets = @($portPid) | Where-Object { $_ -and $_ -gt 0 } | Select-Object -Unique
    foreach ($pidValue in $targets) {
        $process = Get-Process -Id $pidValue -ErrorAction SilentlyContinue
        if ($process) {
            Stop-Process -Id $pidValue -Force -ErrorAction SilentlyContinue
            Write-Host "$($info.DisplayName) 已停止，PID $pidValue。"
        }
    }
    Remove-Item -LiteralPath $info.PidFile -Force -ErrorAction SilentlyContinue
    if (-not $targets) { Write-Host "$($info.DisplayName) 当前未运行。" }
}

function Invoke-EdServiceCommand {
    param([string]$Service, [string]$Operation)
    $knownServices = @('backend', 'frontend', 'all')
    $knownOperations = @('status', 'start', 'stop', 'restart')
    if ([string]::IsNullOrWhiteSpace($Service)) { $Service = 'all' }
    if ($knownServices -notcontains $Service) { throw "service 只支持 backend、frontend 或 all，当前为 $Service。" }
    if ([string]::IsNullOrWhiteSpace($Operation)) { $Operation = 'status' }
    if ($knownOperations -notcontains $Operation) { throw "不支持的 service 操作: $Operation。" }
    $targets = if ($Service -eq 'all') { @('backend', 'frontend') } else { @($Service) }
    if ($Operation -eq 'status') { Write-EdStatus -Services $targets; return }
    foreach ($item in $targets) {
        if ($Operation -in @('stop', 'restart')) { Stop-EdService $item }
        if ($Operation -in @('start', 'restart')) { Start-EdService $item }
    }
}

function Invoke-EdLogs {
    param([string]$Service, [bool]$Follow)
    if ([string]::IsNullOrWhiteSpace($Service)) { $Service = 'backend' }
    $info = Get-ServiceInfo $Service
    $files = @($info.LogFile, $info.ErrorLogFile) | Where-Object { Test-Path -LiteralPath $_ }
    if (-not $files) { throw "日志文件不存在: $($info.LogFile)" }
    Write-Host "日志: $($info.LogFile)；错误日志: $($info.ErrorLogFile)"
    if ($Follow) { Get-Content -LiteralPath $files -Tail 120 -Wait }
    else { Get-Content -LiteralPath $files -Tail 120 }
}

function Invoke-EdDoctor {
    function Result([string]$Level, [string]$Item, [string]$Message) {
        [pscustomobject]@{ Level = $Level; Item = $Item; Message = $Message }
    }
    $results = [System.Collections.Generic.List[object]]::new()
    [void]$results.Add((Result '通过' '工作区' $projectRoot))
    if (Test-Path -LiteralPath (Join-Path $backendRoot '.venv\Scripts\python.exe')) { [void]$results.Add((Result '通过' 'Python 环境' 'backend\.venv')) }
    elseif (Get-Command py -ErrorAction SilentlyContinue) { [void]$results.Add((Result '警告' 'Python 环境' '使用 PATH 中的 py，建议创建 backend\.venv')) }
    else { [void]$results.Add((Result '错误' 'Python 环境' '未找到 Python 3.11+')) }
    if (Get-Command npm.cmd -ErrorAction SilentlyContinue) { [void]$results.Add((Result '通过' 'Node.js/npm' ((Get-Command npm.cmd).Source))) }
    else { [void]$results.Add((Result '错误' 'Node.js/npm' '未找到 npm.cmd')) }
    foreach ($service in @('backend', 'frontend')) {
        $info = Get-ServiceInfo $service
        $status = Get-EdServiceStatus $service
        if ($status.ListeningPid) { [void]$results.Add((Result '通过' "服务 $service" "端口 $($info.Port)，PID $($status.ListeningPid)")) }
        else { [void]$results.Add((Result '警告' "服务 $service" "端口 $($info.Port) 未监听")) }
    }
    if (Wait-EdHttp "http://127.0.0.1:$backendPort/healthz") { [void]$results.Add((Result '通过' '后端健康' '/healthz 返回 200')) }
    else { [void]$results.Add((Result '错误' '后端健康' '/healthz 无法访问')) }
    if (Wait-EdHttp "http://127.0.0.1:$backendPort/readyz" -ExpectedStatus @(200, 503)) {
        [void]$results.Add((Result '通过' '数据库/Redis' '/readyz 可访问（200 表示就绪，503 表示依赖未就绪）'))
    }
    else { [void]$results.Add((Result '警告' '数据库/Redis' '/readyz 无法访问')) }
    if (Wait-EdHttp "http://127.0.0.1:$frontendPort/") { [void]$results.Add((Result '通过' '前端页面' "http://127.0.0.1:$frontendPort/ 返回 200")) }
    else { [void]$results.Add((Result '警告' '前端页面' "http://127.0.0.1:$frontendPort/ 无法访问")) }
    $errors = @($results | Where-Object Level -eq '错误').Count
    $warnings = @($results | Where-Object Level -eq '警告').Count
    $results | Format-Table -AutoSize
    Write-Host "doctor 检查完成：错误 $errors 个，警告 $warnings 个。"
    if ($errors -gt 0) { exit 1 }
}

function Invoke-EdTests {
    param([string]$Suite)
    if ([string]::IsNullOrWhiteSpace($Suite)) { $Suite = 'all' }
    if ($Suite -notin @('backend', 'frontend', 'all')) { throw 'test 只支持 backend、frontend 或 all。' }
    if ($Suite -in @('backend', 'all')) {
        $python = Join-Path $backendRoot '.venv\Scripts\python.exe'
        if (-not (Test-Path -LiteralPath $python)) { $python = (Get-Command py -ErrorAction SilentlyContinue).Source }
        if ([string]::IsNullOrWhiteSpace($python)) { throw '未找到 Python。' }
        Push-Location $backendRoot
        try { & $python -m pytest -q; if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE } }
        finally { Pop-Location }
    }
    if ($Suite -in @('frontend', 'all')) {
        Push-Location $frontendRoot
        try { & npm.cmd run typecheck; if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }; & npm.cmd run build:prod; if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE } }
        finally { Pop-Location }
    }
}

function Invoke-EdWorker {
    $python = Join-Path $backendRoot '.venv\Scripts\python.exe'
    if (-not (Test-Path -LiteralPath $python)) { $python = (Get-Command py -ErrorAction SilentlyContinue).Source }
    if ([string]::IsNullOrWhiteSpace($python)) { throw '未找到 Python。' }
    Push-Location $backendRoot
    try { & $python -m app.workers.run_once @Options; exit $LASTEXITCODE }
    finally { Pop-Location }
}

if ($Help -or $Command -in @('help', '-h', '--help', '/?')) { Show-EdHelp; exit 0 }

try {
    switch ($Command.ToLowerInvariant()) {
        'project' {
            Write-Host '项目: 教育业务系统'
            Write-Host "工作区: $projectRoot"
            Write-Host "后端: http://127.0.0.1:$backendPort"
            Write-Host "前端: http://127.0.0.1:$frontendPort"
        }
        'status' { Write-EdStatus }
        'service' { Invoke-EdServiceCommand -Service $Target -Operation $Action }
        'logs' { Invoke-EdLogs -Service $Target -Follow ($Follow -or $Options -contains '-f' -or $Options -contains '--follow' -or $Options -contains 'follow') }
        'browser' {
            if ($Target -and $Target -ne 'frontend') { throw 'browser 只支持 frontend。' }
            Start-Process "http://127.0.0.1:$frontendPort/" | Out-Null
            Write-Host "已打开前端: http://127.0.0.1:$frontendPort/"
        }
        'doctor' { Invoke-EdDoctor }
        'install' {
            $installer = Join-Path $projectRoot 'scripts\install_edctl.ps1'
            if ($Target) { & powershell.exe -NoLogo -NoProfile -ExecutionPolicy Bypass -File $installer -GlobalHome $Target }
            else { & powershell.exe -NoLogo -NoProfile -ExecutionPolicy Bypass -File $installer }
            exit $LASTEXITCODE
        }
        'test' { Invoke-EdTests -Suite $Target }
        'worker' { Invoke-EdWorker }
        default { throw "不支持的命令: $Command。运行 edctl help 查看用法。" }
    }
}
catch {
    Write-Error "执行失败：$($_.Exception.Message)"
    exit 1
}
