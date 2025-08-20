"""Celery configuration for the budget manager."""
import os
from celery import Celery
from celery.schedules import crontab
from django.conf import settings
from typing import Any, Dict

# Set the default Django settings module for the 'celery' program.
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'budget_manager.settings')

app = Celery('budget_manager')

# Using a string here means the worker doesn't have to serialize
# the configuration object to child processes.
# - namespace='CELERY' means all celery-related configuration keys
#   should have a `CELERY_` prefix.
app.config_from_object('django.conf:settings', namespace='CELERY')

# Load task modules from all registered Django app configs.
app.autodiscover_tasks()

# Configure periodic tasks
app.conf.beat_schedule: Dict[str, Any] = {
    'check-campaign-budgets': {
        'task': 'budget.tasks.check_campaign_budgets',
        'schedule': crontab(minute='*/5'),  # Every 5 minutes
    },
    'reset-daily-budgets': {
        'task': 'budget.tasks.reset_daily_budgets',
        'schedule': crontab(hour=0, minute=0),  # Daily at midnight UTC
    },
    'reset-monthly-budgets': {
        'task': 'budget.tasks.reset_monthly_budgets',
        'schedule': crontab(day_of_month=1, hour=0, minute=0),  # First day of the month at midnight UTC
    },
    'update-campaign-statuses': {
        'task': 'budget.tasks.update_campaign_statuses',
        'schedule': crontab(minute='*/5'),  # Every 5 minutes
    },
}

app.conf.timezone = 'UTC'

@app.task(bind=True)
def debug_task(self) -> None:
    """Debug task to verify Celery is working."""
    print(f'Request: {self.request!r}')
