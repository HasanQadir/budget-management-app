"""
Management command to seed the database with sample data for testing.
"""
import random
from typing import Any, Dict, List, Tuple
from datetime import time, datetime, timedelta
from decimal import Decimal

from django.core.management.base import BaseCommand
from django.utils import timezone
from django.db import transaction

from budget.models import Brand, Campaign, DaypartingSchedule
from budget.models.campaign import CampaignStatus


class Command(BaseCommand):
    """Command to seed the database with sample data."""
    
    help = 'Seed the database with sample data for testing'
    
    def add_arguments(self, parser):
        """Add command line arguments."""
        parser.add_argument(
            '--clear',
            action='store_true',
            help='Clear existing data before seeding'
        )
        parser.add_argument(
            '--brands',
            type=int,
            default=3,
            help='Number of brands to create (default: 3)'
        )
        parser.add_argument(
            '--campaigns-per-brand',
            type=int,
            default=2,
            help='Number of campaigns to create per brand (default: 2)'
        )
    
    def handle(self, *args: Any, **options: Any) -> None:
        """Execute the command."""
        clear_existing = options['clear']
        num_brands = options['brands']
        campaigns_per_brand = options['campaigns_per_brand']
        
        self.stdout.write('Starting data seeding...')
        
        try:
            with transaction.atomic():
                # Clear existing data if requested
                if clear_existing:
                    self._clear_existing_data()
                
                # Create brands
                brands = self._create_brands(num_brands)
                
                # Create campaigns for each brand
                all_campaigns = []
                for brand in brands:
                    campaigns = self._create_campaigns(brand, campaigns_per_brand)
                    all_campaigns.extend(campaigns)
                
                # Create dayparting schedules for some campaigns
                self._create_dayparting_schedules(all_campaigns)
                
                self.stdout.write(
                    self.style.SUCCESS(
                        f'Successfully seeded database with {len(brands)} brands, '
                        f'{len(all_campaigns)} campaigns, and dayparting schedules.'
                    )
                )
                
                # Log success instead of returning a dictionary
                self.stdout.write(
                    self.style.SUCCESS(
                        f'Successfully seeded database with {len(brands)} brands, '
                        f'{len(all_campaigns)} campaigns, and dayparting schedules.\n'
                    )
                )
                return None
                
        except Exception as e:
            self.stderr.write(
                self.style.ERROR(f'Error seeding data: {str(e)}')
            )
            raise
    
    def _clear_existing_data(self) -> None:
        """Clear existing data from the database."""
        self.stdout.write('Clearing existing data...')
        
        # Delete in the correct order to avoid foreign key constraint violations
        DaypartingSchedule.objects.all().delete()
        Campaign.objects.all().delete()
        Brand.objects.all().delete()
        
        self.stdout.write(self.style.SUCCESS('Successfully cleared existing data.'))
    
    def _create_brands(self, count: int) -> List[Brand]:
        """Create sample brands."""
        self.stdout.write(f'Creating {count} brands...')
        
        brand_names = [
            'Acme Corp', 'Globex', 'Soylent', 'Initech', 'Umbrella',
            'Stark Industries', 'Wayne Enterprises', 'Cyberdyne',
            'Wonka Industries', 'Tyrell Corp'
        ]
        
        # Shuffle the brand names to get a random selection
        random.shuffle(brand_names)
        
        brands = []
        for i in range(min(count, len(brand_names))):
            daily_budget = Decimal(str(round(random.uniform(100, 1000), 2)))
            monthly_budget = daily_budget * 30  # Rough monthly estimate
            
            brand = Brand.objects.create(
                name=brand_names[i],
                daily_budget=daily_budget,
                monthly_budget=monthly_budget,
                current_daily_spend=Decimal('0.00'),
                current_monthly_spend=Decimal('0.00'),
                is_active=random.choice([True, True, True, False])  # 75% chance of being active
            )
            
            self.stdout.write(f"  - Created brand: {brand.name} (${daily_budget:.2f} daily budget)")
            brands.append(brand)
        
        return brands
    
    def _create_campaigns(self, brand: Brand, count: int) -> List[Campaign]:
        """Create sample campaigns for a brand."""
        self.stdout.write(f'Creating {count} campaigns for {brand.name}...')
        
        campaign_types = [
            'Search', 'Display', 'Video', 'Social', 'Native',
            'Retargeting', 'Prospecting', 'Awareness', 'Consideration', 'Conversion'
        ]
        
        campaigns = []
        for i in range(count):
            # Generate a campaign name based on brand and type
            campaign_type = random.choice(campaign_types)
            campaign_name = f"{brand.name.split()[0]} {campaign_type} Campaign {i+1}"
            
            # Set a daily budget (10-30% of brand's daily budget)
            brand_daily_budget = float(brand.daily_budget)
            min_budget = max(10.0, brand_daily_budget * 0.1)  # At least $10 or 10% of brand budget
            max_budget = brand_daily_budget * 0.3
            daily_budget = Decimal(str(round(random.uniform(min_budget, max_budget), 2)))
            
            campaign = Campaign.objects.create(
                name=campaign_name,
                brand=brand,
                daily_budget=daily_budget,
                current_daily_spend=Decimal('0.00'),
                status=random.choice([
                    CampaignStatus.ACTIVE,
                    CampaignStatus.PAUSED,
                    CampaignStatus.ACTIVE,
                    CampaignStatus.ACTIVE,  # Higher chance of being active
                    CampaignStatus.COMPLETED,
                ]),
                is_active=False,  # Will be set based on status and budget
                last_daily_reset=timezone.now().date()
            )
            
            # Update is_active based on status
            if campaign.status == CampaignStatus.ACTIVE:
                campaign.is_active = True
                campaign.save(update_fields=['is_active'])
            
            self.stdout.write(
                f"  - Created campaign: {campaign.name} (${daily_budget:.2f} daily budget) | "
                f"Status: {campaign.get_status_display()}"
            )
            
            campaigns.append(campaign)
        
        return campaigns
    
    def _create_dayparting_schedules(self, campaigns: List[Campaign]) -> None:
        """Create dayparting schedules for some campaigns."""
        self.stdout.write('Creating dayparting schedules...')
        
        # Only create schedules for some campaigns (about 60%)
        campaigns_with_schedules = random.sample(
            campaigns,
            k=int(len(campaigns) * 0.6)
        )
        
        # Common time slots
        time_slots = [
            # (start_hour, start_minute, end_hour, end_minute)
            (9, 0, 17, 0),   # Business hours
            (8, 0, 20, 0),   # Extended hours
            (0, 0, 23, 59),  # All day
            (12, 0, 15, 0),  # Lunch hours
            (18, 0, 23, 0),  # Evening hours
        ]
        
        for campaign in campaigns_with_schedules:
            # Determine how many days to schedule (1-7)
            num_days = random.randint(1, 7)
            days = random.sample(range(7), k=num_days)  # 0=Monday, 6=Sunday
            
            # Choose a time slot
            start_hour, start_minute, end_hour, end_minute = random.choice(time_slots)
            
            # Create a schedule for each selected day
            for day in days:
                DaypartingSchedule.objects.create(
                    campaign=campaign,
                    day_of_week=day,
                    start_time=time(hour=start_hour, minute=start_minute),
                    end_time=time(hour=end_hour, minute=end_minute),
                    timezone='UTC',
                    is_active=random.choice([True, True, False]),  # 2/3 chance of being active
                    priority=random.randint(1, 10)
                )
            
            self.stdout.write(
                f"  - Added {len(days)} day schedule(s) to {campaign.name} | "
                f"{time(hour=start_hour, minute=start_minute).strftime('%H:%M')} - "
                f"{time(hour=end_hour, minute=end_minute).strftime('%H:%M')} UTC"
            )
