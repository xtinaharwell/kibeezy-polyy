#!/bin/bash

# Database Migration Script: SQLite to PostgreSQL
# This script helps migrate from SQLite to PostgreSQL

set -e

echo "======================================"
echo "Kibeezy Poly: SQLite to PostgreSQL Migration"
echo "======================================"
echo ""

# Check if PostgreSQL is installed
if ! command -v psql &> /dev/null; then
    echo "ERROR: PostgreSQL is not installed. Please install it first."
    exit 1
fi

# Source environment variables
if [ -f .env ]; then
    source .env
else
    echo "ERROR: .env file not found. Please create it first."
    exit 1
fi

# Create database
echo "Creating PostgreSQL database..."
createdb -h $DB_HOST -U $DB_USER $DB_NAME 2>/dev/null || echo "Database already exists or error occurred"

# Run migrations
echo "Running Django migrations..."
python manage.py migrate

# Create superuser (optional)
echo ""
echo "Creating admin superuser..."
python manage.py createsuperuser --noinput \
    --username admin \
    --email admin@kibeezy.local 2>/dev/null || echo "Superuser creation skipped"

# Collect static files
echo "Collecting static files..."
python manage.py collectstatic --noinput

echo ""
echo "======================================"
echo "Migration Complete!"
echo "======================================"
echo ""
echo "Next steps:"
echo "1. Test: python manage.py runserver"
echo "2. Or start with Gunicorn: gunicorn -c gunicorn_config.py api.wsgi"
echo "3. Configure Nginx with nginx.conf"
echo ""
