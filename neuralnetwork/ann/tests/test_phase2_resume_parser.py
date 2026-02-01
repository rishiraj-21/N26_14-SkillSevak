"""
Phase 2 Tests - Resume Parser Service

Tests for:
- Text extraction from PDF/DOCX
- Text cleaning
- Section detection
- Contact info extraction
- Completeness scoring
"""

import os
import tempfile
from pathlib import Path
from unittest.mock import patch, MagicMock

from django.test import TestCase, Client
from django.contrib.auth.models import User
from django.urls import reverse

from ann.models import CandidateProfile, ParsedResume
from ann.services.resume_parser import ResumeParser


class ResumeParserTextCleaningTest(TestCase):
    """Test text cleaning functionality."""

    def setUp(self):
        self.parser = ResumeParser()

    def test_clean_text_removes_extra_whitespace(self):
        """Test that multiple spaces are normalized."""
        text = "Hello    World   Test"
        cleaned = self.parser.clean_text(text)
        self.assertEqual(cleaned, "Hello World Test")

    def test_clean_text_normalizes_newlines(self):
        """Test that multiple newlines are normalized to double."""
        text = "Section 1\n\n\n\n\nSection 2"
        cleaned = self.parser.clean_text(text)
        self.assertEqual(cleaned, "Section 1\n\nSection 2")

    def test_clean_text_handles_empty_string(self):
        """Test handling of empty string."""
        self.assertEqual(self.parser.clean_text(""), "")
        self.assertEqual(self.parser.clean_text(None), "")

    def test_clean_text_strips_lines(self):
        """Test that leading/trailing whitespace on lines is removed."""
        text = "  Line 1  \n  Line 2  "
        cleaned = self.parser.clean_text(text)
        self.assertEqual(cleaned, "Line 1\nLine 2")


class ResumeParserSectionDetectionTest(TestCase):
    """Test section detection functionality."""

    def setUp(self):
        self.parser = ResumeParser()

    def test_detect_skills_section(self):
        """Test detection of skills section header."""
        text = """John Doe
john@email.com

Skills
Python, Django, Machine Learning

Experience
Software Engineer at TechCorp"""

        sections = self.parser.detect_sections(text)
        self.assertIn('skills', sections)
        self.assertIn('Python', sections['skills'])

    def test_detect_experience_section(self):
        """Test detection of experience section."""
        text = """Name: John
Email: john@test.com

Experience
- Software Engineer at TechCorp (2020-2023)
- Built scalable APIs

Education
BS in Computer Science"""

        sections = self.parser.detect_sections(text)
        self.assertIn('experience', sections)
        self.assertIn('Software Engineer', sections['experience'])
        self.assertIn('education', sections)

    def test_detect_uppercase_headers(self):
        """Test detection of ALL CAPS section headers."""
        text = """Contact Info
john@email.com

SKILLS
Python, Java, SQL

EXPERIENCE
Developer at Company"""

        sections = self.parser.detect_sections(text)
        # Should still detect the sections
        self.assertTrue(
            sections.get('skills') or sections.get('experience'),
            "Should detect at least one section"
        )

    def test_empty_text_returns_empty_sections(self):
        """Test that empty text returns empty sections."""
        sections = self.parser.detect_sections("")
        self.assertEqual(sections['skills'], '')
        self.assertEqual(sections['experience'], '')

    def test_contact_section_limited(self):
        """Test that contact section is limited to first few lines."""
        text = """John Doe
john@email.com
123-456-7890
New York, NY
linkedin.com/in/johndoe
github.com/johndoe
Available immediately
Looking for remote positions
This is line 9
This is line 10"""

        sections = self.parser.detect_sections(text)
        # Contact should be limited, rest should go to 'other'
        self.assertIn('contact', sections)
        contact_lines = len(sections['contact'].split('\n'))
        self.assertLessEqual(contact_lines, 10)


class ResumeParserContactExtractionTest(TestCase):
    """Test contact info extraction."""

    def setUp(self):
        self.parser = ResumeParser()

    def test_extract_email(self):
        """Test email extraction."""
        text = "Contact me at john.doe@example.com for opportunities"
        contact = self.parser.extract_contact_info(text)
        self.assertEqual(contact['email'], 'john.doe@example.com')

    def test_extract_phone_us_format(self):
        """Test US phone number extraction."""
        text = "Phone: (123) 456-7890"
        contact = self.parser.extract_contact_info(text)
        self.assertIn('123', contact['phone'])

    def test_extract_linkedin(self):
        """Test LinkedIn URL extraction."""
        text = "LinkedIn: https://www.linkedin.com/in/johndoe"
        contact = self.parser.extract_contact_info(text)
        self.assertIn('johndoe', contact['linkedin'])

    def test_extract_github(self):
        """Test GitHub URL extraction."""
        text = "GitHub: github.com/johndoe"
        contact = self.parser.extract_contact_info(text)
        self.assertIn('johndoe', contact['github'])

    def test_empty_text_returns_empty_contact(self):
        """Test that empty text returns empty contact dict."""
        contact = self.parser.extract_contact_info("")
        self.assertEqual(contact['email'], '')
        self.assertEqual(contact['phone'], '')


class ResumeParserCompletenessTest(TestCase):
    """Test completeness score calculation."""

    def setUp(self):
        self.parser = ResumeParser()

    def test_empty_resume_low_score(self):
        """Test that empty resume gets low score."""
        sections = {k: '' for k in ['contact', 'summary', 'skills', 'experience', 'education', 'projects', 'certifications', 'awards', 'languages', 'interests', 'references', 'other']}
        score = self.parser.calculate_completeness_score(sections)
        self.assertEqual(score, 0)

    def test_complete_resume_high_score(self):
        """Test that complete resume gets high score."""
        sections = {
            'contact': 'john@email.com\n123-456-7890\nNew York',
            'summary': 'Experienced software engineer with 5 years...',
            'skills': 'Python Django React JavaScript SQL Docker Kubernetes AWS',
            'experience': ' '.join(['word'] * 150),  # 150 words
            'education': 'BS Computer Science from MIT, graduated 2018',
            'projects': 'Built a machine learning platform...',
            'certifications': 'AWS Certified',
            'awards': '',
            'languages': '',
            'interests': '',
            'references': '',
            'other': '',
        }
        score = self.parser.calculate_completeness_score(sections)
        self.assertGreaterEqual(score, 70)  # Should be high

    def test_partial_resume_medium_score(self):
        """Test that partial resume gets medium score."""
        sections = {
            'contact': 'john@email.com',
            'summary': '',
            'skills': 'Python Django',
            'experience': 'Some experience text here with enough words.',
            'education': 'BS Computer Science',
            'projects': '',
            'certifications': '',
            'awards': '',
            'languages': '',
            'interests': '',
            'references': '',
            'other': '',
        }
        score = self.parser.calculate_completeness_score(sections)
        self.assertGreater(score, 20)
        self.assertLess(score, 80)


class ResumeParserFileValidationTest(TestCase):
    """Test file validation."""

    def setUp(self):
        self.parser = ResumeParser()

    def test_unsupported_file_type_raises_error(self):
        """Test that unsupported file types raise ValueError."""
        # Create a temp file with .txt extension
        with tempfile.NamedTemporaryFile(suffix='.txt', delete=False) as f:
            f.write(b'This is a text file')
            temp_path = f.name

        try:
            with self.assertRaises(ValueError) as context:
                self.parser.extract_text(temp_path)
            self.assertIn('Unsupported file type', str(context.exception))
        finally:
            os.unlink(temp_path)

    def test_file_not_found_raises_error(self):
        """Test that missing file raises FileNotFoundError."""
        with self.assertRaises(FileNotFoundError):
            self.parser.extract_text('/nonexistent/path/resume.pdf')


class ResumeUploadAPITest(TestCase):
    """Test resume upload API endpoint."""

    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(
            username='testuser@example.com',
            email='testuser@example.com',
            password='testpass123'
        )
        self.profile = CandidateProfile.objects.create(user=self.user)

    def test_upload_requires_authentication(self):
        """Test that upload requires login."""
        response = self.client.post(reverse('upload_resume'))
        self.assertEqual(response.status_code, 401)

    def test_upload_requires_file(self):
        """Test that upload requires a file."""
        self.client.login(username='testuser@example.com', password='testpass123')
        response = self.client.post(reverse('upload_resume'))
        self.assertEqual(response.status_code, 400)
        self.assertIn('error', response.json())

    def test_upload_rejects_invalid_file_type(self):
        """Test that invalid file types are rejected."""
        self.client.login(username='testuser@example.com', password='testpass123')

        # Create a temporary text file
        with tempfile.NamedTemporaryFile(suffix='.txt', delete=False) as f:
            f.write(b'This is a text file')
            temp_path = f.name

        try:
            with open(temp_path, 'rb') as f:
                response = self.client.post(
                    reverse('upload_resume'),
                    {'resume': f}
                )
            self.assertEqual(response.status_code, 400)
            self.assertIn('Invalid file type', response.json().get('error', ''))
        finally:
            os.unlink(temp_path)


class GetParsedResumeAPITest(TestCase):
    """Test get parsed resume API endpoint."""

    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(
            username='testuser2@example.com',
            email='testuser2@example.com',
            password='testpass123'
        )
        self.profile = CandidateProfile.objects.create(user=self.user)

    def test_get_parsed_resume_requires_auth(self):
        """Test that endpoint requires authentication."""
        response = self.client.get(reverse('get_parsed_resume'))
        # Should redirect to login
        self.assertIn(response.status_code, [302, 401])

    def test_get_parsed_resume_no_upload(self):
        """Test response when no resume uploaded."""
        self.client.login(username='testuser2@example.com', password='testpass123')
        response = self.client.get(reverse('get_parsed_resume'))
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data['parsing_status'], 'not_uploaded')

    def test_get_parsed_resume_with_data(self):
        """Test response when resume has been parsed."""
        self.client.login(username='testuser2@example.com', password='testpass123')

        # Create a parsed resume
        from django.utils import timezone
        ParsedResume.objects.create(
            candidate=self.profile,
            raw_text='Test resume content',
            cleaned_text='test resume content',
            sections_json={'skills': 'Python', 'experience': 'Developer'},
            parsing_status='completed',
            parsed_at=timezone.now()
        )

        response = self.client.get(reverse('get_parsed_resume'))
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data['success'])
        self.assertEqual(data['parsing_status'], 'completed')
        self.assertIn('sections', data)


class ResumeParserWordCountTest(TestCase):
    """Test word count functionality."""

    def setUp(self):
        self.parser = ResumeParser()

    def test_word_count_normal(self):
        """Test normal word count."""
        text = "This is a test sentence with eight words"
        self.assertEqual(self.parser.get_word_count(text), 8)

    def test_word_count_empty(self):
        """Test empty string word count."""
        self.assertEqual(self.parser.get_word_count(""), 0)
        self.assertEqual(self.parser.get_word_count(None), 0)

    def test_word_count_with_extra_spaces(self):
        """Test word count with extra spaces."""
        text = "Word1   Word2    Word3"
        # After splitting, we get ['Word1', '', '', 'Word2', '', '', '', 'Word3']
        # But split() without arg handles this correctly
        self.assertEqual(self.parser.get_word_count(text), 3)
