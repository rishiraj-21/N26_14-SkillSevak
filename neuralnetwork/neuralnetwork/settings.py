"""
Django settings for SkillSevak - AI-Powered Resume Matching System

Security-hardened settings using environment variables.
See PRD.md for architecture details.
"""

from pathlib import Path
from decouple import config, Csv
import os

# =============================================================================
# BASE CONFIGURATION
# =============================================================================
BASE_DIR = Path(__file__).resolve().parent.parent

# =============================================================================
# SECURITY SETTINGS (Fixed per PRD.md security guidelines)
# =============================================================================
# SECURITY: Secret key from environment variable
SECRET_KEY = config(
    'SECRET_KEY',
    default='django-insecure-dev-only-change-in-production-z1o^6@aw'
)

# SECURITY: Debug mode from environment (False in production)
DEBUG = config('DEBUG', default=True, cast=bool)

# SECURITY: Allowed hosts from environment
ALLOWED_HOSTS = config(
    'ALLOWED_HOSTS',
    default='localhost,127.0.0.1',
    cast=Csv()
)

# =============================================================================
# APPLICATION DEFINITION
# =============================================================================
INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'django.contrib.sites',
    # Authentication (Google OAuth)
    'allauth',
    'allauth.account',
    'allauth.socialaccount',
    'allauth.socialaccount.providers.google',
    # SkillSevak App
    'ann',
]

# Background Tasks (Phase 6) - add if Celery packages are installed
try:
    import django_celery_results
    INSTALLED_APPS.append('django_celery_results')
except ImportError:
    pass

try:
    import django_celery_beat
    INSTALLED_APPS.append('django_celery_beat')
except ImportError:
    pass

# Django Sites Framework (required by allauth)
SITE_ID = 1

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    'allauth.account.middleware.AccountMiddleware',
]

# =============================================================================
# AUTHENTICATION BACKENDS
# =============================================================================
AUTHENTICATION_BACKENDS = [
    'django.contrib.auth.backends.ModelBackend',
    'allauth.account.auth_backends.AuthenticationBackend',
]

ROOT_URLCONF = 'neuralnetwork.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [os.path.join(BASE_DIR, 'templates')],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'neuralnetwork.wsgi.application'

# =============================================================================
# DATABASE CONFIGURATION
# =============================================================================
# PostgreSQL for both development and production (better for embeddings)
# Install PostgreSQL and create database: createdb skillsevak

DATABASE_URL = config('DATABASE_URL', default='')

if DATABASE_URL:
    # Production: Use DATABASE_URL
    import dj_database_url
    DATABASES = {
        'default': dj_database_url.parse(DATABASE_URL)
    }
else:
    # Development: PostgreSQL (recommended for vector operations)
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.postgresql',
            'NAME': config('DB_NAME', default='skillsevak'),
            'USER': config('DB_USER', default='postgres'),
            'PASSWORD': config('DB_PASSWORD', default='postgres'),
            'HOST': config('DB_HOST', default='localhost'),
            'PORT': config('DB_PORT', default='5432'),
        }
    }

# Fallback to SQLite if PostgreSQL is not available (for quick testing)
# Set USE_SQLITE=True in .env to use SQLite
if config('USE_SQLITE', default=False, cast=bool):
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.sqlite3',
            'NAME': BASE_DIR / 'db.sqlite3',
        }
    }

# =============================================================================
# PASSWORD VALIDATION
# =============================================================================
AUTH_PASSWORD_VALIDATORS = [
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

# =============================================================================
# INTERNATIONALIZATION
# =============================================================================
LANGUAGE_CODE = 'en-us'
TIME_ZONE = 'UTC'
USE_I18N = True
USE_TZ = True

# =============================================================================
# STATIC & MEDIA FILES
# =============================================================================
STATIC_URL = 'static/'
STATICFILES_DIRS = [os.path.join(BASE_DIR, 'static')] if os.path.exists(os.path.join(BASE_DIR, 'static')) else []
STATIC_ROOT = os.path.join(BASE_DIR, 'staticfiles')

MEDIA_URL = '/media/'
MEDIA_ROOT = os.path.join(BASE_DIR, 'media')

# =============================================================================
# DEFAULT PRIMARY KEY
# =============================================================================
DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# =============================================================================
# CELERY CONFIGURATION (Phase 6 - Background Tasks)
# =============================================================================
CELERY_BROKER_URL = config('CELERY_BROKER_URL', default='redis://localhost:6379/0')

# Use django-celery-results to store task results in database
# This allows tracking task status without Redis
CELERY_RESULT_BACKEND = 'django-db'

# Content settings
CELERY_ACCEPT_CONTENT = ['json']
CELERY_TASK_SERIALIZER = 'json'
CELERY_RESULT_SERIALIZER = 'json'
CELERY_TIMEZONE = TIME_ZONE

# Task result expiration (7 days)
CELERY_RESULT_EXPIRES = 60 * 60 * 24 * 7

# Track task state changes
CELERY_TASK_TRACK_STARTED = True

# Celery Beat scheduler (stores schedule in database) - only if installed
try:
    import django_celery_beat
    CELERY_BEAT_SCHEDULER = 'django_celery_beat.schedulers:DatabaseScheduler'
except ImportError:
    pass

# Enable async resume processing (set False to use sync processing)
# Useful for development without Redis
# Requires: pip install celery redis django-celery-results django-celery-beat
USE_ASYNC_PROCESSING = config('USE_ASYNC_PROCESSING', default=False, cast=bool)

# =============================================================================
# CACHING (Redis for match score caching per PRD.md)
# =============================================================================
CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.redis.RedisCache',
        'LOCATION': config('REDIS_URL', default='redis://localhost:6379/1'),
    } if not DEBUG else {
        'BACKEND': 'django.core.cache.backends.locmem.LocMemCache',
        'LOCATION': 'unique-snowflake',
    }
}

# =============================================================================
# FILE UPLOAD SETTINGS (Resume Processing per PRD.md)
# =============================================================================
# Max upload size: 5MB (per PRD.md Phase 2)
DATA_UPLOAD_MAX_MEMORY_SIZE = 5 * 1024 * 1024  # 5MB
FILE_UPLOAD_MAX_MEMORY_SIZE = 5 * 1024 * 1024  # 5MB

# Allowed resume file types
ALLOWED_RESUME_EXTENSIONS = ['.pdf', '.docx']

# =============================================================================
# ML/AI CONFIGURATION (SkillSevak Core - per PRD.md)
# =============================================================================
# Embedding model (all-MiniLM-L6-v2 outputs 384 dimensions)
EMBEDDING_MODEL_NAME = 'all-MiniLM-L6-v2'
EMBEDDING_DIMENSION = 384

# spaCy model for NLP
SPACY_MODEL = 'en_core_web_sm'

# =============================================================================
# ANN MODEL CONFIGURATION (Phase 5)
# =============================================================================
# Path to trained model weights
ANN_MODEL_PATH = os.path.join(BASE_DIR, 'ann', 'ml', 'weights', 'match_predictor.pth')

# Enable ANN-based scoring (uses trained model if available)
# Set to False to always use weighted average formula
# NOTE: ANN disabled for now - weighted average gives more accurate scores
# until ANN is retrained with real recruiter decision data
USE_ANN_MODEL = config('USE_ANN_MODEL', default=False, cast=bool)

# Match score weights (MVP - fixed weights per PRD.md)
# Used as fallback when ANN model is not available
# Phase 5: ANN learns optimal weights automatically
MATCH_WEIGHTS = {
    'semantic': 0.25,
    'skills': 0.35,
    'experience': 0.20,
    'education': 0.10,
    'profile': 0.10,
}

# Skills score breakdown weights
SKILLS_WEIGHTS = {
    'technical': 0.70,   # Programming, frameworks, tools
    'domain': 0.20,      # Industry-specific knowledge
    'soft': 0.10,        # Communication, leadership, teamwork
}

# =============================================================================
# LOGGING CONFIGURATION
# =============================================================================
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'verbose': {
            'format': '{levelname} {asctime} {module} {message}',
            'style': '{',
        },
    },
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
            'formatter': 'verbose',
        },
    },
    'loggers': {
        'ann': {
            'handlers': ['console'],
            'level': 'DEBUG' if DEBUG else 'INFO',
        },
        'ann.services': {
            'handlers': ['console'],
            'level': 'DEBUG' if DEBUG else 'INFO',
        },
    },
}

# =============================================================================
# SECURITY HEADERS (Production)
# =============================================================================
if not DEBUG:
    SECURE_BROWSER_XSS_FILTER = True
    SECURE_CONTENT_TYPE_NOSNIFF = True
    X_FRAME_OPTIONS = 'DENY'
    SECURE_HSTS_SECONDS = 31536000
    SECURE_HSTS_INCLUDE_SUBDOMAINS = True
    SECURE_HSTS_PRELOAD = True
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True

# =============================================================================
# DJANGO-ALLAUTH CONFIGURATION (Google OAuth)
# =============================================================================
# Login/Logout URLs
LOGIN_URL = 'login'
LOGIN_REDIRECT_URL = 'candidate'
LOGOUT_REDIRECT_URL = 'index'

# Allauth settings
ACCOUNT_LOGIN_ON_GET = True
ACCOUNT_LOGOUT_ON_GET = True
ACCOUNT_EMAIL_REQUIRED = True
ACCOUNT_USERNAME_REQUIRED = False
ACCOUNT_AUTHENTICATION_METHOD = 'email'
ACCOUNT_EMAIL_VERIFICATION = 'optional'
ACCOUNT_UNIQUE_EMAIL = True

# Social account settings
SOCIALACCOUNT_AUTO_SIGNUP = True
SOCIALACCOUNT_LOGIN_ON_GET = True
SOCIALACCOUNT_EMAIL_AUTHENTICATION = True
SOCIALACCOUNT_EMAIL_AUTHENTICATION_AUTO_CONNECT = True

# Google OAuth Provider Configuration
# Set these in your .env file:
# GOOGLE_CLIENT_ID=your-client-id.apps.googleusercontent.com
# GOOGLE_CLIENT_SECRET=your-client-secret
SOCIALACCOUNT_PROVIDERS = {
    'google': {
        'APP': {
            'client_id': config('GOOGLE_CLIENT_ID', default=''),
            'secret': config('GOOGLE_CLIENT_SECRET', default=''),
            'key': '',
        },
        'SCOPE': [
            'profile',
            'email',
        ],
        'AUTH_PARAMS': {
            'access_type': 'online',
        },
        'OAUTH_PKCE_ENABLED': True,
    }
}
