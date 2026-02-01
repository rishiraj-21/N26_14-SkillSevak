from django.core.management.base import BaseCommand
from ann.models import Job


class Command(BaseCommand):
    help = 'Populate the database with sample jobs'

    def handle(self, *args, **options):
        jobs_data = [
            {
                'title': 'Senior Data Scientist',
                'company': 'TechCorp',
                'location': 'San Francisco, CA',
                'salary_min': 130000,
                'salary_max': 180000,
                'job_type': 'full-time',
                'description': 'We are looking for a Senior Data Scientist to join our team and help build innovative machine learning solutions.',
                'requirements': '5+ years of experience in data science, strong Python skills, experience with TensorFlow/PyTorch',
                'benefits': 'Stock options, unlimited PTO, remote flexible, health insurance',
                'skills_required': 'Python,TensorFlow,Machine Learning,SQL,Statistics',
                'match_score': 98
            },
            {
                'title': 'Machine Learning Engineer',
                'company': 'DataFlow Inc',
                'location': 'New York, NY',
                'salary_min': 120000,
                'salary_max': 160000,
                'job_type': 'full-time',
                'description': 'Join our ML team to build scalable machine learning systems and deploy models to production.',
                'requirements': '3+ years ML engineering experience, strong software engineering background, cloud experience',
                'benefits': 'Competitive salary, flexible hours, learning budget, gym membership',
                'skills_required': 'Python,AWS,Docker,Kubernetes,Machine Learning',
                'match_score': 92
            },
            {
                'title': 'AI Research Scientist',
                'company': 'InnovateAI',
                'location': 'Seattle, WA',
                'salary_min': 150000,
                'salary_max': 200000,
                'job_type': 'full-time',
                'description': 'Lead cutting-edge AI research projects and publish papers in top-tier conferences.',
                'requirements': 'PhD in AI/ML or related field, strong publication record, deep learning expertise',
                'benefits': 'Research budget, conference travel, publication support, competitive package',
                'skills_required': 'Deep Learning,Research,Python,PyTorch,Computer Vision',
                'match_score': 88
            },
            {
                'title': 'Data Analyst',
                'company': 'Analytics Pro',
                'location': 'Austin, TX',
                'salary_min': 70000,
                'salary_max': 95000,
                'job_type': 'full-time',
                'description': 'Analyze business data to provide insights and support decision-making processes.',
                'requirements': '2+ years data analysis experience, SQL proficiency, Excel expertise',
                'benefits': 'Health insurance, 401k, professional development, work-life balance',
                'skills_required': 'SQL,Excel,Python,Tableau,Statistics',
                'match_score': 85
            },
            {
                'title': 'Full Stack Developer',
                'company': 'WebTech Solutions',
                'location': 'Remote',
                'salary_min': 80000,
                'salary_max': 120000,
                'job_type': 'full-time',
                'description': 'Build and maintain web applications using modern technologies and best practices.',
                'requirements': '3+ years full-stack development, React/Node.js experience, database knowledge',
                'benefits': 'Remote work, flexible schedule, equipment allowance, health benefits',
                'skills_required': 'React,Node.js,JavaScript,PostgreSQL,MongoDB',
                'match_score': 75
            }
        ]

        for job_data in jobs_data:
            job, created = Job.objects.get_or_create(
                title=job_data['title'],
                company=job_data['company'],
                defaults=job_data
            )
            if created:
                self.stdout.write(
                    self.style.SUCCESS(f'Created job: {job.title} at {job.company}')
                )
            else:
                self.stdout.write(
                    self.style.WARNING(f'Job already exists: {job.title} at {job.company}')
                )

        self.stdout.write(
            self.style.SUCCESS('Successfully populated database with sample jobs')
        )




