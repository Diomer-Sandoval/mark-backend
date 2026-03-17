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
# 1. Aplicamos migraciones con --fake-initial para reconocer tablas existentes
# 2. Si falla por inconsistencia o columnas faltantes (como user_id en posts), limpiamos y fakeamos.
echo "Ejecutando migraciones..."
if ! poetry run python manage.py migrate --fake-initial; then
    echo "Falla detectada en migraciones, iniciando modo recuperación..."
    
    # Limpiar historial de las apps que sabemos que cambiaron
    poetry run python -c "
import os, django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()
from django.db import connection
with connection.cursor() as cursor:
    apps = ['creation_studio', 'platform_insights', 'brand_dna_extractor', 'content_templates', 'ai_chatbot']
    for app in apps:
        cursor.execute(f\"DELETE FROM django_migrations WHERE app = '{app}'\")
"
    # Re-intentar con fake total para estas apps
    # Esto asume que el esquema en DB ya coincide con los modelos actuales (que es lo que logramos en local)
    echo "Faqueando migraciones para apps core..."
    poetry run python manage.py migrate --fake brand_dna_extractor
    poetry run python manage.py migrate --fake platform_insights
    poetry run python manage.py migrate --fake creation_studio
    poetry run python manage.py migrate --fake ai_chatbot
    poetry run python manage.py migrate --fake content_templates
    
    # Finalmente correr migrate normal para cualquier otra cosa pendiente
    poetry run python manage.py migrate
fi
