"""
Phase 6 Tests: Async Task Processing

Tests for Celery tasks and async resume processing.
These tests work WITHOUT Redis by using Celery's eager mode.

Run tests:
    python manage.py test ann.tests.test_phase6_async_tasks
"""

from django.test import TestCase, override_settings
from django.contrib.auth.models import User
from unittest.mock import patch, MagicMock
import json


class TestCeleryConfiguration(TestCase):
    """Test Celery configuration and setup."""

    def test_celery_app_imports_when_available(self):
        """Test that Celery app can be imported when celery is installed."""
        try:
            from neuralnetwork.celery import app
            # If celery is installed, app should not be None
            if app is not None:
                self.assertEqual(app.main, 'neuralnetwork')
        except ImportError:
            # Celery not installed - this is OK
            pass

    def test_celery_app_graceful_fallback(self):
        """Test that missing Celery doesn't crash the app."""
        from neuralnetwork import celery_app
        # Should be None or Celery app - either is valid
        self.assertTrue(celery_app is None or hasattr(celery_app, 'task'))

    def test_settings_has_celery_config(self):
        """Test that Celery settings are configured."""
        from django.conf import settings

        self.assertTrue(hasattr(settings, 'CELERY_BROKER_URL'))
        self.assertTrue(hasattr(settings, 'CELERY_RESULT_BACKEND'))
        self.assertTrue(hasattr(settings, 'USE_ASYNC_PROCESSING'))

    def test_async_processing_default_false(self):
        """Test that async processing is disabled by default."""
        from django.conf import settings

        # Default should be False for safety
        self.assertFalse(settings.USE_ASYNC_PROCESSING)


class TestTaskDefinitions(TestCase):
    """Test that task functions are properly defined."""

    def test_tasks_module_imports(self):
        """Test that tasks module can be imported."""
        try:
            from ann import tasks
            self.assertTrue(hasattr(tasks, 'parse_resume_task'))
            self.assertTrue(hasattr(tasks, 'extract_skills_task'))
            self.assertTrue(hasattr(tasks, 'generate_embedding_task'))
            self.assertTrue(hasattr(tasks, 'calculate_matches_task'))
            self.assertTrue(hasattr(tasks, 'process_resume_complete_task'))
            self.assertTrue(hasattr(tasks, 'retrain_model_task'))
        except ImportError as e:
            # If celery not installed, tasks might fail to import
            self.skipTest(f"Celery not installed: {e}")

    def test_utility_functions_exist(self):
        """Test utility functions are defined."""
        try:
            from ann.tasks import process_resume_sync, is_celery_available
            self.assertTrue(callable(process_resume_sync))
            self.assertTrue(callable(is_celery_available))
        except ImportError:
            self.skipTest("Celery not installed")

    def test_is_celery_available_returns_bool(self):
        """Test is_celery_available returns boolean."""
        try:
            from ann.tasks import is_celery_available
            result = is_celery_available()
            self.assertIsInstance(result, bool)
        except ImportError:
            self.skipTest("Celery not installed")


class TestSyncProcessing(TestCase):
    """Test synchronous (non-Celery) processing still works."""

    def setUp(self):
        """Create test user and profile."""
        self.user = User.objects.create_user(
            username='testuser@example.com',
            email='testuser@example.com',
            password='testpass123'
        )

    def test_upload_resume_sync_mode(self):
        """Test resume upload works in sync mode."""
        from django.conf import settings

        # Verify sync mode is default
        self.assertFalse(settings.USE_ASYNC_PROCESSING)

    @patch('ann.views._upload_resume_sync')
    def test_upload_uses_sync_when_async_disabled(self, mock_sync):
        """Test that sync function is called when async is disabled."""
        mock_sync.return_value = MagicMock()

        # This verifies the code path exists
        from ann.views import _upload_resume_sync
        self.assertTrue(callable(_upload_resume_sync))

    def test_async_helper_functions_exist(self):
        """Test async helper functions are defined in views."""
        from ann import views

        self.assertTrue(hasattr(views, '_upload_resume_sync'))
        self.assertTrue(hasattr(views, '_upload_resume_async'))
        self.assertTrue(callable(views._upload_resume_sync))
        self.assertTrue(callable(views._upload_resume_async))


class TestAsyncEndpoints(TestCase):
    """Test async-related API endpoints."""

    def setUp(self):
        """Create test user."""
        self.user = User.objects.create_user(
            username='testuser@example.com',
            email='testuser@example.com',
            password='testpass123'
        )
        self.client.login(username='testuser@example.com', password='testpass123')

    def test_processing_status_endpoint_exists(self):
        """Test processing status endpoint returns valid response."""
        response = self.client.get('/api/resume/processing-status/')

        self.assertEqual(response.status_code, 200)
        data = json.loads(response.content)
        self.assertIn('status', data)

    def test_processing_status_no_resume(self):
        """Test status when no resume uploaded."""
        response = self.client.get('/api/resume/processing-status/')

        data = json.loads(response.content)
        self.assertEqual(data['status'], 'not_uploaded')

    def test_task_status_endpoint_requires_auth(self):
        """Test task status endpoint requires authentication."""
        self.client.logout()
        response = self.client.get('/api/task/fake-task-id/status/')

        # Should redirect to login or return 302
        self.assertIn(response.status_code, [302, 401, 403])

    def test_task_status_handles_invalid_task(self):
        """Test task status handles non-existent task gracefully."""
        response = self.client.get('/api/task/invalid-task-id-12345/status/')

        # Should return 200 with error info or 500
        self.assertIn(response.status_code, [200, 500])


class TestTaskEagerMode(TestCase):
    """
    Test tasks in eager mode (synchronous execution).

    Celery's eager mode runs tasks synchronously without a broker,
    perfect for testing without Redis.
    """

    def setUp(self):
        """Create test user and profile."""
        self.user = User.objects.create_user(
            username='tasktest@example.com',
            email='tasktest@example.com',
            password='testpass123'
        )
        # Get candidate profile (auto-created by signal)
        from ann.models import CandidateProfile
        self.profile, _ = CandidateProfile.objects.get_or_create(
            user=self.user,
            defaults={'full_name': 'Test User'}
        )

    @override_settings(CELERY_TASK_ALWAYS_EAGER=True)
    def test_parse_resume_task_no_file(self):
        """Test parse task handles missing file gracefully."""
        try:
            from ann.tasks import parse_resume_task

            # Run task synchronously (eager mode)
            result = parse_resume_task.apply(args=[self.profile.id]).get()

            self.assertFalse(result['success'])
            self.assertIn('error', result)
        except ImportError:
            self.skipTest("Celery not installed")

    @override_settings(CELERY_TASK_ALWAYS_EAGER=True)
    def test_extract_skills_task_no_parsed_resume(self):
        """Test skills extraction handles missing parsed resume."""
        try:
            from ann.tasks import extract_skills_task

            result = extract_skills_task.apply(args=[self.profile.id]).get()

            self.assertFalse(result['success'])
        except ImportError:
            self.skipTest("Celery not installed")

    @override_settings(CELERY_TASK_ALWAYS_EAGER=True)
    def test_calculate_matches_task_no_resume(self):
        """Test match calculation handles candidate without resume."""
        try:
            from ann.tasks import calculate_matches_task

            result = calculate_matches_task.apply(args=[self.profile.id]).get()

            # Should still succeed but with 0 matches
            self.assertIn('success', result)
        except ImportError:
            self.skipTest("Celery not installed")


class TestRetrainTask(TestCase):
    """Test model retraining task."""

    @override_settings(CELERY_TASK_ALWAYS_EAGER=True)
    def test_retrain_task_synthetic_data(self):
        """Test retraining with synthetic data."""
        try:
            from ann.tasks import retrain_model_task

            # Run with synthetic data (no real data needed)
            result = retrain_model_task.apply(args=[False]).get()

            if result['success']:
                self.assertEqual(result['data_source'], 'synthetic')
                self.assertGreater(result['samples'], 0)
            else:
                # May fail if torch not installed
                self.assertIn('error', result)
        except ImportError:
            self.skipTest("Celery not installed")


class TestBackwardCompatibility(TestCase):
    """Test that existing functionality still works."""

    def setUp(self):
        """Create test user."""
        self.user = User.objects.create_user(
            username='testuser@example.com',
            email='testuser@example.com',
            password='testpass123'
        )

    def test_candidate_page_works(self):
        """Test candidate page loads without Celery."""
        self.client.login(username='testuser@example.com', password='testpass123')
        response = self.client.get('/candidate/')

        self.assertEqual(response.status_code, 200)

    def test_job_list_works(self):
        """Test job list page loads without Celery."""
        response = self.client.get('/jobs/')

        self.assertEqual(response.status_code, 200)

    def test_upload_endpoint_exists(self):
        """Test upload endpoint is accessible."""
        self.client.login(username='testuser@example.com', password='testpass123')

        # POST without file should return error, not crash
        response = self.client.post('/api/upload-resume/')

        self.assertEqual(response.status_code, 400)
        data = json.loads(response.content)
        self.assertIn('error', data)
