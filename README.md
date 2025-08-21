# Budget Management System

A Django 5.2.5 + Celery based system for managing advertising budgets and campaign scheduling.

## Requirements

- Python 3.10+
- Redis 6.0+
- Django 5.2.5 (LTS)
- Celery 5.3.6
- PostgreSQL 13+ (recommended) or SQLite (for development)
- Node.js 16+ (if using frontend assets)

## Features

- Track daily and monthly advertising spend per brand
- Automatic campaign activation/deactivation based on budget limits
- Dayparting support for campaign scheduling
- Periodic budget resets
- Type-safe codebase with static type checking

## Prerequisites

### Database Setup

#### macOS (using Homebrew)
```bash
# Install PostgreSQL
brew install postgresql

# Start PostgreSQL service
brew services start postgresql

# Create a database user (optional, but recommended)
createuser -s postgres
```

#### Ubuntu/Debian
```bash
# Install PostgreSQL
sudo apt update
sudo apt install postgresql postgresql-contrib

# Start PostgreSQL service
sudo service postgresql start

# Create a database user (optional, but recommended)
sudo -u postgres createuser --superuser $USER
```

#### Windows
1. Download the installer from [PostgreSQL Downloads](https://www.postgresql.org/download/windows/)
2. Run the installer and follow the setup wizard
3. Make sure to remember the password you set for the postgres user
4. Add PostgreSQL's bin directory to your system PATH (usually `C:\Program Files\PostgreSQL\<version>\bin`)

## Environment Setup

### Development
```bash
# Copy development environment file
cp packaging/environments/env.dev.example .env

# Install development dependencies
cp packaging/requirements/requirements-dev.txt requirements.txt
pip install -r requirements.txt

```

### QA
```bash
# Copy QA environment file
cp packaging/environments/env.qa.example .env

# Install QA dependencies
cp packaging/requirements/requirements-qa.txt requirements.txt
pip install -r requirements.txt
```

### Production
```bash
# Copy production environment file
cp packaging/environments/env.prod.example .env

# Install production dependencies
cp packaging/requirements/requirements-prod.txt requirements.txt
pip install -r requirements.txt
```

### Common Setup Steps

1. Create and activate a virtual environment:
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: .\venv\Scripts\activate
   ```

2. Install the appropriate requirements as shown above for your environment.

3. Update the `.env` file with your specific configuration values.

4. Run database migrations:
   ```bash
   python manage.py migrate
   ```

5. Install and start Redis:
   ### Redis Installation

   To install Redis, follow the instructions for your operating system:

   - **macOS**: Use Homebrew to install Redis.
     ```bash
     brew install redis
     brew services start redis
     ```

   - **Linux**: Use the package manager specific to your distribution. For example, on Ubuntu:
     ```bash
     sudo apt update
     sudo apt install redis-server
     sudo systemctl enable redis-server.service
     sudo systemctl start redis-server.service
     ```

   - **Windows**: Use the Windows Subsystem for Linux (WSL) or download a Redis installer from the official Redis website.

   Ensure that Redis is running before starting Celery.

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
