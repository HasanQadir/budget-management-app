""SpendRecord model for tracking advertising spend."""
from decimal import Decimal
from typing import Optional, TYPE_CHECKING
from django.db import models
from django.core.validators import MinValueValidator
from django.utils import timezone

if TYPE_CHECKING:
    from .brand import Brand
    from .campaign import Campaign


class SpendRecord(models.Model):
    ""
    Tracks individual spend events for campaigns and brands.
    
    Each record represents a single spend event with an amount and timestamp.
    """
    brand = models.ForeignKey(
        'brand.Brand',
        on_delete=models.CASCADE,
        related_name='spend_records',
        help_text="The brand associated with this spend record.",
    )
    
    campaign = models.ForeignKey(
        'campaign.Campaign',
        on_delete=models.CASCADE,
        related_name='spend_records',
        help_text="The campaign associated with this spend record.",
        null=True,
        blank=True,
    )
    
    amount = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        validators=[MinValueValidator(Decimal('0.01'))],
        help_text="Amount spent in USD.",
    )
    
    timestamp = models.DateTimeField(
        default=timezone.now,
        help_text="When the spend occurred.",
    )
    
    reference_id = models.CharField(
        max_length=255,
        unique=True,
        help_text="External reference ID for this spend record.",
    )
    
    metadata = models.JSONField(
        default=dict,
        blank=True,
        help_text="Additional metadata about the spend record.",
    )
    
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        """Meta options for the SpendRecord model."""
        ordering = ['-timestamp']
        indexes = [
            models.Index(fields=['brand', 'timestamp']),
            models.Index(fields=['campaign', 'timestamp']),
            models.Index(fields=['reference_id']),
            models.Index(fields=['timestamp']),
        ]
        verbose_name = 'Spend Record'
        verbose_name_plural = 'Spend Records'
    
    def __str__(self) -> str:
        """Return string representation of the spend record."""
        campaign_name = self.campaign.name if self.campaign else 'No Campaign'
        return f"{self.amount} USD - {campaign_name} - {self.timestamp}"
    
    def save(self, *args: Any, **kwargs: Any) -> None:
        ""
        Override save to update related campaign and brand spend.
        
        Args:
            *args: Variable length argument list.
            **kwargs: Arbitrary keyword arguments.
            
        Raises:
            ValueError: If the spend record is invalid.
        """
        is_new = self._state.adding
        
        if is_new:
            # Validate that the campaign belongs to the brand
            if self.campaign and self.campaign.brand != self.brand:
                raise ValueError("Campaign does not belong to the specified brand.")
            
            # Record spend on the campaign and brand
            if self.campaign:
                self.campaign.record_spend(self.amount)
            else:
                self.brand.record_spend(self.amount)
        
        super().save(*args, **kwargs)
    
    @classmethod
    def get_daily_spend(cls, brand: 'Brand', date: Optional[date] = None) -> Decimal:
        ""
        Get total spend for a brand on a specific day.
        
        Args:
            brand: The brand to get spend for.
            date: The date to get spend for. Defaults to today.
            
        Returns:
            Decimal: Total spend for the day.
        """
        if date is None:
            date = timezone.now().date()
            
        start = timezone.make_aware(datetime.combine(date, time.min))
        end = timezone.make_aware(datetime.combine(date, time.max))
        
        total = cls.objects.filter(
            brand=brand,
            timestamp__range=(start, end)
        ).aggregate(total=models.Sum('amount'))['total'] or Decimal('0.00')
        
        return total
    
    @classmethod
    def get_monthly_spend(cls, brand: 'Brand', year: Optional[int] = None, 
                         month: Optional[int] = None) -> Decimal:
        ""
        Get total spend for a brand in a specific month.
        
        Args:
            brand: The brand to get spend for.
            year: The year to get spend for. Defaults to current year.
            month: The month to get spend for. Defaults to current month.
            
        Returns:
            Decimal: Total spend for the month.
        """
        now = timezone.now()
        if year is None:
            year = now.year
        if month is None:
            month = now.month
            
        start = timezone.make_aware(datetime(year, month, 1))
        
        if month == 12:
            end = timezone.make_aware(datetime(year + 1, 1, 1))
        else:
            end = timezone.make_aware(datetime(year, month + 1, 1))
            
        total = cls.objects.filter(
            brand=brand,
            timestamp__range=(start, end)
        ).aggregate(total=models.Sum('amount'))['total'] or Decimal('0.00')
        
        return total
