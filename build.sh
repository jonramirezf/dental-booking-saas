#!/usr/bin/env bash
# ============================================================
# build.sh — script que Render ejecuta en cada deploy
# En Render: Settings → Build Command → ./build.sh
# ============================================================
set -o errexit   # salir si cualquier comando falla

pip install --upgrade pip
pip install -r requirements.txt

python manage.py collectstatic --noinput
python manage.py migrate
