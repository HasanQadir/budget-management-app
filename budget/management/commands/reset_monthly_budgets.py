"""
Management command to reset monthly budgets for all brands.
"""
from typing import Any, Dict
from decimal import Decimal
from django.core.management.base import BaseCommand
from django.utils import timezone
from django.db import transaction

from budget.models import Brand


class Command(BaseCommand):
    """Command to reset monthly budgets for all brands."""
    
    help = 'Reset monthly budgets for all brands'
    
    def handle(self, *args: Any, **options: Any) -> None:
        """Execute the command."""
        self.stdout.write('Starting monthly budget reset...')
        
        try:
            with transaction.atomic():
                # Reset brand monthly budgets
                updated_brands = Brand.objects.update(
                    current_monthly_spend=Decimal('0.00'),
                    last_monthly_reset=timezone.now().date()
                )
                
                result = {
                    'timestamp': timezone.now().isoformat(),
                    'brands_updated': updated_brands,
                }
                
                self.stdout.write(
                    self.style.SUCCESS(
                        f'Successfully reset monthly budgets for {updated_brands} brands.'
                    )
                )
                self.stdout.write(f'Reset complete at {result["timestamp"]}')
                
        except Exception as e:
            self.stderr.write(
                self.style.ERROR(f'Error resetting monthly budgets: {str(e)}')
            )
            raise
