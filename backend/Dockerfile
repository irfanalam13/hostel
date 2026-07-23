# syntax=docker/dockerfile:1
# =============================================================================
# Hostel SaaS — backend (Django + Gunicorn) production image
# Multi-stage build: dependencies are compiled in a fat builder stage, then only
# the resulting virtualenv + application code land in a slim runtime image.
# =============================================================================

# -----------------------------------------------------------------------------
# Stage 1 — builder: install Python dependencies into an isolated virtualenv
# -----------------------------------------------------------------------------
FROM python:3.14-slim@sha256:d3400aa122fa42cf0af0dbe8ec3091b047eac5c8f7e3539f7135e86d855dc015 AS builder

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# Build-only system deps (compilers + headers). These never reach the final image.
RUN apt-get update && apt-get install -y --no-install-recommends \
        build-essential \
        libffi-dev \
    && rm -rf /var/lib/apt/lists/*

# Create the virtualenv that will be copied verbatim into the runtime stage.
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

WORKDIR /app

# Dependency layer is cached independently of source so code edits don't reinstall.
COPY requirements.txt .
RUN --mount=type=cache,target=/root/.cache/pip \
    pip install --upgrade 'pip==25.0.1' && \
    pip install -r requirements.txt

# -----------------------------------------------------------------------------
# Stage 2 — runtime: slim image with only the libraries needed to *run*
# -----------------------------------------------------------------------------
FROM python:3.14-slim@sha256:d3400aa122fa42cf0af0dbe8ec3091b047eac5c8f7e3539f7135e86d855dc015 AS runtime

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PATH="/opt/venv/bin:$PATH" \
    DJANGO_SETTINGS_MODULE=config.settings

# Runtime system libraries:
#   - libpq is bundled by psycopg[binary], so no libpq needed here.
#   - WeasyPrint (PDF reports) needs pango / cairo / gdk-pixbuf + fonts.
#   - curl is used by the container HEALTHCHECK.
RUN apt-get update && apt-get install -y --no-install-recommends \
        curl \
        libpango-1.0-0 \
        libpangocairo-1.0-0 \
        libpangoft2-1.0-0 \
        libgdk-pixbuf-2.0-0 \
        libcairo2 \
        libffi8 \
        libjpeg62-turbo \
        shared-mime-info \
        fonts-liberation \
    && rm -rf /var/lib/apt/lists/*

# Run as an unprivileged user — never as root.
RUN groupadd --system --gid 1001 app && \
    useradd --system --uid 1001 --gid app --create-home --home-dir /home/app app

# Bring the prebuilt virtualenv across from the builder stage.
COPY --from=builder /opt/venv /opt/venv

WORKDIR /app

# Application source.
COPY --chown=app:app . .

# Collect static assets at build time (no DB required). DEBUG=True here only so
# the build doesn't demand production secrets; it does not affect the running app.
RUN chmod +x /app/entrypoint.sh && \
    DEBUG=True python manage.py collectstatic --noinput && \
    mkdir -p /app/media /app/logs /app/staticfiles && \
    chown -R app:app /app/media /app/logs /app/staticfiles

USER app

EXPOSE 8000

# Liveness check used by Docker / orchestrators.
HEALTHCHECK --interval=30s --timeout=5s --start-period=20s --retries=3 \
    CMD curl -fsS http://127.0.0.1:8000/health/ || exit 1

# entrypoint runs DB migrations (when enabled) then execs the given command.
ENTRYPOINT ["/app/entrypoint.sh"]

# Default: serve the WSGI app with Gunicorn. Tunable via GUNICORN_* env vars.
CMD ["sh", "-c", "gunicorn config.wsgi:application \
    --bind 0.0.0.0:8000 \
    --workers ${GUNICORN_WORKERS:-3} \
    --threads ${GUNICORN_THREADS:-2} \
    --timeout ${GUNICORN_TIMEOUT:-60} \
    --access-logfile - \
    --error-logfile -"]
