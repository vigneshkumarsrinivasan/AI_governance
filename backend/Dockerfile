# AegisAI Governance OS - Backend
FROM python:3.11-slim

WORKDIR /app

# System deps needed by asyncpg/bcrypt build chains stay minimal on slim images.
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

RUN useradd --create-home --uid 1000 aegis && \
    mkdir -p /app/evidence_storage && chown -R aegis:aegis /app
USER aegis

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=15s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/health', timeout=3)" || exit 1

# Runs Alembic migrations before starting the server. In production, run
# migrations as a separate release step instead of on every container start;
# this default keeps `docker compose up` friction-free for local development.
CMD ["sh", "-c", "alembic upgrade head && uvicorn aegis_app.main:app --host 0.0.0.0 --port 8000"]
