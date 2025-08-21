# budget/models/__init__.pyi
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from django.db.models import Model
    from django.db.models.manager import Manager
    from .brand import Brand as Brand
    from .campaign import Campaign as Campaign
    from .spend import SpendRecord as SpendRecord
    from .schedule import DaypartingSchedule as DaypartingSchedule

__all__ = [
    'Brand',
    'Campaign',
    'SpendRecord',
    'DaypartingSchedule',
]