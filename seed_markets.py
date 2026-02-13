import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'api.settings')
django.setup()

from markets.models import Market

def seed():
    markets = [
        {
            "question": "Will William Ruto be re-elected in 2027?",
            "category": "Politics",
            "yes_probability": 45,
            "volume": "$1.2M",
            "end_date": "Aug 2027",
            "image_url": "https://upload.wikimedia.org/wikipedia/commons/thumb/1/13/William_Ruto_2023.jpg/440px-William_Ruto_2023.jpg"
        },
        {
            "question": "Will the Central Bank of Kenya lower the base rate by June?",
            "category": "Economy",
            "yes_probability": 68,
            "volume": "$450K",
            "end_date": "Jun 30, 2026",
            "image_url": "https://upload.wikimedia.org/wikipedia/commons/thumb/c/c5/Central_Bank_of_Kenya_building.jpg/500px-Central_Bank_of_Kenya_building.jpg"
        },
        {
            "question": "Will Eliud Kipchoge win his next major marathon?",
            "category": "Sports",
            "yes_probability": 72,
            "volume": "$890K",
            "end_date": "Apr 15, 2026",
            "image_url": "https://upload.wikimedia.org/wikipedia/commons/thumb/9/9f/Eliud_Kipchoge_after_2018_Berlin_Marathon.jpg/440px-Eliud_Kipchoge_after_2018_Berlin_Marathon.jpg"
        },
        {
            "question": "Will Nairobi receive above-average rainfall in March 2026?",
            "category": "Environment",
            "yes_probability": 55,
            "volume": "$120K",
            "end_date": "Mar 31, 2026",
            "image_url": "https://images.unsplash.com/photo-1549417229-aa67d3263c09?q=80&w=1000&auto=format&fit=crop"
        },
        {
            "question": "Will Kenya launch its own Digital Currency (CBDC) by 2027?",
            "category": "Crypto",
            "yes_probability": 30,
            "volume": "$210K",
            "end_date": "Dec 31, 2026",
            "image_url": "https://images.unsplash.com/photo-1621761191319-c6fb62004040?q=80&w=1000&auto=format&fit=crop"
        }
    ]

    for m in markets:
        market, created = Market.objects.update_or_create(
            question=m['question'],
            defaults={
                'category': m['category'],
                'yes_probability': m['yes_probability'],
                'volume': m['volume'],
                'end_date': m['end_date'],
                'image_url': m['image_url'],
                'is_live': True
            }
        )
        if created:
            print(f"Created market: {market.question}")
        else:
            print(f"Updated market: {market.question}")

if __name__ == "__main__":
    seed()
