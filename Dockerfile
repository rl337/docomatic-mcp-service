FROM python:3.11-alpine

# Install system dependencies
RUN apk add --no-cache \
    sqlite \
    postgresql-client \
    gzip \
    curl \
    git \
    && rm -rf /var/cache/apk/*

# Install UV
COPY --from=ghcr.io/astral-sh/uv:latest /uv /bin/uv

# Set working directory
WORKDIR /app

# Copy project files for dependency resolution
COPY pyproject.toml ./
COPY uv.lock ./

# Copy application code (needed for uv sync to build the package)
COPY docomatic/ ./docomatic/

# Install dependencies using UV
# Sync without --frozen to allow updating lock file if dependencies changed
RUN uv sync --no-dev

# Create data directory for SQLite database (if used)
RUN mkdir -p /app/data && \
    chmod 755 /app/data

# Non-root user for security
RUN adduser -D -s /bin/sh docomatic && \
    chown -R docomatic:docomatic /app

USER docomatic

# Environment variables
# Note: DATABASE_URL defaults to PostgreSQL for containerized setup
# For local development with SQLite, override: DATABASE_URL=sqlite:///./data/docomatic.db
ENV DATABASE_URL=postgresql://postgres:postgres@postgresql:5432/docomatic
ENV DB_POOL_SIZE=5
ENV DB_MAX_OVERFLOW=10
ENV SQL_ECHO=false
# Optional: GitHub token for export functionality
# ENV GITHUB_TOKEN=

# Run the HTTP API server using UV
CMD ["uv", "run", "uvicorn", "docomatic.http_api:app", "--host", "0.0.0.0", "--port", "8005"]
