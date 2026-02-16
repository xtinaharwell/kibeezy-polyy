#!/usr/bin/env python
"""
KASOKO System Verification Script
Checks if all required files, settings, and dependencies are in place
"""

import os
import sys
import json
from pathlib import Path
from django.conf import settings
from django.core.management import call_command

def check_environment():
    """Check environment variables are set"""
    print("\n=== ENVIRONMENT VARIABLES ===")
    required_env_vars = [
        'CELERY_BROKER_URL',
        'CELERY_RESULT_BACKEND',
        'MPESA_CONSUMER_KEY',
        'MPESA_CONSUMER_SECRET',
        'MPESA_PRODUCTION',
    ]
    
    missing = []
    for var in required_env_vars:
        value = os.getenv(var)
        if value:
            # Hide sensitive values
            if 'KEY' in var or 'SECRET' in var or 'CREDENTIAL' in var:
                print(f"  ✓ {var}: [SET]")
            else:
                print(f"  ✓ {var}: {value}")
        else:
            print(f"  ✗ {var}: NOT SET")
            missing.append(var)
    
    return len(missing) == 0, missing

def check_files():
    """Check if required files exist"""
    print("\n=== REQUIRED FILES ===")
    required_files = [
        'payments/daraja_b2c.py',
        'payments/settlement_tasks.py',
        'markets/admin_settlement_views.py',
        'api/celery.py',
        'payments/models.py',
        'markets/models.py',
        'users/models.py',
    ]
    
    missing_files = []
    for filepath in required_files:
        full_path = Path(filepath)
        if full_path.exists():
            size = full_path.stat().st_size
            print(f"  ✓ {filepath} ({size} bytes)")
        else:
            print(f"  ✗ {filepath}: NOT FOUND")
            missing_files.append(filepath)
    
    return len(missing_files) == 0, missing_files

def check_models():
    """Check if Transaction model has required fields"""
    print("\n=== TRANSACTION MODEL FIELDS ===")
    try:
        from payments.models import Transaction
        
        required_fields = [
            'external_ref',
            'mpesa_response',
            'status',
            'amount',
            'user',
            'type',
        ]
        
        missing_fields = []
        for field_name in required_fields:
            try:
                field = Transaction._meta.get_field(field_name)
                if field_name == 'external_ref':
                    unique = getattr(field, 'unique', False)
                    print(f"  ✓ {field_name} (unique={unique})")
                else:
                    print(f"  ✓ {field_name}")
            except Exception as e:
                print(f"  ✗ {field_name}: {str(e)}")
                missing_fields.append(field_name)
        
        return len(missing_fields) == 0, missing_fields
    except ImportError as e:
        print(f"  ✗ Could not import Transaction model: {str(e)}")
        return False, ['Transaction model import failed']

def check_celery_config():
    """Check Celery configuration"""
    print("\n=== CELERY CONFIGURATION ===")
    try:
        broker = getattr(settings, 'CELERY_BROKER_URL', 'NOT SET')
        backend = getattr(settings, 'CELERY_RESULT_BACKEND', 'NOT SET')
        
        print(f"  Broker: {broker}")
        print(f"  Result Backend: {backend}")
        
        # Try to import celery app
        from api.celery import app as celery_app
        print(f"  ✓ Celery app imported successfully")
        
        return True, []
    except Exception as e:
        print(f"  ✗ Celery configuration error: {str(e)}")
        return False, [str(e)]

def check_redis_connection():
    """Check if Redis is reachable"""
    print("\n=== REDIS CONNECTION ===")
    try:
        import redis
        
        broker_url = os.getenv('CELERY_BROKER_URL', 'redis://127.0.0.1:6379/0')
        # Parse Redis URL (simplified)
        if '://' in broker_url:
            parts = broker_url.split('://')[-1].split(':')
            host = parts[0]
            port = int(parts[1].split('/')[0])
        else:
            host, port = '127.0.0.1', 6379
        
        r = redis.Redis(host=host, port=port, socket_connect_timeout=5)
        pong = r.ping()
        
        if pong:
            print(f"  ✓ Redis is running at {host}:{port}")
            return True, []
    except Exception as e:
        print(f"  ✗ Redis connection failed: {str(e)}")
        print(f"     Try: docker run -d -p 6379:6379 redis:latest")
        return False, [str(e)]

def check_mpesa_settings():
    """Check M-Pesa configuration"""
    print("\n=== M-PESA CONFIGURATION ===")
    try:
        mpesa_settings = {
            'CONSUMER_KEY': getattr(settings, 'MPESA_CONSUMER_KEY', 'NOT SET'),
            'CONSUMER_SECRET': getattr(settings, 'MPESA_CONSUMER_SECRET', 'NOT SET'),
            'INITIATOR_NAME': getattr(settings, 'MPESA_INITIATOR_NAME', 'NOT SET'),
            'PAYBILL': getattr(settings, 'MPESA_PAYBILL', 'NOT SET'),
            'PRODUCTION': getattr(settings, 'MPESA_PRODUCTION', False),
        }
        
        for key, value in mpesa_settings.items():
            if value == 'NOT SET':
                print(f"  ✗ MPESA_{key}: NOT SET")
            elif key in ['CONSUMER_KEY', 'CONSUMER_SECRET']:
                print(f"  ✓ MPESA_{key}: [SET]")
            else:
                print(f"  ✓ MPESA_{key}: {value}")
        
        return True, []
    except Exception as e:
        print(f"  ✗ M-Pesa configuration error: {str(e)}")
        return False, [str(e)]

def check_urls():
    """Check if URLs are properly configured"""
    print("\n=== URL ROUTING ===")
    try:
        from django.urls import get_resolver
        resolver = get_resolver()
        
        routes_to_check = [
            'api:place_bet',
            'api:b2c_callback',
            'api:resolve_market',
            'api:settlement_status',
        ]
        
        found = []
        missing = []
        
        for route_name in routes_to_check:
            try:
                url = resolver.reverse(route_name, args=[1] if 'status' in route_name else [])
                found.append(route_name)
                print(f"  ✓ {route_name}: {url}")
            except Exception:
                missing.append(route_name)
                print(f"  ✗ {route_name}: NOT FOUND")
        
        return len(missing) == 0, missing
    except Exception as e:
        print(f"  ✗ Could not check URLs: {str(e)}")
        return False, [str(e)]

def main():
    """Run all checks"""
    print("=" * 60)
    print("KASOKO SYSTEM VERIFICATION")
    print("=" * 60)
    
    checks = [
        ("Environment Variables", check_environment),
        ("Required Files", check_files),
        ("Transaction Model", check_models),
        ("Celery Configuration", check_celery_config),
        ("Redis Connection", check_redis_connection),
        ("M-Pesa Configuration", check_mpesa_settings),
        ("URL Routing", check_urls),
    ]
    
    results = {}
    for check_name, check_func in checks:
        try:
            is_ok, issues = check_func()
            results[check_name] = {'ok': is_ok, 'issues': issues}
        except Exception as e:
            print(f"\n✗ Exception in {check_name}: {str(e)}")
            results[check_name] = {'ok': False, 'issues': [str(e)]}
    
    # Summary
    print("\n" + "=" * 60)
    print("SUMMARY")
    print("=" * 60)
    
    all_ok = all(result['ok'] for result in results.values())
    
    for check_name, result in results.items():
        status = "✓ PASS" if result['ok'] else "✗ FAIL"
        print(f"{status}: {check_name}")
        if result['issues']:
            for issue in result['issues']:
                print(f"      → {issue}")
    
    print("\n" + "=" * 60)
    if all_ok:
        print("✓ ALL CHECKS PASSED! System is ready.")
        print("\nNext steps:")
        print("  1. Ensure Redis is running: docker run -d -p 6379:6379 redis:latest")
        print("  2. Start Celery worker: celery -A api worker -l info")
        print("  3. Start Django: python manage.py runserver")
    else:
        print("✗ SOME CHECKS FAILED. Please fix issues above before proceeding.")
    
    print("=" * 60)
    
    return 0 if all_ok else 1

if __name__ == '__main__':
    # This script needs to run inside Django environment
    import django
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'api.settings')
    django.setup()
    
    sys.exit(main())
