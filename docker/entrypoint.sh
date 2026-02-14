#!/usr/bin/env bash
set -euo pipefail

python manage.py migrate --noinput
exec gunicorn config.wsgi:application --config docker/gunicorn.conf.py
