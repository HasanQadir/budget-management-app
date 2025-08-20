"""DaypartingSchedule model for managing campaign schedules."""

from typing import Optional, TYPE_CHECKING, List, Dict, Any
from django.db import models
from django.utils import timezone
from django.core.validators import MinValueValidator, MaxValueValidator

if TYPE_CHECKING:
    from .campaign import Campaign


class DayOfWeek(models.IntegerChoices):
    """Day of week choices for dayparting schedules."""
    MONDAY = 0, 'Monday'
    TUESDAY = 1, 'Tuesday'
    WEDNESDAY = 2, 'Wednesday'
    THURSDAY = 3, 'Thursday'
    FRIDAY = 4, 'Friday'
    SATURDAY = 5, 'Saturday'
    SUNDAY = 6, 'Sunday'


class DaypartingSchedule(models.Model):
    """
    Defines when a campaign should be active during the week.
    
    Multiple schedules can be created for a single campaign to support
    complex dayparting requirements.
    """
    campaign = models.ForeignKey(
        'budget.Campaign',
        on_delete=models.CASCADE,
        related_name='dayparting_schedules',
        help_text="The campaign this schedule applies to.",
    )
    
    day_of_week = models.IntegerField(
        choices=DayOfWeek.choices,
        help_text="Day of the week this schedule applies to.",
    )
    
    start_time = models.TimeField(
        help_text="Start time for the schedule (inclusive).",
    )
    
    end_time = models.TimeField(
        help_text="End time for the schedule (inclusive).",
    )
    
    timezone = models.CharField(
        max_length=50,
        default='UTC',
        help_text="Timezone for the schedule times.",
    )
    
    is_active = models.BooleanField(
        default=True,
        help_text="Whether this schedule is active.",
    )
    
    priority = models.PositiveSmallIntegerField(
        default=0,
        help_text="Higher priority schedules take precedence.",
        validators=[
            MinValueValidator(0),
            MaxValueValidator(100)
        ],
    )
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        """Meta options for the DaypartingSchedule model."""
        ordering = ['campaign', 'day_of_week', 'start_time']
        verbose_name = 'Dayparting Schedule'
        verbose_name_plural = 'Dayparting Schedules'
        constraints = [
            models.UniqueConstraint(
                fields=['campaign', 'day_of_week', 'start_time', 'end_time'],
                name='unique_schedule_per_campaign_time',
                violation_error_message='A schedule already exists for this campaign, day, and time range.'
            ),
            models.CheckConstraint(
                condition=models.Q(end_time__gt=models.F('start_time')),
                name='end_time_after_start_time',
                violation_error_message='End time must be after start time.'
            )
        ]
    
    def __str__(self) -> str:
        """Return string representation of the dayparting schedule."""
        return f"{self.campaign} - {self.get_day_of_week_display()} {self.start_time}-{self.end_time}"
    
    def clean(self) -> None:
        """
        Validate the schedule data.
        
        Raises:
            ValidationError: If the schedule data is invalid.
        """
        from django.core.exceptions import ValidationError
        
        if self.end_time <= self.start_time:
            if self.end_time == self.start_time and self.end_time.hour == 0 and self.end_time.minute == 0:
                # Special case: 24-hour schedule
                pass
            else:
                raise ValidationError({
                    'end_time': 'End time must be after start time.'
                })
        
        # Check for overlapping schedules for the same campaign and day
        overlapping = DaypartingSchedule.objects.filter(
            campaign=self.campaign,
            day_of_week=self.day_of_week,
            is_active=True
        ).exclude(pk=self.pk if self.pk else None)
        
        # Check for any overlap in time ranges
        for schedule in overlapping:
            if (self.start_time < schedule.end_time and 
                self.end_time > schedule.start_time):
                raise ValidationError(
                    f"This schedule overlaps with an existing schedule: {schedule}"
                )
    
    def save(self, *args: Any, **kwargs: Any) -> None:
        """Override save to validate the schedule."""
        self.full_clean()
        super().save(*args, **kwargs)
        # Update the campaign's active status based on the new schedule
        self.campaign.update_status_based_on_budget()
    
    def is_active_now(self, tz: Optional[str] = None) -> bool:
        """
        Check if this schedule is currently active.
        
        Args:
            tz: Optional timezone to check against. Uses schedule's timezone if not provided.
            
        Returns:
            bool: True if the schedule is active now, False otherwise.
        """
        from datetime import datetime, time
        
        # Get current time in the schedule's timezone
        tz_to_use = tz or self.timezone
        now = timezone.now()
        
        try:
            # Convert to the target timezone
            from pytz import timezone as pytz_timezone
            tz_obj = pytz_timezone(tz_to_use)
            now = now.astimezone(tz_obj)
        except Exception:
            # Fallback to UTC if timezone is invalid
            now = timezone.now()
        
        # Check if today is the scheduled day
        if now.weekday() != self.day_of_week:
            return False
        
        # Check if current time is within the schedule
        current_time = now.time()
        
        # Handle schedules that cross midnight (end time is next day)
        if self.end_time <= self.start_time:
            # Schedule crosses midnight (e.g., 22:00-02:00)
            return current_time >= self.start_time or current_time <= self.end_time
        else:
            # Regular schedule within the same day
            return self.start_time <= current_time <= self.end_time
    
    @classmethod
    def get_active_schedules_for_campaign(cls, campaign: 'Campaign') -> List['DaypartingSchedule']:
        """
        Get all active schedules for a campaign, ordered by priority.
        
        Args:
            campaign: The campaign to get schedules for.
            
        Returns:
            List[DaypartingSchedule]: List of active schedules, ordered by priority (highest first).
        """
        return list(cls.objects.filter(
            campaign=campaign,
            is_active=True
        ).order_by('-priority', 'day_of_week', 'start_time'))
