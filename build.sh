#!/usr/bin/env bash
# exit on error
set -o errexit

pip install -r requirements.txt

# Устанавливаем браузеры для Playwright
python -m playwright install --with-deps chromium

python manage.py collectstatic --no-input
python manage.py migrate