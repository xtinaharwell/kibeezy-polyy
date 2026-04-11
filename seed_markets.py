import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'api.settings')
django.setup()

from markets.models import Market

def seed():
    markets = [
        {
            "question": "Chelsea vs Manchester City - Premier League",
            "category": "Sports",
            "market_type": "OPTION_LIST",
            "volume": "KES 0",
            "end_date": "Apr 12, 2026, 4:30pm",
            "description": "Premier League match: Chelsea vs Manchester City at Stamford Bridge. Kickoff: 4:30pm GMT, Sunday 12th April 2026.",
            "image_url": "https://images.unsplash.com/photo-1461896836934-ffe607ba8211?q=80&w=1000&auto=format&fit=crop",
            "options": [
                {"label": "Chelsea Win", "yes_probability": 35},
                {"label": "Draw", "yes_probability": 30},
                {"label": "Manchester City Win", "yes_probability": 35}
            ]
        }
    ]

    for m in markets:
        question = m['question']
        market_type = m.get('market_type', 'BINARY')
        
        if market_type == 'OPTION_LIST':
            # For OPTION_LIST markets, format options properly
            options_data = []
            for idx, opt in enumerate(m.get('options', [])):
                options_data.append({
                    'id': idx + 1,
                    'label': opt['label'],
                    'yes_probability': opt['yes_probability'],
                    'no_probability': 100 - opt['yes_probability']
                })
            market, created = Market.objects.update_or_create(
                question=question,
                defaults={
                    'category': m['category'],
                    'yes_probability': 50,  # Not used for OPTION_LIST
                    'volume': m['volume'],
                    'end_date': m['end_date'],
                    'description': m.get('description', ''),
                    'image_url': m['image_url'],
                    'market_type': 'OPTION_LIST',
                    'options': options_data,
                    'is_live': True
                }
            )
        else:
            # For BINARY markets
            market, created = Market.objects.update_or_create(
                question=question,
                defaults={
                    'category': m['category'],
                    'yes_probability': m['yes_probability'],
                    'volume': m['volume'],
                    'end_date': m['end_date'],
                    'description': m.get('description', ''),
                    'image_url': m['image_url'],
                    'market_type': 'BINARY',
                    'is_live': True
                }
            )
        
        if created:
            print(f"Created market: {market.question}")
        else:
            print(f"Updated market: {market.question}")

if __name__ == "__main__":
    seed()
