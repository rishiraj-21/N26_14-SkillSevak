
from django.urls import path
from . import views

urlpatterns = [
    path('', views.index, name='index'),
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),

    # Registration
    path('register/job-seeker/', views.register_job_seeker, name='register_job_seeker'),
    path('register/company/', views.register_company, name='register_company'),

    # Candidate side
    path('candidate/', views.candidate_page, name='candidate'),
    path('jobs/', views.job_list, name='job_list'),
    path('jobs/recommended/', views.recommended_jobs, name='recommended_jobs'),
    path('job/<int:job_id>/', views.job_detail, name='job_detail'),
    path('jobs/<int:job_id>/apply/', views.apply_for_job, name='apply_for_job'),

    # Recruiter workspace pages
    path('recruiter/', views.recruiter_page, name='recruiter'),
    path('recruiter/dashboard/', views.recruiter_dashboard, name='dashboard'),
    path('recruiter/jobs/', views.recruiter_jobs, name='jobs'),
    path('recruiter/jobs/<int:job_id>/', views.recruiter_job_detail, name='recruiter_job_detail'),
    path('recruiter/jobs/<int:job_id>/info/', views.recruiter_job_info, name='recruiter_job_info'),
    path('recruiter/pipeline/', views.recruiter_pipeline, name='pipeline'),
    path('recruiter/pipeline/<int:application_id>/update-status/',
         views.pipeline_update_status,
         name='pipeline_update_status'),
    path('recruiter/schedule/', views.recruiter_schedule, name='schedule'),
    path('recruiter/analytics/', views.recruiter_analytics, name='analytics'),
    path('recruiter/templates/', views.recruiter_email_templates, name='email_templates'),

    # Company side (job giver)
    path('company/jobs/', views.company_jobs, name='company_jobs'),
    path('company/jobs/<int:job_id>/edit/', views.company_edit_job, name='job_edit'),
    path('company/jobs/<int:job_id>/status/<str:status>/', views.job_change_status, name='job_change_status'),
    path('company/jobs/new/', views.company_create_job, name='company_create_job'),
    path('company/jobs/<int:job_id>/applicants/', views.company_job_applicants, name='company_job_applicants'),
    path('company/applications/<int:application_id>/status/', 
         views.company_update_application_status, 
         name='company_update_application_status'),

    # Interview scheduling
    path('recruiter/interviews/create/', views.interview_create, name='interview_create'),
    path('recruiter/interviews/<int:interview_id>/update-status/',
         views.interview_update_status,
         name='interview_update_status'),
    
    # Email templates
    path('recruiter/templates/create/', views.email_template_create, name='email_template_create'),
    
    # API endpoints
    path('api/upload-resume/', views.upload_resume, name='upload_resume'),
    path('api/apply-job/<int:job_id>/', views.apply_job, name='apply_job'),

    # Phase 2: Resume Parsing API
    path('api/resume/parsed/', views.get_parsed_resume, name='get_parsed_resume'),
    path('api/resume/reparse/', views.reparse_resume, name='reparse_resume'),

    # Phase 6: Async Task Status API
    path('api/task/<str:task_id>/status/', views.get_task_status, name='get_task_status'),
    path('api/resume/processing-status/', views.get_processing_status, name='get_processing_status'),
]