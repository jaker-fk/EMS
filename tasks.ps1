<#
.SYNOPSIS
    Windows 下的常用工程命令（等价于 Makefile）。
.EXAMPLE
    .\tasks.ps1 install
    .\tasks.ps1 test
    .\tasks.ps1 dev
#>
param(
    [ValidateSet('help', 'install', 'lint', 'test', 'test-mysql', 'migrate', 'seed', 'dev', 'up', 'down', 'logs', 'backup')]
    [string]$Action = 'help'
)

$ErrorActionPreference = 'Stop'
$Root = $PSScriptRoot
$Python = Join-Path $Root '.venv-mysql\Scripts\python.exe'
if (-not (Test-Path $Python)) { $Python = 'python' }

function Invoke-InBackend([scriptblock]$Command) {
    Push-Location (Join-Path $Root 'backend')
    try { & $Command } finally { Pop-Location }
}

switch ($Action) {
    'help' {
        Write-Host @'
可用命令：
  .\tasks.ps1 install     安装后端依赖（含 ruff / pytest-cov）
  .\tasks.ps1 lint        ruff 检查
  .\tasks.ps1 test        后端测试（临时 SQLite）
  .\tasks.ps1 test-mysql  后端测试（先设置 $env:TEST_DB_URL）
  .\tasks.ps1 migrate     alembic upgrade head
  .\tasks.ps1 seed        幂等补齐内置数据
  .\tasks.ps1 dev         本地启动后端（热重载）
  .\tasks.ps1 up / down   docker compose 启停
  .\tasks.ps1 logs        查看后端容器日志
  .\tasks.ps1 backup      备份 MySQL（Docker 部署）
'@
    }
    'install' { & $Python -m pip install -r (Join-Path $Root 'backend\requirements-dev.txt') }
    'lint' { Invoke-InBackend { & 'ruff' check . } }
    'test' { Invoke-InBackend { & $Python -m pytest -q } }
    'test-mysql' { Invoke-InBackend { & $Python -m pytest -q } }
    'migrate' { Invoke-InBackend { & $Python -m app.cli migrate } }
    'seed' { Invoke-InBackend { & $Python -m app.cli seed } }
    'dev' { Invoke-InBackend { & $Python -m uvicorn app.main:app --reload --port 8000 } }
    'up' { docker compose up -d --build }
    'down' { docker compose down }
    'logs' { docker compose logs -f --tail=100 backend }
    'backup' { & powershell -ExecutionPolicy Bypass -File (Join-Path $Root 'scripts\backup_mysql.ps1') }
}
