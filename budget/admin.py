"""Django admin configuration for the budget app."""
from django.contrib import admin
from django.utils.html import format_html
from django.urls import reverse
from django.utils.safestring import mark_safe
from django.utils import timezone
from django.http import HttpRequest
from django.db.models.query import QuerySet
from typing import Optional, Dict, Any, List, Tuple
from django.db.models import F


from .models import (
    Brand,
    Campaign,
    SpendRecord,
    DaypartingSchedule,
)


class BrandAdmin(admin.ModelAdmin):
    """Admin configuration for the Brand model."""
    list_display = (
        'name', 
        'daily_budget', 
        'monthly_budget',
        'current_daily_spend',
        'current_monthly_spend',
        'daily_budget_used',
        'monthly_budget_used',
        'is_active',
        'last_daily_reset',
        'last_monthly_reset',
    )
    
    list_filter = ('is_active', 'last_daily_reset', 'last_monthly_reset')
    search_fields = ('name',)
    readonly_fields = (
        'current_daily_spend', 
        'current_monthly_spend',
        'last_daily_reset',
        'last_monthly_reset',
        'created_at',
        'updated_at',
    )
    
    fieldsets = (
        (None, {
            'fields': ('name', 'is_active')
        }),
        ('Budget', {
            'fields': (
                'daily_budget', 
                'monthly_budget',
                'current_daily_spend',
                'current_monthly_spend',
            )
        }),
        ('Reset Information', {
            'fields': (
                'last_daily_reset',
                'last_monthly_reset',
            )
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    def daily_budget_used(self, obj: Brand) -> str:
        """Display the percentage of daily budget used."""
        if obj.daily_budget == 0:
            return "N/A"
        percentage = (obj.current_daily_spend / obj.daily_budget) * 100
        return f"{percentage:.1f}%"
    daily_budget_used.short_description = 'Daily Budget Used'  # type: ignore[attr-defined]
    
    def monthly_budget_used(self, obj: Brand) -> str:
        """Display the percentage of monthly budget used."""
        if obj.monthly_budget == 0:
            return "N/A"
        percentage = (obj.current_monthly_spend / obj.monthly_budget) * 100
        return f"{percentage:.1f}%"
    monthly_budget_used.short_description = 'Monthly Budget Used'  # type: ignore[attr-defined]
    
    actions = ['reset_daily_spend', 'reset_monthly_spend']
    
    def reset_daily_spend(self, request: HttpRequest, queryset: QuerySet[Brand]) -> None:
        """Custom action to reset daily spend for selected brands."""
        updated = queryset.update(
            current_daily_spend=0,
            last_daily_reset=timezone.now().date()
        )
        self.message_user(
            request, 
            f"Successfully reset daily spend for {updated} brands."
        )
    reset_daily_spend.short_description = "Reset daily spend for selected brands"  # type: ignore[attr-defined]
    
    def reset_monthly_spend(self, request: HttpRequest, queryset: QuerySet[Brand]) -> None:
        """Custom action to reset monthly spend for selected brands."""
        updated = queryset.update(
            current_monthly_spend=0,
            last_monthly_reset=timezone.now().date()
        )
        self.message_user(
            request, 
            f"Successfully reset monthly spend for {updated} brands."
        )
    reset_monthly_spend.short_description = "Reset monthly spend for selected brands"  # type: ignore[attr-defined]


class CampaignStatusFilter(admin.SimpleListFilter):
    """Filter for campaign status."""
    title = 'status'
    parameter_name = 'status'
    
    def lookups(self, request: HttpRequest, model_admin: admin.ModelAdmin) -> List[Tuple[str, str]]:
        return [
            ('active', 'Active'),
            ('paused', 'Paused'),
            ('over_budget', 'Over Budget'),
            ('inactive_schedule', 'Inactive (Schedule)')
        ]
    
    def queryset(self, request: HttpRequest, queryset: QuerySet) -> Optional[QuerySet]:
        if self.value() == 'active':
            return queryset.filter(is_active=True)
        elif self.value() == 'paused':
            return queryset.filter(is_active=False)
        elif self.value() == 'over_budget':
            return queryset.filter(
                current_daily_spend__gte=F('daily_budget')
            )
        elif self.value() == 'inactive_schedule':
            # This would require a more complex query in a real implementation
            return queryset.none()
        return None  # Added to satisfy mypy for all branches


class CampaignAdmin(admin.ModelAdmin):
    """Admin configuration for the Campaign model."""
    list_display = (
        'name',
        'brand_link',
        'status',
        'daily_budget',
        'current_daily_spend',
        'daily_budget_used',
        'is_active',
        'last_daily_reset',
        'has_dayparting',
        'created_at',
    )
    
    list_filter = (
        'status',
        'is_active',
        'last_daily_reset',
        'brand',
        CampaignStatusFilter,
    )
    
    search_fields = ('name', 'brand__name')
    list_select_related = ('brand',)
    readonly_fields = (
        'current_daily_spend',
        'last_daily_reset',
        'created_at',
        'updated_at',
    )
    
    fieldsets = (
        (None, {
            'fields': ('name', 'brand', 'status', 'is_active')
        }),
        ('Budget', {
            'fields': (
                'daily_budget',
                'current_daily_spend',
                'last_daily_reset',
            )
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    def brand_link(self, obj: Campaign) -> str:
        """Create a link to the brand's admin page."""
        url = reverse('admin:budget_brand_change', args=[obj.brand.id])
        return format_html('<a href="{}">{}</a>', url, obj.brand.name)
    brand_link.short_description = 'Brand'  # type: ignore[attr-defined]
    brand_link.admin_order_field = 'brand__name'  # type: ignore[attr-defined]
    
    def daily_budget_used(self, obj: Campaign) -> str:
        """Display the percentage of daily budget used."""
        if obj.daily_budget == 0:
            return "N/A"
        percentage = (obj.current_daily_spend / obj.daily_budget) * 100
        return f"{percentage:.1f}%"
    daily_budget_used.short_description = 'Budget Used'  # type: ignore[attr-defined]
    
    def has_dayparting(self, obj: Campaign) -> bool:
        """Check if the campaign has any dayparting schedules."""
        return obj.dayparting_schedules.exists()
    has_dayparting.boolean = True  # type: ignore[attr-defined]
    has_dayparting.short_description = 'Has Dayparting'  # type: ignore[attr-defined]
    
    actions = ['reset_daily_spend', 'activate_campaigns', 'pause_campaigns']
    
    def reset_daily_spend(self, request: HttpRequest, queryset: QuerySet[Campaign]) -> None:
        """Custom action to reset daily spend for selected campaigns."""
        updated = queryset.update(
            current_daily_spend=0,
            last_daily_reset=timezone.now().date()
        )
        self.message_user(
            request, 
            f"Successfully reset daily spend for {updated} campaigns."
        )
    reset_daily_spend.short_description = "Reset daily spend for selected campaigns"  # type: ignore[attr-defined]
    
    def activate_campaigns(self, request: HttpRequest, queryset: QuerySet[Campaign]) -> None:
        """Custom action to activate selected campaigns."""
        updated = queryset.update(is_active=True)
        self.message_user(request, f"Successfully activated {updated} campaigns.")
    activate_campaigns.short_description = "Activate selected campaigns"  # type: ignore[attr-defined]
    
    def pause_campaigns(self, request: HttpRequest, queryset: QuerySet[Campaign]) -> None:
        """Custom action to pause selected campaigns."""
        updated = queryset.update(is_active=False)
        self.message_user(request, f"Successfully paused {updated} campaigns.")
    pause_campaigns.short_description = "Pause selected campaigns"  # type: ignore[attr-defined]


class SpendRecordAdmin(admin.ModelAdmin):
    """Admin configuration for the SpendRecord model."""
    list_display = (
        'timestamp',
        'brand_link',
        'campaign_link',
        'amount',
        'reference_id',
        'created_at',
    )
    
    list_filter = (
        'timestamp',
        'brand',
        'campaign',
    )
    
    search_fields = (
        'brand__name',
        'campaign__name',
        'reference_id',
    )
    
    readonly_fields = (
        'created_at',
    )
    
    date_hierarchy = 'timestamp'
    
    def brand_link(self, obj: SpendRecord) -> str:
        """Create a link to the brand's admin page."""
        url = reverse('admin:budget_brand_change', args=[obj.brand.id])
        return format_html('<a href="{}">{}</a>', url, obj.brand.name)
    brand_link.short_description = 'Brand'  # type: ignore[attr-defined]
    brand_link.admin_order_field = 'brand__name'  # type: ignore[attr-defined]
    
    def campaign_link(self, obj: SpendRecord) -> str:
        """Create a link to the campaign's admin page if it exists."""
        if not obj.campaign:
            return "-"
        url = reverse('admin:budget_campaign_change', args=[obj.campaign.id])
        return format_html('<a href="{}">{}</a>', url, obj.campaign.name)
    campaign_link.short_description = 'Campaign'  # type: ignore[attr-defined]
    campaign_link.admin_order_field = 'campaign__name'  # type: ignore[attr-defined]


class DaypartingScheduleAdmin(admin.ModelAdmin):
    """Admin configuration for the DaypartingSchedule model."""
    list_display = (
        'campaign_link',
        'day_of_week',
        'start_time',
        'end_time',
        'timezone',
        'is_active',
        'priority',
    )
    
    list_filter = (
        'day_of_week',
        'is_active',
        'timezone',
    )
    
    search_fields = (
        'campaign__name',
        'campaign__brand__name',
    )
    
    list_select_related = ('campaign', 'campaign__brand')
    
    def campaign_link(self, obj: DaypartingSchedule) -> str:
        """Create a link to the campaign's admin page."""
        url = reverse('admin:budget_campaign_change', args=[obj.campaign.id])
        return format_html(
            '{} - <a href="{}">{}</a>', 
            obj.campaign.brand.name,
            url, 
            obj.campaign.name
        )
    campaign_link.short_description = 'Campaign'  # type: ignore[attr-defined]
    campaign_link.admin_order_field = 'campaign__name'  # type: ignore[attr-defined]

admin.site.register(Brand, BrandAdmin)
admin.site.register(Campaign, CampaignAdmin)
admin.site.register(SpendRecord, SpendRecordAdmin)
admin.site.register(DaypartingSchedule, DaypartingScheduleAdmin)