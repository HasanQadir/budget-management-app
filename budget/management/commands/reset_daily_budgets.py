"""
Management command to reset daily budgets for all brands and campaigns.
"""
from typing import Any, Dict
from decimal import Decimal
from django.core.management.base import BaseCommand
from django.utils import timezone
from django.db import transaction

from budget.models import Brand, Campaign


class Command(BaseCommand):
    """Command to reset daily budgets for all brands and campaigns."""
    
    help = 'Reset daily budgets for all brands and campaigns'
    
    def handle(self, *args: Any, **options: Any) -> None:
        """Execute the command."""
        self.stdout.write('Starting daily budget reset...')
        
        try:
            with transaction.atomic():
                # Reset brand daily budgets
                updated_brands = Brand.objects.update(
                    current_daily_spend=Decimal('0.00'),
                    last_daily_reset=timezone.now().date()
                )
                
                # Reset campaign daily budgets
                updated_campaigns = Campaign.objects.update(
                    current_daily_spend=Decimal('0.00'),
                    last_daily_reset=timezone.now().date()
                )
                
                result = {
                    'timestamp': timezone.now().isoformat(),
                    'brands_updated': updated_brands,
                    'campaigns_updated': updated_campaigns,
                }
                
                self.stdout.write(
                    self.style.SUCCESS(
                        f'Successfully reset daily budgets for {updated_brands} brands and {updated_campaigns} campaigns.'
                    )
                )
                self.stdout.write(f'Reset complete at {result["timestamp"]}')
                
        except Exception as e:
            self.stderr.write(
                self.style.ERROR(f'Error resetting daily budgets: {str(e)}')
            )
            raise
