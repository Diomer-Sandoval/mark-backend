#!/usr/bin/env bash
# exit on error
set -o errexit

# Instalar dependencias
pip install --upgrade pip
pip install poetry
poetry install --no-root

# Recolectar archivos estáticos
poetry run python manage.py collectstatic --no-input

# RESET DE BASE DE DATOS (Limpieza profunda)
# Esto borrará todas las tablas para que las migraciones corran desde cero.
echo "Borrando base de datos para instalación limpia..."
poetry run python -c "
import os, django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()
from django.db import connection
with connection.cursor() as cursor:
    cursor.execute('DROP SCHEMA public CASCADE; CREATE SCHEMA public;')
"

poetry run python manage.py createcachetable

# Ejecutar migraciones desde cero
echo "Ejecutando todas las migraciones..."
poetry run python manage.py migrate
