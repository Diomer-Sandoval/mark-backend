#!/usr/bin/env bash
# exit on error
set -o errexit

# Instalar dependencias
pip install --upgrade pip
pip install poetry
poetry install --no-root

# Recolectar archivos estáticos
poetry run python manage.py collectstatic --no-input

# Intentar arreglar historial inconsistente de migraciones (común en refactors grandes)
# 1. Limpiamos historial de apps problemáticas si existe inconsistencia
# 2. Aplicamos migraciones con --fake-initial para reconocer tablas existentes
poetry run python manage.py migrate --fake-initial || {
    echo "Inconsistencia detectada, intentando limpieza automática..."
    # Ejecutar script python para limpiar historial de migraciones de apps que cambiaron estructura
    poetry run python -c "
import os, django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()
from django.db import connection
with connection.cursor() as cursor:
    cursor.execute(\"DELETE FROM django_migrations WHERE app IN ('creation_studio', 'platform_insights', 'brand_dna_extractor', 'content_templates')\")
"
    # Re-intentar migración con fake-initial
    poetry run python manage.py migrate --fake-initial
}
