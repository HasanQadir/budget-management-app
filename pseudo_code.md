# Pseudo-code and System Overview

## Core Models

```plaintext
Class Brand:
    Attributes: 
        - name, daily_budget, monthly_budget
        - current_daily_spend, current_monthly_spend
        - is_active, last_daily_reset, last_monthly_reset
    
    Methods:
        - record_spend(amount): Record spend against brand's budget
        - has_daily_budget_available(): Check if daily budget is available
        - has_monthly_budget_available(): Check if monthly budget is available

Class Campaign:
    Attributes:
        - name, brand (FK), status (ACTIVE/PAUSED/COMPLETED/ARCHIVED)
        - daily_budget, current_daily_spend, last_daily_reset
        - is_active, created_at, updated_at
    
    Methods:
        - save(): Handle status and active state changes
        - record_spend(amount): Record spend against campaign
        - has_daily_budget_available(): Check budget availability
        - should_be_active(): Check if campaign should be active
        - update_status_based_on_budget(): Sync active state with conditions

Class DaypartingSchedule:
    Attributes:
        - campaign (FK), day_of_week, start_time, end_time
        - timezone, is_active, priority
    
    Methods:
        - is_active_now(): Check if current time is within schedule
        - clean(): Validate schedule times and overlaps
```

## Scheduled Tasks

```plaintext
Task check_campaign_budgets (Runs every 5 minutes):
    For each active campaign:
        If campaign.should_be_active() is False:
            If campaign.is_active is True:
                campaign.is_active = False
                campaign.save()
                Log campaign paused
        Else:
            If campaign.is_active is False:
                campaign.is_active = True
                campaign.save()
                Log campaign activated

Task reset_daily_budgets (Runs at midnight UTC):
    For each brand:
        Reset current_daily_spend to 0
        Update last_daily_reset to today
    
    For each campaign:
        Reset current_daily_spend to 0
        Update last_daily_reset to today
        If campaign.status is ACTIVE and campaign.should_be_active():
            campaign.is_active = True
            campaign.save()

Task reset_monthly_budgets (Runs 1st of each month):
    For each brand:
        Reset current_monthly_spend to 0
        Update last_monthly_reset to today
    Reactivate eligible campaigns

Task update_campaign_statuses (Runs every 5 minutes):
    For each campaign with dayparting schedules:
        If within any active schedule:
            If not campaign.is_active and campaign.should_be_active():
                campaign.is_active = True
                campaign.save()
        Else:
            If campaign.is_active:
                campaign.is_active = False
                campaign.save()
```

## Key Methods

```plaintext
Campaign.should_be_active():
    If status is not ACTIVE: return False
    If brand is not active: return False
    If no daily budget available: return False
    If has dayparting schedules and none are active: return False
    Return True

Campaign.update_status_based_on_budget():
    should_activate = self.should_be_active()
    If self.is_active != should_activate:
        self.is_active = should_activate
        self.save()
        Return True
    Return False

DaypartingSchedule.is_active_now():
    Get current time in schedule's timezone
    If current day matches day_of_week:
        If current time is between start_time and end_time:
            Return True
    Return False
```

## Signal Handlers

```plaintext
On Campaign.save():
    If status is ARCHIVED/COMPLETED/PAUSED:
        Set is_active = False
    Else if status is ACTIVE:
        Update is_active based on should_be_active()
    Call update_status_based_on_budget() if needed

On DaypartingSchedule.save():
    Validate schedule times
    Check for overlaps
    Update related campaign's status

On Brand budget/spend change:
    Update all related campaigns' statuses
```

## Celery Configuration

```plaintext
# File: budget_manager/celery.py

1. Initialize Celery app with Django settings
   - Set broker_url to Redis
   - Configure timezone and task settings

2. Define Beat Schedule (Periodic Tasks):
   - check_campaign_budgets: Runs every 5 minutes
     - Task: 'check_campaign_budgets'
     - Schedule: crontab(minute='*/5')
   
   - reset_daily_budgets: Runs daily at midnight UTC
     - Task: 'reset_daily_budgets'
     - Schedule: crontab(hour=0, minute=0)
   
   - reset_monthly_budgets: Runs 1st of each month at midnight
     - Task: 'reset_monthly_budgets'
     - Schedule: crontab(day_of_month=1, hour=0, minute=0)
   
   - update_campaign_statuses: Runs every 5 minutes
     - Task: 'update_campaign_statuses'
     - Schedule: crontab(minute='*/5')

3. Task Configuration:
   - Task time limits and retries
   - Queue configuration
   - Error handling and logging

4. Worker Configuration:
   - Concurrency settings
   - Prefetch multiplier
   - Task routing
```

## Admin Actions

```plaintext
Action activate_campaigns:
    For selected campaigns:
        If campaign.should_be_active():
            campaign.is_active = True
            campaign.save()

Action pause_campaigns:
    For selected campaigns:
        campaign.is_active = False
        campaign.save()

Action reset_daily_spend:
    For selected campaigns:
        Reset current_daily_spend to 0
        Update last_daily_reset
