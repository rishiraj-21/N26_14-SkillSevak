"""
SkillSevak Database Models

Core entities for the AI-powered resume matching system.
See PRD.md Section 6 for database design details.

Key Principle: NO HARDCODED SKILLS - all skills are extracted dynamically via NLP.
"""

from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone


class CompanyProfile(models.Model):
    """
    Company-side profile for job givers.
    """
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    company_name = models.CharField(max_length=200)
    industry = models.CharField(max_length=200, blank=True)
    website = models.URLField(blank=True)
    location = models.CharField(max_length=200, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.company_name


class Job(models.Model):
    # New FK for dynamic company side; keep old company text for backwards compatibility
    company_profile = models.ForeignKey(
        CompanyProfile,
        on_delete=models.CASCADE,
        related_name='jobs',
        null=True,
        blank=True,
    )
    title = models.CharField(max_length=200)
    company = models.CharField(max_length=200)
    location = models.CharField(max_length=200)
    salary_min = models.IntegerField()
    salary_max = models.IntegerField()
    job_type = models.CharField(max_length=50, choices=[
        ('full-time', 'Full-time'),
        ('part-time', 'Part-time'),
        ('contract', 'Contract'),
        ('internship', 'Internship'),
    ])
    category = models.CharField(max_length=100, blank=True)  # Developer, Sales, etc.
    description = models.TextField()
    requirements = models.TextField()
    benefits = models.TextField(blank=True)
    skills_required = models.TextField()  # JSON string of skills
    match_score = models.IntegerField(default=0)
    status = models.CharField(max_length=20, choices=[
        ('open', 'Open'),
        ('closed', 'Closed'),
    ], default='open')
    created_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        company_name = self.company_profile.company_name if self.company_profile else self.company
        return f"{self.title} at {company_name}"

class CandidateProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    resume_file = models.FileField(upload_to='resumes/', blank=True, null=True)
    skills = models.TextField(blank=True)  # JSON string of skills
    experience_years = models.IntegerField(default=0)
    salary_expectation = models.IntegerField(blank=True, null=True)
    profile_strength = models.IntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return f"{self.user.username}'s Profile"

class Application(models.Model):
    candidate = models.ForeignKey(User, on_delete=models.CASCADE)
    job = models.ForeignKey(Job, on_delete=models.CASCADE)
    applied_at = models.DateTimeField(auto_now_add=True)
    status = models.CharField(max_length=50, choices=[
        ('applied', 'Applied'),
        ('reviewed', 'Under Review'),
        ('interview', 'Interview Scheduled'),
        ('rejected', 'Rejected'),
        ('hired', 'Hired'),
    ], default='applied')

    class Meta:
        unique_together = ['candidate', 'job']

    def __str__(self):
        return f"{self.candidate.username} applied for {self.job.title}"


# =============================================================================
# AI/ML PIPELINE MODELS (Phase 1 - per PROJECT_PLAN.md)
# =============================================================================

class ParsedResume(models.Model):
    """
    Stores extracted and processed resume data.

    This model holds:
    - Raw text extracted from PDF/DOCX
    - Cleaned/normalized text for NLP processing
    - Detected sections (skills, experience, education, etc.)
    - Semantic embedding for similarity matching

    Per PRD.md: Resume parsing is async (Phase 6) but stored here.
    """

    PARSING_STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('processing', 'Processing'),
        ('completed', 'Completed'),
        ('failed', 'Failed'),
    ]

    candidate = models.OneToOneField(
        CandidateProfile,
        on_delete=models.CASCADE,
        related_name='parsed_resume'
    )

    # Extracted text content
    raw_text = models.TextField(
        blank=True,
        help_text="Raw text extracted from PDF/DOCX"
    )
    cleaned_text = models.TextField(
        blank=True,
        help_text="Cleaned and normalized text for NLP"
    )

    # Structured sections detected by resume parser
    sections_json = models.JSONField(
        default=dict,
        help_text="Detected sections: {skills, experience, education, projects, ...}"
    )

    # Semantic embedding for similarity matching (384 dimensions per PRD.md)
    # Stored as binary for efficiency; deserialize with numpy.frombuffer()
    embedding = models.BinaryField(
        null=True,
        blank=True,
        help_text="Semantic embedding vector (384 dims, stored as binary)"
    )

    # Processing status
    parsing_status = models.CharField(
        max_length=20,
        choices=PARSING_STATUS_CHOICES,
        default='pending'
    )
    parsed_at = models.DateTimeField(null=True, blank=True)
    error_message = models.TextField(blank=True)

    # Metadata
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Parsed Resume"
        verbose_name_plural = "Parsed Resumes"

    def __str__(self):
        return f"ParsedResume for {self.candidate.user.username} ({self.parsing_status})"

    def mark_completed(self):
        """Mark parsing as completed with timestamp."""
        self.parsing_status = 'completed'
        self.parsed_at = timezone.now()
        self.save(update_fields=['parsing_status', 'parsed_at'])

    def mark_failed(self, error: str):
        """Mark parsing as failed with error message."""
        self.parsing_status = 'failed'
        self.error_message = error
        self.save(update_fields=['parsing_status', 'error_message'])


class CandidateSkill(models.Model):
    """
    Dynamically extracted skills from candidate resumes.

    CRITICAL: NO HARDCODED SKILL DICTIONARY!
    Skills are extracted via NLP (spaCy) from resume text.
    This allows SkillSevak to work for ANY industry.

    Per PRD.md Section 8.1:
    - Works for tech, law, healthcare, marketing, any field
    - Self-improving with more data
    - No manual updates needed
    """

    SOURCE_CHOICES = [
        ('skills_section', 'Skills Section'),
        ('experience', 'Experience Section'),
        ('projects', 'Projects Section'),
        ('education', 'Education Section'),
        ('summary', 'Summary/Objective'),
        ('full_text', 'Full Text Analysis'),
    ]

    candidate = models.ForeignKey(
        CandidateProfile,
        on_delete=models.CASCADE,
        related_name='extracted_skills'
    )

    # Skill text (as extracted)
    skill_text = models.CharField(
        max_length=200,
        help_text="Original skill text: 'Machine Learning'"
    )

    # Normalized for matching
    normalized_text = models.CharField(
        max_length=200,
        help_text="Lowercase normalized: 'machine learning'"
    )

    # Proficiency estimation (1-5 scale)
    proficiency_level = models.IntegerField(
        default=3,
        help_text="1=Beginner, 2=Basic, 3=Intermediate, 4=Proficient, 5=Expert"
    )

    # Where the skill was found
    source = models.CharField(
        max_length=50,
        choices=SOURCE_CHOICES,
        default='full_text'
    )

    # Context for explainability
    context = models.TextField(
        blank=True,
        help_text="Sentence where skill was found (for explainability)"
    )

    # NLP confidence score
    confidence_score = models.FloatField(
        default=0.8,
        help_text="NLP extraction confidence (0.0-1.0)"
    )

    # Metadata
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Candidate Skill"
        verbose_name_plural = "Candidate Skills"
        # Prevent duplicate skills per candidate
        unique_together = ['candidate', 'normalized_text']
        indexes = [
            models.Index(fields=['normalized_text']),
            models.Index(fields=['candidate', 'proficiency_level']),
        ]

    def __str__(self):
        return f"{self.skill_text} ({self.candidate.user.username})"

    def save(self, *args, **kwargs):
        # Auto-normalize on save
        if not self.normalized_text:
            self.normalized_text = self.skill_text.lower().strip()
        super().save(*args, **kwargs)


class JobSkill(models.Model):
    """
    Skills extracted from job descriptions.

    Like CandidateSkill, these are DYNAMICALLY extracted via NLP.
    No hardcoded skill lists - works for any industry.

    Per PRD.md: Includes importance level (required/preferred/nice_to_have)
    for weighted matching.
    """

    IMPORTANCE_CHOICES = [
        ('required', 'Required'),
        ('preferred', 'Preferred'),
        ('nice_to_have', 'Nice to Have'),
    ]

    job = models.ForeignKey(
        Job,
        on_delete=models.CASCADE,
        related_name='extracted_skills'
    )

    skill_text = models.CharField(
        max_length=200,
        help_text="Original skill text from job description"
    )

    normalized_text = models.CharField(
        max_length=200,
        help_text="Lowercase normalized for matching"
    )

    importance = models.CharField(
        max_length=20,
        choices=IMPORTANCE_CHOICES,
        default='required',
        help_text="Skill importance for weighted scoring"
    )

    # Context from job description
    context = models.TextField(
        blank=True,
        help_text="Context where skill was mentioned"
    )

    # Metadata
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Job Skill"
        verbose_name_plural = "Job Skills"
        unique_together = ['job', 'normalized_text']
        indexes = [
            models.Index(fields=['normalized_text']),
            models.Index(fields=['job', 'importance']),
        ]

    def __str__(self):
        return f"{self.skill_text} ({self.importance}) - {self.job.title}"

    def save(self, *args, **kwargs):
        if not self.normalized_text:
            self.normalized_text = self.skill_text.lower().strip()
        super().save(*args, **kwargs)


class MatchScore(models.Model):
    """
    Pre-computed match scores between candidates and jobs.

    This is the CORE of SkillSevak's value proposition:
    - Candidates see match % BEFORE applying
    - Recruiters see candidates ranked by match
    - Explainable: shows WHY the score is what it is

    Per PRD.md Section 8.3 (Scoring Formula):
    MVP: Match % = (0.25*Semantic) + (0.35*Skills) + (0.20*Exp) + (0.10*Edu) + (0.10*Profile)
    V1:  Match % = ANN([semantic, skills, experience, education, profile])
    """

    candidate = models.ForeignKey(
        CandidateProfile,
        on_delete=models.CASCADE,
        related_name='match_scores'
    )

    job = models.ForeignKey(
        Job,
        on_delete=models.CASCADE,
        related_name='match_scores'
    )

    # Overall match score (0-100)
    overall_score = models.FloatField(
        help_text="Final match score 0-100%"
    )

    # Component scores for explainability (all 0-100)
    semantic_similarity = models.FloatField(
        default=0,
        help_text="Text similarity via embeddings (0-100)"
    )
    skill_match_score = models.FloatField(
        default=0,
        help_text="Skill overlap score (0-100)"
    )
    experience_match_score = models.FloatField(
        default=0,
        help_text="Experience fit score (0-100)"
    )
    education_match_score = models.FloatField(
        default=0,
        help_text="Education relevance score (0-100)"
    )
    profile_completeness_score = models.FloatField(
        default=0,
        help_text="Profile completeness (0-100)"
    )

    # Skill breakdown for transparency
    matched_skills = models.JSONField(
        default=list,
        help_text="Skills that matched: [{skill, matched_with, importance}]"
    )
    missing_skills = models.JSONField(
        default=list,
        help_text="Skills candidate lacks: [{skill, importance}]"
    )

    # Actionable suggestions
    suggestions = models.JSONField(
        default=list,
        help_text="Improvement tips: ['Add Docker to improve by 5%']"
    )

    # Validity tracking (invalidate when resume/job changes)
    calculated_at = models.DateTimeField(auto_now=True)
    is_valid = models.BooleanField(
        default=True,
        help_text="False if resume or job was updated since calculation"
    )

    class Meta:
        verbose_name = "Match Score"
        verbose_name_plural = "Match Scores"
        unique_together = ['candidate', 'job']
        indexes = [
            models.Index(fields=['candidate', 'overall_score']),
            models.Index(fields=['job', 'overall_score']),
            models.Index(fields=['is_valid']),
        ]
        ordering = ['-overall_score']

    def __str__(self):
        return f"{self.candidate.user.username} <-> {self.job.title}: {self.overall_score:.1f}%"

    def invalidate(self):
        """Mark this score as stale (needs recalculation)."""
        self.is_valid = False
        self.save(update_fields=['is_valid'])

    @property
    def breakdown(self) -> dict:
        """Return score breakdown for display."""
        return {
            'semantic_similarity': round(self.semantic_similarity, 1),
            'skill_match': round(self.skill_match_score, 1),
            'experience_match': round(self.experience_match_score, 1),
            'education_match': round(self.education_match_score, 1),
            'profile_completeness': round(self.profile_completeness_score, 1),
        }

    @property
    def match_quality(self) -> str:
        """Human-readable match quality label."""
        if self.overall_score >= 85:
            return 'Excellent Match'
        elif self.overall_score >= 70:
            return 'Good Match'
        elif self.overall_score >= 50:
            return 'Potential Match'
        else:
            return 'Low Match'
