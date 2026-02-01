from django.shortcuts import render, get_object_or_404, redirect
from django.contrib import messages
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse, HttpResponseForbidden
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods, require_POST, require_GET
from django.urls import reverse
from django.contrib.auth.models import User
from django.db import transaction
from django.db.models import Q
from django.utils import timezone
from django.conf import settings
import json
import os
import logging

from .models import Job, CandidateProfile, Application, CompanyProfile, ParsedResume, CandidateSkill, JobSkill

logger = logging.getLogger(__name__)


def index(request):
    return render(request, 'index.html')


def login_view(request):
    if request.method == 'POST':
        email = request.POST.get('email')
        password = request.POST.get('password')
        next_url = request.POST.get('next', None)
        
        if email and password:
            # Try to get existing user
            try:
                user = User.objects.get(username=email)
            except User.DoesNotExist:
                messages.error(request, 'Account not found. Please register first.')
                return render(request, 'login.html', {'next': next_url})
            
            # Authenticate the user
            user = authenticate(request, username=email, password=password)
            if user is not None:
                login(request, user)
                messages.success(request, 'Successfully logged in!')
                
                # Smart redirect based on user type
                if next_url:
                    return redirect(next_url)
                elif hasattr(user, 'companyprofile'):
                    # User is a company - redirect to recruiter jobs page
                    return redirect('jobs')  # This goes to recruiter/jobs/
                elif hasattr(user, 'candidateprofile'):
                    # User is a candidate - redirect to candidate dashboard
                    return redirect('candidate')
                else:
                    # Fallback to home
                    return redirect('index')
            else:
                messages.error(request, 'Invalid email or password.')
        else:
            messages.error(request, 'Please provide both email and password.')
    
    return render(request, 'login.html', {'next': request.GET.get('next', '')})


def logout_view(request):
    logout(request)
    messages.success(request, 'Successfully logged out!')
    return redirect('index')


def candidate_page(request):
    # Get or create candidate profile
    profile = None
    if request.user.is_authenticated:
        profile, created = CandidateProfile.objects.get_or_create(
            user=request.user,
            defaults={'profile_strength': 60}
        )
    
    # Get filter parameter
    filter_type = request.GET.get('filter', 'best_match')
    
    # Get recommended jobs with filtering
    if filter_type == 'best_match':
        jobs = Job.objects.all().order_by('-match_score')[:10]
    elif filter_type == 'newest_first':
        jobs = Job.objects.all().order_by('-created_at')[:10]
    elif filter_type == 'salary':
        jobs = Job.objects.all().order_by('-salary_max')[:10]
    else:
        jobs = Job.objects.all()[:10]
    
    # Calculate stats
    applications_count = 0
    interviews_count = 0
    if request.user.is_authenticated:
        applications_count = Application.objects.filter(candidate=request.user).count()
        interviews_count = Application.objects.filter(
            candidate=request.user, 
            status='interview'
        ).count()
    
    context = {
        'user': request.user if request.user.is_authenticated else None,
        'profile': profile,
        'jobs': jobs,
        'applications_count': applications_count,
        'interviews_count': interviews_count,
        'current_filter': filter_type,
    }
    return render(request, 'candidate.html', context)


def recruiter_page(request):
    """
    Entry point for recruiter workspace – redirect to dashboard page.
    """
    return redirect('dashboard')


def recruiter_dashboard(request):
    """
    Dashboard: candidate discovery page.
    For now, this uses placeholder data so the page renders correctly.
    """
    search_term = request.GET.get('q', '')
    min_match = int(request.GET.get('min_match', 0) or 0)
    status = request.GET.get('status', '')
    experience_level = request.GET.get('experience_level', '')
    sort = request.GET.get('sort', 'match')

    context = {
        'candidates': [],  # TODO: wire to real Candidate model if available
        'candidates_loading': False,
        'search_term': search_term,
        'min_match': min_match,
        'status': status,
        'experience_levels': ['Junior', 'Mid-Level', 'Senior', 'Lead', 'Executive'],
        'experience_level': experience_level,
        'sort': sort,
    }
    return render(request, 'dashboard.html', context)


# def recruiter_jobs(request):
#     """
#     Jobs management page – currently shows basic stats with no jobs.
#     """
#     jobs = []  # replace with real queryset when you add a Job entity for recruiter UI
#     active_jobs = 0
#     total_applications = 0

#     context = {
#         'jobs': jobs,
#         'jobs_loading': False,
#         'active_jobs': active_jobs,
#         'total_applications': total_applications,
#     }
#     return render(request, 'jobs.html', context)


@login_required
@login_required
@require_http_methods(["POST"])
def job_change_status(request, job_id, status):
    """
    View to change job status (active/paused/closed)
    """
    job = get_object_or_404(Job, id=job_id)
    
    # Verify the user owns this job
    if not hasattr(request.user, 'companyprofile') or job.company_profile != request.user.companyprofile:
        return HttpResponseForbidden("You don't have permission to modify this job.")
    
    # Validate status
    if status not in ['active', 'paused', 'closed']:
        messages.error(request, 'Invalid status.')
        return redirect('jobs')
    
    # Update status
    job.status = status
    job.save()
    
    messages.success(request, f'Job status updated to {status}.')
    return redirect('jobs')


@login_required
def recruiter_jobs(request):
    """
    Recruiter jobs page – show all jobs posted by this company
    using the recruiter UI.
    """
    # Only company accounts can see this page
    if not hasattr(request.user, 'companyprofile'):
        messages.error(request, 'Only companies can access this page.')
        return redirect('index')

    # Get all jobs posted by this company
    jobs = Job.objects.filter(
        company_profile=request.user.companyprofile
    ).order_by('-created_at')

    # Calculate stats
    active_jobs = jobs.filter(status='open').count()
    total_applications = Application.objects.filter(
        job__company_profile=request.user.companyprofile
    ).count()

    context = {
        'jobs': jobs,
        'jobs_loading': False,
        'active_jobs': active_jobs,
        'total_applications': total_applications,
        'total_jobs': jobs.count(),
    }

    # Use the recruiter jobs template
    return render(request, 'jobs.html', context)


def recruiter_pipeline(request):
    """
    Pipeline (Kanban) page – placeholder data so layout renders.
    """
    stages = [
        {'id': 'applied', 'label': 'Applied', 'color': 'bg-slate-100 border-slate-300'},
        {'id': 'screening', 'label': 'Screening', 'color': 'bg-blue-100 border-blue-300'},
        {'id': 'phone_interview', 'label': 'Phone Interview', 'color': 'bg-purple-100 border-purple-300'},
        {'id': 'technical_interview', 'label': 'Technical', 'color': 'bg-indigo-100 border-indigo-300'},
        {'id': 'final_interview', 'label': 'Final Round', 'color': 'bg-amber-100 border-amber-300'},
        {'id': 'offer', 'label': 'Offer', 'color': 'bg-emerald-100 border-emerald-300'},
        {'id': 'hired', 'label': 'Hired', 'color': 'bg-green-100 border-green-300'},
        {'id': 'rejected', 'label': 'Rejected', 'color': 'bg-rose-100 border-rose-300'},
    ]

    applications_by_stage = {s['id']: [] for s in stages}

    context = {
        'stages': stages,
        'applications_by_stage': applications_by_stage,
        'jobs': [],
        'selected_job_id': request.GET.get('job_id') or '',
    }
    return render(request, 'pipeline.html', context)


def recruiter_schedule(request):
    """
    """
    from datetime import date, timedelta

    selected_date = date.fromisoformat(request.GET.get('date')) if request.GET.get('date') else date.today()
    
    # For demo purposes, we'll use empty lists
    upcoming_interviews = []
    day_interviews = []

    context = {
        'selected_date': selected_date,
        'upcoming_interviews': upcoming_interviews,
        'day_interviews': day_interviews,
    }
    return render(request, 'schedule.html', context)


def interview_create(request):
    """
    View for creating a new interview.
    This is a placeholder that shows a message since we don't have the full implementation.
    In a real application, this would handle the interview creation form.
    """
    from django.contrib import messages
    from django.shortcuts import redirect
    
    # For now, just show a success message and redirect back to schedule
    messages.success(request, 'Interview creation will be implemented here.')
    return redirect('schedule')


def recruiter_analytics(request):
    """
    Analytics dashboard – renders with zeroed metrics.
    """
    pipeline_data = [
        {'stage': 'Applied', 'count': 0},
        {'stage': 'Screening', 'count': 0},
        {'stage': 'Interview', 'count': 0},
        {'stage': 'Offer', 'count': 0},
        {'stage': 'Hired', 'count': 0},
    ]
    max_pipeline_count = max((row['count'] for row in pipeline_data), default=0)

    source_data = []  # e.g. [{'name': 'LinkedIn', 'value': 10, 'percent': 50, 'color': '#6366f1'}, ...]
    top_jobs = []
    max_job_applications = 0

    context = {
        'total_applications': 0,
        'active_jobs': 0,
        'scheduled_interviews': 0,
        'conversion_rate': 0,
        'pipeline_data': pipeline_data,
        'max_pipeline_count': max_pipeline_count,
        'source_data': source_data,
        'top_jobs': top_jobs,
        'max_job_applications': max_job_applications,
    }
    return render(request, 'analytics.html', context)


def email_template_create(request):
    """
    View for creating a new email template.
    This is a placeholder that shows a message since we don't have the full implementation.
    In a real application, this would handle the email template creation form.
    """
    from django.contrib import messages
    from django.shortcuts import redirect
    
    # For now, just show a success message and redirect back to templates list
    messages.info(request, 'Email template creation will be implemented here.')
    return redirect('email_templates')


def recruiter_email_templates(request):
    """
    Email templates page – no templates yet.
    """
    context = {
        'loading': False,
        'templates': [],
    }
    return render(request, 'email_templates.html', context)


# ===== Registration for job seekers and companies =====

def register_job_seeker(request):
    if request.method == 'POST':
        name = request.POST.get('name')
        email = request.POST.get('email')
        phone = request.POST.get('phone')
        password = request.POST.get('password')

        if not all([name, email, password]):
            messages.error(request, 'Please fill in all required fields.')
            return render(request, 'register_job_seeker.html')

        if User.objects.filter(username=email).exists():
            messages.error(request, 'Email already registered.')
            return render(request, 'register_job_seeker.html')

        with transaction.atomic():
            user = User.objects.create_user(
                username=email,
                email=email,
                first_name=name,
                password=password,
            )
            CandidateProfile.objects.create(user=user)
        messages.success(request, 'Account created. Please log in.')
        return redirect('login')

    return render(request, 'register_job_seeker.html')


def register_company(request):
    if request.method == 'POST':
        company_name = request.POST.get('company_name')
        email = request.POST.get('email')
        password = request.POST.get('password')
        industry = request.POST.get('industry')

        if not all([company_name, email, password]):
            messages.error(request, 'Please fill in all required fields.')
            return render(request, 'register_company.html')

        if User.objects.filter(username=email).exists():
            messages.error(request, 'Email already registered.')
            return render(request, 'register_company.html')

        with transaction.atomic():
            user = User.objects.create_user(
                username=email,
                email=email,
                first_name=company_name,
                password=password,
            )
            CompanyProfile.objects.create(
                user=user,
                company_name=company_name,
                industry=industry or '',
            )
        messages.success(request, 'Company account created. Please log in.')
        return redirect('login')

    return render(request, 'register_company.html')


# ===== Job seeker side: browsing and applying =====

def job_list(request):
    q = request.GET.get('q', '')
    category = request.GET.get('category', '')
    location = request.GET.get('location', '')
    skills = request.GET.get('skills', '')

    jobs = Job.objects.filter(status='open')

    if q:
        jobs = jobs.filter(Q(title__icontains=q) | Q(description__icontains=q))
    if category:
        jobs = jobs.filter(category__iexact=category)
    if location:
        jobs = jobs.filter(location__icontains=location)
    if skills:
        skill_list = [s.strip().lower() for s in skills.split(',')]
        for s in skill_list:
            jobs = jobs.filter(skills_required__icontains=s)

    context = {
        'jobs': jobs.select_related('company_profile'),
        'categories': Job.objects.exclude(category='').values_list('category', flat=True).distinct(),
    }
    return render(request, 'jobs_list.html', context)


@login_required
def apply_for_job(request, job_id):
    job = get_object_or_404(Job, id=job_id, status='open')

    if hasattr(request.user, 'companyprofile'):
        messages.error(request, 'Company accounts cannot apply for jobs.')
        return redirect('job_detail', job_id=job_id)

    if Application.objects.filter(candidate=request.user, job=job).exists():
        messages.info(request, 'You have already applied for this job.')
        return redirect('job_detail', job_id=job_id)

    profile = CandidateProfile.objects.filter(user=request.user).first()
    if not profile or not profile.resume_file:
        messages.error(request, 'Please upload your resume in your profile before applying.')
        return redirect('candidate')

    Application.objects.create(candidate=request.user, job=job)
    messages.success(request, 'Application submitted successfully.')
    return redirect('job_detail', job_id=job_id)


@login_required
def recommended_jobs(request):
    profile = CandidateProfile.objects.filter(user=request.user).first()
    if not profile or not profile.skills:
        jobs = Job.objects.filter(status='open')[:20]
    else:
        try:
            skills = [s.lower() for s in json.loads(profile.skills)]
        except Exception:
            skills = []
        qs = Job.objects.filter(status='open')
        for s in skills:
            qs = qs | Job.objects.filter(skills_required__icontains=s)
        jobs = qs.distinct()[:20]

    return render(request, 'jobs_recommended.html', {'jobs': jobs})


# ===== Company side: posting and managing jobs =====

@login_required
def company_jobs(request):
    if not hasattr(request.user, 'companyprofile'):
        messages.error(request, 'Only companies can access this page.')
        return redirect('index')

    jobs = Job.objects.filter(company_profile=request.user.companyprofile)
    return render(request, 'company_jobs.html', {'jobs': jobs})


@login_required
@require_http_methods(["GET", "POST"])
def company_edit_job(request, job_id):
    """
    Edit an existing job posting
    """
    if not hasattr(request.user, 'companyprofile'):
        messages.error(request, 'Only companies can edit jobs.')
        return redirect('index')
    
    job = get_object_or_404(Job, id=job_id, company_profile=request.user.companyprofile)
    
    if request.method == 'POST':
        job.title = request.POST.get('title', job.title)
        job.location = request.POST.get('location', job.location)
        job.salary_min = request.POST.get('salary_min', job.salary_min) or 0
        job.salary_max = request.POST.get('salary_max', job.salary_max) or 0
        job.job_type = request.POST.get('job_type', job.job_type)
        job.category = request.POST.get('category', job.category) or ''
        job.description = request.POST.get('description', job.description)
        job.requirements = request.POST.get('requirements', job.requirements)
        job.benefits = request.POST.get('benefits', job.benefits) or ''
        job.skills_required = request.POST.get('skills_required', job.skills_required) or ''
        job.save()

        # Phase 3: Re-extract skills after job update
        skills_count = extract_job_skills(job)
        logger.info(f"Updated job '{job.title}' with {skills_count} extracted skills")

        messages.success(request, 'Job updated successfully.')
        return redirect('jobs')
    
    context = {
        'job': job,
        'editing': True
    }
    return render(request, 'company_create_job.html', context)


def company_create_job(request):
    if not hasattr(request.user, 'companyprofile'):
        messages.error(request, 'Only companies can post jobs.')
        return redirect('index')

    if request.method == 'POST':
        cp = request.user.companyprofile
        job = Job.objects.create(
            company_profile=cp,
            company=cp.company_name,
            title=request.POST.get('title'),
            location=request.POST.get('location'),
            salary_min=request.POST.get('salary_min') or 0,
            salary_max=request.POST.get('salary_max') or 0,
            job_type=request.POST.get('job_type'),
            category=request.POST.get('category') or '',
            description=request.POST.get('description'),
            requirements=request.POST.get('requirements'),
            benefits=request.POST.get('benefits') or '',
            skills_required=request.POST.get('skills_required') or '',
        )

        # Phase 3: Extract skills from job description using NLP
        skills_count = extract_job_skills(job)
        logger.info(f"Created job '{job.title}' with {skills_count} extracted skills")

        messages.success(request, 'Job posted successfully.')
        return redirect('jobs')  # recruiter jobs page

    return render(request, 'company_create_job.html', {'editing': False})


# @login_required
# def company_job_applicants(request, job_id):
#     if not hasattr(request.user, 'companyprofile'):
#         messages.error(request, 'Only companies can access this page.')
#         return redirect('index')

#     job = get_object_or_404(Job, id=job_id, company_profile=request.user.companyprofile)
#     apps = Application.objects.filter(job=job).select_related('candidate')
#     return render(request, 'company_job_applicants.html', {'job': job, 'applications': apps})

@login_required
def company_job_applicants(request, job_id):
    if not hasattr(request.user, 'companyprofile'):
        messages.error(request, 'Only companies can access this page.')
        return redirect('index')
    
    job = get_object_or_404(Job, id=job_id, company_profile=request.user.companyprofile)
    apps = Application.objects.filter(job=job).select_related('candidate')
    
    # Get status choices from the model
    status_choices = Application._meta.get_field('status').choices
    
    return render(request, 'company_job_applicants.html', {
        'job': job, 
        'applications': apps,
        'status_choices': status_choices
    })


@login_required
@require_http_methods(["POST"])
def company_update_application_status(request, application_id):
    if not hasattr(request.user, 'companyprofile'):
        messages.error(request, 'Only companies can access this page.')
        return redirect('index')

    app = get_object_or_404(Application, id=application_id, job__company_profile=request.user.companyprofile)
    new_status = request.POST.get('status')
    valid_statuses = dict(Application._meta.get_field('status').choices).keys()
    if new_status in valid_statuses:
        app.status = new_status
        app.save()
        messages.success(request, 'Status updated.')
    else:
        messages.error(request, 'Invalid status.')

    return redirect('company_job_applicants', job_id=app.job.id)


def job_detail(request, job_id):
    job = get_object_or_404(Job, id=job_id)
    
    # Get or create candidate profile
    profile = None
    if request.user.is_authenticated:
        profile, created = CandidateProfile.objects.get_or_create(
            user=request.user,
            defaults={'profile_strength': 60}
        )
    
    # Check if user has already applied
    has_applied = False
    if request.user.is_authenticated:
        has_applied = Application.objects.filter(
            candidate=request.user,
            job=job
        ).exists()
    
    # Parse skills required
    skills_required = []
    if job.skills_required:
        try:
            skills_required = json.loads(job.skills_required)
        except Exception:
            skills_required = []
    
    context = {
        'job': job,
        'profile': profile,
        'has_applied': has_applied,
        'skills_required': skills_required,
        'user': request.user if request.user.is_authenticated else None,
    }
    return render(request, 'job_detail.html', context)


def extract_candidate_skills(profile, sections: dict, full_text: str) -> int:
    """
    Extract skills from resume and store in database.

    Phase 3 implementation per PROJECT_PLAN.md.

    Args:
        profile: CandidateProfile instance
        sections: Dict of resume sections from parser
        full_text: Full cleaned resume text

    Returns:
        Number of skills extracted
    """
    from ann.services.skill_extractor import DynamicSkillExtractor

    extractor = DynamicSkillExtractor()
    all_skills = []
    seen_normalized = set()

    # Map resume sections to CandidateSkill source choices
    section_mapping = {
        'skills': 'skills_section',
        'experience': 'experience',
        'projects': 'projects',
        'education': 'education',
        'summary': 'summary',
    }

    # Extract skills from each section
    for section_name, section_text in sections.items():
        if not section_text or not section_text.strip():
            continue

        source = section_mapping.get(section_name, 'full_text')
        skills = extractor.extract_skills(section_text, section_name)

        for skill in skills:
            normalized = skill['normalized']
            if normalized not in seen_normalized:
                seen_normalized.add(normalized)
                skill['db_source'] = source
                all_skills.append(skill)

    # Also extract from full text (catches skills missed in section parsing)
    full_text_skills = extractor.extract_skills(full_text, 'full_text')
    for skill in full_text_skills:
        normalized = skill['normalized']
        if normalized not in seen_normalized:
            seen_normalized.add(normalized)
            skill['db_source'] = 'full_text'
            all_skills.append(skill)

    # Clear existing skills for this candidate
    CandidateSkill.objects.filter(candidate=profile).delete()

    # Store extracted skills in database
    skills_created = 0
    for skill_data in all_skills:
        try:
            # Estimate proficiency from context
            proficiency = extractor.estimate_proficiency(
                skill_data['skill'],
                full_text
            )

            CandidateSkill.objects.create(
                candidate=profile,
                skill_text=skill_data['skill'][:200],  # Truncate if too long
                normalized_text=skill_data['normalized'][:200],
                proficiency_level=proficiency,
                source=skill_data.get('db_source', 'full_text'),
                context=skill_data.get('context', '')[:500],  # Truncate context
                confidence_score=skill_data.get('confidence', 0.7),
                category=skill_data.get('category', 'domain'),
            )
            skills_created += 1
        except Exception as e:
            logger.warning(f"Failed to save skill '{skill_data.get('skill', '')}': {e}")
            continue

    logger.info(f"Extracted {skills_created} skills for candidate {profile.user.username}")
    return skills_created


def extract_job_skills(job) -> int:
    """
    Extract skills from job description and requirements.

    Phase 3 implementation per PROJECT_PLAN.md.

    Args:
        job: Job instance

    Returns:
        Number of skills extracted
    """
    from ann.services.skill_extractor import DynamicSkillExtractor

    extractor = DynamicSkillExtractor()

    # Combine description and requirements
    description = job.description or ''
    requirements = job.requirements or ''

    # Extract skills with importance levels
    skills = extractor.extract_job_skills(description, requirements)

    # Clear existing skills for this job
    JobSkill.objects.filter(job=job).delete()

    # Store extracted skills
    skills_created = 0
    for skill_data in skills:
        try:
            JobSkill.objects.create(
                job=job,
                skill_text=skill_data['skill'][:200],
                normalized_text=skill_data['normalized'][:200],
                importance=skill_data.get('importance', 'required'),
                category=skill_data.get('category', 'domain'),
                context=skill_data.get('context', '')[:500],
            )
            skills_created += 1
        except Exception as e:
            logger.warning(f"Failed to save job skill '{skill_data.get('skill', '')}': {e}")
            continue

    logger.info(f"Extracted {skills_created} skills for job {job.title}")
    return skills_created


@csrf_exempt
@require_http_methods(["POST"])
def upload_resume(request):
    """
    Upload and parse a resume file (PDF or DOCX).

    Phase 2 implementation per PROJECT_PLAN.md:
    - Validates file type and size
    - Extracts text from PDF/DOCX
    - Detects resume sections
    - Stores parsed data for skill extraction (Phase 3)

    Returns JSON with parsing results.
    """
    if not request.user.is_authenticated:
        return JsonResponse({'error': 'Authentication required'}, status=401)

    if 'resume' not in request.FILES:
        return JsonResponse({'error': 'No file uploaded'}, status=400)

    resume_file = request.FILES['resume']

    # Validate file type
    allowed_extensions = getattr(settings, 'ALLOWED_RESUME_EXTENSIONS', ['.pdf', '.docx'])
    file_ext = os.path.splitext(resume_file.name)[1].lower()
    if file_ext not in allowed_extensions:
        return JsonResponse({
            'error': f'Invalid file type. Allowed: {", ".join(allowed_extensions)}'
        }, status=400)

    # Validate file size (5MB max per PRD.md)
    max_size = getattr(settings, 'FILE_UPLOAD_MAX_MEMORY_SIZE', 5 * 1024 * 1024)
    if resume_file.size > max_size:
        return JsonResponse({
            'error': f'File too large. Maximum size: {max_size // (1024 * 1024)}MB'
        }, status=400)

    try:
        # Get or create candidate profile
        profile, created = CandidateProfile.objects.get_or_create(user=request.user)

        # Save the file first
        profile.resume_file = resume_file
        profile.save()

        # Now parse the resume
        from ann.services.resume_parser import ResumeParser

        parser = ResumeParser()
        file_path = profile.resume_file.path

        # Extract text
        raw_text = parser.extract_text(file_path)
        cleaned_text = parser.clean_text(raw_text)
        sections = parser.detect_sections(raw_text)
        contact_info = parser.extract_contact_info(raw_text)

        # Calculate completeness score
        completeness_score = parser.calculate_completeness_score(sections)

        # Get section stats
        section_stats = parser.get_section_stats(sections)

        # Create or update ParsedResume
        parsed_resume, pr_created = ParsedResume.objects.update_or_create(
            candidate=profile,
            defaults={
                'raw_text': raw_text,
                'cleaned_text': cleaned_text,
                'sections_json': sections,
                'parsing_status': 'completed',
                'parsed_at': timezone.now(),
                'error_message': '',
            }
        )

        # Update profile strength based on resume completeness
        profile.profile_strength = completeness_score
        profile.save()

        # Phase 3: Extract skills from resume using NLP
        skills_extracted = extract_candidate_skills(profile, sections, cleaned_text)

        # Prepare response
        sections_found = [k for k, v in sections.items() if v.strip()]

        logger.info(
            f"Resume parsed for user {request.user.username}: "
            f"{len(cleaned_text)} chars, {len(sections_found)} sections, "
            f"{skills_extracted} skills extracted"
        )

        return JsonResponse({
            'success': True,
            'message': 'Resume uploaded and parsed successfully',
            'profile_strength': profile.profile_strength,
            'parsing_results': {
                'total_characters': len(cleaned_text),
                'total_words': parser.get_word_count(cleaned_text),
                'sections_found': sections_found,
                'contact_info': contact_info,
                'completeness_score': completeness_score,
                'skills_extracted': skills_extracted,
            }
        })

    except ValueError as e:
        # File validation errors
        logger.warning(f"Resume validation error for {request.user.username}: {e}")
        return JsonResponse({'error': str(e)}, status=400)

    except Exception as e:
        # Parsing errors - still save the file but mark as failed
        logger.error(f"Resume parsing failed for {request.user.username}: {e}")

        # Try to mark parsing as failed
        try:
            profile = CandidateProfile.objects.get(user=request.user)
            ParsedResume.objects.update_or_create(
                candidate=profile,
                defaults={
                    'parsing_status': 'failed',
                    'error_message': str(e),
                }
            )
        except Exception:
            pass

        return JsonResponse({
            'success': True,
            'message': 'Resume uploaded but parsing failed. You can still apply for jobs.',
            'error_detail': str(e),
            'profile_strength': profile.profile_strength if profile else 0,
        })


@csrf_exempt
@require_http_methods(["POST"])
def apply_job(request, job_id):
    if not request.user.is_authenticated:
        return JsonResponse({'error': 'Authentication required'}, status=401)
    
    job = get_object_or_404(Job, id=job_id)
    application, created = Application.objects.get_or_create(
        candidate=request.user,
        job=job
    )
    
    if created:
        return JsonResponse({
            'success': True,
            'message': 'Application submitted successfully'
        })
    else:
        return JsonResponse({
            'error': 'You have already applied for this job'
        }, status=400)


# @login_required
# def recruiter_job_detail(request, job_id):
#     """
#     Recruiter-side job detail page showing job info + applicants
#     """
#     if not hasattr(request.user, 'companyprofile'):
#         messages.error(request, 'Only companies can access this page.')
#         return redirect('index')
    
#     # Get the job (must belong to this company)
#     job = get_object_or_404(Job, id=job_id, company_profile=request.user.companyprofile)
    
#     # Get all applications for this job
#     applications = Application.objects.filter(job=job).select_related('candidate').order_by('-applied_at')
    
#     context = {
#         'job': job,
#         'applications': applications,
#     }
    
#     return render(request, 'recruiter_job_detail.html', context)


@login_required
def recruiter_job_detail(request, job_id):
    """
    Recruiter-side job detail page with integrated candidate discovery
    Shows job info + ALL applicants with search/filter features
    """
    if not hasattr(request.user, 'companyprofile'):
        messages.error(request, 'Only companies can access this page.')
        return redirect('index')
    
    # Get the job (must belong to this company)
    job = get_object_or_404(Job, id=job_id, company_profile=request.user.companyprofile)
    
    # Get search and filter parameters
    search_term = request.GET.get('q', '')
    status_filter = request.GET.get('status', '')
    sort_by = request.GET.get('sort', 'recent')
    
    # Start with all applications for this job
    applications = Application.objects.filter(job=job).select_related('candidate', 'candidate__candidateprofile')
    
    # Apply search filter
    if search_term:
        applications = applications.filter(
            Q(candidate__first_name__icontains=search_term) |
            Q(candidate__last_name__icontains=search_term) |
            Q(candidate__email__icontains=search_term)
        )
    
    # Apply status filter
    if status_filter:
        applications = applications.filter(status=status_filter)
    
    # Apply sorting
    if sort_by == 'recent':
        applications = applications.order_by('-applied_at')
    elif sort_by == 'name':
        applications = applications.order_by('candidate__first_name')
    elif sort_by == 'status':
        applications = applications.order_by('status')
    
    # Calculate stats
    total_applicants = Application.objects.filter(job=job).count()
    new_applicants = Application.objects.filter(job=job, status='applied').count()
    in_review = Application.objects.filter(job=job, status__in=['screening', 'interview']).count()
    
    context = {
        'job': job,
        'applications': applications,
        'search_term': search_term,
        'status_filter': status_filter,
        'sort_by': sort_by,
        'total_applicants': total_applicants,
        'new_applicants': new_applicants,
        'in_review': in_review,
    }
    
    return render(request, 'recruiter_job_detail.html', context)


@login_required
def recruiter_job_info(request, job_id):
    """
    Simple job information page (description, requirements, benefits only)
    """
    if not hasattr(request.user, 'companyprofile'):
        messages.error(request, 'Only companies can access this page.')
        return redirect('index')

    job = get_object_or_404(Job, id=job_id, company_profile=request.user.companyprofile)
    applications = Application.objects.filter(job=job)

    context = {
        'job': job,
        'applications': applications,
    }

    return render(request, 'recruiter_job_info.html', context)


# =============================================================================
# PHASE 2: Resume Parsing API Endpoints
# =============================================================================

@login_required
@require_GET
def get_parsed_resume(request):
    """
    Get the parsed resume data for the current user.

    Returns:
    - Parsing status
    - Extracted sections
    - Contact info
    - Completeness score
    """
    try:
        profile = CandidateProfile.objects.get(user=request.user)
    except CandidateProfile.DoesNotExist:
        return JsonResponse({
            'error': 'No candidate profile found'
        }, status=404)

    try:
        parsed = ParsedResume.objects.get(candidate=profile)

        # Extract contact info from raw text
        from ann.services.resume_parser import ResumeParser
        parser = ResumeParser()
        contact_info = parser.extract_contact_info(parsed.raw_text)

        return JsonResponse({
            'success': True,
            'parsing_status': parsed.parsing_status,
            'parsed_at': parsed.parsed_at.isoformat() if parsed.parsed_at else None,
            'sections': parsed.sections_json,
            'contact_info': contact_info,
            'stats': {
                'total_characters': len(parsed.cleaned_text),
                'total_words': parser.get_word_count(parsed.cleaned_text),
                'sections_found': [k for k, v in parsed.sections_json.items() if v.strip()],
            },
            'completeness_score': profile.profile_strength,
            'error_message': parsed.error_message if parsed.parsing_status == 'failed' else None,
        })

    except ParsedResume.DoesNotExist:
        return JsonResponse({
            'success': False,
            'parsing_status': 'not_uploaded',
            'message': 'No resume has been uploaded yet'
        })


@login_required
@require_POST
def reparse_resume(request):
    """
    Re-parse an existing uploaded resume.

    Useful when parsing logic is updated or if initial parsing failed.
    """
    try:
        profile = CandidateProfile.objects.get(user=request.user)
    except CandidateProfile.DoesNotExist:
        return JsonResponse({'error': 'No candidate profile found'}, status=404)

    if not profile.resume_file:
        return JsonResponse({'error': 'No resume file uploaded'}, status=400)

    try:
        from ann.services.resume_parser import ResumeParser

        parser = ResumeParser()
        file_path = profile.resume_file.path

        # Re-extract and parse
        raw_text = parser.extract_text(file_path)
        cleaned_text = parser.clean_text(raw_text)
        sections = parser.detect_sections(raw_text)
        completeness_score = parser.calculate_completeness_score(sections)

        # Update ParsedResume
        parsed_resume, created = ParsedResume.objects.update_or_create(
            candidate=profile,
            defaults={
                'raw_text': raw_text,
                'cleaned_text': cleaned_text,
                'sections_json': sections,
                'parsing_status': 'completed',
                'parsed_at': timezone.now(),
                'error_message': '',
            }
        )

        # Update profile strength
        profile.profile_strength = completeness_score
        profile.save()

        logger.info(f"Resume re-parsed for user {request.user.username}")

        return JsonResponse({
            'success': True,
            'message': 'Resume re-parsed successfully',
            'completeness_score': completeness_score,
            'sections_found': [k for k, v in sections.items() if v.strip()],
        })

    except Exception as e:
        logger.error(f"Resume re-parsing failed for {request.user.username}: {e}")
        return JsonResponse({
            'error': f'Re-parsing failed: {str(e)}'
        }, status=500)
