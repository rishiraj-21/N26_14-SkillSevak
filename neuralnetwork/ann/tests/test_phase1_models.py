"""
Phase 1 Tests - Foundation Models

Tests for the new AI/ML pipeline models:
- ParsedResume
- CandidateSkill
- JobSkill
- MatchScore
"""

from django.test import TestCase
from django.contrib.auth.models import User
from ann.models import (
    CandidateProfile,
    CompanyProfile,
    Job,
    ParsedResume,
    CandidateSkill,
    JobSkill,
    MatchScore,
)


class ParsedResumeModelTest(TestCase):
    """Test ParsedResume model."""

    def setUp(self):
        self.user = User.objects.create_user(
            username='testcandidate@example.com',
            email='testcandidate@example.com',
            password='testpass123'
        )
        self.candidate = CandidateProfile.objects.create(
            user=self.user,
            experience_years=3,
            profile_strength=60
        )

    def test_create_parsed_resume(self):
        """Test creating a ParsedResume instance."""
        parsed = ParsedResume.objects.create(
            candidate=self.candidate,
            raw_text="Sample resume text",
            cleaned_text="sample resume text",
            sections_json={'skills': 'Python, Django', 'experience': '3 years'},
            parsing_status='completed'
        )

        self.assertEqual(parsed.candidate, self.candidate)
        self.assertEqual(parsed.parsing_status, 'completed')
        self.assertIn('skills', parsed.sections_json)

    def test_mark_completed(self):
        """Test mark_completed method."""
        parsed = ParsedResume.objects.create(
            candidate=self.candidate,
            parsing_status='processing'
        )

        parsed.mark_completed()
        parsed.refresh_from_db()

        self.assertEqual(parsed.parsing_status, 'completed')
        self.assertIsNotNone(parsed.parsed_at)

    def test_mark_failed(self):
        """Test mark_failed method."""
        parsed = ParsedResume.objects.create(
            candidate=self.candidate,
            parsing_status='processing'
        )

        parsed.mark_failed("Test error message")
        parsed.refresh_from_db()

        self.assertEqual(parsed.parsing_status, 'failed')
        self.assertEqual(parsed.error_message, "Test error message")


class CandidateSkillModelTest(TestCase):
    """Test CandidateSkill model."""

    def setUp(self):
        self.user = User.objects.create_user(
            username='testcandidate2@example.com',
            email='testcandidate2@example.com',
            password='testpass123'
        )
        self.candidate = CandidateProfile.objects.create(
            user=self.user,
            experience_years=5
        )

    def test_create_candidate_skill(self):
        """Test creating a CandidateSkill instance."""
        skill = CandidateSkill.objects.create(
            candidate=self.candidate,
            skill_text="Machine Learning",
            proficiency_level=4,
            source='skills_section',
            confidence_score=0.9
        )

        self.assertEqual(skill.skill_text, "Machine Learning")
        self.assertEqual(skill.normalized_text, "machine learning")  # Auto-normalized
        self.assertEqual(skill.proficiency_level, 4)

    def test_auto_normalization(self):
        """Test that skills are auto-normalized on save."""
        skill = CandidateSkill.objects.create(
            candidate=self.candidate,
            skill_text="  Django Framework  ",
            source='experience'
        )

        self.assertEqual(skill.normalized_text, "django framework")

    def test_unique_together_constraint(self):
        """Test that duplicate skills per candidate are prevented."""
        CandidateSkill.objects.create(
            candidate=self.candidate,
            skill_text="Python",
            source='skills_section'
        )

        # Attempting to create duplicate should raise error
        from django.db import IntegrityError
        with self.assertRaises(IntegrityError):
            CandidateSkill.objects.create(
                candidate=self.candidate,
                skill_text="Python",  # Same normalized text
                source='experience'
            )


class JobSkillModelTest(TestCase):
    """Test JobSkill model."""

    def setUp(self):
        self.user = User.objects.create_user(
            username='testrecruiter@example.com',
            email='testrecruiter@example.com',
            password='testpass123'
        )
        self.company = CompanyProfile.objects.create(
            user=self.user,
            company_name="Test Company"
        )
        self.job = Job.objects.create(
            company_profile=self.company,
            company="Test Company",
            title="Software Engineer",
            location="Remote",
            salary_min=80000,
            salary_max=120000,
            job_type='full-time',
            description="Test description",
            requirements="Python, Django experience",
            skills_required="Python, Django"
        )

    def test_create_job_skill(self):
        """Test creating a JobSkill instance."""
        skill = JobSkill.objects.create(
            job=self.job,
            skill_text="Python",
            importance='required'
        )

        self.assertEqual(skill.skill_text, "Python")
        self.assertEqual(skill.normalized_text, "python")
        self.assertEqual(skill.importance, 'required')


class MatchScoreModelTest(TestCase):
    """Test MatchScore model."""

    def setUp(self):
        # Create candidate
        self.candidate_user = User.objects.create_user(
            username='candidate@example.com',
            email='candidate@example.com',
            password='testpass123'
        )
        self.candidate = CandidateProfile.objects.create(
            user=self.candidate_user,
            experience_years=3
        )

        # Create job
        self.recruiter_user = User.objects.create_user(
            username='recruiter@example.com',
            email='recruiter@example.com',
            password='testpass123'
        )
        self.company = CompanyProfile.objects.create(
            user=self.recruiter_user,
            company_name="Test Company"
        )
        self.job = Job.objects.create(
            company_profile=self.company,
            company="Test Company",
            title="Data Scientist",
            location="NYC",
            salary_min=100000,
            salary_max=150000,
            job_type='full-time',
            description="ML role",
            requirements="Python, ML",
            skills_required="Python, ML"
        )

    def test_create_match_score(self):
        """Test creating a MatchScore instance."""
        match = MatchScore.objects.create(
            candidate=self.candidate,
            job=self.job,
            overall_score=85.5,
            semantic_similarity=80.0,
            skill_match_score=90.0,
            experience_match_score=85.0,
            education_match_score=75.0,
            profile_completeness_score=80.0,
            matched_skills=[{'skill': 'Python', 'matched_with': 'python'}],
            missing_skills=[{'skill': 'ML', 'importance': 'required'}],
            suggestions=['Add ML certification']
        )

        self.assertEqual(match.overall_score, 85.5)
        self.assertTrue(match.is_valid)
        self.assertEqual(match.match_quality, 'Excellent Match')

    def test_match_quality_property(self):
        """Test match_quality property returns correct labels."""
        # Excellent (>= 85)
        match = MatchScore.objects.create(
            candidate=self.candidate,
            job=self.job,
            overall_score=90.0
        )
        self.assertEqual(match.match_quality, 'Excellent Match')

        match.overall_score = 75.0
        self.assertEqual(match.match_quality, 'Good Match')

        match.overall_score = 55.0
        self.assertEqual(match.match_quality, 'Potential Match')

        match.overall_score = 40.0
        self.assertEqual(match.match_quality, 'Low Match')

    def test_invalidate_method(self):
        """Test invalidate method marks score as stale."""
        match = MatchScore.objects.create(
            candidate=self.candidate,
            job=self.job,
            overall_score=80.0
        )

        self.assertTrue(match.is_valid)
        match.invalidate()
        match.refresh_from_db()
        self.assertFalse(match.is_valid)

    def test_breakdown_property(self):
        """Test breakdown property returns formatted scores."""
        match = MatchScore.objects.create(
            candidate=self.candidate,
            job=self.job,
            overall_score=80.0,
            semantic_similarity=82.333,
            skill_match_score=85.666,
            experience_match_score=75.123,
            education_match_score=70.999,
            profile_completeness_score=80.555
        )

        breakdown = match.breakdown
        self.assertEqual(breakdown['semantic_similarity'], 82.3)
        self.assertEqual(breakdown['skill_match'], 85.7)
        self.assertEqual(breakdown['experience_match'], 75.1)
