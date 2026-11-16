<#
.SYNOPSIS
    启动 / 停止 / 查看本项目专用的本地 MySQL 8 实例（127.0.0.1:3307）。

.DESCRIPTION
    数据目录和配置都在仓库根目录的 .mysql-3307/ 下（已加入 .gitignore），
    与系统里 3306 端口的 MySQL 服务互不影响，端口也避开了 docker compose 的 3307 映射冲突
    （两者不要同时启动；用 Docker 部署前先 stop）。

    首次使用（当前机器已经完成，换机器时才需要）：
        1. 初始化数据目录（root 临时空密码）：
           & $mysqld --initialize-insecure --basedir="<MySQL 安装目录>" --datadir="<仓库>\.mysql-3307\data"
        2. start 起来后设置密码并建库：
           ALTER USER 'root'@'localhost' IDENTIFIED BY '<密码>';
           CREATE DATABASE admin_panel CHARACTER SET utf8mb4;

.PARAMETER Action
    start  启动实例（后台进程）
    stop   优雅关闭实例（需要 mysqladmin）
    status 查看端口与进程状态

.EXAMPLE
    .\mysql\local-mysql.ps1 start
    .\mysql\local-mysql.ps1 status
    .\mysql\local-mysql.ps1 stop
#>
param(
    [ValidateSet('start', 'stop', 'status')]
    [string]$Action = 'status'
)

$ErrorActionPreference = 'Stop'
$RepoRoot = Split-Path -Parent $PSScriptRoot
$InstanceDir = Join-Path $RepoRoot '.mysql-3307'
$IniFile = Join-Path $InstanceDir 'my.ini'
$DataDir = Join-Path $InstanceDir 'data'
$PidFile = Join-Path $InstanceDir 'mysqld-3307.pid'
$Port = 3307

function Find-MySqlBin([string]$Name) {
    if ($env:MYSQL_BIN_DIR) {
        $candidate = Join-Path $env:MYSQL_BIN_DIR "$Name.exe"
        if (Test-Path $candidate) { return $candidate }
    }
    $cmd = Get-Command "$Name.exe" -ErrorAction SilentlyContinue
    if ($cmd) { return $cmd.Source }
    foreach ($base in @('D:\Program Files\MySQL\MySQL Server 8.0', 'C:\Program Files\MySQL\MySQL Server 8.0')) {
        $candidate = Join-Path $base "bin\$Name.exe"
        if (Test-Path $candidate) { return $candidate }
    }
    throw "找不到 $Name.exe，请把 MySQL 的 bin 目录加到 PATH 或设置环境变量 MYSQL_BIN_DIR"
}

function Test-PortOpen {
    return [bool](Test-NetConnection -ComputerName 127.0.0.1 -Port $Port -InformationLevel Quiet -WarningAction SilentlyContinue)
}

function Get-AppPassword {
    $envFile = Join-Path $RepoRoot 'backend\.env'
    if (Test-Path $envFile) {
        $line = Select-String -Path $envFile -Pattern '^\s*MYSQL_PASSWORD\s*=' | Select-Object -Last 1
        if ($line) { return ($line.Line -split '=', 2)[1].Trim() }
    }
    return ''
}

switch ($Action) {
    'start' {
        if (Test-PortOpen) { Write-Host "MySQL 已在 $Port 端口运行。" -ForegroundColor Green; return }
        if (-not (Test-Path $DataDir)) {
            throw "数据目录不存在：$DataDir`n请先参考脚本注释里的步骤初始化实例。"
        }
        $mysqld = Find-MySqlBin 'mysqld'
        Start-Process -FilePath $mysqld -ArgumentList "--defaults-file=$IniFile" -WindowStyle Hidden | Out-Null
        for ($i = 0; $i -lt 20; $i++) {
            Start-Sleep -Seconds 1
            if (Test-PortOpen) {
                Write-Host "MySQL 已启动：127.0.0.1:$Port（数据目录 $DataDir）" -ForegroundColor Green
                return
            }
        }
        throw "启动超时，请查看错误日志：$(Join-Path $InstanceDir 'mysqld-3307.err')"
    }
    'stop' {
        if (-not (Test-PortOpen)) { Write-Host "MySQL 未在 $Port 端口运行。" -ForegroundColor Yellow; return }
        $mysqladmin = Find-MySqlBin 'mysqladmin'
        $password = Get-AppPassword
        if ($password) { $env:MYSQL_PWD = $password }
        try {
            & $mysqladmin --host=127.0.0.1 --port=$Port --user=admin shutdown 2>&1 | Out-Null
        }
        finally {
            Remove-Item Env:\MYSQL_PWD -ErrorAction SilentlyContinue
        }
        Start-Sleep -Seconds 2
        if (Test-PortOpen) { throw "关闭失败，可查看错误日志或手动结束 mysqld 进程。" }
        Write-Host "MySQL 已关闭。" -ForegroundColor Green
    }
    'status' {
        $running = Test-PortOpen
        if ($running) {
            Write-Host "运行中：127.0.0.1:$Port" -ForegroundColor Green
        }
        else {
            Write-Host "未运行：127.0.0.1:$Port" -ForegroundColor Yellow
        }
        if (Test-Path $PidFile) {
            $pidText = (Get-Content $PidFile -ErrorAction SilentlyContinue | Select-Object -First 1)
            Write-Host "pid 文件：$PidFile（pid=$pidText）"
        }
        Write-Host "数据目录：$DataDir"
    }
}
