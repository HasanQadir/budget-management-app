"""Signals for the budget app."""
from typing import Any, Dict, Optional
from django.db.models.signals import post_save, pre_save
from django.dispatch import receiver
from django.utils import timezone

from .models import Brand, Campaign, DaypartingSchedule


@receiver(pre_save, sender=Brand)
def update_brand_timestamps(sender: Any, instance: Brand, **kwargs: Any) -> None:
    """Update timestamps when a brand is saved."""
    # Ensure timestamps are set on creation
    if not instance.pk:
        now = timezone.now()
        if not instance.last_daily_reset:
            instance.last_daily_reset = now.date()
        if not instance.last_monthly_reset:
            instance.last_monthly_reset = now.date()
    
    # Ensure current spend doesn't exceed budgets
    if instance.current_daily_spend > instance.daily_budget:
        instance.current_daily_spend = instance.daily_budget
    
    if instance.current_monthly_spend > instance.monthly_budget:
        instance.current_monthly_spend = instance.monthly_budget


@receiver(pre_save, sender=Campaign)
def update_campaign_timestamps(sender: Any, instance: Campaign, **kwargs: Any) -> None:
    """Update timestamps when a campaign is saved."""
    # Ensure timestamp is set on creation
    if not instance.pk and not instance.last_daily_reset:
        instance.last_daily_reset = timezone.now().date()
    
    # Ensure current spend doesn't exceed budget
    if instance.current_daily_spend > instance.daily_budget:
        instance.current_daily_spend = instance.daily_budget
    
    # Ensure active status is consistent with status field
    if instance.status != Campaign.CampaignStatus.ACTIVE:
        instance.is_active = False


@receiver(post_save, sender=DaypartingSchedule)
def update_campaign_status_on_schedule_change(
    sender: Any, 
    instance: DaypartingSchedule, 
    **kwargs: Any
) -> None:
    """Update campaign status when a dayparting schedule changes."""
    # Only update if the schedule is active
    if instance.is_active:
        instance.campaign.update_status_based_on_budget()


@receiver(post_save, sender=Campaign)
def update_campaign_status_on_change(
    sender: Any, 
    instance: Campaign, 
    **kwargs: Any
) -> None:
    """Update campaign status when campaign data changes."""
    # Update status based on budget and schedule
    instance.update_status_based_on_budget()


@receiver(post_save, sender=Brand)
def update_brand_campaigns_status(
    sender: Any, 
    instance: Brand, 
    **kwargs: Any
) -> None:
    """Update status of all campaigns when brand data changes."""
    from django.db import transaction
    
    # Update all active campaigns for this brand
    for campaign in instance.campaigns.filter(is_active=True):
        with transaction.atomic():
            campaign.update_status_based_on_budget()
