"""
Management command to initialize q_yes and q_no for existing markets.

This ensures all markets have LMSR parameters calculated from their yes_probability.
"""

from django.core.management.base import BaseCommand
from django.db import transaction
from markets.models import Market
from markets.bootstrap import bootstrap_market
import logging

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Initialize LMSR q_yes and q_no parameters for all markets'

    def add_arguments(self, parser):
        parser.add_argument(
            '--fix-all',
            action='store_true',
            help='Recalculate q values for ALL markets, even if already set'
        )
        parser.add_argument(
            '--market-id',
            type=int,
            help='Initialize specific market by ID'
        )

    def handle(self, *args, **options):
        fix_all = options.get('fix_all', False)
        market_id = options.get('market_id')

        if market_id:
            # Initialize single market
            self.initialize_market(market_id, force=fix_all)
        else:
            # Initialize all markets
            self.initialize_all_markets(force=fix_all)

    def initialize_market(self, market_id, force=False):
        """Initialize a single market"""
        try:
            market = Market.objects.get(id=market_id)
            
            # Skip if already initialized (unless force=True)
            if not force and market.q_yes != 0 and market.q_no != 0:
                self.stdout.write(
                    self.style.WARNING(
                        f"Market {market_id} ({market.question}) already has q values: "
                        f"q_yes={market.q_yes:.4f}, q_no={market.q_no:.4f}"
                    )
                )
                return
            
            # Calculate q values from yes_probability
            yes_prob_decimal = float(market.yes_probability) / 100.0
            b = float(market.b) if market.b else 100.0
            
            q_yes, q_no = bootstrap_market(yes_prob_decimal, b)
            
            market.q_yes = q_yes
            market.q_no = q_no
            market.save()
            
            self.stdout.write(
                self.style.SUCCESS(
                    f"✓ Market {market_id} ({market.question[:50]}): "
                    f"yes_prob={market.yes_probability}% → q_yes={q_yes:.4f}, q_no={q_no:.4f}"
                )
            )
            
        except Market.DoesNotExist:
            self.stdout.write(
                self.style.ERROR(f"Market {market_id} not found")
            )
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f"Error initializing market {market_id}: {str(e)}")
            )

    def initialize_all_markets(self, force=False):
        """Initialize all markets"""
        if force:
            markets = Market.objects.all()
            message = "Recalculating q values for all markets..."
        else:
            # Find markets with q values not set
            markets = Market.objects.filter(q_yes=0, q_no=0)
            message = f"Initializing q values for {markets.count()} markets without q parameters..."
        
        self.stdout.write(self.style.SUCCESS(message))
        
        if not markets.exists():
            self.stdout.write(self.style.WARNING("No markets to initialize"))
            return
        
        count = 0
        errors = 0
        
        with transaction.atomic():
            for market in markets:
                try:
                    # Calculate q values from yes_probability
                    yes_prob_decimal = float(market.yes_probability) / 100.0
                    b = float(market.b) if market.b else 100.0
                    
                    q_yes, q_no = bootstrap_market(yes_prob_decimal, b)
                    
                    market.q_yes = q_yes
                    market.q_no = q_no
                    market.save()
                    
                    self.stdout.write(
                        f"  {count + 1}. Market {market.id}: {market.question[:50]} "
                        f"(yes_prob={market.yes_probability}% → q_yes={q_yes:.4f})"
                    )
                    
                    count += 1
                    
                except Exception as e:
                    self.stdout.write(
                        self.style.ERROR(f"  ✗ Market {market.id}: {str(e)}")
                    )
                    errors += 1
        
        self.stdout.write(
            self.style.SUCCESS(
                f"\n✓ Successfully initialized {count} markets"
            )
        )
        
        if errors > 0:
            self.stdout.write(
                self.style.WARNING(f"⚠ {errors} markets had errors")
            )
