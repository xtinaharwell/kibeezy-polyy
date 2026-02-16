# Kibeezy Poly - Betting Markets Platform

Production-ready Django + Next.js application for prediction markets with M-Pesa integration.

## Features

- **User Management**: Phone number + PIN authentication
- **Markets**: Browse and place bets on prediction markets
- **Betting**: Place Yes/No bets with probability tracking
- **Payments**: M-Pesa integration for deposits/withdrawals
- **Admin Dashboard**: Manage markets, resolve bets, view statistics
- **Responsive UI**: Built with Next.js and React

## Project Structure

```
kibeezy-polyy/          # Django Backend
├── api/                 # Django settings
├── users/               # User authentication
├── markets/             # Markets and betting
├── payments/            # Payment integration
└── ...

kibeezy-poly/           # Next.js Frontend
├── app/                 # Pages and routes
├── components/          # React components
└── ...
```

## Technology Stack

### Backend
- **Django 4.1** - Web framework
- **PostgreSQL** - Production database
- **Gunicorn** - Application server
- **Nginx** - Reverse proxy
- **Redis** - Sessions & caching (Week 2)

### Frontend
- **Next.js 13** - React framework
- **TypeScript** - Type safety
- **Tailwind CSS** - Styling

### Deployment
- **Docker** - Containerization
- **Docker Compose** - Local development
- **Systemd** - Service management (Linux)

## Quick Start

### Option 1: Docker (Recommended)

```bash
cd kibeezy-polyy
docker-compose up -d

# Access the application
# Frontend: http://localhost
# Backend: http://localhost/api
# Admin: http://localhost/admin
```

### Option 2: Manual Setup

1. **Install dependencies**
```bash
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

2. **Setup PostgreSQL**
```bash
# Create database and user
psql -U postgres
CREATE USER kibeezy WITH PASSWORD 'password';
CREATE DATABASE kibeezy_poly OWNER kibeezy;
```

3. **Configure environment**
```bash
cp .env.example .env
# Edit .env with your database credentials
```

4. **Run migrations**
```bash
python manage.py migrate
python manage.py createsuperuser
```

5. **Start development server**
```bash
python manage.py runserver
```

## Development

### Backend Development

```bash
# Activate virtual environment
source venv/bin/activate

# Run migrations
python manage.py migrate

# Create test data
python manage.py seed_markets

# Start server
python manage.py runserver

# Run tests
python manage.py test

# Access admin panel
open http://localhost:8000/admin
```

### Frontend Development

```bash
cd ../kibeezy-poly
npm install
npm run dev

# Open http://localhost:3000
```

## Production Deployment

See [DEPLOYMENT.md](DEPLOYMENT.md) for complete production setup guide.

**Quick Production Start:**

```bash
# 1. Ensure PostgreSQL is installed and running
# 2. Configure .env for production
# 3. Setup with systemd
sudo cp kibeezy-poly.service /etc/systemd/system/
sudo systemctl start kibeezy-poly
sudo systemctl enable kibeezy-poly

# 4. Setup Nginx
sudo cp nginx.conf /etc/nginx/sites-available/kibeezy-poly
sudo ln -s /etc/nginx/sites-available/kibeezy-poly /etc/nginx/sites-enabled/
sudo systemctl restart nginx
```

## API Documentation

### Authentication

**Login**
```bash
POST /api/auth/login/
{
  "phone_number": "+254712345678",
  "pin": "1234"
}
```

**Signup**
```bash
POST /api/auth/signup/
{
  "full_name": "John Doe",
  "phone_number": "+254712345678", 
  "pin": "1234"
}
```

**Check Auth**
```bash
GET /api/auth/check/
```

### Markets

**List Markets**
```bash
GET /api/markets/
```

**Place Bet**  
```bash
POST /api/markets/bet/
{
  "market_id": 1,
  "outcome": "Yes",
  "amount": 100
}
```

### Dashboard

**Get Dashboard**
```bash
GET /api/markets/dashboard/
```

**Get Transaction History**
```bash
GET /api/markets/history/
```

### Payments

**Initiate STK Push (M-Pesa)**
```bash
POST /api/payments/stk-push/
{
  "amount": 100
}
```

## Configuration

### Environment Variables

See `.env.example` for all available variables. Key ones:

```
# Database
DB_NAME=kibeezy_poly
DB_USER=kibeezy
DB_PASSWORD=secure_password
DB_HOST=localhost
DB_PORT=5432

# Django
SECRET_KEY=your-secret-key
DEBUG=False (for production)

# M-Pesa
MPESA_CONSUMER_KEY=xxxx
MPESA_CONSUMER_SECRET=xxxx
MPESA_SHORTCODE=xxxx
```

## Scaling to 1000+ Users

Infrastructure improvements already implemented:

### Week 1 ✅ (COMPLETE)
- PostgreSQL database (concurrent users)
- Gunicorn application server (multi-worker)
- Nginx reverse proxy (load balancing, caching)
- Docker support (easy deployment)

### Week 2 (Redis & Caching)
- Redis sessions (5x faster lookup)
- Redis caching (reduce DB queries)
- PgBouncer (connection pooling)

### Week 3 (Optimization)
- Database indices
- Query optimization
- API rate limiting
- Celery async tasks

### Week 4 (Monitoring)
- Error tracking (Sentry)
- Performance monitoring (DataDog)
- Log aggregation (ELK)
- Auto-scaling setup

See [WEEK1_IMPLEMENTATION.md](WEEK1_IMPLEMENTATION.md) for detailed scaling guide.

## Testing

```bash
# Backend tests
python manage.py test

# Test with pytest
pytest

# Test coverage
coverage run -m pytest
coverage report
```

## Troubleshooting

### Database Connection Issues
```bash
# Test PostgreSQL connection
psql -h localhost -U kibeezy -d kibeezy_poly

# Check Django settings
python manage.py shell
>>> from django.db import connection
>>> connection.ensure_connection()
```

### Gunicorn Issues
```bash
# Check if port 8001 is in use
lsof -i :8001

# Start with debug output
gunicorn --bind 0.0.0.0:8001 --workers 1 api.wsgi --log-level debug
```

### Nginx Issues
```bash
# Test configuration
nginx -t

# Check error logs
tail -f /var/log/nginx/kibeezy_poly_error.log
```

## Performance Monitoring

### Monitor Gunicorn
```bash
top -p $(pgrep -f gunicorn)
```

### Monitor Database
```bash
psql -U kibeezy -d kibeezy_poly
SELECT datname, count(*) FROM pg_stat_activity GROUP BY datname;
```

### Monitor Nginx  
```bash
tail -f /var/log/nginx/kibeezy_poly_access.log
```

## Contributing

1. Fork the repository
2. Create a feature branch
3. Commit your changes
4. Push to the branch
5. Create a Pull Request

## License

Proprietary - All rights reserved

## Support

For issues and questions:
- Create an issue on GitHub
- Contact: support@kibeezy.co.ke

## Documentation

- [Deployment Guide](DEPLOYMENT.md) - Production setup
- [Week 1 Implementation](WEEK1_IMPLEMENTATION.md) - Detailed scaling steps
- [Quick Reference](WEEK1_QUICK_REFERENCE.md) - Quick lookup

---

**Status**: Production Ready ✅  
**Version**: 1.0.0  
**Last Updated**: February 2026


```python
# api/wsgi.py
app = get_wsgi_application()
```

The corresponding `WSGI_APPLICATION` setting is configured to use the `app` variable from the `api.wsgi` module:

```python
# api/settings.py
WSGI_APPLICATION = 'api.wsgi.app'
```

There is a single view which renders the current time in `example/views.py`:

```python
# example/views.py
from datetime import datetime

from django.http import HttpResponse


def index(request):
    now = datetime.now()
    html = f'''
    <html>
        <body>
            <h1>Hello from Vercel!</h1>
            <p>The current time is { now }.</p>
        </body>
    </html>
    '''
    return HttpResponse(html)
```

This view is exposed a URL through `example/urls.py`:

```python
# example/urls.py
from django.urls import path

from example.views import index


urlpatterns = [
    path('', index),
]
```

Finally, it's made accessible to the Django server inside `api/urls.py`:

```python
# api/urls.py
from django.urls import path, include

urlpatterns = [
    ...
    path('', include('example.urls')),
]
```

This example uses the Web Server Gateway Interface (WSGI) with Django to enable handling requests on Vercel with Serverless Functions.

## Running Locally

```bash
python manage.py runserver
```

Your Django application is now available at `http://localhost:8000`.

## One-Click Deploy

Deploy the example using [Vercel](https://vercel.com?utm_source=github&utm_medium=readme&utm_campaign=vercel-examples):

[![Deploy with Vercel](https://vercel.com/button)](https://vercel.com/new/clone?repository-url=https%3A%2F%2Fgithub.com%2Fvercel%2Fexamples%2Ftree%2Fmain%2Fpython%2Fdjango&demo-title=Django%20%2B%20Vercel&demo-description=Use%20Django%204%20on%20Vercel%20with%20Serverless%20Functions%20using%20the%20Python%20Runtime.&demo-url=https%3A%2F%2Fdjango-template.vercel.app%2F&demo-image=https://assets.vercel.com/image/upload/v1669994241/random/django.png)
