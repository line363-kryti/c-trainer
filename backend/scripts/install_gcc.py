"""Ставит компилятор C (gcc 10.2.0) в Piston. Нужно один раз на новом сервере.

Запуск: docker compose -f docker-compose.prod.yml exec backend python scripts/install_gcc.py
(локально: docker compose exec backend python scripts/install_gcc.py)

Piston скачивает пакет (~700 МБ) с GitHub, поэтому это может занять несколько минут.
"""
import os
import sys
import time

import httpx

PISTON_URL = os.environ.get("PISTON_URL", "http://piston:2000")
PACKAGE = {"language": "gcc", "version": "10.2.0"}
WAIT_MINUTES = 30


def installed() -> bool:
    runtimes = httpx.get(f"{PISTON_URL}/api/v2/runtimes", timeout=10).json()
    return any(r["language"] == "c" and r["version"] == PACKAGE["version"] for r in runtimes)


def main() -> int:
    if installed():
        print("gcc уже установлен — ничего делать не нужно.")
        return 0

    print("Ставлю gcc 10.2.0 в Piston (~700 МБ, несколько минут)…")
    try:
        r = httpx.post(f"{PISTON_URL}/api/v2/packages", json=PACKAGE, timeout=WAIT_MINUTES * 60)
        if r.status_code >= 400:
            print(f"Piston ответил ошибкой {r.status_code}: {r.text}")
            return 1
    except httpx.ReadTimeout:
        pass  # установка могла продолжиться — проверим ниже

    for _ in range(WAIT_MINUTES * 6):
        if installed():
            print("Готово: компилятор C установлен.")
            return 0
        time.sleep(10)

    print("Не дождался установки. Посмотри логи: docker compose -f docker-compose.prod.yml logs piston")
    return 1


if __name__ == "__main__":
    sys.exit(main())
