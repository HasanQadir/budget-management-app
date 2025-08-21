"""Django settings for budget_manager project."""
from pathlib import Path
import os
from dotenv import load_dotenv
from typing import List, Dict, Any, Optional, Union

# Load environment variables
load_dotenv()

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY: str = os.getenv('SECRET_KEY', 'django-insecure-your-secret-key-here')

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG: bool = os.getenv('DEBUG', 'False') == 'True' and os.getenv('ENVIRONMENT') != 'production'

ALLOWED_HOSTS: List[str] = os.getenv('ALLOWED_HOSTS', 'localhost,127.0.0.1,0.0.0.0').split(',')

# Security settings
SECURE_HSTS_SECONDS = 31536000  # 1 year
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_HSTS_PRELOAD = True
# Only enable SSL redirect in production
SECURE_SSL_REDIRECT = not DEBUG
# Only use secure cookies in production
SESSION_COOKIE_SECURE = not DEBUG
CSRF_COOKIE_SECURE = not DEBUG
# This is safe to keep as it only affects requests that already have the header
SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')

# Additional security settings
SECURE_CONTENT_TYPE_NOSNIFF = True
SECURE_BROWSER_XSS_FILTER = True
X_FRAME_OPTIONS = 'DENY'

# For development, you can override these in local_settings.py
try:
    from .local_settings import *  # noqa: F401, F403
except ImportError:
    pass

# Generate a new secret key if not in production
if DEBUG and (SECRET_KEY == 'django-insecure-your-secret-key-here' or len(SECRET_KEY) < 50):
    from django.core.management.utils import get_random_secret_key
    SECRET_KEY = get_random_secret_key()

# Application definition
INSTALLED_APPS: List[str] = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'django_celery_beat',
    'django_celery_results',
    'budget.apps.BudgetConfig',
]

MIDDLEWARE: List[str] = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF: str = 'budget_manager.urls'

TEMPLATES: List[Dict[str, Any]] = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION: str = 'budget_manager.wsgi.application'

# Database
DATABASES: Dict[str, Dict[str, Any]] = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': BASE_DIR / 'db.sqlite3',
    }
}

# Password validation
AUTH_PASSWORD_VALIDATORS: List[Dict[str, str]] = [
    {
        'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',
    },
]

# Internationalization
LANGUAGE_CODE: str = 'en-us'
TIME_ZONE: str = 'UTC'
USE_I18N: bool = True
USE_TZ: bool = True

# Static files (CSS, JavaScript, Images)
STATIC_URL: str = 'static/'

# Default primary key field type
DEFAULT_AUTO_FIELD: str = 'django.db.models.BigAutoField'

# Celery Configuration
CELERY_BROKER_URL: str = os.getenv('REDIS_URL', 'redis://localhost:6379/0')
CELERY_RESULT_BACKEND: str = 'django-db'
CELERY_ACCEPT_CONTENT: List[str] = ['application/json']
CELERY_TASK_SERIALIZER: str = 'json'
CELERY_RESULT_SERIALIZER: str = 'json'
CELERY_TIMEZONE: str = TIME_ZONE

# Celery Beat Configuration
CELERY_BEAT_SCHEDULER: str = 'django_celery_beat.schedulers:DatabaseScheduler'

# Worker Configuration
# Number of worker processes/threads (default: number of CPU cores)
CELERY_WORKER_CONCURRENCY: int = 4
# Number of messages to prefetch per worker (default: 4 * concurrency)
CELERY_WORKER_PREFETCH_MULTIPLIER: int = 2
# Maximum number of tasks a worker can execute before being replaced (prevents memory leaks)
CELERY_WORKER_MAX_TASKS_PER_CHILD: int = 100
# Time in seconds after which a task will be killed if it hasn't completed
CELERY_TASK_TIME_LIMIT: int = 30 * 60  # 30 minutes
# Time in seconds after which a task will raise a SoftTimeLimitExceeded exception
CELERY_TASK_SOFT_TIME_LIMIT: int = 25 * 60  # 25 minutes

# Logging Configuration
LOGGING: Dict[str, Any] = {
    'version': 1,
    'disable_existing_loggers': False,
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
        },
    },
    'root': {
        'handlers': ['console'],
        'level': 'INFO',
    },
}
