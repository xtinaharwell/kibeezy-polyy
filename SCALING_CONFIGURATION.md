# Scaling Configuration Templates

## Phase 1: Quick Wins (Current → 100K users)

### `settings.py` - Phase 1 Configuration

```python
# =============================================================================
# PHASE 1: DATABASE OPTIMIZATION & QUICK WINS
# =============================================================================

# 1. INCREASE DATABASE POOL SIZE & TUNE
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': config('DB_NAME', default='kibeezy_poly'),
        'USER': config('DB_USER', default='postgres'),
        'PASSWORD': config('DB_PASSWORD', default='postgres'),
        'HOST': config('DB_HOST', default='localhost'),
        'PORT': config('DB_PORT', default='5432'),
        
        # Increase connection pooling
        'CONN_MAX_AGE': 300,  # Keep connections for 5 mins (was 180)
        'ATOMIC_REQUESTS': True,  # Transactional safety
        
        'OPTIONS': {
            'connect_timeout': 10,
            'options': '-c statement_timeout=30000',  # 30 second timeout
            'isolation_level': psycopg2.extensions.ISOLATION_LEVEL_READ_COMMITTED,
        }
    }
}

# 2. ADD REDIS FOR SESSIONS & CACHING
CACHES = {
    'default': {
        'BACKEND': 'django_redis.cache.RedisCache',
        'LOCATION': config('REDIS_URL', default='redis://redis:6379/1'),
        'OPTIONS': {
            'CLIENT_CLASS': 'django_redis.client.DefaultClient',
            'CONNECTION_POOL_KWARGS': {
                'max_connections': 50,
                'retry_on_timeout': True,
            },
            'SOCKET_CONNECT_TIMEOUT': 5,
            'SOCKET_TIMEOUT': 5,
            'COMPRESSOR': 'django_redis.compressors.zlib.ZlibCompressor',
        }
    }
}

# Move sessions to Redis (much faster than database)
SESSION_ENGINE = 'django.contrib.sessions.backends.cache'
SESSION_CACHE_ALIAS = 'default'

# 3. ENABLE QUERY CACHING
# Cache expensive queries
QUERY_CACHE_TTL = 3600  # 1 hour for static queries
USER_PROFILE_CACHE_TTL = 1800  # 30 mins for user profiles
MARKET_LIST_CACHE_TTL = 60  # 1 minute (changes frequently)

# 4. LOGGING FOR SLOW QUERIES
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
        },
        'file': {
            'class': 'logging.handlers.RotatingFileHandler',
            'filename': '/var/log/cache/django.log',
            'maxBytes': 1024 * 1024 * 100,  # 100MB
            'backupCount': 10,
        },
    },
    'loggers': {
        'django.db.backends': {
            'handlers': ['file'],
            'level': 'DEBUG',
            'propagate': False,
        },
    },
}

# Enable slow query logging
SLOW_QUERY_THRESHOLD = 1  # Log queries > 1 second

# 5. MIDDLEWARE OPTIMIZATIONS
MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',  # Serve static files faster
    'corsheaders.middleware.CorsMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.cache.UpdateCacheMiddleware',  # Add caching
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.cache.FetchFromCacheMiddleware',  # Cache GET requests
]

# Cache configuration - cache GET requests for 60 seconds
CACHE_MIDDLEWARE_SECONDS = 60

print("✅ Phase 1 Settings Loaded")
```

---

## Phase 2: Distributed Architecture (100K → 500K users)

### `settings.py` - Phase 2 Configuration

```python
# =============================================================================
# PHASE 2: DISTRIBUTED ARCHITECTURE WITH READ REPLICAS
# =============================================================================

# 1. PRIMARY + READ REPLICAS
DATABASES = {
    'default': {  # Primary for writes
        'ENGINE': 'django.db.backends.postgresql',
        'HOST': config('DB_PRIMARY_HOST'),
        'NAME': config('DB_NAME'),
        'CONN_MAX_AGE': 300,
        'ATOMIC_REQUESTS': True,
    },
    
    'replica1': {  # Read replica 1
        'ENGINE': 'django.db.backends.postgresql',
        'HOST': config('DB_REPLICA1_HOST'),
        'NAME': config('DB_NAME'),
        'CONN_MAX_AGE': 300,
    },
    'replica2': {  # Read replica 2
        'ENGINE': 'django.db.backends.postgresql',
        'HOST': config('DB_REPLICA2_HOST'),
        'NAME': config('DB_NAME'),
        'CONN_MAX_AGE': 300,
    },
    'replica3': {  # Read replica 3
        'ENGINE': 'django.db.backends.postgresql',
        'HOST': config('DB_REPLICA3_HOST'),
        'NAME': config('DB_NAME'),
        'CONN_MAX_AGE': 300,
    },
}

# 2. DATABASE ROUTER FOR READ/WRITE SPLITTING
class ReadReplicaRouter:
    def db_for_read(self, model, **hints):
        """Route read queries to replicas"""
        return random.choice(['replica1', 'replica2', 'replica3'])
    
    def db_for_write(self, model, **hints):
        """Route writes to primary"""
        return 'default'

DATABASE_ROUTERS = ['api.routers.ReadReplicaRouter']

# 3. EXPANDED CACHING
CACHES = {
    'default': {
        'BACKEND': 'django_redis.cache.RedisCache',
        'LOCATION': config('REDIS_URL', default='redis://redis:6379/1'),
        'OPTIONS': {
            'CLIENT_CLASS': 'django_redis.client.DefaultClient',
            'CONNECTION_POOL_KWARGS': {'max_connections': 100},
        }
    },
    'sessions': {
        'BACKEND': 'django_redis.cache.RedisCache',
        'LOCATION': config('REDIS_SESSION_URL', default='redis://redis:6379/2'),
    }
}

SESSION_ENGINE = 'django.contrib.sessions.backends.cache'
SESSION_CACHE_ALIAS = 'sessions'

# 4. CELERY ASYNC TASKS
CELERY_BROKER_URL = config('CELERY_BROKER_URL', default='redis://redis:6379/0')
CELERY_RESULT_BACKEND = config('CELERY_RESULT_BACKEND', default='redis://redis:6379/3')
CELERY_ACCEPT_CONTENT = ['json']
CELERY_TASK_SERIALIZER = 'json'
CELERY_RESULT_SERIALIZER = 'json'
CELERY_TIMEZONE = 'UTC'

# Task configuration
CELERY_TASK_TRACK_STARTED = True
CELERY_TASK_TIME_LIMIT = 30 * 60  # 30 minutes hard limit
CELERY_TASK_SOFT_TIME_LIMIT = 25 * 60  # 25 minutes soft limit

# Celery beat schedule
from celery.schedules import crontab

CELERY_BEAT_SCHEDULE = {
    'reconcile-balances': {
        'task': 'payments.tasks.reconcile_balances',
        'schedule': crontab(hour=2, minute=0),  # Daily at 2 AM
    },
    'retry-failed-payouts': {
        'task': 'payments.tasks.retry_failed_payouts',
        'schedule': crontab(hour='*/4'),  # Every 4 hours
    },
}

# 5. MATERIALIZED VIEW FOR STATISTICS
# Run: python manage.py create_materialized_views
MATERIALIZED_VIEWS = [
    'user_stats',
    'market_stats',
    'payout_summary',
]

print("✅ Phase 2 Settings Loaded")
```

---

## Phase 3: Microservices & Sharding (500K → 1M users)

### `settings.py` - Phase 3 Configuration

```python
# =============================================================================
# PHASE 3: MICROSERVICES & DATABASE SHARDING
# =============================================================================

# 1. DATABASE SHARDING (Hash-based by user_id)
SHARD_COUNT = 4

def get_shard_id(user_id):
    """Calculate shard number from user ID"""
    return user_id % SHARD_COUNT

# Dynamically build shard databases
DATABASES = {'default': {...}}  # Primary (for new accounts)

for i in range(SHARD_COUNT):
    DATABASES[f'shard_{i}'] = {
        'ENGINE': 'django.db.backends.postgresql',
        'HOST': config(f'DB_SHARD_{i}_HOST'),
        'NAME': config('DB_NAME'),
        'USER': config('DB_USER'),
        'PASSWORD': config('DB_PASSWORD'),
        'CONN_MAX_AGE': 300,
    }

class ShardRouter:
    def db_for_read(self, model, **hints):
        if 'user_id' in hints:
            user_id = hints['user_id']
            shard_num = get_shard_id(user_id)
            return f'shard_{shard_num}'
        return 'default'
    
    def db_for_write(self, model, **hints):
        if 'user_id' in hints:
            user_id = hints['user_id']
            shard_num = get_shard_id(user_id)
            return f'shard_{shard_num}'
        return 'default'

DATABASE_ROUTERS = ['api.routers.ShardRouter']

# 2. KUBERNETES SERVICE DISCOVERY
# Services communicate via Kubernetes DNS
if config('ENVIRONMENT') == 'kubernetes':
    # User service
    USER_SERVICE_URL = 'http://user-service:8001'
    # Market service
    MARKET_SERVICE_URL = 'http://market-service:8002'
    # Payment service
    PAYMENT_SERVICE_URL = 'http://payment-service:8003'
else:
    # Local development
    USER_SERVICE_URL = 'http://localhost:8001'
    MARKET_SERVICE_URL = 'http://localhost:8002'
    PAYMENT_SERVICE_URL = 'http://localhost:8003'

# 3. INTER-SERVICE AUTHENTICATION
from requests.auth import HTTPBasicAuth

SERVICE_AUTH = HTTPBasicAuth(
    config('SERVICE_USERNAME'),
    config('SERVICE_PASSWORD')
)

# 4. CIRCUIT BREAKER FOR SERVICE CALLS
from pybreaker import CircuitBreaker

user_service_breaker = CircuitBreaker(
    fail_max=5,
    reset_timeout=60,
    listeners=[CircuitBreakerListener()]
)

market_service_breaker = CircuitBreaker(
    fail_max=5,
    reset_timeout=60,
)

# 5. MULTI-REGION CONFIGURATION
REGIONS = {
    'east-africa': {
        'db_primary': 'db-ea-primary.rds.aws',
        'redis': 'redis-ea.elasticache.aws',
        'api_endpoint': 'https://api-ea.cache.co.ke',
    },
    'southern-africa': {
        'db_primary': 'db-sa-primary.rds.aws',
        'redis': 'redis-sa.elasticache.aws',
        'api_endpoint': 'https://api-sa.cache.co.ke',
    },
    'europe': {
        'db_primary': 'db-eu-primary.rds.aws',
        'redis': 'redis-eu.elasticache.aws',
        'api_endpoint': 'https://api-eu.cache.co.ke',
    },
}

CURRENT_REGION = config('REGION', default='east-africa')

# 6. ADVANCED CACHING WITH CLUSTER
CACHES = {
    'default': {
        'BACKEND': 'django_redis.cache.RedisClusterCache',
        'LOCATION': [
            'redis-node-1:6379',
            'redis-node-2:6379',
            'redis-node-3:6379',
        ],
        'OPTIONS': {
            'CONNECTION_POOL_CLASS': 'rediscluster.connection.ClusterConnectionPool',
        }
    }
}

# 7. MONITORING & OBSERVABILITY
INSTALLED_APPS = [
    ...
    'corsheaders',
    'debug_toolbar',  # Development only
    'django_extensions',
]

MIDDLEWARE = [
    ...
    'django_prometheus.middleware.PrometheusBeforeMiddleware',
    'debug_toolbar.middleware.DebugToolbarMiddleware',
    'django_prometheus.middleware.PrometheusAfterMiddleware',
]

# Prometheus metrics
PROMETHEUS_EXPORT_MIGRATIONS = True

print("✅ Phase 3 Settings Loaded (Microservices Ready)")
```

---

## docker-compose.yml Evolution

### Phase 1
```yaml
services:
  db:
    image: postgres:15
    environment:
      POSTGRES_DB: kibeezy_poly
  redis:
    image: redis:7-alpine
  web:
    command: gunicorn --workers 16 api.wsgi:application
```

### Phase 2
```yaml
services:
  # Primary
  db-primary:
    image: postgres:15-alpine
  # Replicas
  db-replica1:
    image: postgres:15-alpine
    # Replication configured
  
  redis:
    image: redis:7-alpine
    
  # Celery workers
  celery-worker:
    command: celery -A api worker -c 10
```

### Phase 3 (Kubernetes)
**Move to Kubernetes manifests instead of docker-compose:**

```yaml
# kubernetes/services.yaml
---
apiVersion: v1
kind: Service
metadata:
  name: user-service
spec:
  selector:
    app: user-service
  ports:
    - port: 8001
---
apiVersion: apps/v1
kind: Deployment
metadata:
  name: user-service
spec:
  replicas: 10
  template:
    spec:
      containers:
      - name: user-service
        image: cache/user-service:latest
        resources:
          limits:
            cpu: "2"
            memory: "2Gi"
```

---

## Environment Variables for Each Phase

### Phase 1 (.env)
```
# Database
DB_NAME=kibeezy_poly
DB_USER=kibeezy
DB_PASSWORD=***
DB_HOST=postgres
DB_PORT=5432

# Redis
REDIS_URL=redis://redis:6379/1
```

### Phase 2 (.env)
```
# Database - Primary
DB_PRIMARY_HOST=db-primary.rds.aws
# Replicas
DB_REPLICA1_HOST=db-replica1.rds.aws
DB_REPLICA2_HOST=db-replica2.rds.aws
DB_REPLICA3_HOST=db-replica3.rds.aws
DB_NAME=kibeezy_poly

# Redis
REDIS_URL=redis://node1:6379
REDIS_SESSION_URL=redis://node2:6379

# Celery
CELERY_BROKER_URL=redis://message-broker:6379/0
CELERY_RESULT_BACKEND=redis://result-backend:6379/0
```

### Phase 3 (.env)
```
# Database - Sharded
DB_SHARD_0_HOST=shard0.rds.aws
DB_SHARD_1_HOST=shard1.rds.aws
DB_SHARD_2_HOST=shard2.rds.aws
DB_SHARD_3_HOST=shard3.rds.aws
DB_NAME=kibeezy_poly

# Region
REGION=east-africa
ENVIRONMENT=kubernetes

# Service URLs (Kubernetes)
USER_SERVICE_URL=http://user-service:8001
MARKET_SERVICE_URL=http://market-service:8002
PAYMENT_SERVICE_URL=http://payment-service:8003

# Redis cluster
REDIS_CLUSTER_NODES=redis1:6379,redis2:6379,redis3:6379
```

---

## Migration Path

### From Phase 1 to Phase 2
```bash
# 1. Add read replicas (AWS RDS)
aws rds create-db-instance-read-replica \
  --db-instance-identifier kibeezy-replica-1

# 2. Update settings.py with replica hosts
# Edit: DB_REPLICA1_HOST, etc.

# 3. Test read routing
python manage.py shell
>>> from django.db import router
>>> User.objects.using(router.db_for_read(User)).all()

# 4. Deploy new settings
docker-compose up -d
```

### From Phase 2 to Phase 3
```bash
# 1. Create Kubernetes cluster
minikube start  # or EKS/GKE

# 2. Migrate databases to shards
python manage.py shard_migration --count 4

# 3. Deploy microservices
kubectl apply -f kubernetes/

# 4. Verify routing
python manage.py test_shard_routing
```

---

**Status**: Configuration templates ready for each phase
**Last Updated**: 2026-04-10
