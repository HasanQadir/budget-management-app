"""Budget app configuration."""
from django.apps import AppConfig
from typing import Dict, Any


class BudgetConfig(AppConfig):
    """Budget app configuration."""
    default_auto_field: str = 'django.db.models.BigAutoField'
    name: str = 'budget'

    def ready(self) -> None:
        """
        Import signals and tasks when the app is ready.
        This ensures that the signal handlers are registered.
        """
        # Import signals to register them
        import budget.signals  # noqa: F401
        
        # Import Celery tasks to ensure they are registered
        import budget.tasks  # noqa: F401
