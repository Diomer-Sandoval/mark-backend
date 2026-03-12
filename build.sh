#!/usr/bin/env bash
# exit on error
set -o errexit

# Instalar dependencias
pip install --upgrade pip
pip install poetry
poetry install --no-root

# Recolectar archivos estáticos
python manage.py collectstatic --no-input

# Aplicar migraciones (Opcional, pero recomendado)
python manage.py migrate
