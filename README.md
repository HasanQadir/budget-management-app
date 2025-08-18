# Budget Management System

A Django + Celery based system for managing advertising budgets and campaign scheduling.

## Features

- Track daily and monthly advertising spend per brand
- Automatic campaign activation/deactivation based on budget limits
- Dayparting support for campaign scheduling
- Periodic budget resets
- Type-safe codebase with static type checking

## Setup

1. Create and activate a virtual environment:
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: .\venv\Scripts\activate
   ```

2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

3. Set up environment variables in `.env` file:
   ```
   SECRET_KEY=your-secret-key
   DEBUG=True
   REDIS_URL=redis://localhost:6379/0
   ```

4. Run migrations:
   ```bash
   python manage.py migrate
   ```

5. Start Redis server (required for Celery)

6. Start Celery worker:
   ```bash
   celery -A budget_manager worker -l info
   ```

7. Start Celery beat (for scheduled tasks):
   ```bash
   celery -A budget_manager beat -l info --scheduler django_celery_beat.schedulers:DatabaseScheduler
   ```

8. Run the development server:
   ```bash
   python manage.py runserver
   ```

## Data Models

### Brand
- Represents an advertising brand
- Has daily and monthly budget limits
- Tracks current spend

### Campaign
- Belongs to a Brand
- Has a status (active/paused)
- Has a daily spend limit
- Has dayparting schedule

### SpendRecord
- Tracks spend per campaign
- Records timestamp and amount
- Links to Brand and Campaign

### DaypartingSchedule
- Defines when a campaign should be active
- Includes days of week and time ranges

## System Workflow

1. **Daily Reset (Midnight)**
   - Reset daily spend for all brands
   - Reactivate eligible campaigns
   - Update campaign statuses based on dayparting

2. **Monthly Reset (First day of month, 00:00)**
   - Reset monthly spend for all brands
   - Reactivate eligible campaigns

3. **Periodic Budget Checks (Every 5 minutes)**
   - Check campaign spend against budgets
   - Pause campaigns that exceed limits
   - Update campaign statuses based on dayparting

## Type Checking

Run the following command to check for type errors:
```bash
mypy .
```

## Testing

Run the test suite with:
```bash
python manage.py test
```

## Assumptions

- Timezone is handled at the application level (UTC)
- Spend records are created by an external system
- Campaigns are managed through the admin interface
- Redis is used as the message broker for Celery
