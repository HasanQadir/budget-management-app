"""Celery configuration for the budget manager."""
import os
from celery import Celery  # type: ignore
from celery.schedules import crontab  # type: ignore
from django.conf import settings
from typing import Any, Dict, Callable

# Set the default Django settings module for the 'celery' program.
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'budget_manager.settings')

app = Celery('budget_manager')

# Using a string here means the worker doesn't have to serialize
# the configuration object to child processes.
# - namespace='CELERY' means all celery-related configuration keys
#   should have a `CELERY_` prefix.
app.config_from_object('django.conf:settings', namespace='CELERY')

# Worker settings and task settings
app.conf.update(
    worker_concurrency=settings.CELERY_WORKER_CONCURRENCY,
    worker_prefetch_multiplier=settings.CELERY_WORKER_PREFETCH_MULTIPLIER,
    worker_max_tasks_per_child=settings.CELERY_WORKER_MAX_TASKS_PER_CHILD,
    task_time_limit=settings.CELERY_TASK_TIME_LIMIT,
    task_soft_time_limit=settings.CELERY_TASK_SOFT_TIME_LIMIT,
    task_track_started=True,
    task_send_sent_event=True,
    timezone='UTC',
)

# Load task modules from all registered Django app configs.
app.autodiscover_tasks()

# Configure periodic tasks
app.conf.beat_schedule = {
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

# Define a type for the task decorator
TaskDecorator = Callable[[Callable[[Any], None]], Callable[[Any], None]]

@app.task(bind=True, ignore_result=True)  # type: ignore[misc]
def debug_task(self: Any) -> None:
    """Debug task to verify Celery is working."""
    print(f'Request: {self.request!r}')