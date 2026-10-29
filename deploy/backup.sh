#!/usr/bin/env bash
# Резервная копия базы (аккаунты и прогресс) в backups/ctrainer-ГГГГ-ММ-ДД.sql.gz.
# Хранит 14 последних копий, более старые удаляет.
# Запуск вручную: bash deploy/backup.sh   (или каждый день через cron — см. DEPLOY.md)
# Восстановить:   gunzip -c backups/ФАЙЛ.sql.gz | docker compose -f docker-compose.prod.yml exec -T db sh -c 'psql -U "$POSTGRES_USER" "$POSTGRES_DB"'
set -euo pipefail
cd "$(dirname "$0")/.."

mkdir -p backups
file="backups/ctrainer-$(date +%F).sql.gz"

docker compose -f docker-compose.prod.yml exec -T db sh -c 'pg_dump -U "$POSTGRES_USER" "$POSTGRES_DB"' | gzip > "$file"

ls -1t backups/ctrainer-*.sql.gz | tail -n +15 | xargs -r rm --
echo "Резервная копия: $file"
