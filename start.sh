#!/usr/bin/env bash
set -euo pipefail
python manage.py migrate --noinput
python manage.py inicializar_catalogo --se-vazio
python manage.py configurar_admin
python scripts/prepare_media.py
exec gunicorn sayit.wsgi:application --bind "0.0.0.0:${PORT:-8000}" --workers "${WEB_CONCURRENCY:-2}" --timeout 60 --access-logfile - --error-logfile -
