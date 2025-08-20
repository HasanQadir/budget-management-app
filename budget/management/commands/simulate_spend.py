"""
Management command to simulate spending for testing purposes.
"""
import random
import uuid
from typing import Any, Dict, List, Optional, Tuple
from decimal import Decimal
from datetime import timedelta

from django.core.management.base import BaseCommand
from django.utils import timezone
from django.db import transaction

from budget.models import Brand, SpendRecord
from budget.models.campaign import Campaign, CampaignStatus


class Command(BaseCommand):
    """Command to simulate spending for testing purposes."""
    
    help = 'Simulate spending for testing budget tracking and campaign pausing'
    
    def add_arguments(self, parser):
        """Add command line arguments."""
        parser.add_argument(
            '--brand',
            type=str,
            help='Filter by brand name (case-insensitive)'
        )
        parser.add_argument(
            '--campaign',
            type=str,
            help='Filter by campaign name (case-insensitive)'
        )
        parser.add_argument(
            '--amount',
            type=float,
            default=10.0,
            help='Amount to spend per transaction (default: 10.0)'
        )
        parser.add_argument(
            '--transactions',
            type=int,
            default=5,
            help='Number of transactions to simulate (default: 5)'
        )
        parser.add_argument(
            '--randomize',
            action='store_true',
            help='Randomize spend amounts between 1 and --amount'
        )
        parser.add_argument(
            '--backdate',
            type=int,
            default=0,
            help='Backdate transactions by this many days (default: 0)'
        )
    
    def handle(self, *args: Any, **options: Any) -> None:
        """Execute the command."""
        brand_filter = options.get('brand')
        campaign_filter = options.get('campaign')
        amount = Decimal(str(options['amount']))
        num_transactions = options['transactions']
        randomize = options['randomize']
        backdate_days = options['backdate']
        
        self.stdout.write('Starting spend simulation...\n')
        
        try:
            # Get the base queryset
            campaigns = Campaign.objects.select_related('brand').filter(
                is_active=True,
                status=CampaignStatus.ACTIVE
            )
            
            # Apply filters
            if brand_filter:
                campaigns = campaigns.filter(brand__name__icontains=brand_filter)
            
            if campaign_filter:
                campaigns = campaigns.filter(name__icontains=campaign_filter)
            
            if not campaigns.exists():
                self.stdout.write(self.style.ERROR('No matching active campaigns found.'))
                return
            
            # Group campaigns by brand for display
            campaigns_by_brand: Dict[str, List[Campaign]] = {}
            for campaign in campaigns:
                if campaign.brand.name not in campaigns_by_brand:
                    campaigns_by_brand[campaign.brand.name] = []
                campaigns_by_brand[campaign.brand.name].append(campaign)
            
            # Display the campaigns that will be used
            self.stdout.write(self.style.SUCCESS('Found the following campaigns:'))
            for brand_name, brand_campaigns in campaigns_by_brand.items():
                self.stdout.write(f"\n{brand_name}:")
                for campaign in brand_campaigns:
                    self.stdout.write(
                        f"  - {campaign.name} (${campaign.daily_budget:.2f} daily budget | "
                        f"${campaign.current_daily_spend:.2f} spent today | "
                        f"${campaign.get_remaining_daily_budget():.2f} remaining)"
                    )
            
            # Confirm before proceeding
            if not self._confirm_proceed():
                self.stdout.write(self.style.WARNING('Simulation cancelled.'))
                return
            
            # Simulate the transactions
            results = []
            
            with transaction.atomic():
                for i in range(num_transactions):
                    # Select a random campaign
                    campaign = random.choice(campaigns)
                    
                    # Determine the spend amount
                    if randomize:
                        spend_amount = Decimal(str(round(random.uniform(0.1, float(amount)), 2)))
                    else:
                        spend_amount = amount
                    
                    # Create a timestamp (optionally backdated)
                    timestamp = timezone.now() - timedelta(days=backdate_days)
                    
                    # Create the spend record
                    spend_record = SpendRecord.objects.create(
                        brand=campaign.brand,
                        campaign=campaign,
                        amount=spend_amount,
                        reference_id=f'sim-{uuid.uuid4().hex[:8]}',
                        timestamp=timestamp,
                        metadata={
                            'simulation': True,
                            'transaction_num': i + 1,
                            'total_transactions': num_transactions,
                        }
                    )
                    
                    # Update the campaign's current spend
                    campaign.current_daily_spend += spend_amount
                    campaign.save(update_fields=['current_daily_spend'])
                    
                    # Update the brand's current spend
                    campaign.brand.current_daily_spend += spend_amount
                    campaign.brand.current_monthly_spend += spend_amount
                    campaign.brand.save(
                        update_fields=['current_daily_spend', 'current_monthly_spend']
                    )
                    
                    # Check if campaign is now over budget
                    was_active = campaign.is_active
                    campaign.update_status_based_on_budget()
                    
                    results.append({
                        'transaction': i + 1,
                        'campaign': campaign.name,
                        'brand': campaign.brand.name,
                        'amount': spend_amount,
                        'timestamp': timestamp,
                        'campaign_status': 'active' if campaign.is_active else 'paused',
                        'status_changed': was_active != campaign.is_active,
                        'remaining_budget': campaign.get_remaining_daily_budget(),
                    })
            
            # Display results
            self.stdout.write('\n' + self.style.SUCCESS('=== Simulation Results ==='))
            
            for result in results:
                status = (
                    self.style.SUCCESS('ACTIVE' if result['campaign_status'] == 'active' else 'PAUSED')
                )
                
                if result['status_changed']:
                    status = f"{status} {self.style.WARNING('(STATUS CHANGED)')}"
                
                self.stdout.write(
                    f"#{result['transaction']}: {result['brand']} - {result['campaign']} | "
                    f"${result['amount']:.2f} | Remaining: ${result['remaining_budget']:.2f} | {status}"
                )
            
            # Show summary
            total_spent = sum(float(r['amount']) for r in results)
            status_changes = sum(1 for r in results if r['status_changed'])
            
            self.stdout.write('\n' + self.style.SUCCESS('=== Summary ==='))
            self.stdout.write(f'Total transactions: {len(results)}')
            self.stdout.write(f'Total spent: ${total_spent:.2f}')
            self.stdout.write(f'Campaign status changes: {status_changes}')
            
            return {
                'timestamp': timezone.now().isoformat(),
                'total_transactions': len(results),
                'total_spent': str(total_spent),
                'status_changes': status_changes,
                'results': results,
            }
            
        except Exception as e:
            self.stderr.write(
                self.style.ERROR(f'Error during spend simulation: {str(e)}')
            )
            raise
    
    def _confirm_proceed(self) -> bool:
        """Ask for user confirmation before proceeding."""
        self.stdout.write('\n' + self.style.WARNING('This will create spend records and update budgets.'))
        response = input('Do you want to continue? [y/N] ').strip().lower()
        return response == 'y'
