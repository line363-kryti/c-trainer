# Выкладка на сервер

Инструкция для VPS с Ubuntu 24.04 (написана под Timeweb Cloud, подойдёт любой VPS).
Серверная сборка проверена локально; на настоящем сервере — по мере первой выкладки.
Нужны: сервер (2 ядра, 2–4 ГБ памяти, от 30 ГБ диска) и домен.

Команды в блоках выполняются **на сервере**, если не сказано иное. `c-trainer.ru` и `IP_СЕРВЕРА`
замени на свои.

## 1. Направить домен на сервер

В панели регистратора домена → DNS → добавить запись:

| Тип | Имя | Значение |
|---|---|---|
| A | `@` | IP_СЕРВЕРА |

Изменения расходятся от нескольких минут до пары часов. Проверить **на своём компьютере**:

```
nslookup c-trainer.ru
```

В ответе должен быть IP сервера.

## 2. Зайти на сервер

На своём компьютере (PowerShell):

```
ssh root@IP_СЕРВЕРА
```

При первом входе спросят «Are you sure you want to continue connecting» — ответить `yes`.

## 3. Обновить систему и поставить Docker и Git

```
apt update && apt upgrade -y
apt install -y docker.io docker-compose-v2 git
systemctl enable --now docker
docker compose version
```

## 4. Закрыть всё, кроме SSH и сайта

```
ufw allow OpenSSH
ufw allow 80
ufw allow 443
ufw --force enable
```

## 5. Скачать проект и создать .env

```
git clone https://github.com/line363-kryti/c-trainer.git /opt/c-trainer
cd /opt/c-trainer
bash deploy/make-env.sh c-trainer.ru
```

Скрипт сам придумает длинные случайные пароли для базы и JWT и положит их в `.env`
(читать его может только root). Никуда этот файл не отправляй.

## 6. Запустить

```
docker compose -f docker-compose.prod.yml up -d --build
docker compose -f docker-compose.prod.yml ps
```

Первая сборка — несколько минут. Все четыре контейнера (`db`, `piston`, `backend`, `caddy`)
должны быть в состоянии `Up`. Caddy сам получит https-сертификат — для этого домен уже должен
указывать на сервер (шаг 1), а порты 80 и 443 быть открыты (шаг 4).

## 7. Поставить компилятор C (один раз)

```
docker compose -f docker-compose.prod.yml exec backend python scripts/install_gcc.py
```

Скачивается ~700 МБ, это несколько минут. В конце: «Готово: компилятор C установлен».

## 8. Проверить

- https://c-trainer.ru — открывается страница входа, в адресной строке замок.
- https://c-trainer.ru/api/health — `{"status":"ok","db":"ok"}`.
- Создать аккаунт, открыть любую задачу, нажать «Проверить».
- Прогнать эталоны на сервере:

```
docker compose -f docker-compose.prod.yml exec -e PYTHONPATH=. backend python scripts/check_solutions.py
```

## Обновить сайт после изменений

После `git push` с компьютера — на сервере:

```
cd /opt/c-trainer
git pull
docker compose -f docker-compose.prod.yml up -d --build
```

Миграции базы применяются автоматически при старте бэкенда. Новые уроки — это файлы в `content/`,
они попадут на сайт этой же командой.

## Резервные копии базы

Вручную:

```
bash /opt/c-trainer/deploy/backup.sh
```

Каждый день в 4:00 (хранятся 14 последних копий в `/opt/c-trainer/backups/`):

```
(crontab -l 2>/dev/null; echo "0 4 * * * bash /opt/c-trainer/deploy/backup.sh >> /var/log/c-trainer-backup.log 2>&1") | crontab -
```

## Если что-то пошло не так

| Что видно | Где смотреть |
|---|---|
| Сайт не открывается | `docker compose -f docker-compose.prod.yml ps` — все ли контейнеры `Up` |
| Нет https / ошибка сертификата | `docker compose -f docker-compose.prod.yml logs caddy` — обычно домен ещё не указывает на сервер |
| Ошибка 500 / 503 | `docker compose -f docker-compose.prod.yml logs backend` |
| «Сервис запуска недоступен» | `docker compose -f docker-compose.prod.yml logs piston`, повторить шаг 7 |

## Что важно про безопасность

- Наружу открыты только 22 (SSH), 80 и 443. База и песочница доступны только внутри Docker.
- Cookie со входом передаётся только по https (`COOKIE_SECURE=true`).
- Лимиты запросов считаются по настоящему IP посетителя (uvicorn `--proxy-headers` за Caddy).
- Чужой код выполняется в песочнице isolate без сети и с лимитами времени и памяти.
- Лучше входить на сервер по SSH-ключу, а не по паролю.
