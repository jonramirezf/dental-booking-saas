# ============================================================
# Procfile — raíz del proyecto (para Render y Heroku)
# ============================================================
web: gunicorn config.wsgi:application --workers 2 --threads 4 --timeout 60 --bind 0.0.0.0:$PORT
