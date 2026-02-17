#!/usr/bin/env python
import os
import django
from datetime import datetime, timedelta

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'api.settings')
django.setup()

from markets.models import Market

def seed():
    markets = [
        # Politics - 12 markets
        {
            "question": "Will Raila Odinga run for president in 2027?",
            "category": "Politics",
            "yes_probability": 62,
            "volume": "KSh 2.1M",
            "end_date": "Dec 31, 2026",
            "image_url": "https://images.unsplash.com/photo-1552521881-721fb61d4b8f?q=80&w=1000&auto=format&fit=crop"
        },
        {
            "question": "Will Kenya pass a new climate law by 2027?",
            "category": "Politics",
            "yes_probability": 45,
            "volume": "KSh 890K",
            "end_date": "Jun 30, 2027",
            "image_url": "https://images.unsplash.com/photo-1552521881-721fb61d4b8f?q=80&w=1000&auto=format&fit=crop"
        },
        {
            "question": "Will Wajir County finish the water project by June 2026?",
            "category": "Politics",
            "yes_probability": 35,
            "volume": "KSh 420K",
            "end_date": "Jun 30, 2026",
            "image_url": "https://images.unsplash.com/photo-1552521881-721fb61d4b8f?q=80&w=1000&auto=format&fit=crop"
        },
        {
            "question": "Will Uhuru Kenyatta run for office in 2027?",
            "category": "Politics",
            "yes_probability": 28,
            "volume": "KSh 1.5M",
            "end_date": "Dec 31, 2026",
            "image_url": "https://images.unsplash.com/photo-1552521881-721fb61d4b8f?q=80&w=1000&auto=format&fit=crop"
        },
        {
            "question": "Will Kenya's parliament pass the proposed tax reform by March 2026?",
            "category": "Politics",
            "yes_probability": 72,
            "volume": "KSh 950K",
            "end_date": "Mar 31, 2026",
            "image_url": "https://images.unsplash.com/photo-1552521881-721fb61d4b8f?q=80&w=1000&auto=format&fit=crop"
        },
        {
            "question": "Will Nairobi become the African financial hub by 2027?",
            "category": "Politics",
            "yes_probability": 55,
            "volume": "KSh 2.3M",
            "end_date": "Dec 31, 2027",
            "image_url": "https://images.unsplash.com/photo-1552521881-721fb61d4b8f?q=80&w=1000&auto=format&fit=crop"
        },
        # Sports - 12 markets
        {
            "question": "Will Liverpool win the Premier League in 2025-26 season?",
            "category": "Sports",
            "yes_probability": 48,
            "volume": "KSh 3.2M",
            "end_date": "May 31, 2026",
            "image_url": "https://images.unsplash.com/photo-1461896836934-ffe607ba8211?q=80&w=1000&auto=format&fit=crop"
        },
        {
            "question": "Will Manchester City retain the Premier League title?",
            "category": "Sports",
            "yes_probability": 42,
            "volume": "KSh 2.8M",
            "end_date": "May 31, 2026",
            "image_url": "https://images.unsplash.com/photo-1461896836934-ffe607ba8211?q=80&w=1000&auto=format&fit=crop"
        },
        {
            "question": "Will Serena Williams make a tennis comeback in 2026?",
            "category": "Sports",
            "yes_probability": 22,
            "volume": "KSh 670K",
            "end_date": "Dec 31, 2026",
            "image_url": "https://images.unsplash.com/photo-1554285201-be3f0ecda5cb?q=80&w=1000&auto=format&fit=crop"
        },
        {
            "question": "Will Kenya win a medal at the 2026 FIFA World Cup?",
            "category": "Sports",
            "yes_probability": 8,
            "volume": "KSh 120K",
            "end_date": "Nov 30, 2026",
            "image_url": "https://images.unsplash.com/photo-1461896836934-ffe607ba8211?q=80&w=1000&auto=format&fit=crop"
        },
        {
            "question": "Will Novak Djokovic win a Grand Slam in 2026?",
            "category": "Sports",
            "yes_probability": 38,
            "volume": "KSh 1.4M",
            "end_date": "Dec 31, 2026",
            "image_url": "https://images.unsplash.com/photo-1554285201-be3f0ecda5cb?q=80&w=1000&auto=format&fit=crop"
        },
        {
            "question": "Will Cristiano Ronaldo score more than 40 goals in 2026?",
            "category": "Sports",
            "yes_probability": 65,
            "volume": "KSh 2.1M",
            "end_date": "Dec 31, 2026",
            "image_url": "https://images.unsplash.com/photo-1461896836934-ffe607ba8211?q=80&w=1000&auto=format&fit=crop"
        },
        # Economy - 12 markets
        {
            "question": "Will Bitcoin reach $100,000 by June 2026?",
            "category": "Crypto",
            "yes_probability": 58,
            "volume": "KSh 4.5M",
            "end_date": "Jun 30, 2026",
            "image_url": "https://images.unsplash.com/photo-1621761191319-c6fb62004040?q=80&w=1000&auto=format&fit=crop"
        },
        {
            "question": "Will Ethereum overtake Bitcoin in market cap by 2027?",
            "category": "Crypto",
            "yes_probability": 12,
            "volume": "KSh 890K",
            "end_date": "Dec 31, 2027",
            "image_url": "https://images.unsplash.com/photo-1621761191319-c6fb62004040?q=80&w=1000&auto=format&fit=crop"
        },
        {
            "question": "Will the Kenya shilling strengthen against the US dollar by 10%?",
            "category": "Economy",
            "yes_probability": 35,
            "volume": "KSh 2.1M",
            "end_date": "Dec 31, 2026",
            "image_url": "https://images.unsplash.com/photo-1460925895917-adf4e565db13?q=80&w=1000&auto=format&fit=crop"
        },
        {
            "question": "Will Kenya's GDP growth exceed 6% in 2026?",
            "category": "Economy",
            "yes_probability": 52,
            "volume": "KSh 1.8M",
            "end_date": "Dec 31, 2026",
            "image_url": "https://images.unsplash.com/photo-1460925895917-adf4e565db13?q=80&w=1000&auto=format&fit=crop"
        },
        {
            "question": "Will the NSE hit 25,000 points by 2027?",
            "category": "Economy",
            "yes_probability": 48,
            "volume": "KSh 2.4M",
            "end_date": "Dec 31, 2027",
            "image_url": "https://images.unsplash.com/photo-1460925895917-adf4e565db13?q=80&w=1000&auto=format&fit=crop"
        },
        {
            "question": "Will inflation in Kenya drop below 5% by June 2026?",
            "category": "Economy",
            "yes_probability": 68,
            "volume": "KSh 3.2M",
            "end_date": "Jun 30, 2026",
            "image_url": "https://images.unsplash.com/photo-1460925895917-adf4e565db13?q=80&w=1000&auto=format&fit=crop"
        },
        {
            "question": "Will Safaricom's share price double by 2027?",
            "category": "Economy",
            "yes_probability": 42,
            "volume": "KSh 1.6M",
            "end_date": "Dec 31, 2027",
            "image_url": "https://images.unsplash.com/photo-1460925895917-adf4e565db13?q=80&w=1000&auto=format&fit=crop"
        },
        # Environment - 10 markets
        {
            "question": "Will Kenya's forest cover increase by 5% by 2027?",
            "category": "Environment",
            "yes_probability": 45,
            "volume": "KSh 980K",
            "end_date": "Dec 31, 2027",
            "image_url": "https://images.unsplash.com/photo-1441974231531-c6227db76b6e?q=80&w=1000&auto=format&fit=crop"
        },
        {
            "question": "Will Lake Turkana water levels rise by 2m by 2026?",
            "category": "Environment",
            "yes_probability": 38,
            "volume": "KSh 550K",
            "end_date": "Dec 31, 2026",
            "image_url": "https://images.unsplash.com/photo-1441974231531-c6227db76b6e?q=80&w=1000&auto=format&fit=crop"
        },
        {
            "question": "Will Kenya eliminate single-use plastics by 2027?",
            "category": "Environment",
            "yes_probability": 55,
            "volume": "KSh 1.2M",
            "end_date": "Dec 31, 2027",
            "image_url": "https://images.unsplash.com/photo-1441974231531-c6227db76b6e?q=80&w=1000&auto=format&fit=crop"
        },
        {
            "question": "Will Kenya record below-average temperatures in 2026?",
            "category": "Environment",
            "yes_probability": 32,
            "volume": "KSh 420K",
            "end_date": "Dec 31, 2026",
            "image_url": "https://images.unsplash.com/photo-1441974231531-c6227db76b6e?q=80&w=1000&auto=format&fit=crop"
        },
        {
            "question": "Will Mombasa Port expansion be completed by 2027?",
            "category": "Environment",
            "yes_probability": 48,
            "volume": "KSh 1.9M",
            "end_date": "Dec 31, 2027",
            "image_url": "https://images.unsplash.com/photo-1441974231531-c6227db76b6e?q=80&w=1000&auto=format&fit=crop"
        },
        # Additional diverse markets
        {
            "question": "Will Tesla release a sub-$25,000 EV by 2026?",
            "category": "Crypto",
            "yes_probability": 72,
            "volume": "KSh 2.8M",
            "end_date": "Dec 31, 2026",
            "image_url": "https://images.unsplash.com/photo-1621761191319-c6fb62004040?q=80&w=1000&auto=format&fit=crop"
        },
        {
            "question": "Will Apple release an AR headset by 2026?",
            "category": "Crypto",
            "yes_probability": 68,
            "volume": "KSh 2.2M",
            "end_date": "Dec 31, 2026",
            "image_url": "https://images.unsplash.com/photo-1621761191319-c6fb62004040?q=80&w=1000&auto=format&fit=crop"
        },
        {
            "question": "Will OpenAI release GPT-5 before 2026?",
            "category": "Crypto",
            "yes_probability": 45,
            "volume": "KSh 1.8M",
            "end_date": "Dec 31, 2026",
            "image_url": "https://images.unsplash.com/photo-1621761191319-c6fb62004040?q=80&w=1000&auto=format&fit=crop"
        },
        {
            "question": "Will commercial space tourism become mainstream by 2027?",
            "category": "Politics",
            "yes_probability": 35,
            "volume": "KSh 1.1M",
            "end_date": "Dec 31, 2027",
            "image_url": "https://images.unsplash.com/photo-1552521881-721fb61d4b8f?q=80&w=1000&auto=format&fit=crop"
        },
        {
            "question": "Will Starlink provide internet to all of East Africa by 2027?",
            "category": "Politics",
            "yes_probability": 52,
            "volume": "KSh 2.5M",
            "end_date": "Dec 31, 2027",
            "image_url": "https://images.unsplash.com/photo-1552521881-721fb61d4b8f?q=80&w=1000&auto=format&fit=crop"
        },
        {
            "question": "Will a new pandemic emerge before 2027?",
            "category": "Environment",
            "yes_probability": 25,
            "volume": "KSh 890K",
            "end_date": "Dec 31, 2027",
            "image_url": "https://images.unsplash.com/photo-1441974231531-c6227db76b6e?q=80&w=1000&auto=format&fit=crop"
        },
    ]

    count = 0
    for m in markets:
        market, created = Market.objects.update_or_create(
            question=m['question'],
            defaults={
                'category': m['category'],
                'yes_probability': m['yes_probability'],
                'volume': m['volume'],
                'end_date': m['end_date'],
                'description': m.get('description', ''),
                'image_url': m['image_url'],
                'is_live': True
            }
        )
        if created:
            count += 1
            print(f"✅ Created: {market.question}")
        else:
            print(f"⏭️  Already exists: {market.question}")

    print(f"\n✨ Successfully added {count} new markets!")
    total = Market.objects.count()
    print(f"Total markets in database: {total}")

if __name__ == "__main__":
    seed()
