FROM python:3.12-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy backend requirements and install
COPY backend/requirements.txt ./backend/requirements.txt
RUN pip install --no-cache-dir -r backend/requirements.txt

# Copy source code
COPY backend ./backend
COPY sample_docs ./sample_docs
COPY eval ./eval
COPY scripts ./scripts
COPY .env.example ./.env

EXPOSE 8000

# Seed database then start uvicorn (paths quoted for safety)
CMD ["sh", "-c", "python \"scripts/seed.py\" && uvicorn backend.app.main:app --host 0.0.0.0 --port 8000"]
