"""
Management command to re-extract skills for all jobs.

Run after fixing job skill extraction logic.

Usage:
    python manage.py reprocess_job_skills
"""

from django.core.management.base import BaseCommand
from ann.models import Job


class Command(BaseCommand):
    help = 'Re-extract skills and embeddings for all jobs'

    def handle(self, *args, **options):
        from ann.views import extract_job_skills, generate_job_embedding

        jobs = Job.objects.all()
        total = jobs.count()

        for i, job in enumerate(jobs, 1):
            count = extract_job_skills(job)
            generate_job_embedding(job)
            self.stdout.write(f'  [{i}/{total}] {job.title}: {count} skills')

        self.stdout.write(self.style.SUCCESS(f'\nDone: {total} jobs processed'))
