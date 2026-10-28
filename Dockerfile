# Официальный образ python через зеркало Docker Hub от Google
FROM mirror.gcr.io/library/python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app/backend

# INSTALL_DEV=true ставит ещё и библиотеки для тестов (локально, через docker-compose)
ARG INSTALL_DEV=false

COPY backend/requirements.txt backend/requirements-dev.txt ./
# Больше повторов и дольше ожидание — на случай нестабильной сети
RUN if [ "$INSTALL_DEV" = "true" ]; then REQ=requirements-dev.txt; else REQ=requirements.txt; fi \
    && pip install --no-cache-dir --retries 10 --timeout 60 -r "$REQ"

COPY backend/ /app/backend/
COPY frontend/ /app/frontend/
COPY content/ /app/content/

RUN useradd --create-home app && chown -R app /app
USER app

# На хостинге порт приходит в переменной PORT
CMD ["sh", "-c", "alembic upgrade head && uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}"]
