# ─── Backend API (FastAPI + SQLite) ──────────────────────
FROM python:3.11-slim AS backend

WORKDIR /app

# Install system deps for SQLite
RUN apt-get update && \
    apt-get install -y --no-install-recommends gcc && \
    rm -rf /var/lib/apt/lists/*

# Install Python deps (API-only, no vision engine)
COPY requirements-api.txt .
RUN pip install --no-cache-dir -r requirements-api.txt

# Copy backend source
COPY backend/ backend/

# Create data & snapshot directories
RUN mkdir -p data snapshots

EXPOSE 8000

CMD ["uvicorn", "backend.api.main:app", "--host", "0.0.0.0", "--port", "8000"]
