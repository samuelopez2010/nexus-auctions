#!/bin/bash
set -e

echo "-----------------------------------"
echo "🚀 STARTING DEPLOYMENT SCRIPT"
echo "-----------------------------------"

echo "Checking database connection and applying migrations..."
python manage.py showmigrations
python manage.py migrate

echo "-----------------------------------"
echo "✅ MIGRATIONS COMPLETE"
echo "-----------------------------------"

echo "-----------------------------------"
echo "👤 CHECKING SUPERUSER"
echo "-----------------------------------"
python manage.py create_admin_auto

echo "-----------------------------------"
echo "🎁 POPULATING GIFT CARDS"
echo "-----------------------------------"
python manage.py populate_gift_cards

echo "Starting Gunicorn..."
exec gunicorn nexus_core.wsgi --bind 0.0.0.0:${PORT:-8000} --log-file -
