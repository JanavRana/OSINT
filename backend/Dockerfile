FROM python:3.12-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    postgresql-client \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Make scripts executable
RUN chmod +x scripts/*.py 2>/dev/null || true

EXPOSE 8000

# Use entrypoint script for proper initialization
CMD ["sh", "-c", "\
    echo 'Waiting for PostgreSQL...' && \
    if [ -n \"$DATABASE_URL\" ]; then \
        until pg_isready -d \"$DATABASE_URL\"; do sleep 2; done; \
    else \
        until pg_isready -h ${POSTGRES_HOST:-postgres} -p ${POSTGRES_PORT:-5432} -U ${POSTGRES_USER:-osint_user}; do sleep 2; done; \
    fi && \
    echo 'Running Alembic migrations...' && \
    alembic upgrade head && \
    echo 'Starting FastAPI application...' && \
    uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000} --reload \
"]
