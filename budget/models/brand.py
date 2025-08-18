"""Brand model for the budget management system."""
from decimal import Decimal
from typing import Optional, TYPE_CHECKING
from django.db import models
from django.core.validators import MinValueValidator
from django.utils import timezone

if TYPE_CHECKING:
    from django.db.models.manager import RelatedManager
    from .campaign import Campaign
    from .spend import SpendRecord


class Brand(models.Model):
    """
    Represents a brand that runs advertising campaigns.
    
    Each brand has daily and monthly budget limits that control
    how much can be spent on advertising.
    """
    name = models.CharField(
        max_length=255,
        help_text="Name of the brand.",
        unique=True,
    )
    
    daily_budget = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        validators=[MinValueValidator(Decimal('0.00'))],
        help_text="Maximum daily budget in USD.",
    )
    
    monthly_budget = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        validators=[MinValueValidator(Decimal('0.00'))],
        help_text="Maximum monthly budget in USD.",
    )
    
    current_daily_spend = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=Decimal('0.00'),
        help_text="Amount spent today.",
    )
    
    current_monthly_spend = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=Decimal('0.00'),
        help_text="Amount spent this month.",
    )
    
    last_daily_reset = models.DateField(
        default=timezone.now,
        help_text="When the daily spend was last reset.",
    )
    
    last_monthly_reset = models.DateField(
        default=timezone.now,
        help_text="When the monthly spend was last reset.",
    )
    
    is_active = models.BooleanField(
        default=True,
        help_text="Whether the brand is active and can run campaigns.",
    )
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    # Type hints for related managers
    campaigns: 'RelatedManager[Campaign]'
    spend_records: 'RelatedManager[SpendRecord]'
    
    class Meta:
        """Meta options for the Brand model."""
        ordering = ['name']
        verbose_name = 'Brand'
        verbose_name_plural = 'Brands'
    
    def __str__(self) -> str:
        """Return string representation of the brand."""
        return self.name
    
    def reset_daily_spend(self) -> None:
        """Reset the daily spend counter and update the last reset date."""
        self.current_daily_spend = Decimal('0.00')
        self.last_daily_reset = timezone.now().date()
        self.save(update_fields=['current_daily_spend', 'last_daily_reset'])
    
    def reset_monthly_spend(self) -> None:
        """Reset the monthly spend counter and update the last reset date."""
        self.current_monthly_spend = Decimal('0.00')
        self.last_monthly_reset = timezone.now().date()
        self.save(update_fields=['current_monthly_spend', 'last_monthly_reset'])
    
    def record_spend(self, amount: Decimal) -> None:
        """
        Record a spend against this brand's budget.
        
        Args:
            amount: The amount to add to the current spend.
            
        Raises:
            ValueError: If the amount is negative.
        """
        if amount < 0:
            raise ValueError("Spend amount cannot be negative.")
            
        self.current_daily_spend += amount
        self.current_monthly_spend += amount
        
        # Use update_fields to avoid race conditions
        self.save(update_fields=['current_daily_spend', 'current_monthly_spend'])
    
    def has_daily_budget_available(self) -> bool:
        """Check if the brand has daily budget available."""
        return self.current_daily_spend < self.daily_budget
    
    def has_monthly_budget_available(self) -> bool:
        """Check if the brand has monthly budget available."""
        return self.current_monthly_spend < self.monthly_budget
    
    def get_remaining_daily_budget(self) -> Decimal:
        """Get the remaining daily budget."""
        remaining = self.daily_budget - self.current_daily_spend
        return max(Decimal('0.00'), remaining)
    
    def get_remaining_monthly_budget(self) -> Decimal:
        """Get the remaining monthly budget."""
        remaining = self.monthly_budget - self.current_monthly_spend
        return max(Decimal('0.00'), remaining)
