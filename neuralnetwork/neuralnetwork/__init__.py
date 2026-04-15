"""
SkillSevak - AI-Powered Resume Matching System

This module ensures Celery is loaded when Django starts (if available).
"""

# Import Celery app so it's registered when Django starts
# Gracefully handle case when Celery is not installed
try:
    from .celery import app as celery_app
    __all__ = ('celery_app',)
except ImportError:
    # Celery not installed - async processing will be disabled
    celery_app = None
    __all__ = ()
