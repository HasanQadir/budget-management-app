"""
Management command to check system health and status.
"""
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Tuple
from argparse import ArgumentParser

from django.core.management.base import BaseCommand
from django.utils import timezone
from django.db.models import Count, Sum, Q, F

from budget.models import Brand, SpendRecord, DaypartingSchedule
from budget.models.campaign import Campaign, CampaignStatus


class Command(BaseCommand):
    """Command to check system health and status."""
    
    help = 'Check system health and status'
    
    def add_arguments(self, parser: ArgumentParser) -> None:
        """Add command line arguments."""
        parser.add_argument(
            '--verbose',
            action='store_true',
            help='Show detailed information'
        )
    
    def handle(self, *args: Any, **options: Any) -> None:
        """Execute the command."""
        verbose = options['verbose']
        now = timezone.now()
        
        self.stdout.write(self.style.SUCCESS('=== System Status ==='))
        self.stdout.write(f'Current time: {now}')
        self.stdout.write('')
        
        try:
            # Get basic counts
            brand_count = Brand.objects.count()
            campaign_count = Campaign.objects.count()
            spend_record_count = SpendRecord.objects.count()
            schedule_count = DaypartingSchedule.objects.count()
            
            # Get active counts
            active_brands = Brand.objects.filter(is_active=True).count()
            active_campaigns = Campaign.objects.filter(
                is_active=True,
                status=CampaignStatus.ACTIVE
            ).count()
            
            # Get recent spend records
            last_hour = now - timedelta(hours=1)
            recent_spend = SpendRecord.objects.filter(
                timestamp__gte=last_hour
            ).aggregate(
                total_spend=Sum('amount'),
                record_count=Count('id')
            )
            
            # Get campaigns over budget
            over_budget = Campaign.objects.filter(
                current_daily_spend__gte=F('daily_budget'),
                is_active=True
            ).count()
            
            # Get campaigns with no dayparting schedules
            campaigns_without_schedules = Campaign.objects.annotate(
                schedule_count=Count('dayparting_schedules')
            ).filter(
                schedule_count=0,
                is_active=True
            ).count()
            
            # Display summary
            self.stdout.write(self.style.SUCCESS('=== Summary ==='))
            self.stdout.write(f'Brands: {brand_count} total, {active_brands} active')
            self.stdout.write(f'Campaigns: {campaign_count} total, {active_campaigns} active')
            self.stdout.write(f'Spend records: {spend_record_count}')
            self.stdout.write(f'Dayparting schedules: {schedule_count}')
            
            self.stdout.write('\n' + self.style.SUCCESS('=== Recent Activity ==='))
            self.stdout.write(
                f'Last hour: {recent_spend["record_count"] or 0} spend records | '
                f'${recent_spend["total_spend"] or 0:.2f} spent'
            )
            
            self.stdout.write('\n' + self.style.SUCCESS('=== Issues ==='))
            
            # Check for potential issues
            issues = []
            
            if over_budget > 0:
                issues.append((
                    'warning',
                    f'{over_budget} campaigns are over their daily budget but still active'
                ))
            
            if campaigns_without_schedules > 0:
                issues.append((
                    'info',
                    f'{campaigns_without_schedules} active campaigns have no dayparting schedules (will run 24/7)'
                ))
            
            # Check for brands over monthly budget
            brands_over_monthly = Brand.objects.filter(
                current_monthly_spend__gte=F('monthly_budget'),
                is_active=True
            ).count()
            
            if brands_over_monthly > 0:
                issues.append((
                    'warning',
                    f'{brands_over_monthly} brands have exceeded their monthly budget but are still active'
                ))
            
            # Check for outdated resets
            outdated_brands = Brand.objects.filter(
                last_daily_reset__lt=now.date() - timedelta(days=1)
            ).count()
            
            if outdated_brands > 0:
                issues.append((
                    'error',
                    f'{outdated_brands} brands have not had their daily spend reset in over 24 hours'
                ))
            
            # Display issues or all-clear message
            if not issues:
                self.stdout.write(self.style.SUCCESS('No issues detected. System is healthy!'))
            else:
                for level, message in issues:
                    if level == 'error':
                        self.stdout.write(self.style.ERROR(f'✗ {message}'))
                    elif level == 'warning':
                        self.stdout.write(self.style.WARNING(f'⚠ {message}'))
                    else:
                        self.stdout.write(self.style.NOTICE(f'ℹ {message}'))
            
            # Show detailed information if requested
            if verbose:
                self._show_detailed_information(now)
            
        except Exception as e:
            self.stderr.write(
                self.style.ERROR(f'Error checking system status: {str(e)}')
            )
            raise
    
    def _show_detailed_information(self, now: datetime) -> None:
        """Show detailed system information."""
        self.stdout.write('\n' + self.style.SUCCESS('=== Detailed Information ==='))
        
        # Show top spending brands
        top_brands = Brand.objects.order_by('-current_daily_spend')[:5]
        
        self.stdout.write('\n' + self.style.SUCCESS('Top Spending Brands (Today):'))
        for brand in top_brands:
            daily_usage = (
                (brand.current_daily_spend / brand.daily_budget * 100)
                if brand.daily_budget > 0
                else 0
            )
            self.stdout.write(
                f"- {brand.name}: ${brand.current_daily_spend:.2f} / "
                f"${brand.daily_budget:.2f} ({daily_usage:.1f}%)"
            )
        
        # Show campaigns with highest spend
        top_campaigns = Campaign.objects.select_related('brand').order_by(
            '-current_daily_spend'
        )[:5]
        
        self.stdout.write('\n' + self.style.SUCCESS('Top Spending Campaigns (Today):'))
        for campaign in top_campaigns:
            usage = (
                (campaign.current_daily_spend / campaign.daily_budget * 100)
                if campaign.daily_budget > 0
                else 0
            )
            self.stdout.write(
                f"- {campaign.brand.name} - {campaign.name}: "
                f"${campaign.current_daily_spend:.2f} / "
                f"${campaign.daily_budget:.2f} ({usage:.1f}%)"
            )
        
        # Show recent spend activity
        recent_spends = SpendRecord.objects.select_related(
            'brand', 'campaign'
        ).order_by('-timestamp')[:5]
        
        self.stdout.write('\n' + self.style.SUCCESS('Recent Spend Activity:'))
        for spend in recent_spends:
            campaign_name = spend.campaign.name if spend.campaign else 'N/A'
            self.stdout.write(
                f"- {spend.timestamp.strftime('%Y-%m-%d %H:%M:%S')}: "
                f"${spend.amount:.2f} | {spend.brand.name} - {campaign_name}"
            )
        
        # Check scheduled tasks
        self.stdout.write('\n' + self.style.SUCCESS('Next Scheduled Tasks:'))
        self.stdout.write("- Daily budget reset: Today at 00:00:00")
        
        # Calculate next monthly reset (first day of next month at 00:00:00)
        next_month = now.replace(day=1) + timedelta(days=32)
        next_month = next_month.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        self.stdout.write(f"- Monthly budget reset: {next_month.strftime('%Y-%m-%d %H:%M:%S')}")
        
        # Check database health
        self.stdout.write('\n' + self.style.SUCCESS('Database Health:'))
        try:
            # Simple query to check database responsiveness
            Brand.objects.first()
            self.stdout.write("- Connection: ✓ OK")
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"- Connection: ✗ Error: {str(e)}"))