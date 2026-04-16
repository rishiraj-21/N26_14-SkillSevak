from django.shortcuts import render, get_object_or_404, redirect
from django.contrib import messages
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse, HttpResponseForbidden
from django.views.decorators.csrf import csrf_exempt, ensure_csrf_cookie
from django.views.decorators.http import require_http_methods, require_POST, require_GET
from django.urls import reverse
from django.utils.http import url_has_allowed_host_and_scheme
from django.contrib.auth.models import User
from django.db import transaction
from django.db.models import Q, Count
from django.utils import timezone
from django.conf import settings
import json
import os
import logging

from datetime import date, timedelta
from .models import Job, CandidateProfile, Application, CompanyProfile, ParsedResume, CandidateSkill, JobSkill, MatchScore, Interview

logger = logging.getLogger(__name__)


@ensure_csrf_cookie
def index(request):
    return render(request, 'index.html')


@ensure_csrf_cookie
def login_view(request):
    if request.method == 'POST':
        email = request.POST.get('email')
        password = request.POST.get('password')
        next_url = request.POST.get('next', '')
        
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
                if next_url and url_has_allowed_host_and_scheme(next_url, allowed_hosts={request.get_host()}):
                    return redirect(next_url)
                elif hasattr(user, 'companyprofile'):
                    # User is a company - redirect to company jobs page
                    return redirect('company_jobs')
                elif hasattr(user, 'candidateprofile'):
                    # User is a candidate - redirect to candidate dashboard
                    return redirect('candidate')
                else:
                    # Fallback to home
                    return redirect('index')
            else:
                messages.error(request, 'Invalid email or password.')
                return render(request, 'login.html', {'next': next_url})
        else:
            messages.error(request, 'Please provide both email and password.')
            return render(request, 'login.html', {'next': next_url})

    return render(request, 'login.html', {'next': request.GET.get('next', '')})


def logout_view(request):
    logout(request)
    messages.success(request, 'Successfully logged out!')
    return redirect('index')


def _save_match_score(profile, job, match_data):
    """Persist a computed match score to the MatchScore DB table."""
    try:
        breakdown = match_data.get('breakdown', {})
        MatchScore.objects.update_or_create(
            candidate=profile,
            job=job,
            defaults={
                'overall_score': match_data['overall_score'],
                'semantic_similarity': breakdown.get('semantic_similarity', 0),
                'skill_match_score': breakdown.get('skill_match', 0),
                'experience_match_score': breakdown.get('experience_match', 0),
                'education_match_score': breakdown.get('education_match', 0),
                'profile_completeness_score': breakdown.get('profile_completeness', 0),
                'matched_skills': match_data.get('matched_skills', []),
                'missing_skills': match_data.get('missing_skills', []),
                'suggestions': match_data.get('suggestions', []),
                'is_valid': True,
            }
        )
    except Exception as e:
        logger.warning(f"Failed to save match score for {profile.user.username} <-> {job.title}: {e}")




@ensure_csrf_cookie
def candidate_page(request):
    """
    Candidate dashboard with AI-powered job matching.

    Shows jobs ranked by match score calculated using:
    - Semantic similarity (resume vs job)
    - Skill overlap with category weighting
    - Experience match
    - Education relevance
    - Profile completeness

    Phase 4/5: Uses MatchingEngine with ANN predictions.
    """
    # Get or create candidate profile
    profile = None
    jobs_list = []

    if request.user.is_authenticated:
        profile, created = CandidateProfile.objects.get_or_create(
            user=request.user,
            defaults={'profile_strength': 60}
        )

        # Update profile strength
        profile.profile_strength = profile.calculate_profile_strength()
        profile.save(update_fields=['profile_strength'])

    # Get filter parameter
    filter_type = request.GET.get('filter', 'best_match')

    # Get all open jobs
    jobs = list(Job.objects.filter(status='open'))

    # Auto-parse resume if uploaded but never parsed
    if request.user.is_authenticated and profile and profile.resume_file:
        parsed_exists = ParsedResume.objects.filter(candidate=profile, parsing_status='completed').exists()
        if not parsed_exists:
            try:
                _upload_resume_sync(request, profile)
                logger.info(f"Auto-parsed resume for {request.user.username} on page load")
            except Exception as e:
                logger.warning(f"Auto-parse failed for {request.user.username}: {e}")

    # Calculate real match scores for authenticated users with resume
    if request.user.is_authenticated and profile and profile.resume_file:
        from ann.services.matching_engine import MatchingEngine

        try:
            engine = MatchingEngine()

            # Calculate matches, save to DB, and attach to job objects
            for job in jobs:
                match_data = engine.calculate_match(profile, job)
                # Persist to MatchScore table
                _save_match_score(profile, job, match_data)
                # Attach match data directly to job object for template access
                job.match_score = match_data['overall_score']
                job.match_data = match_data
                job.matched_skills = match_data.get('matched_skills', [])
                job.missing_skills = match_data.get('missing_skills', [])
                job.suggestions = match_data.get('suggestions', [])
                job.scoring_method = match_data.get('scoring_method', 'unknown')
                # Breakdown scores for display
                breakdown = match_data.get('breakdown', {})
                job.skill_match_pct = breakdown.get('skill_match', 0)
                job.experience_match_pct = breakdown.get('experience_match', 0)
                job.semantic_match_pct = breakdown.get('semantic_similarity', 0)
                jobs_list.append(job)

        except Exception as e:
            logger.error(f"Match calculation failed: {e}")
            # Fallback to jobs without match scores
            for job in jobs:
                job.match_score = 0
                job.match_data = None
                jobs_list.append(job)
    else:
        # No resume uploaded - show jobs without match scores
        for job in jobs:
            job.match_score = 0
            job.match_data = None
            jobs_list.append(job)

    # Apply sorting based on filter
    if filter_type == 'best_match':
        jobs_list.sort(key=lambda x: x.match_score, reverse=True)
    elif filter_type == 'newest_first':
        jobs_list.sort(key=lambda x: x.created_at, reverse=True)
    elif filter_type == 'salary':
        jobs_list.sort(key=lambda x: x.salary_max or 0, reverse=True)

    # Limit to top 10
    jobs_list = jobs_list[:10]

    # Calculate stats
    applications_count = 0
    interviews_count = 0
    high_matches_count = 0

    if request.user.is_authenticated:
        applications_count = Application.objects.filter(candidate=request.user).count()
        interviews_count = Application.objects.filter(
            candidate=request.user,
            status='interview'
        ).count()
        # Count jobs with 70%+ match
        high_matches_count = len([j for j in jobs_list if j.match_score >= 70])

    # Extra context for sidebar
    candidate_skills_count = 0
    has_parsed_resume = False
    top_candidate_skills = []
    if profile and request.user.is_authenticated:
        candidate_skills_count = CandidateSkill.objects.filter(candidate=profile).count()
        has_parsed_resume = ParsedResume.objects.filter(
            candidate=profile, parsing_status='completed'
        ).exists()
        top_candidate_skills = list(
            CandidateSkill.objects.filter(candidate=profile)
            .order_by('-confidence_score')
            .values_list('skill_text', flat=True)[:8]
        )

    context = {
        'user': request.user if request.user.is_authenticated else None,
        'profile': profile,
        'jobs': jobs_list,
        'applications_count': applications_count,
        'interviews_count': interviews_count,
        'high_matches_count': high_matches_count,
        'current_filter': filter_type,
        'has_resume': bool(profile and profile.resume_file),
        'has_parsed_resume': has_parsed_resume,
        'candidate_skills_count': candidate_skills_count,
        'top_candidate_skills': top_candidate_skills,
    }
    return render(request, 'candidate.html', context)


def recruiter_page(request):
    """
    Entry point for recruiter workspace – redirect to jobs page.
    """
    return redirect('jobs')


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
    ).order_by('-created_at').prefetch_related('application_set')

    # Calculate stats
    active_jobs = jobs.filter(status='open').count()
    total_applications = Application.objects.filter(
        job__company_profile=request.user.companyprofile
    ).count()

    # Add applicant data with match scores for each job
    from ann.services.matching_engine import MatchingEngine
    engine = MatchingEngine()

    jobs_with_data = []
    for job in jobs:
        apps = job.application_set.all().select_related('candidate')
        applicant_count = apps.count()

        # Calculate match scores for applicants
        match_scores = []
        for app in apps[:10]:
            try:
                profile = CandidateProfile.objects.get(user=app.candidate)
                match_data = engine.calculate_match(profile, job)
                score = match_data.get('overall_score', 0)
                match_scores.append(score)
            except CandidateProfile.DoesNotExist:
                pass

        avg_score = sum(match_scores) / len(match_scores) if match_scores else 0
        top_score = max(match_scores) if match_scores else 0

        jobs_with_data.append({
            'job': job,
            'applicant_count': applicant_count,
            'avg_score': round(avg_score, 1),
            'top_score': round(top_score, 1),
        })

    context = {
        'jobs': jobs,
        'jobs_data': jobs_with_data,
        'jobs_loading': False,
        'active_jobs': active_jobs,
        'total_applications': total_applications,
        'total_jobs': jobs.count(),
    }

    # Use the recruiter jobs template
    return render(request, 'jobs.html', context)


@login_required
def recruiter_pipeline(request):
    """
    Pipeline (Kanban) page — real applications grouped by stage.
    """
    if not hasattr(request.user, 'companyprofile'):
        return redirect('index')

    company = request.user.companyprofile
    job_id = request.GET.get('job_id', '')
    jobs = Job.objects.filter(company_profile=company).order_by('-created_at')

    apps_qs = Application.objects.filter(
        job__company_profile=company
    ).select_related('candidate', 'job').order_by('-applied_at')

    if job_id:
        apps_qs = apps_qs.filter(job_id=job_id)

    all_apps = list(apps_qs)

    # Bulk-fetch CandidateProfiles (avoid N+1)
    user_ids = [a.candidate_id for a in all_apps]
    profiles = {cp.user_id: cp for cp in CandidateProfile.objects.filter(user_id__in=user_ids)}

    # Live match engine
    from ann.services.matching_engine import MatchingEngine
    engine = MatchingEngine()

    STAGE_DEFS = [
        {'id': 'applied',         'label': 'Applied',        'hdr_bg': 'bg-slate-100',   'hdr_border': 'border-slate-300',   'badge_bg': 'bg-slate-200',   'badge_text': 'text-slate-700'},
        {'id': 'screening',       'label': 'Screening',      'hdr_bg': 'bg-blue-50',     'hdr_border': 'border-blue-300',    'badge_bg': 'bg-blue-200',    'badge_text': 'text-blue-800'},
        {'id': 'phone_interview', 'label': 'Phone Interview', 'hdr_bg': 'bg-purple-50',  'hdr_border': 'border-purple-300',  'badge_bg': 'bg-purple-200',  'badge_text': 'text-purple-800'},
        {'id': 'technical',       'label': 'Technical',      'hdr_bg': 'bg-indigo-50',   'hdr_border': 'border-indigo-300',  'badge_bg': 'bg-indigo-200',  'badge_text': 'text-indigo-800'},
        {'id': 'final_interview', 'label': 'Final Round',    'hdr_bg': 'bg-amber-50',    'hdr_border': 'border-amber-300',   'badge_bg': 'bg-amber-200',   'badge_text': 'text-amber-800'},
        {'id': 'offer',           'label': 'Offer',          'hdr_bg': 'bg-emerald-50',  'hdr_border': 'border-emerald-300', 'badge_bg': 'bg-emerald-200', 'badge_text': 'text-emerald-800'},
        {'id': 'hired',           'label': 'Hired',          'hdr_bg': 'bg-green-50',    'hdr_border': 'border-green-300',   'badge_bg': 'bg-green-200',   'badge_text': 'text-green-800'},
        {'id': 'rejected',        'label': 'Rejected',       'hdr_bg': 'bg-rose-50',     'hdr_border': 'border-rose-300',    'badge_bg': 'bg-rose-200',    'badge_text': 'text-rose-800'},
    ]

    stages = []
    for s in STAGE_DEFS:
        cards = []
        for app in all_apps:
            if app.status != s['id']:
                continue
            profile = profiles.get(app.candidate_id)
            display_name = (
                (profile.full_name if profile and profile.full_name else None)
                or app.candidate.get_full_name()
                or app.candidate.username
            )
            initials = ''.join(w[0].upper() for w in display_name.split()[:2])

            # Compute live match score
            match_score = None
            top_skills = []
            if profile:
                try:
                    match_data = engine.calculate_match(profile, app.job)
                    match_score = round(match_data.get('overall_score', 0))
                    top_skills = [
                        sk.get('job_skill', sk.get('skill', ''))
                        for sk in match_data.get('matched_skills', [])[:3]
                    ]
                except Exception as e:
                    logger.warning(f"Pipeline match error for {app.candidate_id}: {e}")

            cards.append({
                'app_id':         app.id,
                'candidate_name': display_name,
                'initials':       initials,
                'job_title':      app.job.title,
                'job_id':         app.job_id,
                'applied_at':     app.applied_at,
                'match_score':    match_score,
                'match_quality':  '',
                'top_skills':     top_skills,
                'resume_url':     profile.resume_file.url if profile and profile.resume_file else None,
            })
        stages.append({**s, 'apps': cards, 'count': len(cards)})

    return render(request, 'pipeline.html', {
        'stages':             stages,
        'jobs':               jobs,
        'selected_job_id':    str(job_id),
        'total_applications': len(all_apps),
        'active_count':       sum(s['count'] for s in stages if s['id'] not in ('hired', 'rejected')),
        'hired_count':        next((s['count'] for s in stages if s['id'] == 'hired'), 0),
    })


@login_required
@require_POST
def pipeline_update_status(request, application_id):
    """AJAX: move a candidate card to a new pipeline stage."""
    if not hasattr(request.user, 'companyprofile'):
        return JsonResponse({'error': 'Unauthorized'}, status=403)

    app = get_object_or_404(
        Application, id=application_id,
        job__company_profile=request.user.companyprofile
    )
    try:
        data = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse({'error': 'Invalid JSON'}, status=400)

    new_status = data.get('status', '')
    valid = [c[0] for c in Application._meta.get_field('status').choices]
    if new_status not in valid:
        return JsonResponse({'error': 'Invalid status'}, status=400)

    app.status = new_status
    app.save(update_fields=['status'])
    return JsonResponse({'success': True, 'application_id': application_id, 'new_status': new_status})


@login_required
def recruiter_schedule(request):
    if not hasattr(request.user, 'companyprofile'):
        return redirect('index')

    company = request.user.companyprofile
    date_str = request.GET.get('date')
    selected_date = date.fromisoformat(date_str) if date_str else date.today()

    base_qs = Interview.objects.filter(
        application__job__company_profile=company
    ).select_related('application__candidate', 'application__job').order_by('scheduled_date')

    day_interviews = base_qs.filter(scheduled_date__date=selected_date)

    today = date.today()
    upcoming_interviews = base_qs.filter(
        scheduled_date__date__gte=today,
        scheduled_date__date__lte=today + timedelta(days=7),
        status='scheduled',
    )

    return render(request, 'schedule.html', {
        'selected_date':       selected_date,
        'day_interviews':      day_interviews,
        'upcoming_interviews': upcoming_interviews,
    })


@login_required
def interview_create(request):
    if not hasattr(request.user, 'companyprofile'):
        return redirect('index')

    company = request.user.companyprofile
    applications = Application.objects.filter(
        job__company_profile=company
    ).select_related('candidate', 'job').order_by('job__title', 'candidate__username')

    if request.method == 'POST':
        application_id   = request.POST.get('application_id')
        scheduled_date   = request.POST.get('scheduled_date')
        duration_minutes = request.POST.get('duration_minutes', 60)
        interview_type   = request.POST.get('interview_type', 'technical')
        meeting_link     = request.POST.get('meeting_link', '')
        location         = request.POST.get('location', '')
        interviewer      = request.POST.get('interviewer', '')
        notes            = request.POST.get('notes', '')

        app = get_object_or_404(Application, id=application_id, job__company_profile=company)
        Interview.objects.create(
            application=app,
            scheduled_date=scheduled_date,
            duration_minutes=int(duration_minutes),
            interview_type=interview_type,
            meeting_link=meeting_link,
            location=location,
            interviewer=interviewer,
            notes=notes,
        )
        messages.success(request, 'Interview scheduled successfully.')
        return redirect('schedule')

    return render(request, 'schedule_create.html', {
        'applications':    applications,
        'interview_types': Interview.INTERVIEW_TYPE_CHOICES,
    })


@login_required
@require_POST
def interview_update_status(request, interview_id):
    if not hasattr(request.user, 'companyprofile'):
        return JsonResponse({'error': 'Unauthorized'}, status=403)

    interview = get_object_or_404(
        Interview, id=interview_id,
        application__job__company_profile=request.user.companyprofile
    )
    try:
        data = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse({'error': 'Invalid JSON'}, status=400)

    new_status = data.get('status', '')
    valid = [c[0] for c in Interview.STATUS_CHOICES]
    if new_status not in valid:
        return JsonResponse({'error': 'Invalid status'}, status=400)

    interview.status = new_status
    interview.save(update_fields=['status'])
    return JsonResponse({'success': True, 'new_status': new_status})


def recruiter_analytics(request):
    """
    Analytics dashboard – real metrics from DB.
    """
    company = getattr(request.user, 'companyprofile', None)

    if company:
        company_jobs = Job.objects.filter(company_profile=company)
        company_apps = Application.objects.filter(job__company_profile=company)

        total_applications = company_apps.count()
        active_jobs = company_jobs.filter(status='open').count()
        scheduled_interviews = Interview.objects.filter(
            job__company_profile=company, status='scheduled'
        ).count()
        hired_count = company_apps.filter(status='hired').count()
        conversion_rate = round((hired_count / total_applications * 100), 1) if total_applications else 0

        stage_counts = {
            'applied': company_apps.filter(status='applied').count(),
            'screening': company_apps.filter(status='screening').count(),
            'technical': company_apps.filter(status__in=['phone_interview', 'technical', 'final_interview']).count(),
            'offer': company_apps.filter(status='offer').count(),
            'hired': hired_count,
        }

        pipeline_data = [
            {'stage': 'Applied',    'count': stage_counts['applied']},
            {'stage': 'Screening',  'count': stage_counts['screening']},
            {'stage': 'Interview',  'count': stage_counts['technical']},
            {'stage': 'Offer',      'count': stage_counts['offer']},
            {'stage': 'Hired',      'count': stage_counts['hired']},
        ]

        top_jobs_qs = company_jobs.annotate(
            app_count=Count('application')
        ).order_by('-app_count')[:5]
        top_jobs = [{'title': j.title, 'count': j.app_count} for j in top_jobs_qs]
        max_job_applications = top_jobs[0]['count'] if top_jobs else 0
    else:
        total_applications = 0
        active_jobs = 0
        scheduled_interviews = 0
        conversion_rate = 0
        pipeline_data = [
            {'stage': 'Applied',   'count': 0},
            {'stage': 'Screening', 'count': 0},
            {'stage': 'Interview', 'count': 0},
            {'stage': 'Offer',     'count': 0},
            {'stage': 'Hired',     'count': 0},
        ]
        top_jobs = []
        max_job_applications = 0

    max_pipeline_count = max((row['count'] for row in pipeline_data), default=0)

    context = {
        'total_applications': total_applications,
        'active_jobs': active_jobs,
        'scheduled_interviews': scheduled_interviews,
        'conversion_rate': conversion_rate,
        'pipeline_data': pipeline_data,
        'max_pipeline_count': max_pipeline_count,
        'source_data': [],
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
            CandidateProfile.objects.create(user=user, full_name=name)
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

    jobs = Job.objects.filter(company_profile=request.user.companyprofile).prefetch_related('application_set')

    # Add applicant data with match scores for each job
    from ann.services.matching_engine import MatchingEngine
    engine = MatchingEngine()

    jobs_with_data = []
    for job in jobs:
        apps = job.application_set.all().select_related('candidate')
        applicant_count = apps.count()

        # Calculate match scores for applicants
        match_scores = []
        top_applicants = []
        for app in apps[:5]:  # Top 5 applicants
            try:
                profile = CandidateProfile.objects.get(user=app.candidate)
                match_data = engine.calculate_match(profile, job)
                score = match_data.get('overall_score', 0)
                match_scores.append(score)

                # Get top skills
                top_skills = []
                if hasattr(profile, 'skills') and profile.skills:
                    skills_list = [s.strip() for s in profile.skills.split(',') if s.strip()]
                    top_skills = skills_list[:3]

                top_applicants.append({
                    'name': app.candidate.first_name or app.candidate.username,
                    'score': score,
                    'top_skills': top_skills,
                })
            except CandidateProfile.DoesNotExist:
                pass

        avg_score = sum(match_scores) / len(match_scores) if match_scores else 0
        top_score = max(match_scores) if match_scores else 0

        jobs_with_data.append({
            'job': job,
            'applicant_count': applicant_count,
            'avg_score': round(avg_score, 1),
            'top_score': round(top_score, 1),
            'top_applicants': top_applicants,
        })

    return render(request, 'company_jobs.html', {'jobs_data': jobs_with_data})


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
        # Add experience fields
        job.experience_min = request.POST.get('experience_min') or job.experience_min or 0
        job.experience_max = request.POST.get('experience_max') or job.experience_max or 99
        job.save()

        # Phase 3: Re-extract skills after job update
        skills_count = extract_job_skills(job)

        # Phase 4: Regenerate embedding after job update
        generate_job_embedding(job)

        logger.info(f"Updated job '{job.title}' with {skills_count} extracted skills and embedding")

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
            experience_min=request.POST.get('experience_min') or 0,
            experience_max=request.POST.get('experience_max') or 99,
            job_type=request.POST.get('job_type'),
            category=request.POST.get('category') or '',
            description=request.POST.get('description'),
            requirements=request.POST.get('requirements'),
            benefits=request.POST.get('benefits') or '',
            skills_required=request.POST.get('skills_required') or '',
        )

        # Phase 3: Extract skills from job description using NLP
        skills_count = extract_job_skills(job)

        # Phase 4: Generate semantic embedding for job matching
        generate_job_embedding(job)

        logger.info(f"Created job '{job.title}' with {skills_count} extracted skills and embedding")

        messages.success(request, 'Job posted successfully.')
        return redirect('jobs')  # recruiter jobs page

    return render(request, 'company_create_job.html', {'editing': False})


@login_required
def company_job_applicants(request, job_id):
    """
    Show all applicants for a job with AI match scores.

    Recruiters see:
    - Match percentage for each candidate
    - Top matched skills
    - Missing skills
    - Candidates ranked by match score
    """
    if not hasattr(request.user, 'companyprofile'):
        messages.error(request, 'Only companies can access this page.')
        return redirect('index')

    job = get_object_or_404(Job, id=job_id, company_profile=request.user.companyprofile)
    apps = Application.objects.filter(job=job).select_related('candidate')

    # Get status choices from the model
    status_choices = Application._meta.get_field('status').choices

    # Always compute live match scores
    from ann.services.matching_engine import MatchingEngine
    engine = MatchingEngine()

    candidate_ids = [app.candidate_id for app in apps]
    profile_map = {
        cp.user_id: cp
        for cp in CandidateProfile.objects.filter(user_id__in=candidate_ids)
    }

    applications_with_scores = []
    for app in apps:
        candidate_profile = profile_map.get(app.candidate_id)
        app.candidate_profile = candidate_profile
        app.match_score = 0
        app.match_data = None
        app.matched_skills = []
        app.missing_skills = []
        app.top_skills = []
        app.breakdown = {}

        if candidate_profile:
            try:
                match_data = engine.calculate_match(candidate_profile, job)
                app.match_score = round(match_data.get('overall_score', 0), 1)
                app.matched_skills = match_data.get('matched_skills', [])[:5]
                app.missing_skills = match_data.get('missing_skills', [])[:3]
                app.breakdown = match_data.get('breakdown', {})
                app.match_data = match_data
            except Exception as e:
                logger.error(f"Match compute error for applicant {app.id}: {e}")

            app.top_skills = list(CandidateSkill.objects.filter(
                candidate=candidate_profile
            ).order_by('-confidence_score')[:5].values_list('skill_text', flat=True))

        applications_with_scores.append(app)

    # Sort by match score (highest first)
    applications_with_scores.sort(key=lambda x: x.match_score, reverse=True)

    return render(request, 'company_job_applicants.html', {
        'job': job,
        'applications': applications_with_scores,
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
    match_data = None
    if request.user.is_authenticated:
        profile, created = CandidateProfile.objects.get_or_create(
            user=request.user,
            defaults={'profile_strength': 60}
        )

        # Calculate real match scores using matching engine
        try:
            from ann.services.matching_engine import MatchingEngine
            engine = MatchingEngine()
            match_data = engine.calculate_match(profile, job)
        except Exception as e:
            logger.error(f"Match calculation error for job {job_id}: {e}")
            match_data = None

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
            # Try comma-separated fallback
            skills_required = [s.strip() for s in job.skills_required.split(',') if s.strip()]

    # Parse requirements into list
    requirements_list = []
    if job.requirements:
        # Split by newlines or bullet points
        import re
        lines = re.split(r'[\n•\-\*]+', job.requirements)
        requirements_list = [line.strip() for line in lines if line.strip()]

    context = {
        'job': job,
        'profile': profile,
        'has_applied': has_applied,
        'skills_required': skills_required,
        'requirements_list': requirements_list,
        'user': request.user if request.user.is_authenticated else None,
        # Match data
        'match_score': match_data['overall_score'] if match_data else 0,
        'skill_match': match_data['breakdown']['skill_match'] if match_data else 0,
        'experience_match': match_data['breakdown']['experience_match'] if match_data else 0,
        'semantic_match': match_data['breakdown']['semantic_similarity'] if match_data else 0,
        'education_match': match_data['breakdown']['education_match'] if match_data else 0,
        'matched_skills': match_data['matched_skills'] if match_data else [],
        'missing_skills': match_data['missing_skills'] if match_data else [],
        'suggestions': match_data['suggestions'] if match_data else [],
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

    # Only extract from real content sections - NOT contact/education/other which produce garbage
    VALID_SECTIONS = {
        'skills': 'skills_section',
        'experience': 'experience',
        'projects': 'projects',
        'summary': 'summary',
        'certifications': 'skills_section',
        'awards': 'skills_section',
    }

    # Extract skills from whitelisted sections only
    for section_name, section_text in sections.items():
        if section_name not in VALID_SECTIONS:
            continue  # Skip: contact, education, other, languages, interests, references
        if not section_text or not section_text.strip():
            continue

        source = VALID_SECTIONS[section_name]
        skills = extractor.extract_skills(section_text, section_name)

        for skill in skills:
            normalized = skill['normalized']
            if normalized not in seen_normalized:
                seen_normalized.add(normalized)
                skill['db_source'] = source
                all_skills.append(skill)

    # Clear existing skills for this candidate
    CandidateSkill.objects.filter(candidate=profile).delete()

    # Store extracted skills in database — only high-confidence skills (reduces garbage)
    MIN_CONFIDENCE = 0.75
    skills_created = 0
    for skill_data in all_skills:
        # Skip low-confidence extractions (noun phrases score 0.70, proper nouns 0.80+)
        if skill_data.get('confidence', 0.7) < MIN_CONFIDENCE:
            continue
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
    Extract skills from job's skills_required field.

    Phase 3 implementation per PROJECT_PLAN.md.

    IMPORTANT: Only uses skills_required field, NOT description/requirements.
    This ensures only recruiter-specified skills are matched, not random words.

    Args:
        job: Job instance

    Returns:
        Number of skills extracted
    """
    # Clear existing skills for this job
    JobSkill.objects.filter(job=job).delete()

    skills_text = job.skills_required
    if not skills_text:
        return 0

    # Words that are NOT skills
    non_skills = {
        'intern', 'interns', 'internship', 'manager', 'director', 'engineer',
        'developer', 'analyst', 'designer', 'consultant', 'specialist',
        'senior', 'junior', 'lead', 'associate', 'assistant', 'coordinator',
        'experience', 'years', 'required', 'preferred', 'must', 'have',
        'knowledge', 'understanding', 'ability', 'skills', 'strong',
        'excellent', 'good', 'work', 'team', 'company', 'business',
        'candidate', 'applicant', 'degree', 'bachelor', 'master',
    }

    def is_valid_skill(s):
        s_lower = s.lower().strip()
        if len(s_lower) < 2 or len(s_lower) > 50:
            return False
        if s_lower in non_skills:
            return False
        if s_lower.replace('.', '').replace('-', '').isdigit():
            return False
        return True

    # Parse skills from skills_required field
    skills_list = []

    # Try JSON first
    try:
        parsed = json.loads(skills_text)
        if isinstance(parsed, list):
            skills_list = [s.strip() for s in parsed if s and is_valid_skill(s)]
    except (json.JSONDecodeError, TypeError):
        import re
        # Check if comma-separated (has commas)
        if ',' in skills_text:
            # Comma-separated: "Python, Machine Learning, SQL"
            parts = [s.strip() for s in skills_text.split(',')]
            skills_list = [p for p in parts if p and is_valid_skill(p)]
        else:
            # No commas - might be space-separated: "Git Linux Docker"
            # or single skill: "Python"
            words = skills_text.split()
            if len(words) == 1:
                if is_valid_skill(words[0]):
                    skills_list = [words[0]]
            else:
                # Multiple words with no commas - treat each word as a skill
                # e.g., "Git Linux Docker" → ["Git", "Linux", "Docker"]
                skills_list = [w.strip() for w in words if w.strip() and is_valid_skill(w)]

    # Store skills
    skills_created = 0
    for skill in skills_list:
        try:
            JobSkill.objects.create(
                job=job,
                skill_text=skill,
                normalized_text=skill.lower().strip(),
                importance='required',
                category='technical',
                context='',
            )
            skills_created += 1
        except Exception as e:
            logger.warning(f"Failed to save job skill '{skill}': {e}")
            continue

    logger.info(f"Extracted {skills_created} skills for job {job.title}")
    return skills_created


def generate_job_embedding(job) -> bool:
    """
    Generate and store semantic embedding for a job.

    Phase 4 implementation per PROJECT_PLAN.md.

    Args:
        job: Job instance

    Returns:
        True if embedding generated successfully, False otherwise
    """
    from ann.services.embedding_service import EmbeddingService

    try:
        # Build job text for embedding
        job_text = f"{job.title} {job.description} {job.requirements}"
        if job.skills_required:
            job_text += f" {job.skills_required}"
        if job.category:
            job_text += f" {job.category}"

        # Generate embedding
        embedding_service = EmbeddingService()
        embedding = embedding_service.generate_embedding(job_text)

        # Serialize and store
        job.embedding = embedding_service.serialize_embedding(embedding)
        job.save(update_fields=['embedding'])

        logger.info(f"Generated embedding for job '{job.title}'")
        return True

    except Exception as e:
        logger.error(f"Failed to generate embedding for job '{job.title}': {e}")
        return False


def _infer_experience_years(sections: dict) -> int:
    """
    Infer candidate's years of experience from resume sections.
    Uses explicit 'X years' statements first, then date ranges.
    """
    import re
    from datetime import datetime

    exp_text = sections.get('experience', '') or ''
    full_text = ' '.join(v for v in sections.values() if v)
    current_year = datetime.now().year

    # Pattern 1: Explicit "X years of experience" statements
    explicit_patterns = [
        r'(\d+)\+?\s*years?\s+of\s+(?:experience|exp)',
        r'(\d+)\+?\s*years?\s+(?:experience|exp)',
        r'over\s+(\d+)\s+years?',
        r'(\d+)\s*\+\s*years?\s+(?:in|of)',
    ]
    for pattern in explicit_patterns:
        matches = re.findall(pattern, full_text, re.IGNORECASE)
        if matches:
            years = [int(m) for m in matches if 1 <= int(m) <= 40]
            if years:
                return max(years)

    # Pattern 2: Date ranges in experience section (2018-2022, Jan 2019 - Present)
    year_ranges = re.findall(
        r'\b(20\d{2}|19\d{2})\b\s*[-–]\s*\b(20\d{2}|present|current|now)\b',
        exp_text, re.IGNORECASE
    )
    if year_ranges:
        total = 0
        for start, end in year_ranges:
            s = int(start)
            e = current_year if end.lower() in ('present', 'current', 'now') else int(end)
            if 1970 <= s <= current_year and s < e:
                total += e - s
        if total > 0:
            return min(total, 40)

    # Pattern 3: Span of years mentioned in experience section
    years_in_exp = [int(y) for y in re.findall(r'\b(20\d{2}|19\d{2})\b', exp_text)
                    if 1970 <= int(y) <= current_year]
    if years_in_exp:
        span = max(years_in_exp) - min(years_in_exp)
        if span > 0:
            return min(span, 40)

    return 0


def _infer_education_from_sections(sections: dict):
    """
    Infer education level and field from resume education section.
    Returns (level_str, field_str).
    """
    import re

    edu_text = sections.get('education', '') or ''
    # Use education + full text for field detection
    full_text = edu_text + ' ' + ' '.join(v for v in sections.values() if v)

    level = ''
    # Check from highest to lowest (values must match EDUCATION_LEVEL_CHOICES in models.py)
    if re.search(r'\b(ph\.?d\.?|phd|doctor(?:ate|al)|d\.phil\.?)\b', full_text, re.IGNORECASE):
        level = 'phd'
    elif re.search(r"\b(m\.?s\.?c?\.?|m\.?tech\.?|m\.?e\.?|mba|master'?s?|master\s+of|post.?grad)\b", full_text, re.IGNORECASE):
        level = 'master'
    elif re.search(r"\b(b\.?s\.?c?\.?|b\.?tech\.?|b\.?e\.?|b\.?a\.?|bachelor'?s?|bachelor\s+of|undergraduate|b\.?com\.?)\b", full_text, re.IGNORECASE):
        level = 'bachelor'
    elif re.search(r'\b(diploma|associate|polytechnic|a\.?d\.?)\b', full_text, re.IGNORECASE):
        level = 'associate'
    elif re.search(r'\b(12th|hsc|high\s+school|secondary|10\+2)\b', full_text, re.IGNORECASE):
        level = 'high_school'

    field = ''
    field_patterns = [
        (r'\b(computer\s+science|c\.?s\.?|software\s+engineering|information\s+technology|i\.?t\.?)\b', 'Computer Science'),
        (r'\b(data\s+science|machine\s+learning|artificial\s+intelligence|analytics)\b', 'Data Science'),
        (r'\b(electrical|electronics|ece|eee)\b', 'Electrical Engineering'),
        (r'\b(mechanical|mechatronics)\b', 'Mechanical Engineering'),
        (r'\b(civil|structural\s+engineering)\b', 'Civil Engineering'),
        (r'\b(business\s+administration|commerce|b\.?b\.?a\.?|b\.?com\.?)\b', 'Business Administration'),
        (r'\b(finance|accounting|economics)\b', 'Finance'),
        (r'\b(marketing)\b', 'Marketing'),
        (r'\b(mathematics|math|statistics|applied\s+math)\b', 'Mathematics'),
    ]
    for pattern, label in field_patterns:
        if re.search(pattern, full_text, re.IGNORECASE):
            field = label
            break

    return level, field


@require_http_methods(["POST"])
def upload_resume(request):
    """
    Upload and parse a resume file (PDF or DOCX).

    Phase 2 implementation per PROJECT_PLAN.md:
    - Validates file type and size
    - Extracts text from PDF/DOCX
    - Detects resume sections
    - Stores parsed data for skill extraction (Phase 3)

    Phase 6 Addition:
    - Supports async processing via Celery (if USE_ASYNC_PROCESSING=True)
    - Falls back to sync processing if Celery unavailable

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

        # Save the file first (always sync - fast operation)
        profile.resume_file = resume_file
        profile.save()

        # Always use sync processing (reliable)
        # Async/Celery disabled to ensure scores always update correctly
        return _upload_resume_sync(request, profile)

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


def _upload_resume_async(request, profile):
    """
    Async resume processing using Celery.

    Phase 6: Returns immediately, processing happens in background.
    """
    try:
        from ann.tasks import process_resume_complete_task

        # Mark as processing
        ParsedResume.objects.update_or_create(
            candidate=profile,
            defaults={
                'parsing_status': 'processing',
                'error_message': '',
            }
        )

        # Trigger async processing
        task = process_resume_complete_task.delay(profile.id)

        logger.info(
            f"Resume upload queued for async processing: "
            f"user={request.user.username}, task_id={task.id}"
        )

        return JsonResponse({
            'success': True,
            'message': 'Resume uploaded! Processing in background...',
            'async': True,
            'task_id': task.id,
            'profile_strength': profile.profile_strength,
            'status': 'processing',
        })

    except Exception as e:
        # Celery not available - fall back to sync
        logger.warning(f"Async processing failed, falling back to sync: {e}")
        return _upload_resume_sync(request, profile)


def _upload_resume_sync(request, profile):
    """
    Synchronous resume processing (original behavior).

    Used when Celery is not available or USE_ASYNC_PROCESSING=False.
    """
    from ann.services.resume_parser import ResumeParser
    from ann.services.embedding_service import EmbeddingService

    parser = ResumeParser()
    file_path = profile.resume_file.path

    # Extract text
    raw_text = parser.extract_text(file_path)
    cleaned_text = parser.clean_text(raw_text)
    sections = parser.detect_sections(raw_text)
    contact_info = parser.extract_contact_info(raw_text)

    # Calculate completeness score
    completeness_score = parser.calculate_completeness_score(sections)

    # Phase 4: Generate semantic embedding for similarity matching
    embedding_service = EmbeddingService()
    resume_embedding = embedding_service.generate_embedding(cleaned_text)
    serialized_embedding = embedding_service.serialize_embedding(resume_embedding)

    # Create or update ParsedResume with embedding
    parsed_resume, pr_created = ParsedResume.objects.update_or_create(
        candidate=profile,
        defaults={
            'raw_text': raw_text,
            'cleaned_text': cleaned_text,
            'sections_json': sections,
            'embedding': serialized_embedding,
            'parsing_status': 'completed',
            'parsed_at': timezone.now(),
            'error_message': '',
        }
    )

    # Auto-infer experience years and education from resume content
    inferred_exp = _infer_experience_years(sections)
    inferred_edu_level, inferred_edu_field = _infer_education_from_sections(sections)

    # Update profile strength + inferred fields (only overwrite if we found something)
    profile.profile_strength = completeness_score
    if inferred_exp > 0:
        profile.experience_years = inferred_exp
    if inferred_edu_level and not profile.education_level:
        profile.education_level = inferred_edu_level
    if inferred_edu_field and not profile.education_field:
        profile.education_field = inferred_edu_field
    profile.save()

    # Phase 3: Extract skills from resume using NLP
    skills_extracted = extract_candidate_skills(profile, sections, cleaned_text)

    # Prepare response
    sections_found = [k for k, v in sections.items() if v.strip()]

    logger.info(
        f"Resume parsed for user {request.user.username}: "
        f"{len(cleaned_text)} chars, {len(sections_found)} sections, "
        f"{skills_extracted} skills extracted, embedding generated"
    )

    return JsonResponse({
        'success': True,
        'message': 'Resume uploaded and parsed successfully',
        'async': False,
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

    # Always compute live match scores
    from ann.services.matching_engine import MatchingEngine
    engine = MatchingEngine()

    candidate_ids = [app.candidate_id for app in applications]
    profile_map = {
        cp.user_id: cp
        for cp in CandidateProfile.objects.filter(user_id__in=candidate_ids)
    }

    applications_with_scores = []
    for app in applications:
        profile = profile_map.get(app.candidate_id)
        app_data = {
            'application': app,
            'match_score': 0,
            'matched_skills': [],
            'missing_skills': [],
            'breakdown': {},
            'suggestions': [],
            'candidate_name': app.candidate.get_full_name() or app.candidate.username,
            'candidate_email': app.candidate.email,
            'candidate_profile': profile,
        }

        if profile:
            try:
                match_data = engine.calculate_match(profile, job)
                app_data['match_score'] = round(match_data.get('overall_score', 0), 1)
                app_data['matched_skills'] = match_data.get('matched_skills', [])[:5]
                app_data['missing_skills'] = match_data.get('missing_skills', [])[:3]
                app_data['breakdown'] = match_data.get('breakdown', {})
                app_data['suggestions'] = match_data.get('suggestions', [])
            except Exception as e:
                logger.error(f"Match compute error for {app.candidate.username}: {e}")

        applications_with_scores.append(app_data)

    # Sort by match score if requested
    if sort_by == 'match':
        applications_with_scores.sort(key=lambda x: x['match_score'], reverse=True)

    context = {
        'job': job,
        'applications': applications_with_scores,
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
@require_GET
def get_task_status(request, task_id):
    """
    Get the status of an async task.

    Phase 6: Used by frontend to poll for task completion.

    Returns:
        JSON with task status and results
    """
    try:
        from celery.result import AsyncResult
        from neuralnetwork.celery import app

        result = AsyncResult(task_id, app=app)

        response = {
            'task_id': task_id,
            'status': result.status,
            'ready': result.ready(),
        }

        if result.ready():
            if result.successful():
                response['result'] = result.result
            else:
                response['error'] = str(result.result)

        return JsonResponse(response)

    except Exception as e:
        logger.error(f"Failed to get task status: {e}")
        return JsonResponse({
            'task_id': task_id,
            'status': 'UNKNOWN',
            'error': str(e),
        }, status=500)


@login_required
@require_GET
def get_processing_status(request):
    """
    Get resume processing status for current user.

    Phase 6: Check if resume is still being processed.
    """
    try:
        profile = CandidateProfile.objects.get(user=request.user)
        parsed_resume = ParsedResume.objects.filter(candidate=profile).first()

        if not parsed_resume:
            return JsonResponse({
                'status': 'not_uploaded',
                'message': 'No resume uploaded',
            })

        response = {
            'status': parsed_resume.parsing_status,
            'parsed_at': parsed_resume.parsed_at.isoformat() if parsed_resume.parsed_at else None,
            'profile_strength': profile.profile_strength,
        }

        if parsed_resume.parsing_status == 'completed':
            from ann.models import CandidateSkill
            skills_count = CandidateSkill.objects.filter(candidate=profile).count()
            response['skills_extracted'] = skills_count
            response['has_embedding'] = bool(parsed_resume.embedding)

        elif parsed_resume.parsing_status == 'failed':
            response['error'] = parsed_resume.error_message

        return JsonResponse(response)

    except CandidateProfile.DoesNotExist:
        return JsonResponse({
            'status': 'not_uploaded',
            'message': 'No resume uploaded',
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
