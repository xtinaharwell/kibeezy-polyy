# Week 1 Implementation Guide: PostgreSQL + Gunicorn + Nginx

This guide walks you through implementing the Week 1 critical infrastructure changes.

## Overview

- **PostgreSQL**: Replaces SQLite for concurrent multi-user handling
- **Gunicorn**: Application server (replaces Django dev server)
- **Nginx**: Reverse proxy and load balancer
- **Docker**: Optional containerization for easier deployment

## Implementation Steps

### Phase 1: Database (PostgreSQL)

#### 1.1 Test Current Setup
```bash
# Verify you can access Django
python manage.py shell
# Should open Django shell without errors
exit
```

#### 1.2 Install PostgreSQL
```bash
# On Windows: Download PostgreSQL from https://www.postgresql.org/download/windows/
# On Linux:
sudo apt-get install postgresql postgresql-contrib

# On macOS:
brew install postgresql@15
```

#### 1.3 Create Database and User
```bash
# Start PostgreSQL
# Windows: Use pgAdmin or command line
# Linux:
sudo -u postgres psql

# In psql, run:
CREATE USER kibeezy WITH PASSWORD 'secure_password_here';
CREATE DATABASE kibeezy_poly OWNER kibeezy;
GRANT ALL PRIVILEGES ON DATABASE kibeezy_poly TO kibeezy;

# Test connection:
psql -h localhost -U kibeezy -d kibeezy_poly
# Should connect successfully
```

#### 1.4 Update Django Settings
- ✓ Already done! Check `api/settings.py`
- PostgreSQL is configured to read from `.env`
- Database configuration uses `CONN_MAX_AGE=600` for connection pooling

#### 1.5 Test PostgreSQL Connection
```bash
# Activate virtual environment
source venv/bin/activate  # or venv\Scripts\activate on Windows

# Run migrations (this creates tables in PostgreSQL)
python manage.py migrate

# Should show:
# Running migrations...
# Applying contenttypes.0001_initial... OK
# ... (more migrations)
# Operations to perform ...
# ... (completed)

# Test connection
python manage.py shell
from django.db import connection
print(connection.ensure_connection())
# Should return None without error
exit
```

**✓ Phase 1 Complete: PostgreSQL is configured and tested**

---

### Phase 2: Application Server (Gunicorn)

#### 2.1 Install Gunicorn
```bash
# Already in requirements.txt, but ensure it's installed
pip install -r requirements.txt

# Verify installation
gunicorn --version
# Should output version number
```

#### 2.2 Test Gunicorn Locally
```bash
# Navigate to project directory
cd /path/to/kibeezy-polyy

# Start Gunicorn with 4 workers
gunicorn --bind 0.0.0.0:8001 \
         --workers 4 \
         --timeout 30 \
         --access-logfile - \
         api.wsgi:application

# Should output:
# [TIMESTAMP] [PID] [INFO] Starting gunicorn
# [TIMESTAMP] [PID] [INFO] Listening at: http://0.0.0.0:8001 (PID)
# [TIMESTAMP] [PID] [INFO] Using worker: sync
# [TIMESTAMP] [PID] [INFO] Worker spawned (pid: XXXX)
```

#### 2.3 Test Gunicorn in Another Terminal
```bash
# While Gunicorn is running, test it
curl http://127.0.0.1:8001/api/markets/

# Should return JSON array of markets (or empty array)
```

#### 2.4 Setup Gunicorn Configuration
✓ Already created: `gunicorn_config.py`

#### 2.5 Test with Configuration File
```bash
# Kill previous Gunicorn process
# Then start with config file:
gunicorn -c gunicorn_config.py api.wsgi

# Or using the config:
gunicorn --config gunicorn_config.py \
         --bind 127.0.0.1:8001 \
         api.wsgi:application

# Test again:
curl http://127.0.0.1:8001/api/auth/check/ -b "sessionid=test"
```

**✓ Phase 2 Complete: Gunicorn is configured and tested**

---

### Phase 3: Reverse Proxy (Nginx)

#### 3.1 Install Nginx
```bash
# Windows: https://nginx.org/en/download.html
# Linux:
sudo apt-get install nginx

# macOS:
brew install nginx
```

#### 3.2 Configure Nginx
✓ Already created: `nginx.conf`

#### 3.3 Setup Nginx (Linux/macOS)
```bash
# Copy configuration
sudo cp nginx.conf /etc/nginx/sites-available/kibeezy-poly

# Or for macOS:
sudo cp nginx.conf /usr/local/etc/nginx/servers/kibeezy-poly.conf

# Edit and update paths if needed
sudo nano /etc/nginx/sites-available/kibeezy-poly

# Test configuration
sudo nginx -t
# Should output:
# nginx: the configuration file /etc/nginx/nginx.conf syntax is ok
# nginx: configuration file /etc/nginx/nginx.conf test is successful

# Enable site (Linux only)
sudo ln -s /etc/nginx/sites-available/kibeezy-poly /etc/nginx/sites-enabled/
sudo rm /etc/nginx/sites-enabled/default

# Start Nginx
sudo systemctl start nginx
# or on macOS:
brew services start nginx
```

#### 3.4 Test Nginx Proxy
```bash
# With Gunicorn running on 8001
# Test proxy
curl http://localhost/api/markets/

# Should work and show same response as direct Gunicorn call
curl http://127.0.0.1:8001/api/markets/

# Test static files
curl http://localhost/static/ -I
# Should return proper headers
```

**✓ Phase 3 Complete: Nginx is configured as reverse proxy**

---

### Phase 4: Docker Implementation (Optional)

#### 4.1 Install Docker
```bash
# Windows/Mac: Download Docker Desktop
# Linux:
sudo apt-get install docker.io docker-compose
```

#### 4.2 Build and Run with Docker
```bash
# Navigate to project directory
cd /path/to/kibeezy-polyy

# Build image
docker-compose build

# Start services
docker-compose up -d

# Check status
docker-compose ps
# Should show:
# NAME                COMMAND                STATUS
# kibeezy_postgres    postgres ...          Up (healthy)
# kibeezy_django      gunicorn ...          Up
# kibeezy_nginx       nginx ...             Up
```

#### 4.3 Test Docker Setup
```bash
# Check logs
docker-compose logs -f web

# Test API through Nginx
curl http://localhost/api/markets/

# Should return JSON

# Stop services
docker-compose down
```

**✓ Phase 4 Complete: Docker is ready for production deployment**

---

## Testing Checklist

### PostgreSQL Tests
- [ ] Database created successfully
- [ ] User permissions set correctly
- [ ] Django migrations run without errors
- [ ] Can query the database from shell

### Gunicorn Tests
- [ ] Gunicorn starts without errors
- [ ] Can make requests to Gunicorn directly on port 8001
- [ ] Handles multiple concurrent requests
- [ ] Configuration file loads correctly

### Nginx Tests
- [ ] Nginx configuration syntax is valid
- [ ] Nginx starts without errors
- [ ] API endpoints accessible through Nginx proxy
- [ ] Static files served correctly
- [ ] Rate limiting rules working
- [ ] Security headers present in response

### Integration Tests
- [ ] Frontend can connect to backend through Nginx
- [ ] Login flow works end-to-end
- [ ] API endpoints return correct data
- [ ] Database changes persist correctly
- [ ] Static files load in browser

---

## Common Issues and Fixes

### PostgreSQL Connection Failed
```bash
# Check if PostgreSQL is running
sudo systemctl status postgresql
# or
brew services list | grep postgres

# Check connection parameters in .env
# Ensure DB_HOST, DB_USER, DB_PASSWORD are correct
```

### Gunicorn Port Already in Use
```bash
# Find process using port 8001
lsof -i :8001  # Linux/macOS
netstat -ano | findstr :8001  # Windows

# Kill process
kill -9 <PID>  # Linux/macOS
taskkill /PID <PID> /F  # Windows
```

### Nginx Configuration Invalid
```bash
# Check syntax
sudo nginx -t

# View detailed error
sudo nginx -s reload  # Will show errors

# Check configuration file
cat /etc/nginx/sites-available/kibeezy-poly | head -20
```

### Migrations Fail
```bash
# Create tables manually
python manage.py migrate --run-syncdb

# Check migration status
python manage.py showmigrations

# Rollback if needed
python manage.py migrate <app> <migration_number>
```

---

## Performance Monitoring

### Monitor Gunicorn
```bash
# Check worker processes
ps aux | grep gunicorn

# Monitor system resources
top -p $(pidof gunicorn)

# Check Gunicorn logs
tail -f /var/log/kibeezy/gunicorn_error.log
tail -f /var/log/kibeezy/gunicorn_access.log
```

### Monitor Nginx
```bash
# Check nginx processes
ps aux | grep nginx

# View active connections
netstat -an | grep -E ':(80|443)' | wc -l

# View logs
tail -f /var/log/nginx/kibeezy_poly_access.log
tail -f /var/log/nginx/kibeezy_poly_error.log
```

### Monitor Database
```bash
# Check active connections
sudo -u postgres psql kibeezy_poly
SELECT datname, count(*) FROM pg_stat_activity GROUP BY datname;

# Check slow queries
psql -U kibeezy -d kibeezy_poly
SELECT query, mean_time FROM pg_stat_statements ORDER BY mean_time DESC LIMIT 10;
```

---

## Next Week: Week 2 Tasks

After Week 1 is complete and tested, proceed to:
1. Implement Redis for sessions
2. Setup Redis caching for expensive queries
3. Add database connection pooling with PgBouncer
4. Configure persistent volumes for production

See `DEPLOYMENT.md` for full production setup guide.
