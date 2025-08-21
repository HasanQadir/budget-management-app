"""
Management command to check and log the current status of campaigns.
"""
from typing import Any, Dict, List, Optional
from argparse import ArgumentParser
from django.core.management.base import BaseCommand
from django.utils import timezone
from django.db.models import Q, F

from budget.models import Campaign, Brand


class Command(BaseCommand):
    """Command to check and log the current status of campaigns."""
    
    help = 'Check and log the current status of campaigns'
    
    def add_arguments(self, parser: ArgumentParser) -> None:
        """Add command line arguments."""
        parser.add_argument(
            '--brand',
            type=str,
            help='Filter by brand name (case-insensitive)'
        )
        parser.add_argument(
            '--status',
            type=str,
            choices=['active', 'paused', 'over_budget', 'inactive_schedule'],
            help='Filter by status'
        )
        parser.add_argument(
            '--limit',
            type=int,
            default=50,
            help='Maximum number of campaigns to display (default: 50)'
        )
    
    def handle(self, *args: Any, **options: Any) -> None:
        """Execute the command."""
        brand_filter = options.get('brand')
        status_filter = options.get('status')
        limit = options['limit']
        
        self.stdout.write('Checking campaign statuses...\n')
        
        try:
            # Build the base queryset
            queryset = Campaign.objects.select_related('brand').order_by('brand__name', 'name')
            
            # Apply filters
            if brand_filter:
                queryset = queryset.filter(brand__name__icontains=brand_filter)
            
            if status_filter == 'active':
                queryset = queryset.filter(is_active=True)
            elif status_filter == 'paused':
                queryset = queryset.filter(is_active=False)
            elif status_filter == 'over_budget':
                queryset = queryset.filter(current_daily_spend__gte=F('daily_budget'))
            elif status_filter == 'inactive_schedule':
                # This is a simplified check - in a real implementation, you'd check dayparting schedules
                queryset = queryset.filter(is_active=False)
            
            # Get the campaigns
            campaigns = list(queryset[:limit])
            
            if not campaigns:
                self.stdout.write(self.style.WARNING('No campaigns found matching the criteria.'))
                return
            
            # Calculate summary statistics
            total_campaigns = len(campaigns)
            active_campaigns = sum(1 for c in campaigns if c.status == 'active')
            paused_campaigns = sum(1 for c in campaigns if c.status == 'paused')
            completed_campaigns = sum(1 for c in campaigns if c.status == 'completed')
            
            over_budget = sum(1 for c in campaigns if c.current_daily_spend >= c.daily_budget)
            
            # Display summary
            self.stdout.write(self.style.SUCCESS('=== Campaign Status Summary ==='))
            self.stdout.write(f'Total campaigns: {total_campaigns}')
            self.stdout.write(f'Active: {active_campaigns}')
            self.stdout.write(f'Paused: {paused_campaigns}')
            self.stdout.write(f'Completed: {completed_campaigns}')
            self.stdout.write(f'Over daily budget: {over_budget}')
            self.stdout.write('\n=== Campaign Details ===\n')
            
            # Display details for each campaign
            for campaign in campaigns:
                if campaign.status == 'active':
                    status = self.style.SUCCESS('ACTIVE')
                elif campaign.status == 'completed':
                    status = self.style.NOTICE('COMPLETED')
                else:  # paused or any other status
                    status = self.style.ERROR('PAUSED')
                budget_used = (campaign.current_daily_spend / campaign.daily_budget * 100) if campaign.daily_budget > 0 else 0
                
                # Color code the budget usage
                if budget_used >= 90:
                    budget_str = self.style.ERROR(f'{budget_used:.1f}%')
                elif budget_used >= 75:
                    budget_str = self.style.WARNING(f'{budget_used:.1f}%')
                else:
                    budget_str = self.style.SUCCESS(f'{budget_used:.1f}%')
                
                self.stdout.write(
                    f"{status} | {campaign.brand.name} - {campaign.name}"
                )
                self.stdout.write(
                    f"  Budget: ${campaign.daily_budget:.2f} | "
                    f"Spent: ${campaign.current_daily_spend:.2f} | "
                    f"Remaining: ${campaign.get_remaining_daily_budget():.2f} ({budget_str})"
                )
                
                # Check dayparting status if applicable
                if hasattr(campaign, 'dayparting_schedules'):
                    schedules = campaign.dayparting_schedules.filter(is_active=True)
                    if schedules.exists():
                        day_of_week_display = {
                            0: "Monday",
                            1: "Tuesday",
                            2: "Wednesday",
                            3: "Thursday",
                            4: "Friday",
                            5: "Saturday",
                            6: "Sunday"
                        }
                        schedule_days = [day_of_week_display.get(s.day_of_week, str(s.day_of_week)) for s in schedules]
                        self.stdout.write(
                            f"  Scheduled: {', '.join(schedule_days)} | "
                            f"{schedules[0].start_time} - {schedules[0].end_time} {schedules[0].timezone}"
                        )
                
                self.stdout.write('')
            
            # If we limited the results, show a note
            if len(campaigns) < queryset.count():
                self.stdout.write(
                    self.style.WARNING(
                        f'\nShowing {len(campaigns)} of {queryset.count()} campaigns. '
                        'Use --limit to show more.'
                    )
                )
            
        except Exception as e:
            self.stderr.write(
                self.style.ERROR(f'Error checking campaign statuses: {str(e)}')
            )
            raise