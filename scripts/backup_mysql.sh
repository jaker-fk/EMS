#!/usr/bin/env bash
# MySQL 备份脚本（Docker Compose 部署）。
# 用法：
#   BACKUP_DIR=/data/backups RETAIN_DAYS=14 bash scripts/backup_mysql.sh
# 建议用宿主机 cron 每天执行一次，例如：
#   0 3 * * * cd /srv/admin_panel && BACKUP_DIR=/data/backups bash scripts/backup_mysql.sh >> /var/log/admin_panel_backup.log 2>&1
set -euo pipefail

BACKUP_DIR="${BACKUP_DIR:-$(pwd)/backups}"
RETAIN_DAYS="${RETAIN_DAYS:-14}"
STAMP="$(date +%Y%m%d_%H%M%S)"
mkdir -p "$BACKUP_DIR"
OUT="$BACKUP_DIR/admin_panel_${STAMP}.sql.gz"

# 在 mysql 容器内执行 mysqldump：密码通过容器环境变量读取，不出现在宿主机命令行历史里
docker compose exec -T mysql sh -c \
  'exec mysqldump -uroot -p"$MYSQL_ROOT_PASSWORD" --single-transaction --routines --triggers --no-tablespaces --set-gtid-purged=OFF --databases "$MYSQL_DATABASE"' \
  | gzip > "$OUT"

echo "backup written: $OUT ($(du -h "$OUT" | cut -f1))"
find "$BACKUP_DIR" -maxdepth 1 -type f -name 'admin_panel_*.sql.gz' -mtime +"$RETAIN_DAYS" -delete
