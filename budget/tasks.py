"""Celery tasks for budget management."""
from datetime import datetime, date, timedelta
from typing import List, Optional, Dict, Any
from decimal import Decimal
import logging
from celery import shared_task
from django.utils import timezone
from django.db import transaction
from django.db.models import F, Q

from .models import (
    Brand,
    Campaign,
    CampaignStatus,
    SpendRecord,
    DaypartingSchedule,
)

logger = logging.getLogger(__name__)


@shared_task(name="check_campaign_budgets")
def check_campaign_budgets() -> Dict[str, Any]:
    """
    Check campaign budgets and update statuses if needed.
    
    This task runs periodically to ensure campaigns don't exceed their budgets.
    
    Returns:
        Dict with statistics about the operation.
    """
    stats = {
        'timestamp': timezone.now().isoformat(),
        'campaigns_checked': 0,
        'campaigns_paused': 0,
        'campaigns_reactivated': 0,
        'errors': []
    }
    
    try:
        # Get all active campaigns
        campaigns = Campaign.objects.filter(
            status=CampaignStatus.ACTIVE
        ).select_related('brand')
        
        for campaign in campaigns:
            try:
                with transaction.atomic():
                    stats['campaigns_checked'] += 1
                    
                    # Check if campaign should be active based on budget and schedule
                    should_be_active = campaign.should_be_active()
                    
                    if campaign.is_active and not should_be_active:
                        # Pause the campaign
                        campaign.is_active = False
                        campaign.save(update_fields=['is_active', 'updated_at'])
                        stats['campaigns_paused'] += 1
                        logger.info(
                            f"Paused campaign {campaign.id} - {campaign.name} "
                            f"(Brand: {campaign.brand.name})"
                        )
                    elif not campaign.is_active and should_be_active:
                        # Reactivate the campaign
                        campaign.is_active = True
                        campaign.save(update_fields=['is_active', 'updated_at'])
                        stats['campaigns_reactivated'] += 1
                        logger.info(
                            f"Reactivated campaign {campaign.id} - {campaign.name} "
                            f"(Brand: {campaign.brand.name})"
                        )
            except Exception as e:
                error_msg = f"Error processing campaign {campaign.id}: {str(e)}"
                logger.error(error_msg, exc_info=True)
                stats['errors'].append(error_msg)
    except Exception as e:
        error_msg = f"Error in check_campaign_budgets task: {str(e)}"
        logger.error(error_msg, exc_info=True)
        stats['errors'].append(error_msg)
    
    return stats


def _reactivate_eligible_campaigns() -> Dict[str, int]:
    """Reactivate campaigns that were paused due to budget constraints."""
    stats = {
        'campaigns_reactivated': 0,
        'brands_reactivated': 0
    }
    
    # Reactivate eligible campaigns
    campaigns = Campaign.objects.filter(
        status=CampaignStatus.ACTIVE,
        is_active=False,
        daily_budget__gt=F('current_daily_spend')
    ).select_related('brand')
    
    for campaign in campaigns:
        try:
            # Only reactivate if brand has budget and campaign passes all checks
            if (campaign.brand.is_active and 
                campaign.brand.has_daily_budget_available() and
                campaign.should_be_active()):
                campaign.is_active = True
                campaign.save(update_fields=['is_active', 'updated_at'])
                stats['campaigns_reactivated'] += 1
        except Exception as e:
            logger.error(f"Error reactivating campaign {campaign.id}: {str(e)}", exc_info=True)
    
    return stats

@shared_task(name="reset_daily_budgets")
def reset_daily_budgets() -> Dict[str, Any]:
    """
    Reset daily budgets for all brands and campaigns and reactivate eligible campaigns.
    
    This task runs once per day at midnight to reset daily spend counters.
    
    Returns:
        Dict with statistics about the operation.
    """
    stats = {
        'timestamp': timezone.now().isoformat(),
        'brands_updated': 0,
        'campaigns_updated': 0,
        'campaigns_reactivated': 0,
        'errors': []
    }
    
    try:
        # Reset brand daily spends
        updated_brands = Brand.objects.update(
            current_daily_spend=Decimal('0.00'),
            last_daily_reset=timezone.now().date()
        )
        stats['brands_updated'] = updated_brands
        
        # Reset campaign daily spends
        updated_campaigns = Campaign.objects.update(
            current_daily_spend=Decimal('0.00'),
            last_daily_reset=timezone.now().date()
        )
        stats['campaigns_updated'] = updated_campaigns
        
        # Reactivate eligible campaigns
        reactivation_stats = _reactivate_eligible_campaigns()
        stats.update(reactivation_stats)
        
        logger.info(
            f"Reset daily budgets: {updated_brands} brands, {updated_campaigns} campaigns, "
            f"{reactivation_stats['campaigns_reactivated']} campaigns reactivated"
        )
    except Exception as e:
        error_msg = f"Error in reset_daily_budgets task: {str(e)}"
        logger.error(error_msg, exc_info=True)
        stats['errors'].append(error_msg)
    
    return stats


@shared_task(name="reset_monthly_budgets")
def reset_monthly_budgets() -> Dict[str, Any]:
    """
    Reset monthly budgets for all brands and reactivate eligible campaigns.
    
    This task runs once per month to reset monthly spend counters.
    
    Returns:
        Dict with statistics about the operation.
    """
    stats = {
        'timestamp': timezone.now().isoformat(),
        'brands_updated': 0,
        'campaigns_reactivated': 0,
        'errors': []
    }
    
    try:
        # Reset brand monthly spends
        updated_brands = Brand.objects.update(
            current_monthly_spend=Decimal('0.00'),
            last_monthly_reset=timezone.now().date()
        )
        stats['brands_updated'] = updated_brands
        
        # Reactivate eligible campaigns (both daily and monthly budgets were reset)
        reactivation_stats = _reactivate_eligible_campaigns()
        stats.update(reactivation_stats)
        
        logger.info(
            f"Reset monthly budgets: {updated_brands} brands, "
            f"{reactivation_stats['campaigns_reactivated']} campaigns reactivated"
        )
    except Exception as e:
        error_msg = f"Error in reset_monthly_budgets task: {str(e)}"
        logger.error(error_msg, exc_info=True)
        stats['errors'].append(error_msg)
    
    return stats


@shared_task(name="update_campaign_statuses")
def update_campaign_statuses() -> Dict[str, Any]:
    """
    Update campaign statuses based on dayparting schedules.
    
    This task runs periodically to ensure campaigns are only active during their
    scheduled times.
    
    Returns:
        Dict with statistics about the operation.
    """
    stats = {
        'timestamp': timezone.now().isoformat(),
        'campaigns_checked': 0,
        'status_changes': 0,
        'errors': []
    }
    
    try:
        # Get all active campaigns with dayparting schedules
        campaigns = Campaign.objects.filter(
            status=CampaignStatus.ACTIVE,
            dayparting_schedules__isnull=False
        ).distinct()
        
        for campaign in campaigns:
            try:
                stats['campaigns_checked'] += 1
                
                # Check if campaign should be active based on dayparting
                should_be_active = any(
                    schedule.is_active_now() 
                    for schedule in campaign.dayparting_schedules.filter(is_active=True)
                )
                
                # Update status if needed
                if campaign.is_active != should_be_active:
                    campaign.is_active = should_be_active
                    campaign.save(update_fields=['is_active', 'updated_at'])
                    stats['status_changes'] += 1
                    
                    action = "activated" if should_be_active else "paused"
                    logger.info(
                        f"{action.capitalize()} campaign {campaign.id} - {campaign.name} "
                        f"(Brand: {campaign.brand.name}) based on dayparting schedule"
                    )
            except Exception as e:
                error_msg = f"Error updating status for campaign {campaign.id}: {str(e)}"
                logger.error(error_msg, exc_info=True)
                stats['errors'].append(error_msg)
    except Exception as e:
        error_msg = f"Error in update_campaign_statuses task: {str(e)}"
        logger.error(error_msg, exc_info=True)
        stats['errors'].append(error_msg)
    
    return stats


@shared_task(name="process_spend_record")
def process_spend_record(
    brand_id: int, 
    amount: Decimal, 
    reference_id: str,
    campaign_id: Optional[int] = None,
    metadata: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """
    Process a spend record asynchronously.
    
    Args:
        brand_id: ID of the brand the spend is for.
        amount: Amount spent.
        reference_id: External reference ID for the spend.
        campaign_id: Optional ID of the campaign the spend is for.
        metadata: Optional additional metadata about the spend.
        
    Returns:
        Dict with the result of the operation.
    """
    from .models import Brand, SpendRecord
    from .models.campaign import Campaign, CampaignStatus
    
    result = {
        'success': False,
        'record_id': None,
        'errors': [],
        'warnings': []
    }
    
    try:
        with transaction.atomic():
            # Get the brand
            try:
                brand = Brand.objects.select_for_update().get(pk=brand_id)
            except Brand.DoesNotExist:
                result['errors'].append(f"Brand with ID {brand_id} does not exist")
                return result
            
            # Get the campaign if provided
            campaign = None
            if campaign_id is not None:
                try:
                    campaign = Campaign.objects.select_for_update().get(
                        pk=campaign_id, 
                        brand=brand
                    )
                except Campaign.DoesNotExist:
                    result['warnings'].append(
                        f"Campaign with ID {campaign_id} not found or doesn't belong to brand {brand_id}"
                    )
            
            # Check if the reference_id already exists
            if SpendRecord.objects.filter(reference_id=reference_id).exists():
                result['warnings'].append(
                    f"Spend record with reference_id {reference_id} already exists"
                )
                return result
            
            # Create the spend record
            spend_record = SpendRecord.objects.create(
                brand=brand,
                campaign=campaign,
                amount=amount,
                reference_id=reference_id,
                metadata=metadata or {}
            )
            
            result.update({
                'success': True,
                'record_id': spend_record.id,
                'brand_id': brand.id,
                'campaign_id': campaign.id if campaign else None,
                'amount': str(amount),
                'timestamp': spend_record.timestamp.isoformat()
            })
            
            logger.info(
                f"Processed spend record {spend_record.id} - {amount} USD "
                f"for brand {brand.name}" + 
                (f" and campaign {campaign.name}" if campaign else "")
            )
            
    except Exception as e:
        error_msg = f"Error processing spend record: {str(e)}"
        logger.error(error_msg, exc_info=True)
        result['errors'].append(error_msg)
    
    return result
