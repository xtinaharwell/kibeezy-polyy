#!/usr/bin/env python
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'api.settings')
django.setup()

from markets.models import Market

# Delete all markets
count, deleted_items = Market.objects.all().delete()
print(f"Deleted {deleted_items.get('markets.Market', 0)} markets from database")
