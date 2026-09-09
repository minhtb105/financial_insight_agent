ARG PYTHON_VERSION=3.13
FROM python:${PYTHON_VERSION}-slim AS base
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 PIP_NO_CACHE_DIR=1
WORKDIR /app
RUN apt-get update && apt-get install -y --no-install-recommends curl postgresql-client && rm -rf /var/lib/apt/lists/*
COPY pyproject.toml README.md alembic.ini ./
COPY src ./src
COPY alembic ./alembic
RUN pip install --upgrade pip && pip install -e .

FROM base AS production
ENV PYTHONPATH=/app/src APP_PORT=8000
EXPOSE 8000 8001
CMD ["uvicorn", "interfaces.api.app:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "2"]

FROM base AS development
ENV PYTHONPATH=/app/src LOG_LEVEL=DEBUG
EXPOSE 8000 8001
CMD ["uvicorn", "interfaces.api.app:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]
