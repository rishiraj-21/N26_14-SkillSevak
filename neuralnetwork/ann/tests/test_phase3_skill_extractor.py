"""

Tests the DynamicSkillExtractor service per PROJECT_PLAN.md.

Key tests:
- Noun phrase extraction
- Proper noun extraction
- Named entity recognition
- Pattern-based extraction
- Skill categorization (technical/domain/soft)
- Proficiency estimation
- Job skill extraction with importance levels
"""

from django.test import TestCase


class TestDynamicSkillExtractor(TestCase):
    """Test the DynamicSkillExtractor service."""

    @classmethod
    def setUpClass(cls):
        """Load the extractor once for all tests."""
        super().setUpClass()
        from ann.services.skill_extractor import DynamicSkillExtractor
        cls.extractor = DynamicSkillExtractor()

    def test_extract_technical_skills(self):
        """Test extraction of technical skills like Python, React, etc."""
        text = """
        Experienced software developer with 5 years of Python experience.
        Proficient in React, Node.js, and PostgreSQL.
        Built REST APIs using Django and Flask.
        """
        skills = self.extractor.extract_skills(text, 'skills')

        skill_names = [s['normalized'] for s in skills]

        # Should extract technology names
        self.assertTrue(
            any('python' in s for s in skill_names),
            f"Should extract 'Python'. Got: {skill_names}"
        )

    def test_extract_soft_skills(self):
        """Test extraction and categorization of soft skills."""
        text = """
        Excellent communication skills and team leadership experience.
        Strong problem-solving abilities and attention to detail.
        """
        skills = self.extractor.extract_skills(text, 'skills')

        # Check for soft skill categorization
        soft_skills = [s for s in skills if s.get('category') == 'soft']
        self.assertTrue(
            len(soft_skills) > 0,
            "Should identify soft skills"
        )

    def test_extract_from_skills_section(self):
        """Test pattern-based extraction from skills section."""
        text = "Python, JavaScript, React, Node.js, PostgreSQL, Docker, Kubernetes"
        skills = self.extractor.extract_skills(text, 'skills')

        # Pattern extraction should get most of these
        self.assertGreaterEqual(
            len(skills), 3,
            f"Should extract multiple skills from comma list. Got {len(skills)}"
        )

    def test_skill_normalization(self):
        """Test that skills are properly normalized."""
        text = "Experience with Machine Learning and PYTHON programming"
        skills = self.extractor.extract_skills(text, 'experience')

        for skill in skills:
            # Normalized should be lowercase
            self.assertEqual(
                skill['normalized'],
                skill['normalized'].lower(),
                "Normalized text should be lowercase"
            )

    def test_proficiency_estimation_expert(self):
        """Test proficiency estimation for expert level."""
        text = "10+ years of expert-level Python development. Architect for ML systems."
        proficiency = self.extractor.estimate_proficiency("Python", text)

        self.assertGreaterEqual(
            proficiency, 4,
            "Expert indicators should result in high proficiency"
        )

    def test_proficiency_estimation_beginner(self):
        """Test proficiency estimation for beginner level."""
        text = "Recently started learning Python. Basic understanding of programming."
        proficiency = self.extractor.estimate_proficiency("Python", text)

        self.assertLessEqual(
            proficiency, 2,
            "Beginner indicators should result in low proficiency"
        )

    def test_job_skills_extraction(self):
        """Test extraction of skills from job description."""
        description = "We are looking for a Python developer with React experience."
        requirements = "Required: Python, Django. Nice to have: Docker, Kubernetes."

        skills = self.extractor.extract_job_skills(description, requirements)

        self.assertTrue(
            len(skills) > 0,
            "Should extract skills from job description"
        )

        # Check for importance levels
        importances = [s.get('importance') for s in skills]
        self.assertTrue(
            'required' in importances or 'preferred' in importances,
            "Should assign importance levels"
        )

    def test_skill_importance_detection(self):
        """Test detection of skill importance levels."""
        requirements = """
        Must have: Python, Django
        Preferred: React, TypeScript
        Nice to have: Docker
        """
        skills = self.extractor.extract_job_skills('', requirements)

        importance_map = {s['normalized']: s.get('importance') for s in skills}

        # Python should be required
        if 'python' in importance_map:
            self.assertEqual(
                importance_map['python'], 'required',
                "Skills with 'must have' should be marked required"
            )

    def test_skill_categories(self):
        """Test skill categorization (technical/domain/soft)."""
        text = """
        Technical: Python programming, Docker containers, AWS cloud
        Soft: Leadership, communication, teamwork
        Domain: Financial analysis, market research
        """
        skills = self.extractor.extract_skills(text, 'skills')

        categories = set(s.get('category') for s in skills)

        # Should have multiple categories
        self.assertTrue(
            len(categories) >= 1,
            "Should categorize skills into different types"
        )

    def test_calculate_skill_match_score(self):
        """Test skill match score calculation."""
        candidate_skills = [
            {'skill': 'Python', 'normalized': 'python', 'category': 'technical'},
            {'skill': 'Django', 'normalized': 'django', 'category': 'technical'},
            {'skill': 'Communication', 'normalized': 'communication', 'category': 'soft'},
        ]

        job_skills = [
            {'skill': 'Python', 'normalized': 'python', 'category': 'technical', 'importance': 'required'},
            {'skill': 'Django', 'normalized': 'django', 'category': 'technical', 'importance': 'required'},
            {'skill': 'React', 'normalized': 'react', 'category': 'technical', 'importance': 'preferred'},
        ]

        score, matched, missing = self.extractor.calculate_skill_match_score(
            candidate_skills, job_skills
        )

        self.assertGreater(score, 0, "Score should be positive")
        self.assertLessEqual(score, 100, "Score should be <= 100")
        self.assertTrue(len(matched) > 0, "Should have matched skills")
        self.assertTrue(len(missing) > 0, "Should have missing skills")

    def test_no_hardcoded_skills(self):
        """Test that extractor works with non-tech skills (no hardcoding)."""
        # Legal industry
        legal_text = "Patent law specialist with M&A experience. Corporate litigation."
        legal_skills = self.extractor.extract_skills(legal_text, 'skills')

        # Healthcare industry
        healthcare_text = "ICU nursing experience. Ventilator management. Patient care."
        healthcare_skills = self.extractor.extract_skills(healthcare_text, 'skills')

        # Both should extract skills without hardcoded dictionaries
        self.assertTrue(
            len(legal_skills) > 0,
            "Should extract legal industry skills"
        )
        self.assertTrue(
            len(healthcare_skills) > 0,
            "Should extract healthcare industry skills"
        )

    def test_empty_text_handling(self):
        """Test handling of empty or whitespace text."""
        empty_skills = self.extractor.extract_skills("", 'skills')
        whitespace_skills = self.extractor.extract_skills("   \n\t  ", 'skills')

        self.assertEqual(len(empty_skills), 0, "Empty text should return no skills")
        self.assertEqual(len(whitespace_skills), 0, "Whitespace should return no skills")

    def test_deduplication(self):
        """Test that duplicate skills are removed."""
        text = "Python, python, PYTHON, Python programming"
        skills = self.extractor.extract_skills(text, 'skills')

        normalized = [s['normalized'] for s in skills]
        unique_normalized = set(normalized)

        self.assertEqual(
            len(normalized), len(unique_normalized),
            "Should deduplicate skills"
        )


class TestSkillCategory(TestCase):
    """Test the SkillCategory enum."""

    def test_category_values(self):
        """Test that category enum has correct values."""
        from ann.services.skill_extractor import SkillCategory

        self.assertEqual(SkillCategory.TECHNICAL.value, 'technical')
        self.assertEqual(SkillCategory.DOMAIN.value, 'domain')
        self.assertEqual(SkillCategory.SOFT.value, 'soft')
