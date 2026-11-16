<#
.SYNOPSIS
    备份本机 MySQL（默认读取 backend/.env 里的 3307 实例配置）。
.EXAMPLE
    .\scripts\backup_mysql.ps1
    .\scripts\backup_mysql.ps1 -OutDir D:\backups -RetainDays 7
#>
param(
    [string]$OutDir = (Join-Path $PSScriptRoot '..\backups'),
    [int]$RetainDays = 14
)

$ErrorActionPreference = 'Stop'
$Root = Resolve-Path (Join-Path $PSScriptRoot '..')

# 从 backend/.env 读连接信息，避免把密码写进脚本
$envFile = Join-Path $Root 'backend\.env'
$config = @{ MYSQL_HOST = '127.0.0.1'; MYSQL_PORT = '3307'; MYSQL_USER = 'admin'; MYSQL_PASSWORD = ''; MYSQL_DB = 'admin_panel' }
if (Test-Path $envFile) {
    Get-Content $envFile | Where-Object { $_ -match '^\s*MYSQL_[A-Z_]+\s*=' } | ForEach-Object {
        $parts = $_ -split '=', 2
        $config[$parts[0].Trim()] = $parts[1].Trim()
    }
}

$mysqldump = $env:MYSQLDUMP
if (-not $mysqldump) {
    foreach ($base in @('D:\Program Files\MySQL\MySQL Server 8.0', 'C:\Program Files\MySQL\MySQL Server 8.0')) {
        $candidate = Join-Path $base 'bin\mysqldump.exe'
        if (Test-Path $candidate) { $mysqldump = $candidate; break }
    }
}
if (-not $mysqldump) { throw '找不到 mysqldump.exe，请设置环境变量 MYSQLDUMP' }

New-Item -ItemType Directory -Force -Path $OutDir | Out-Null
$stamp = Get-Date -Format 'yyyyMMdd_HHmmss'
$sqlFile = Join-Path $OutDir "admin_panel_$stamp.sql"
$gzFile = "$sqlFile.gz"

$env:MYSQL_PWD = $config['MYSQL_PASSWORD']
try {
    & $mysqldump --host=$($config['MYSQL_HOST']) --port=$($config['MYSQL_PORT']) `
        --user=$($config['MYSQL_USER']) --single-transaction --routines --triggers --no-tablespaces `
        --set-gtid-purged=OFF --result-file=$sqlFile --databases $($config['MYSQL_DB'])
    if ($LASTEXITCODE -ne 0) { throw "mysqldump 失败，exit=$LASTEXITCODE" }
}
finally {
    Remove-Item Env:\MYSQL_PWD -ErrorAction SilentlyContinue
}

$in = [IO.File]::OpenRead($sqlFile)
try {
    $out = [IO.File]::Create($gzFile)
    try {
        $gzip = New-Object IO.Compression.GZipStream($out, [IO.Compression.CompressionMode]::Compress)
        try { $in.CopyTo($gzip) } finally { $gzip.Dispose() }
    }
    finally { $out.Dispose() }
}
finally { $in.Dispose() }
Remove-Item $sqlFile -Force

Get-ChildItem $OutDir -Filter 'admin_panel_*.sql.gz' |
    Where-Object { $_.LastWriteTime -lt (Get-Date).AddDays(-$RetainDays) } |
    Remove-Item -Force

Write-Host "backup written: $gzFile ($([math]::Round((Get-Item $gzFile).Length / 1MB, 2)) MB)"
