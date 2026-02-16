"""
Gunicorn configuration file for production
Run with: gunicorn -c gunicorn_config.py api.wsgi
"""

import multiprocessing
import os

# Server socket
bind = "127.0.0.1:8001"  # Listen on localhost:8001 (Nginx will proxy to this)
backlog = 2048

# Worker processes
workers = multiprocessing.cpu_count() * 2 + 1  # Formula for optimal workers
worker_class = "sync"
worker_connections = 1000
timeout = 30
keepalive = 2

# Logging
accesslog = os.environ.get('LOG_DIR', '/var/log/kibeezy') + '/gunicorn_access.log'
errorlog = os.environ.get('LOG_DIR', '/var/log/kibeezy') + '/gunicorn_error.log'
loglevel = 'info'
access_log_format = '%(h)s %(l)s %(u)s %(t)s "%(r)s" %(s)s %(b)s "%(f)s" "%(a)s"'

# Process naming
proc_name = 'kibeezy_poly'

# Server mechanics
daemon = False
pidfile = "/var/run/gunicorn.pid"  # For systemd, set to None
umask = 0o022
tmp_upload_dir = None

# SSL (handled by Nginx, not here)
keyfile = None
certfile = None

# Application
pythonpath = "/path/to/kibeezy-polyy"  # Update this path
reload = False  # Set to True for development
reload_extra_files = []

# Hook functions
def on_starting(server):
    """Called when Gunicorn first starts"""
    print("Gunicorn server is starting...")

def when_ready(server):
    """Called when Gunicorn is ready to receive requests"""
    print("Gunicorn server is ready. Spawning workers")

def on_exit(server):
    """Called when Gunicorn shutdown is complete"""
    print("Gunicorn server shutting down...")
