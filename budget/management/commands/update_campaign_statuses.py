""
Management command to update campaign statuses based on budgets and schedules.
"""
from typing import Any, Dict, List
from django.core.management.base import BaseCommand
from django.utils import timezone
from django.db import transaction

from budget.models import Campaign


class Command(BaseCommand):
    ""Command to update campaign statuses based on budgets and schedules."""
    
    help = 'Update campaign statuses based on budgets and dayparting schedules'
    
    def add_arguments(self, parser):
        ""Add command line arguments."""
        parser.add_argument(
            '--campaign-ids',
            nargs='+',
            type=int,
            help='Specific campaign IDs to update (default: all campaigns)'
        )
        parser.add_argument(
            '--force',
            action='store_true',
            help='Force update even if no changes are detected'
        )
    
    def handle(self, *args: Any, **options: Any) -> None:
        ""Execute the command."""
        campaign_ids = options.get('campaign_ids')
        force = options.get('force', False)
        
        self.stdout.write('Starting campaign status update...')
        
        try:
            # Get the queryset based on provided campaign IDs
            queryset = Campaign.objects.all()
            if campaign_ids:
                queryset = queryset.filter(id__in=campaign_ids)
            
            updated_campaigns: List[Dict[str, Any]] = []
            
            with transaction.atomic():
                for campaign in queryset.select_related('brand'):
                    old_status = campaign.is_active
                    
                    # Update status based on budget and schedule
                    status_changed = campaign.update_status_based_on_budget()
                    
                    # If status changed or force is True, add to results
                    if status_changed or force:
                        new_status = campaign.is_active
                        
                        # Get the current status string
                        if status_changed:
                            status_str = 'activated' if new_status else 'paused'
                            status_change = f"{old_status} -> {new_status}"
                        else:
                            status_str = 'active' if new_status else 'paused'
                            status_change = f"{status_str} (no change)"
                        
                        updated_campaigns.append({
                            'id': campaign.id,
                            'name': campaign.name,
                            'brand': campaign.brand.name,
                            'status_change': status_change,
                            'daily_budget': str(campaign.daily_budget),
                            'current_spend': str(campaign.current_daily_spend),
                            'remaining_budget': str(campaign.get_remaining_daily_budget()),
                        })
            
            # Output results
            if updated_campaigns:
                self.stdout.write(self.style.SUCCESS('Updated the following campaigns:'))
                for campaign in updated_campaigns:
                    self.stdout.write(
                        f"- {campaign['name']} (ID: {campaign['id']}, "
                        f"Brand: {campaign['brand']}): {campaign['status_change']} | "
                        f"Budget: ${campaign['daily_budget']} | "
                        f"Spent: ${campaign['current_spend']} | "
                        f"Remaining: ${campaign['remaining_budget']}"
                    )
            else:
                self.stdout.write(self.style.WARNING('No campaigns were updated.'))
            
            return {
                'timestamp': timezone.now().isoformat(),
                'campaigns_updated': len(updated_campaigns),
                'updated_campaigns': updated_campaigns,
            }
            
        except Exception as e:
            self.stderr.write(
                self.style.ERROR(f'Error updating campaign statuses: {str(e)}')
            )
            raise
