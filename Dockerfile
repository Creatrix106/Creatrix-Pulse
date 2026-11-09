# syntax=docker/dockerfile:1.7
#
# Production image: Python 3.15, locked production-only dependencies (uv.lock), non-root user.
#   docker build -t creatrix-pulse-api .
#   docker run --env-file .env -p 8000:8000 creatrix-pulse-api

# ------------------------------------------------------------------ build: install locked dependencies
FROM python:3.15-slim-bookworm AS build
ENV UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    UV_PYTHON_DOWNLOADS=never \
    UV_PROJECT_ENVIRONMENT=/opt/venv
RUN pip install --no-cache-dir uv==0.13.7
WORKDIR /src
COPY pyproject.toml uv.lock .python-version ./
# --frozen: install exactly what uv.lock says; --no-dev: no test/lint tooling in the image.
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen --no-dev --no-install-project

# ------------------------------------------------------------------------------------------ runtime
FROM python:3.15-slim-bookworm AS runtime
ENV PATH="/opt/venv/bin:$PATH" \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    ENVIRONMENT=production \
    WEB_CONCURRENCY=2
RUN useradd --system --create-home --uid 10001 app
WORKDIR /app
COPY --from=build /opt/venv /opt/venv
COPY alembic.ini docker-entrypoint.sh ./
COPY migrations ./migrations
COPY app ./app
RUN chmod +x docker-entrypoint.sh
USER app
EXPOSE 8000
HEALTHCHECK --interval=30s --timeout=5s --start-period=30s --retries=3 \
    CMD python -c "import urllib.request as u; u.urlopen('http://127.0.0.1:8000/health', timeout=3)" || exit 1
ENTRYPOINT ["./docker-entrypoint.sh"]
# uvicorn reads WEB_CONCURRENCY for the number of worker processes; X-Forwarded-* headers are trusted only from
# FORWARDED_ALLOW_IPS (default: 127.0.0.1) – set it to your reverse proxy's address.
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--no-access-log"]
