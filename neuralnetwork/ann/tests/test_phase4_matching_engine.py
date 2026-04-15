"""

Tests the MatchingEngine and EmbeddingService per PROJECT_PLAN.md.

Key tests:
- Semantic similarity calculation
- Skill match with category weighting
- Experience match
- Education match
- Profile completeness
- Overall score calculation
- Suggestion generation
"""

from django.test import TestCase
from django.contrib.auth.models import User
from unittest.mock import Mock, patch, MagicMock
import numpy as np


class TestEmbeddingService(TestCase):
    """Test the EmbeddingService."""

    def test_generate_embedding_returns_correct_shape(self):
        """Test that embeddings have correct dimensions."""
        from ann.services.embedding_service import EmbeddingService

        service = EmbeddingService()
        text = "Python developer with machine learning experience"
        embedding = service.generate_embedding(text)

        self.assertEqual(embedding.shape, (384,))
        self.assertEqual(embedding.dtype, np.float32)

    def test_empty_text_returns_zero_embedding(self):
        """Test that empty text returns zero vector."""
        from ann.services.embedding_service import EmbeddingService

        service = EmbeddingService()

        empty_embedding = service.generate_embedding("")
        whitespace_embedding = service.generate_embedding("   ")

        self.assertTrue(np.allclose(empty_embedding, np.zeros(384)))
        self.assertTrue(np.allclose(whitespace_embedding, np.zeros(384)))

    def test_similar_texts_have_high_similarity(self):
        """Test that similar texts have high cosine similarity."""
        from ann.services.embedding_service import EmbeddingService
        from sklearn.metrics.pairwise import cosine_similarity

        service = EmbeddingService()

        text1 = "Python developer with machine learning experience"
        text2 = "Software engineer proficient in Python and ML"

        emb1 = service.generate_embedding(text1)
        emb2 = service.generate_embedding(text2)

        similarity = cosine_similarity(
            emb1.reshape(1, -1),
            emb2.reshape(1, -1)
        )[0][0]

        # Similar texts should have similarity > 0.5
        self.assertGreater(similarity, 0.5)

    def test_different_texts_have_lower_similarity(self):
        """Test that different texts have lower similarity."""
        from ann.services.embedding_service import EmbeddingService
        from sklearn.metrics.pairwise import cosine_similarity

        service = EmbeddingService()

        text1 = "Python developer with machine learning experience"
        text2 = "Chef specializing in Italian cuisine"

        emb1 = service.generate_embedding(text1)
        emb2 = service.generate_embedding(text2)

        similarity = cosine_similarity(
            emb1.reshape(1, -1),
            emb2.reshape(1, -1)
        )[0][0]

        # Different texts should have similarity < 0.5
        self.assertLess(similarity, 0.5)

    def test_serialize_deserialize_embedding(self):
        """Test embedding serialization and deserialization."""
        from ann.services.embedding_service import EmbeddingService

        service = EmbeddingService()

        original = service.generate_embedding("Test text")
        serialized = service.serialize_embedding(original)
        deserialized = service.deserialize_embedding(serialized)

        self.assertTrue(np.allclose(original, deserialized))

    def test_batch_embedding_generation(self):
        """Test batch embedding generation."""
        from ann.services.embedding_service import EmbeddingService

        service = EmbeddingService()

        texts = [
            "Python developer",
            "Data scientist",
            "Machine learning engineer"
        ]

        embeddings = service.generate_embeddings_batch(texts)

        self.assertEqual(embeddings.shape, (3, 384))


class TestMatchingEngine(TestCase):
    """Test the MatchingEngine."""

    def setUp(self):
        """Set up test data."""
        # Create test user and candidate
        self.user = User.objects.create_user(
            username='testcandidate',
            email='test@example.com',
            password='testpass123'
        )

    def test_matching_engine_initialization(self):
        """Test that matching engine initializes with correct weights."""
        from ann.services.matching_engine import MatchingEngine

        engine = MatchingEngine()

        # Check main weights
        self.assertEqual(engine.weights['semantic'], 0.25)
        self.assertEqual(engine.weights['skills'], 0.35)
        self.assertEqual(engine.weights['experience'], 0.20)
        self.assertEqual(engine.weights['education'], 0.10)
        self.assertEqual(engine.weights['profile'], 0.10)

        # Check skill category weights
        self.assertEqual(engine.skills_weights['technical'], 0.70)
        self.assertEqual(engine.skills_weights['domain'], 0.20)
        self.assertEqual(engine.skills_weights['soft'], 0.10)

    def test_experience_match_perfect(self):
        """Test experience match when candidate meets requirements."""
        from ann.services.matching_engine import MatchingEngine

        engine = MatchingEngine()

        # Mock candidate with 5 years experience
        candidate = Mock()
        candidate.experience_years = 5

        # Mock job requiring 3-7 years
        job = Mock()
        job.experience_min = 3
        job.experience_max = 7

        score = engine._calculate_experience_match(candidate, job)

        self.assertEqual(score, 100.0)

    def test_experience_match_underqualified(self):
        """Test experience match when candidate is underqualified."""
        from ann.services.matching_engine import MatchingEngine

        engine = MatchingEngine()

        # Mock candidate with 1 year experience
        candidate = Mock()
        candidate.experience_years = 1

        # Mock job requiring 5-10 years
        job = Mock()
        job.experience_min = 5
        job.experience_max = 10

        score = engine._calculate_experience_match(candidate, job)

        # Should be penalized but not zero
        self.assertLess(score, 100.0)
        self.assertGreater(score, 0.0)

    def test_experience_match_overqualified(self):
        """Test experience match when candidate is overqualified."""
        from ann.services.matching_engine import MatchingEngine

        engine = MatchingEngine()

        # Mock candidate with 15 years experience
        candidate = Mock()
        candidate.experience_years = 15

        # Mock job requiring 3-7 years
        job = Mock()
        job.experience_min = 3
        job.experience_max = 7

        score = engine._calculate_experience_match(candidate, job)

        # Should be slightly penalized
        self.assertLess(score, 100.0)
        self.assertGreaterEqual(score, 70.0)  # Minimum 70 for overqualified

    def test_profile_completeness_calculation(self):
        """Test profile completeness score calculation."""
        from ann.services.matching_engine import MatchingEngine

        engine = MatchingEngine()

        # Mock candidate with profile_strength set
        candidate = Mock()
        candidate.profile_strength = 85

        score = engine._calculate_profile_completeness(candidate)

        self.assertEqual(score, 85.0)

    def test_suggestion_generation(self):
        """Test that suggestions are generated based on scores."""
        from ann.services.matching_engine import MatchingEngine

        engine = MatchingEngine()

        # Test with missing skills
        missing_skills = [
            {'skill': 'Python', 'importance': 'required'},
            {'skill': 'Django', 'importance': 'required'},
        ]

        suggestions = engine._generate_suggestions(
            missing_skills=missing_skills,
            skill_score=40.0,
            experience_score=80.0,
            overall_score=55.0
        )

        self.assertTrue(len(suggestions) > 0)
        self.assertTrue(len(suggestions) <= 3)  # Max 3 suggestions

    def test_suggestion_for_low_match(self):
        """Test suggestions for low overall match."""
        from ann.services.matching_engine import MatchingEngine

        engine = MatchingEngine()

        suggestions = engine._generate_suggestions(
            missing_skills=[],
            skill_score=20.0,
            experience_score=30.0,
            overall_score=25.0
        )

        # Should suggest considering other roles
        any_suggest_other = any(
            'consider' in s.lower() or 'aligned' in s.lower()
            for s in suggestions
        )
        self.assertTrue(any_suggest_other)

    def test_suggestion_for_high_match(self):
        """Test suggestions for high overall match."""
        from ann.services.matching_engine import MatchingEngine

        engine = MatchingEngine()

        suggestions = engine._generate_suggestions(
            missing_skills=[],
            skill_score=90.0,
            experience_score=95.0,
            overall_score=92.0
        )

        # Should encourage applying
        any_strong_match = any(
            'strong match' in s.lower()
            for s in suggestions
        )
        self.assertTrue(any_strong_match)

    def test_weights_sum_to_one(self):
        """Test that main weights sum to 1.0."""
        from ann.services.matching_engine import MatchingEngine

        engine = MatchingEngine()

        total = sum(engine.weights.values())
        self.assertAlmostEqual(total, 1.0, places=5)

    def test_skill_weights_sum_to_one(self):
        """Test that skill category weights sum to 1.0."""
        from ann.services.matching_engine import MatchingEngine

        engine = MatchingEngine()

        total = sum(engine.skills_weights.values())
        self.assertAlmostEqual(total, 1.0, places=5)

    def test_build_job_text(self):
        """Test job text building for embedding."""
        from ann.services.matching_engine import MatchingEngine

        engine = MatchingEngine()

        job = Mock()
        job.title = "Software Engineer"
        job.description = "Build amazing software"
        job.requirements = "Python experience required"
        job.skills_required = "Python, Django"
        job.category = "Engineering"

        text = engine._build_job_text(job)

        self.assertIn("Software Engineer", text)
        self.assertIn("Build amazing software", text)
        self.assertIn("Python experience required", text)

    def test_parse_skills_required_comma_separated(self):
        """Test parsing comma-separated skills."""
        from ann.services.matching_engine import MatchingEngine

        engine = MatchingEngine()

        job = Mock()
        job.skills_required = "Python, Django, React, Node.js"

        skills = engine._parse_skills_required(job)

        self.assertEqual(len(skills), 4)
        skill_names = [s.skill_text for s in skills]
        self.assertIn("Python", skill_names)
        self.assertIn("Django", skill_names)

    def test_parse_skills_required_json(self):
        """Test parsing JSON skills list."""
        from ann.services.matching_engine import MatchingEngine
        import json

        engine = MatchingEngine()

        job = Mock()
        job.skills_required = json.dumps(["Python", "Django", "React"])

        skills = engine._parse_skills_required(job)

        self.assertEqual(len(skills), 3)


class TestMatchScoreCalculation(TestCase):
    """Test complete match score calculation."""

    def test_calculate_match_returns_all_fields(self):
        """Test that calculate_match returns all required fields."""
        from ann.services.matching_engine import MatchingEngine
        from ann.models import CandidateProfile, Job
        from django.contrib.auth.models import User

        engine = MatchingEngine()

        # Create real objects
        user = User.objects.create_user(
            username='matchtest',
            email='match@test.com',
            password='test123'
        )
        candidate = CandidateProfile.objects.create(
            user=user,
            experience_years=3
        )

        job = Job.objects.create(
            title='Software Engineer',
            company='Test Company',
            description='Build software',
            requirements='Python required',
            location='Remote',
            salary_min=50000,
            salary_max=100000,
            job_type='full-time',
            skills_required='Python, Django'
        )

        result = engine.calculate_match(candidate, job)

        # Check all required fields exist
        self.assertIn('overall_score', result)
        self.assertIn('breakdown', result)
        self.assertIn('matched_skills', result)
        self.assertIn('missing_skills', result)
        self.assertIn('suggestions', result)

        # Check breakdown fields
        breakdown = result['breakdown']
        self.assertIn('semantic_similarity', breakdown)
        self.assertIn('skill_match', breakdown)
        self.assertIn('experience_match', breakdown)
        self.assertIn('education_match', breakdown)
        self.assertIn('profile_completeness', breakdown)

        # Check score is in valid range
        self.assertGreaterEqual(result['overall_score'], 0)
        self.assertLessEqual(result['overall_score'], 100)
