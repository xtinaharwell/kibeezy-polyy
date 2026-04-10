#!/usr/bin/env python
"""
System Capacity Assessment Tool

Analyzes current infrastructure and predicts:
- Maximum concurrent users
- Request throughput
- Database capacity
- Growth runway

Usage:
    python capacity_check.py
    python capacity_check.py --verbose
"""

import os
import sys
import django
from decimal import Decimal

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'api.settings')
sys.path.insert(0, os.path.dirname(__file__))
django.setup()

from django.db import connection
from django.conf import settings
from users.models import CustomUser
from payments.models import Transaction
from markets.models import Market, Bet


class CapacityAssessment:
    def __init__(self):
        self.current_users = CustomUser.objects.count()
        self.current_transactions = Transaction.objects.count()
        self.current_markets = Market.objects.count()
        self.current_bets = Bet.objects.count()
    
    def get_database_stats(self):
        """Get PostgreSQL database size and stats"""
        with connection.cursor() as cursor:
            # Database size
            cursor.execute("""
                SELECT 
                    pg_size_pretty(pg_database.datsize) as db_size,
                    datname as db_name
                FROM pg_database
                WHERE datname = %s;
            """, [settings.DATABASES['default']['NAME']])
            db_info = cursor.fetchone()
            
            # Table sizes
            cursor.execute("""
                SELECT 
                    schemaname,
                    tablename,
                    pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename)) as size
                FROM pg_tables
                WHERE schemaname NOT IN ('pg_catalog', 'information_schema')
                ORDER BY pg_total_relation_size(schemaname||'.'||tablename) DESC;
            """)
            tables = cursor.fetchall()
        
        return {'db_info': db_info, 'tables': tables}
    
    def estimate_capacity(self):
        """Estimate current system capacity"""
        
        # Gunicorn workers (from docker-compose default: 4)
        workers = 4  # or read from settings/environment
        requests_per_worker = 25  # Conservative
        
        max_rps = workers * requests_per_worker  # 100 RPS
        max_concurrent_users = max_rps * 5  # Assume avg 5 RPS per active user
        
        # PostgreSQL capacity
        # PostgreSQL: typically 200 connections at 4GB RAM
        pg_connections = 200
        queries_per_sec = 100  # Conservative for single instance
        
        return {
            'max_rps': max_rps,
            'max_concurrent_users': max_concurrent_users,
            'pg_connections': pg_connections,
            'queries_per_sec': queries_per_sec,
        }
    
    def project_runway(self):
        """Project when we'll hit capacity limits"""
        capacity = self.estimate_capacity()
        
        # Assume current growth rate (rough estimates)
        daily_new_users = 10
        daily_transactions = 50
        
        # Days until hitting limits
        current = self.current_users
        max_users = capacity['max_concurrent_users']
        headroom_factor = 0.8  # Use 80% of capacity
        
        if current > 0:
            days_until_limit = (max_users * headroom_factor - current) / daily_new_users
            weeks_until_limit = days_until_limit / 7
        else:
            weeks_until_limit = float('inf')
        
        return {
            'current_users': current,
            'capacity': max_users,
            'weeks_runway': weeks_until_limit,
            'daily_growth_rate': daily_new_users,
        }
    
    def get_bottlenecks(self):
        """Identify current bottlenecks"""
        bottlenecks = []
        
        # Check for missing indexes
        with connection.cursor() as cursor:
            cursor.execute("""
                SELECT indexname FROM pg_indexes
                WHERE tablename IN ('users_customuser', 'payments_transaction', 'markets_bet')
                ORDER BY tablename;
            """)
            indexes = cursor.fetchall()
        
        if len(indexes) < 10:  # Should have many indexes
            bottlenecks.append({
                'severity': 'HIGH',
                'issue': 'Missing database indexes',
                'impact': 'Query performance degradation',
                'fix': 'Add compound indexes on (user, created_at), (status, created_at), etc.'
            })
        
        # Check for session backend
        session_backend = settings.SESSION_ENGINE
        if 'database' in session_backend:
            bottlenecks.append({
                'severity': 'MEDIUM',
                'issue': 'Sessions stored in database',
                'impact': 'Extra DB load (~50K writes/sec at 1M users)',
                'fix': 'Use Redis backend instead'
            })
        
        # Check for Redis
        if not hasattr(settings, 'CACHES') or 'redis' not in str(settings.CACHES):
            bottlenecks.append({
                'severity': 'HIGH',
                'issue': 'No Redis caching',
                'impact': 'Every market list = full table scan',
                'fix': 'Add Redis cache layer'
            })
        
        # Check for Celery
        if not hasattr(settings, 'CELERY_BROKER_URL'):
            bottlenecks.append({
                'severity': 'MEDIUM',
                'issue': 'No async queue system',
                'impact': 'M-Pesa/email calls block workers',
                'fix': 'Set up Celery + Redis'
            })
        
        return bottlenecks
    
    def print_report(self, verbose=False):
        """Print comprehensive capacity report"""
        print("\n" + "="*70)
        print("CACHE SYSTEM CAPACITY ASSESSMENT")
        print("="*70)
        
        # Current state
        print("\n📊 CURRENT STATE")
        print(f"  Users:           {self.current_users:,}")
        print(f"  Transactions:    {self.current_transactions:,}")
        print(f"  Markets:         {self.current_markets:,}")
        print(f"  Bets:            {self.current_bets:,}")
        
        # Database stats
        db_stats = self.get_database_stats()
        if db_stats['db_info']:
            print(f"\n  Database Size:   {db_stats['db_info'][0]}")
        
        if verbose and db_stats['tables']:
            print("\n  Table Sizes:")
            for schema, table, size in db_stats['tables'][:5]:
                print(f"    - {table}: {size}")
        
        # Capacity
        capacity = self.estimate_capacity()
        print(f"\n⚙️  CURRENT CAPACITY")
        print(f"  Max RPS:         {capacity['max_rps']} req/sec")
        print(f"  Concurrent Users: {capacity['max_concurrent_users']:,}")
        print(f"  DB Connections:  {capacity['pg_connections']}")
        print(f"  Queries/sec:     {capacity['queries_per_sec']}")
        
        # Runway
        runway = self.project_runway()
        if runway['weeks_runway'] != float('inf'):
            print(f"\n📈 GROWTH RUNWAY")
            print(f"  Weeks until limit: {runway['weeks_runway']:.1f} weeks")
            print(f"  Daily growth rate: {runway['daily_growth_rate']} users/day")
            
            if runway['weeks_runway'] < 12:
                print(f"  ⚠️  ACTION NEEDED: Scale within {runway['weeks_runway']:.1f} weeks")
            elif runway['weeks_runway'] < 26:
                print(f"  ⚠️  Start planning for scaling (6 months runway)")
            else:
                print(f"  ✅ Plenty of runway ({runway['weeks_runway']:.0f} weeks)")
        
        # Bottlenecks
        bottlenecks = self.get_bottlenecks()
        if bottlenecks:
            print(f"\n🚨 BOTTLENECKS IDENTIFIED")
            for i, bn in enumerate(bottlenecks, 1):
                print(f"\n  {i}. {bn['issue']} [{bn['severity']}]")
                print(f"     Impact: {bn['impact']}")
                print(f"     Fix:    {bn['fix']}")
        else:
            print(f"\n✅ NO CRITICAL BOTTLENECKS DETECTED")
        
        # Recommendations
        print(f"\n💡 RECOMMENDATIONS")
        if self.current_users < 50000:
            print("  Phase 1 Priority: Database optimization & indexing")
            print("  - Run: python manage.py migrate (apply missing indexes)")
            print("  - Implement quick wins from SCALABILITY_ANALYSIS.md")
        elif self.current_users < 250000:
            print("  Phase 2 Priority: Distributed architecture")
            print("  - Add read replicas")
            print("  - Implement Redis caching")
            print("  - Set up Celery workers")
        else:
            print("  Phase 3 Priority: Microservices & sharding")
            print("  - Plan database sharding")
            print("  - Migrate to Kubernetes")
            print("  - Split monolith into services")
        
        print("\n" + "="*70)


def main():
    import argparse
    parser = argparse.ArgumentParser(description='System Capacity Assessment')
    parser.add_argument('--verbose', '-v', action='store_true', help='Verbose output')
    args = parser.parse_args()
    
    assessment = CapacityAssessment()
    assessment.print_report(verbose=args.verbose)


if __name__ == '__main__':
    main()
