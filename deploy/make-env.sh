#!/usr/bin/env bash
# Создаёт .env для сервера со случайными паролями — придумывать и печатать их не нужно.
# Использование (на сервере, в папке проекта):  bash deploy/make-env.sh c-trainer.ru
set -euo pipefail
cd "$(dirname "$0")/.."

DOMAIN="${1:?Укажи домен: bash deploy/make-env.sh c-trainer.ru}"

if [ -f .env ]; then
  echo ".env уже есть — не перезаписываю. Если нужен новый, сначала переименуй старый."
  exit 1
fi

DB_PASSWORD=$(openssl rand -hex 24)
JWT_SECRET=$(openssl rand -hex 48)

cat > .env <<EOF
# Создано deploy/make-env.sh. Файл секретный: не коммитить, никому не отправлять.
DOMAIN=$DOMAIN

POSTGRES_USER=ctrainer
POSTGRES_PASSWORD=$DB_PASSWORD
POSTGRES_DB=ctrainer
DATABASE_URL=postgresql+psycopg://ctrainer:$DB_PASSWORD@db:5432/ctrainer

JWT_SECRET=$JWT_SECRET
COOKIE_SECURE=true
RUNNER=piston
EOF

chmod 600 .env   # читать файл может только владелец
echo "Готово: .env создан для $DOMAIN (пароли случайные и лежат только в этом файле)."
