"""
Celery Configuration for SkillSevak

Phase 6: Async task processing for heavy ML operations.

This module configures Celery for background task processing:
- Resume parsing (PDF extraction, text cleaning)
- Skill extraction (NLP processing)
- Embedding generation (ML model inference)
- Match score calculation (batch processing)
- Model retraining (scheduled)

Usage:
    # Install Celery first:
    pip install celery redis django-celery-results django-celery-beat

    # Start Redis:
    redis-server

    # Start Celery worker:
    celery -A neuralnetwork worker -l info

    # Start Celery beat (scheduler):
    celery -A neuralnetwork beat -l info

    # Or run both together (development):
    celery -A neuralnetwork worker -B -l info
"""

import os

try:
    from celery import Celery
    from celery.schedules import crontab
    CELERY_AVAILABLE = True
except ImportError:
    CELERY_AVAILABLE = False
    Celery = None

# Exit early if Celery not installed
if not CELERY_AVAILABLE:
    app = None
    raise ImportError(
        "Celery is not installed. Install with: pip install celery redis"
    )

# Set the default Django settings module
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'neuralnetwork.settings')

# Create the Celery app
app = Celery('neuralnetwork')

# Load config from Django settings, using CELERY_ namespace
app.config_from_object('django.conf:settings', namespace='CELERY')

# Auto-discover tasks from all registered Django apps
app.autodiscover_tasks()

# Configure Celery Beat schedule (periodic tasks)
app.conf.beat_schedule = {
    # Retrain ANN model weekly with real recruiter data
    'retrain-model-weekly': {
        'task': 'ann.tasks.retrain_model_task',
        'schedule': crontab(hour=2, minute=0, day_of_week=0),  # Sunday 2 AM
        'options': {'queue': 'ml'},
    },
    # Recalculate stale match scores daily
    'recalculate-stale-matches': {
        'task': 'ann.tasks.recalculate_stale_matches_task',
        'schedule': crontab(hour=3, minute=0),  # Daily 3 AM
        'options': {'queue': 'default'},
    },
}

# Task routing - send ML tasks to dedicated queue
app.conf.task_routes = {
    'ann.tasks.parse_resume_task': {'queue': 'default'},
    'ann.tasks.extract_skills_task': {'queue': 'default'},
    'ann.tasks.generate_embedding_task': {'queue': 'ml'},
    'ann.tasks.calculate_matches_task': {'queue': 'default'},
    'ann.tasks.retrain_model_task': {'queue': 'ml'},
    'ann.tasks.process_resume_complete_task': {'queue': 'default'},
}

# Task execution settings
app.conf.task_acks_late = True  # Acknowledge after completion (safer)
app.conf.task_reject_on_worker_lost = True  # Requeue if worker crashes
app.conf.worker_prefetch_multiplier = 1  # Don't prefetch (better for long tasks)


@app.task(bind=True, ignore_result=True)
def debug_task(self):
    """Debug task to verify Celery is working."""
    print(f'Request: {self.request!r}')
