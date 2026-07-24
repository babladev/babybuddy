#!/bin/sh
# Container entrypoint for Baby Buddy.
#
# Usage:
#   entrypoint.sh gunicorn        Run the application server (default).
#   entrypoint.sh manage <args>   Run a Django management command.
#   entrypoint.sh <command>       Run an arbitrary command.
set -eu

log() {
    printf '[babybuddy] %s\n' "$1"
}

fail() {
    printf '[babybuddy] ERROR: %s\n' "$1" >&2
    exit 1
}

# ---------------------------------------------------------------------------
# Configuration checks. These fail fast rather than starting an insecure
# instance.
# ---------------------------------------------------------------------------
check_configuration() {
    if [ -z "${SECRET_KEY:-}" ]; then
        fail "SECRET_KEY is not set. Generate one with:
           python -c 'import secrets; print(secrets.token_urlsafe(64))'
       and set it in your .env file."
    fi

    case "${ALLOWED_HOSTS:-*}" in
        *'*'*)
            log "WARNING: ALLOWED_HOSTS allows any host. Set it to your own"
            log "         hostname(s) to prevent Host header attacks."
            ;;
    esac

    if [ "${SESSION_COOKIE_SECURE:-False}" != "True" ]; then
        log "WARNING: SESSION_COOKIE_SECURE is not True. Session cookies may be"
        log "         sent over plain HTTP. Enable it once TLS is in place."
    fi
}

# ---------------------------------------------------------------------------
# Writable data directory. The image declares /data as a volume; a bind mount
# owned by the host user is a common cause of startup failures.
# ---------------------------------------------------------------------------
check_data_directory() {
    data_dir="${BABYBUDDY_DATA_DIR:-/data}"
    if [ ! -w "${data_dir}" ]; then
        fail "${data_dir} is not writable by uid $(id -u). Fix the ownership of the
       mounted volume, for example:
           sudo chown -R 1000:1000 /path/to/babybuddy-data"
    fi
    mkdir -p "${data_dir}/media"
}

case "${1:-gunicorn}" in
    gunicorn)
        check_configuration
        check_data_directory

        log "Applying database migrations"
        python manage.py migrate --noinput

        log "Starting gunicorn on 0.0.0.0:${PORT:-8000}"
        exec gunicorn babybuddy.wsgi:application \
            --bind "0.0.0.0:${PORT:-8000}" \
            --workers "${GUNICORN_WORKERS:-3}" \
            --timeout "${GUNICORN_TIMEOUT:-60}" \
            --access-logfile - \
            --error-logfile - \
            --forwarded-allow-ips "${GUNICORN_FORWARDED_ALLOW_IPS:-*}"
        ;;
    manage)
        shift
        exec python manage.py "$@"
        ;;
    *)
        exec "$@"
        ;;
esac
