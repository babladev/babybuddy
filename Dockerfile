# syntax=docker/dockerfile:1

# Baby Buddy self-hosted image.
#
# Build:
#   docker build -t babybuddy:local .
#
# The image runs as a non-root user, serves static files through WhiteNoise and
# expects a TLS-terminating reverse proxy in front of it (see docker-compose.yml).

ARG PYTHON_VERSION=3.11
ARG NODE_VERSION=24


# ---------------------------------------------------------------------------
# Stage 1: build front-end assets (CSS, JS, fonts, images) with gulp.
# ---------------------------------------------------------------------------
FROM node:${NODE_VERSION}-bookworm-slim AS frontend

WORKDIR /build

# Install exactly the locked dependency tree.
COPY package.json package-lock.json ./
RUN npm ci --no-audit --no-fund

# Only the sources gulp actually reads.
COPY gulpfile.js gulpfile.config.js .stylelintrc ./
COPY babybuddy/static_src ./babybuddy/static_src
COPY core/static_src ./core/static_src
COPY dashboard/static_src ./dashboard/static_src
COPY guidance/static_src ./guidance/static_src
COPY reports/static_src ./reports/static_src

# Produces babybuddy/static/babybuddy/{css,js,font,img,logo,root}.
RUN npx gulp build


# ---------------------------------------------------------------------------
# Stage 2: build the Python virtual environment.
# ---------------------------------------------------------------------------
FROM python:${PYTHON_VERSION}-slim-bookworm AS python-deps

ENV PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PIP_NO_CACHE_DIR=1

# Build toolchain for any dependency without a matching wheel.
RUN apt-get update \
    && apt-get install --no-install-recommends -y \
        build-essential \
        libjpeg-dev \
        libpq-dev \
        zlib1g-dev \
    && rm -rf /var/lib/apt/lists/*

RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:${PATH}"

COPY requirements.txt ./
RUN pip install -r requirements.txt


# ---------------------------------------------------------------------------
# Stage 3: runtime image.
# ---------------------------------------------------------------------------
FROM python:${PYTHON_VERSION}-slim-bookworm AS runtime

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PATH="/opt/venv/bin:${PATH}" \
    DJANGO_SETTINGS_MODULE=babybuddy.settings.base \
    DB_NAME=/data/db.sqlite3 \
    MEDIA_ROOT=/data/media \
    GUNICORN_WORKERS=3 \
    GUNICORN_TIMEOUT=60 \
    PORT=8000

# Runtime libraries only - no compilers in the final image.
RUN apt-get update \
    && apt-get install --no-install-recommends -y \
        curl \
        libjpeg62-turbo \
        libpq5 \
        tini \
        zlib1g \
    && rm -rf /var/lib/apt/lists/*

# Unprivileged account that owns the application code and data.
RUN groupadd --system --gid 1000 babybuddy \
    && useradd --system --uid 1000 --gid babybuddy --create-home --home-dir /home/babybuddy babybuddy

COPY --from=python-deps /opt/venv /opt/venv

WORKDIR /app

# Application source.
COPY --chown=babybuddy:babybuddy api ./api
COPY --chown=babybuddy:babybuddy babybuddy ./babybuddy
COPY --chown=babybuddy:babybuddy core ./core
COPY --chown=babybuddy:babybuddy dashboard ./dashboard
COPY --chown=babybuddy:babybuddy guidance ./guidance
COPY --chown=babybuddy:babybuddy reports ./reports
COPY --chown=babybuddy:babybuddy locale ./locale
COPY --chown=babybuddy:babybuddy manage.py ./

# Compiled front-end assets from stage 1.
COPY --from=frontend --chown=babybuddy:babybuddy /build/babybuddy/static ./babybuddy/static

COPY --chown=babybuddy:babybuddy docker/entrypoint.sh /usr/local/bin/entrypoint.sh
RUN chmod 0755 /usr/local/bin/entrypoint.sh

# Collect static files at build time so the runtime filesystem can stay
# read-only and the WhiteNoise manifest is always present.
RUN SECRET_KEY=build-time-only-not-used-at-runtime \
    DEBUG=False \
    python manage.py collectstatic --noinput --clear \
    && chown -R babybuddy:babybuddy /app/static

# Application data (SQLite database and uploaded media) lives here.
RUN mkdir -p /data/media && chown -R babybuddy:babybuddy /data
VOLUME ["/data"]

USER babybuddy

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=30s --retries=3 \
    CMD curl -fsS -o /dev/null -H "Host: 127.0.0.1" "http://127.0.0.1:${PORT}/login/" || exit 1

ENTRYPOINT ["/usr/bin/tini", "--", "/usr/local/bin/entrypoint.sh"]
CMD ["gunicorn"]
