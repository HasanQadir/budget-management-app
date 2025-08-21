"""Campaign model for the budget management system."""
from decimal import Decimal
from typing import Optional, TYPE_CHECKING, List, Dict, Any, Tuple
from datetime import datetime, date
from django.db import models
from django.db.models import CharField, ForeignKey, DecimalField, DateField, BooleanField, DateTimeField
from django.core.validators import MinValueValidator
from django.utils import timezone

if TYPE_CHECKING:
    from django.db.models.manager import Manager
    from .brand import Brand
    from .spend import SpendRecord
    from .schedule import DaypartingSchedule


class CampaignStatus(models.TextChoices):
    """Status choices for a campaign."""
    ACTIVE = 'active', 'Active'
    PAUSED = 'paused', 'Paused'
    COMPLETED = 'completed', 'Completed'
    ARCHIVED = 'archived', 'Archived'


class Campaign(models.Model):
    """
    Represents an advertising campaign for a brand.
    
    Campaigns can be active or paused based on budget limits and dayparting schedules.
    """
    name: CharField = models.CharField(
        max_length=255,
        help_text="Name of the campaign.",
    )
    
    brand: ForeignKey = models.ForeignKey(
        'budget.Brand',
        on_delete=models.CASCADE,
        related_name='campaigns',
        help_text="The brand that owns this campaign.",
    )
    
    status: CharField = models.CharField(
        max_length=20,
        choices=CampaignStatus.choices,
        default=CampaignStatus.ACTIVE,
        help_text="Current status of the campaign.",
    )
    
    daily_budget: DecimalField = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        validators=[MinValueValidator(Decimal('0.00'))],
        help_text="Maximum daily budget for this campaign in USD.",
    )
    
    current_daily_spend: DecimalField = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=Decimal('0.00'),
        help_text="Amount spent by this campaign today.",
    )
    
    last_daily_reset: DateField = models.DateField(
        default=timezone.now,
        help_text="When the daily spend was last reset.",
    )
    
    is_active: BooleanField = models.BooleanField(
        default=True,
        help_text="Whether the campaign is active and can accrue spend.",
    )
    
    created_at: DateTimeField = models.DateTimeField(auto_now_add=True)
    updated_at: DateTimeField = models.DateTimeField(auto_now=True)
    
    # Type hints for related managers
    spend_records: 'Manager[SpendRecord]'
    dayparting_schedules: 'Manager[DaypartingSchedule]'
    
    class Meta:
        """Meta options for the Campaign model."""
        ordering = ['brand__name', 'name']
        unique_together = ['brand', 'name']
        verbose_name = 'Campaign'
        verbose_name_plural = 'Campaigns'
    
    def __str__(self) -> str:
        """Return string representation of the campaign."""
        brand_name: str = self.brand.name  # Explicit type assertion
        return f"{brand_name} - {self.name}"
    
    def save(self, *args: Any, **kwargs: Any) -> None:
        """
        Override save to ensure proper state management.
        
        Rules:
        - ARCHIVED: Always inactive
        - COMPLETED: Always inactive
        - PAUSED: Always inactive
        - ACTIVE: Active only if should_be_active() is True
        """
        if self.status in [CampaignStatus.ARCHIVED, CampaignStatus.COMPLETED, CampaignStatus.PAUSED]:
            self.is_active = False
        elif self.status == CampaignStatus.ACTIVE:
            if not self.should_be_active() and self.is_active:
                self.is_active = False
        
        super().save(*args, **kwargs)
        
        if kwargs.get('update_fields') is None and self.pk:
            self.update_status_based_on_budget()
    
    def reset_daily_spend(self) -> None:
        """Reset the daily spend counter and update the last reset date."""
        self.current_daily_spend = Decimal('0.00')
        self.last_daily_reset = timezone.now().date()
        self.save(update_fields=['current_daily_spend', 'last_daily_reset'])
    
    def record_spend(self, amount: Decimal) -> None:
        """
        Record a spend against this campaign's budget.
        
        Args:
            amount: The amount to add to the current spend.
            
        Raises:
            ValueError: If the amount is negative or campaign is not active.
        """
        if not self.is_active:
            raise ValueError("Cannot record spend for inactive campaign.")
            
        if amount < 0:
            raise ValueError("Spend amount cannot be negative.")
            
        self.current_daily_spend += amount
        self.save(update_fields=['current_daily_spend'])
        
        self.brand.record_spend(amount)
    
    def has_daily_budget_available(self) -> bool:
        """Check if the campaign has daily budget available."""
        current_daily_spend: Decimal = self.current_daily_spend  # Explicit type assertion
        daily_budget: Decimal = self.daily_budget  # Explicit type assertion
        return current_daily_spend < daily_budget
    
    def get_remaining_daily_budget(self) -> Decimal:
        """Get the remaining daily budget."""
        current_daily_spend: Decimal = self.current_daily_spend  # Explicit type assertion
        daily_budget: Decimal = self.daily_budget  # Explicit type assertion
        remaining = daily_budget - current_daily_spend
        return max(Decimal('0.00'), remaining)
    
    def should_be_active(self) -> bool:
        """
        Determine if the campaign should be active based on:
        - Campaign status
        - Brand's budget status
        - Dayparting schedule
        """
        if not self.is_active or self.status != CampaignStatus.ACTIVE:
            return False
            
        if not self.brand.is_active or not self.brand.has_daily_budget_available():
            return False
            
        if not self.has_daily_budget_available():
            return False
            
        if self.dayparting_schedules.exists():
            now = timezone.now()
            current_weekday = now.weekday()
            current_time = now.time()
            
            return self.dayparting_schedules.filter(
                day_of_week=current_weekday,
                start_time__lte=current_time,
                end_time__gte=current_time,
                is_active=True
            ).exists()
            
        return True
    
    def update_status_based_on_budget(self) -> bool:
        """
        Update the campaign's active status based on budget and schedule.
        
        Returns:
            bool: True if status changed, False otherwise.
        """
        should_be_active = self.should_be_active()
        
        if self.is_active != should_be_active:
            self.is_active = should_be_active
            self.save(update_fields=['is_active'])
            return True
            
        return False