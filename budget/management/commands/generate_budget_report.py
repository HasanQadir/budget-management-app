"""
Management command to generate budget performance reports.
"""
from datetime import datetime, timedelta, time, date
from typing import Any, Dict, List, Tuple
from argparse import ArgumentParser

from django.core.management.base import BaseCommand
from django.utils import timezone
from django.db.models import Count, Sum, F, Q

from budget.models import Brand, Campaign, SpendRecord


class Command(BaseCommand):
    """Command to generate budget performance reports."""
    
    help = 'Generate budget performance reports'
    
    def add_arguments(self, parser: ArgumentParser) -> None:
        """Add command line arguments."""
        parser.add_argument(
            '--period',
            type=str,
            default='today',
            choices=['today', 'yesterday', 'this_week', 'last_week', 'this_month', 'last_month'],
            help='Time period for the report'
        )
    
    def handle(self, *args: Any, **options: Any) -> None:
        """Execute the command."""
        period = options['period']
        start_date, end_date = self._get_date_range(period)
        
        self.stdout.write(self.style.SUCCESS(
            f'Budget Report: {start_date} to {end_date}\n'
        ))
        
        try:
            # Generate report data
            report_data = self._generate_report_data(start_date, end_date)
            
            # Print the report
            self._print_report(report_data)
            
        except Exception as e:
            self.stderr.write(self.style.ERROR(f'Error generating report: {str(e)}'))
    
    def _get_date_range(self, period: str) -> Tuple[date, date]:
        """Get start and end dates based on period."""
        today = timezone.now().date()
        
        if period == 'today':
            return today, today
        elif period == 'yesterday':
            yesterday = today - timedelta(days=1)
            return yesterday, yesterday
        elif period == 'this_week':
            # Monday to Sunday
            start = today - timedelta(days=today.weekday())
            return start, today
        elif period == 'last_week':
            end = today - timedelta(days=today.weekday() + 1)  # Last Sunday
            start = end - timedelta(days=6)  # Previous Monday
            return start, end
        elif period == 'this_month':
            start = today.replace(day=1)
            return start, today
        elif period == 'last_month':
            end = today.replace(day=1) - timedelta(days=1)  # Last day of last month
            start = end.replace(day=1)  # First day of last month
            return start, end
        
        return today, today
    
    def _generate_report_data(
        self,
        start_date: date,
        end_date: date
    ) -> Dict[str, Any]:
        """Generate the report data."""
        start_datetime = timezone.make_aware(datetime.combine(start_date, time.min))
        end_datetime = timezone.make_aware(datetime.combine(end_date, time.max))
        
        # Get spend summary by brand
        brand_summary = self._get_brand_summary(start_datetime, end_datetime)
        
        # Get top performing campaigns
        top_campaigns = self._get_top_campaigns(start_datetime, end_datetime)
        
        return {
            'period': {'start': start_date, 'end': end_date},
            'brand_summary': brand_summary,
            'top_campaigns': top_campaigns,
            'generated_at': timezone.now()
        }
    
    def _get_brand_summary(
        self,
        start_datetime: datetime,
        end_datetime: datetime
    ) -> List[Dict[str, Any]]:
        """Get spend summary by brand."""
        spend_by_brand = SpendRecord.objects.filter(
            timestamp__range=(start_datetime, end_datetime),
            brand__isnull=False
        ).values('brand__name').annotate(
            total_spend=Sum('amount'),
            campaign_count=Count('campaign', distinct=True)
        ).order_by('-total_spend')
        
        return list(spend_by_brand)
    
    def _get_top_campaigns(
        self,
        start_datetime: datetime,
        end_datetime: datetime,
        limit: int = 5
    ) -> List[Dict[str, Any]]:
        """Get top performing campaigns by spend."""
        return list(SpendRecord.objects.filter(
            timestamp__range=(start_datetime, end_datetime),
            campaign__isnull=False
        ).values('campaign__name', 'brand__name').annotate(
            total_spend=Sum('amount')
        ).order_by('-total_spend')[:limit])
    
    def _print_report(self, report_data: Dict[str, Any]) -> None:
        """Print the report to console."""
        # Header
        self.stdout.write(self.style.SUCCESS(
            f"=== Budget Report ===\n"
            f"Period: {report_data['period']['start']} to {report_data['period']['end']}\n"
            f"Generated: {report_data['generated_at']}\n"
        ))
        
        # Brand Summary
        self.stdout.write(self.style.SUCCESS("Brand Summary:"))
        for brand in report_data['brand_summary']:
            self.stdout.write(
                f"- {brand['brand__name']}: "
                f"${brand['total_spend']:.2f} across {brand['campaign_count']} campaigns"
            )
        
        # Top Campaigns
        self.stdout.write("\n" + self.style.SUCCESS("Top Performing Campaigns:"))
        for i, campaign in enumerate(report_data['top_campaigns'], 1):
            self.stdout.write(
                f"{i}. {campaign['brand__name']} - {campaign['campaign__name']}: "
                f"${campaign['total_spend']:.2f}"
            )
        
        self.stdout.write("\n" + "=" * 40)