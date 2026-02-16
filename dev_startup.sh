#!/bin/bash

# Development Startup Script
# This script starts all necessary services for local development

set -e

echo "======================================"
echo "Kibeezy Poly - Development Startup"
echo "======================================"
echo ""

# Check if virtual environment exists
if [ ! -d "venv" ]; then
    echo "Creating virtual environment..."
    python3 -m venv venv
    source venv/bin/activate
    pip install --upgrade pip
    pip install -r requirements.txt
else
    source venv/bin/activate
fi

# Check if .env exists
if [ ! -f ".env" ]; then
    echo "Creating .env from .env.example..."
    cp .env.example .env
    echo "Please update .env with your settings"
fi

# Run migrations
echo "Running migrations..."
python manage.py migrate

# Create superuser if it doesn't exist
echo "Checking for superuser..."
python manage.py shell << END
from django.contrib.auth import get_user_model
User = get_user_model()
if not User.objects.filter(username='admin').exists():
    print("Creating default admin user: admin/admin")
    User.objects.create_superuser('admin', 'admin@local.dev', 'admin')
else:
    print("Admin user already exists")
END

echo ""
echo "======================================"
echo "Development Environment Ready!"
echo "======================================"
echo ""
echo "Starting servers..."
echo ""

# In a real dev environment, you'd use processes like:
# python manage.py runserver &
# npm run dev &

echo "Run the following commands in separate terminals:"
echo ""
echo "1. Start Django server:"
echo "   python manage.py runserver"
echo ""
echo "2. Start Next.js frontend:"
echo "   cd ../kibeezy-poly && npm run dev"
echo ""
echo "Access the application at:"
echo "   Frontend: http://localhost:3000"
echo "   Backend: http://localhost:8000"
echo "   Admin: http://localhost:8000/admin"
echo ""
echo "Login with:"
echo "   Username: admin"
echo "   Password: admin"
echo ""
