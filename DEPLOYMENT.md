# Kibeezy Poly - Production Deployment Guide

## Week 1: PostgreSQL + Gunicorn + Nginx

This guide covers deploying the Kibeezy Poly application with PostgreSQL, Gunicorn, and Nginx for production use with 1000+ users.

### Prerequisites

- Ubuntu 20.04 LTS or later
- PostgreSQL 12+
- Python 3.8+
- Nginx
- Systemd (for service management)

### Step 1: Install System Dependencies

```bash
# Update system packages
sudo apt-get update
sudo apt-get upgrade -y

# Install PostgreSQL
sudo apt-get install -y postgresql postgresql-contrib

# Install Python dependencies
sudo apt-get install -y python3 python3-pip python3-dev python3-venv

# Install Nginx
sudo apt-get install -y nginx

# Install Node.js (for frontend/build tools)
curl -fsSL https://deb.nodesource.com/setup_18.x | sudo -E bash -
sudo apt-get install -y nodejs
```

### Step 2: Setup PostgreSQL Database

```bash
# Connect to PostgreSQL
sudo -u postgres psql

# Inside psql:
CREATE USER kibeezy WITH PASSWORD 'your_secure_password';
CREATE DATABASE kibeezy_poly OWNER kibeezy;

# Add connections permission
ALTER ROLE kibeezy SET client_encoding TO 'utf8';
ALTER ROLE kibeezy SET default_transaction_isolation TO 'read committed';
ALTER ROLE kibeezy SET default_transaction_deferrable TO on;
ALTER ROLE kibeezy SET default_timezone TO 'UTC';

# Grant privileges
GRANT ALL PRIVILEGES ON DATABASE kibeezy_poly TO kibeezy;

# Exit psql
\q
```

### Step 3: Clone and Setup Application

```bash
# Create application directory
sudo mkdir -p /var/www/kibeezy-poly
cd /var/www/kibeezy-poly

# Clone repository
git clone https://github.com/your-repo/kibeezy-polyy.git .

# Create Python virtual environment
python3 -m venv venv
source venv/bin/activate

# Install Python dependencies
pip install --upgrade pip
pip install -r requirements.txt

# Create .env file
cp .env.example .env

# Edit .env with your settings (database credentials, secret key, etc.)
nano .env
```

### Step 4: Configure Django and Run Migrations

```bash
# Activate virtual environment
source venv/bin/activate

# Run migrations
python manage.py migrate

# Create superuser
python manage.py createsuperuser

# Collect static files
python manage.py collectstatic --noinput

# Create log directory
sudo mkdir -p /var/log/kibeezy
sudo chown www-data:www-data /var/log/kibeezy
```

### Step 5: Setup Gunicorn

```bash
# Update gunicorn_config.py with correct paths
# Update the pythonpath to: /var/www/kibeezy-poly

# Create Gunicorn systemd service
sudo cp kibeezy-poly.service /etc/systemd/system/

# Update service file paths
sudo nano /etc/systemd/system/kibeezy-poly.service

# Update these paths in the service file:
# WorkingDirectory=/var/www/kibeezy-poly
# EnvironmentFile=/var/www/kibeezy-poly/.env
# Environment="PATH=/var/www/kibeezy-poly/venv/bin"
# ExecStart=/var/www/kibeezy-poly/venv/bin/gunicorn ...

# Set proper permissions
sudo chown -R www-data:www-data /var/www/kibeezy-poly
sudo chmod -R 755 /var/www/kibeezy-poly

# Reload systemd and start service
sudo systemctl daemon-reload
sudo systemctl start kibeezy-poly
sudo systemctl enable kibeezy-poly

# Check status
sudo systemctl status kibeezy-poly
```

### Step 6: Setup Nginx

```bash
# Copy Nginx configuration
sudo cp nginx.conf /etc/nginx/sites-available/kibeezy-poly

# Update paths in nginx.conf:
# alias /var/www/kibeezy-poly/staticfiles/;
# alias /var/www/kibeezy-poly/media/;

# Edit the configuration
sudo nano /etc/nginx/sites-available/kibeezy-poly

# Enable site
sudo ln -s /etc/nginx/sites-available/kibeezy-poly /etc/nginx/sites-enabled/

# Disable default site
sudo rm /etc/nginx/sites-enabled/default

# Test Nginx configuration
sudo nginx -t

# Restart Nginx
sudo systemctl restart nginx
```

### Step 7: Setup SSL with Let's Encrypt (IMPORTANT for production)

```bash
# Install Certbot
sudo apt-get install -y certbot python3-certbot-nginx

# Get SSL certificate
sudo certbot certonly --nginx -d yourdomain.com

# Update nginx.conf with SSL configuration
# Uncomment the HTTPS section in nginx.conf

# Auto-renewal
sudo systemctl enable certbot.timer
sudo systemctl start certbot.timer
```

### Step 8: Test the Deployment

```bash
# Test Gunicorn is running
curl http://127.0.0.1:8001/api/markets/

# Test Nginx is serving correctly
curl http://localhost/api/markets/
curl http://localhost/static/ -I

# Test through browser
# Visit: http://yourdomain.com
```

### Step 9: Monitor and Maintain

```bash
# View Gunicorn logs
sudo journalctl -u kibeezy-poly -f

# View Nginx logs
sudo tail -f /var/log/nginx/kibeezy_poly_access.log
sudo tail -f /var/log/nginx/kibeezy_poly_error.log

# Monitor system resources
top
htop

# Check database connections
sudo -u postgres psql kibeezy_poly
\d+  -- to see table info
SELECT datname, count(*) FROM pg_stat_activity GROUP BY datname;
```

### Performance Tuning

#### PostgreSQL Connection Pooling

```bash
# Install PgBouncer
sudo apt-get install -y pgbouncer

# Configure /etc/pgbouncer/pgbouncer.ini
sudo nano /etc/pgbouncer/pgbouncer.ini

# Add to [databases] section:
# kibeezy_poly = host=127.0.0.1 port=5432 dbname=kibeezy_poly

# Add to [pgbouncer] section:
# pool_mode = transaction
# max_client_conn = 1000
# default_pool_size = 25
# reserve_pool_size = 5
# reserve_pool_timeout = 3
# max_db_connections = 100

# Restart PgBouncer
sudo systemctl restart pgbouncer
```

#### Nginx Optimization

In nginx.conf:
- Gzip compression: ✓ (already configured)
- Caching: ✓ (already configured for static files)
- Worker processes: `worker_processes auto;`
- Keep-alive: `keepalive_timeout 65;`

### Deployment Checklist

- [ ] PostgreSQL database created and configured
- [ ] Application dependencies installed
- [ ] .env file created with production settings
- [ ] Django migrations run successfully
- [ ] Static files collected
- [ ] Gunicorn service created and enabled
- [ ] Nginx configured and serving static files
- [ ] SSL certificate installed
- [ ] Firewall rules configured (if applicable)
- [ ] Log rotation configured
- [ ] Monitoring and alerts setup
- [ ] Backup strategy implemented
- [ ] Database backups scheduled

### Common Issues and Solutions

**1. Port 8001 already in use**
```bash
# Find and kill process
lsof -i :8001
kill -9 <PID>
```

**2. Permission denied errors**
```bash
# Fix permissions
sudo chown -R www-data:www-data /var/www/kibeezy-poly
```

**3. Static files not loading**
```bash
# Re-collect static files
python manage.py collectstatic --clear --noinput
```

**4. Database connection errors**
```bash
# Test PostgreSQL connection
psql -h localhost -U kibeezy -d kibeezy_poly
```

### Next Steps

After Week 1 is complete, proceed to:
- **Week 2**: Redis for sessions and caching
- **Week 3**: Database optimization and rate limiting
- **Week 4**: Monitoring, Celery, and async tasks

---

For more information, see:
- Django Deployment: https://docs.djangoproject.com/en/4.1/howto/deployment/
- Gunicorn: https://gunicorn.org/
- Nginx: https://nginx.org/en/docs/
