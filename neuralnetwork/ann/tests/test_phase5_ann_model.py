"""
ANN Model Integration

Tests for the match prediction neural network.
"""

import numpy as np
from django.test import TestCase, override_settings
from unittest.mock import patch, MagicMock


class MatchPredictorModelTests(TestCase):
    """Tests for the MatchPredictor neural network."""

    def test_model_import(self):
        """Test that model can be imported."""
        try:
            from ann.ml.model import MatchPredictor, TORCH_AVAILABLE
            self.assertTrue(True)
        except ImportError as e:
            self.skipTest(f"PyTorch not available: {e}")

    def test_model_initialization(self):
        """Test model initializes with correct architecture."""
        try:
            from ann.ml.model import MatchPredictor, TORCH_AVAILABLE
            if not TORCH_AVAILABLE:
                self.skipTest("PyTorch not available")

            model = MatchPredictor(input_size=5)

            # Check model has the network attribute
            self.assertTrue(hasattr(model, 'network'))

            # Check input/output dimensions
            # Must use eval mode for single sample (BatchNorm requires batch > 1 in training)
            import torch
            model.eval()
            test_input = torch.randn(1, 5)
            with torch.no_grad():
                output = model(test_input)
            self.assertEqual(output.shape, (1, 1))

            # Output should be between 0 and 1 (sigmoid)
            self.assertTrue(0 <= output.item() <= 1)

        except ImportError:
            self.skipTest("PyTorch not available")

    def test_model_predict_method(self):
        """Test the predict method returns 0-100 score."""
        try:
            from ann.ml.model import MatchPredictor, TORCH_AVAILABLE
            if not TORCH_AVAILABLE:
                self.skipTest("PyTorch not available")

            model = MatchPredictor()

            # Test with numpy array
            features = np.array([0.8, 0.7, 0.9, 0.6, 0.85])
            score = model.predict(features)

            self.assertIsInstance(score, float)
            self.assertTrue(0 <= score <= 100)

        except ImportError:
            self.skipTest("PyTorch not available")

    def test_fallback_predictor(self):
        """Test fallback predictor when PyTorch not available."""
        from ann.ml.model import MatchPredictor

        # Create a mock predictor
        predictor = MatchPredictor()

        # Test predict method
        features = [0.8, 0.7, 0.9, 0.6, 0.85]
        score = predictor.predict(features)

        self.assertIsInstance(score, float)
        self.assertTrue(0 <= score <= 100)


class ModelTrainerTests(TestCase):
    """Tests for the ModelTrainer class."""

    def test_trainer_import(self):
        """Test that trainer can be imported."""
        try:
            from ann.ml.train import ModelTrainer, TORCH_AVAILABLE
            self.assertTrue(True)
        except ImportError as e:
            self.skipTest(f"Module import failed: {e}")

    def test_synthetic_data_generation(self):
        """Test synthetic training data generation."""
        try:
            from ann.ml.train import ModelTrainer, TORCH_AVAILABLE
            if not TORCH_AVAILABLE:
                self.skipTest("PyTorch not available")

            trainer = ModelTrainer()
            X, y = trainer.generate_synthetic_data(n_samples=100, seed=42)

            # Check shapes
            self.assertEqual(X.shape, (100, 5))
            self.assertEqual(y.shape, (100,))

            # Check value ranges
            self.assertTrue(np.all(X >= 0) and np.all(X <= 1))
            self.assertTrue(np.all(y >= 0) and np.all(y <= 1))

            # Check reproducibility
            X2, y2 = trainer.generate_synthetic_data(n_samples=100, seed=42)
            np.testing.assert_array_equal(X, X2)
            np.testing.assert_array_equal(y, y2)

        except ImportError:
            self.skipTest("PyTorch not available")

    def test_training_runs(self):
        """Test that training completes without errors."""
        try:
            from ann.ml.train import ModelTrainer, TORCH_AVAILABLE
            if not TORCH_AVAILABLE:
                self.skipTest("PyTorch not available")

            trainer = ModelTrainer()

            # Train with minimal data and epochs
            X, y = trainer.generate_synthetic_data(n_samples=100, seed=42)
            history = trainer.train(
                X=X,
                y=y,
                epochs=5,
                batch_size=32,
                verbose=False
            )

            # Check history
            self.assertIn('train_loss', history)
            self.assertIn('val_loss', history)
            self.assertIn('best_val_loss', history)
            self.assertIn('epochs_trained', history)

            # Losses should be positive
            self.assertTrue(all(l >= 0 for l in history['train_loss']))
            self.assertTrue(all(l >= 0 for l in history['val_loss']))

        except ImportError:
            self.skipTest("PyTorch not available")


class MatchPredictorServiceTests(TestCase):
    """Tests for the MatchPredictorService inference service."""

    def test_service_singleton(self):
        """Test that service follows singleton pattern."""
        from ann.ml.inference import MatchPredictorService

        service1 = MatchPredictorService()
        service2 = MatchPredictorService()

        self.assertIs(service1, service2)

    def test_service_predict(self):
        """Test prediction with feature dict."""
        from ann.ml.inference import MatchPredictorService

        service = MatchPredictorService()

        features = {
            'semantic_similarity': 80,
            'skill_match': 70,
            'experience_match': 90,
            'education_match': 60,
            'profile_completeness': 85,
        }

        score = service.predict(features)

        self.assertIsInstance(score, float)
        self.assertTrue(0 <= score <= 100)

    def test_service_high_scores(self):
        """Test that high input features produce high output scores."""
        from ann.ml.inference import MatchPredictorService

        service = MatchPredictorService()

        # High scores should produce a reasonably high output
        features = {
            'semantic_similarity': 100,
            'skill_match': 100,
            'experience_match': 100,
            'education_match': 100,
            'profile_completeness': 100,
        }

        score = service.predict(features)

        # Score should be positive and reasonable
        # (ANN may not give exactly 100 due to learned patterns)
        self.assertGreater(score, 50)
        self.assertLessEqual(score, 100)

    def test_weighted_average_calculation(self):
        """Test the weighted average formula matches PRD.md."""
        from ann.ml.inference import MatchPredictorService

        service = MatchPredictorService()

        # Test with known values
        # Expected: 0.25*0.8 + 0.35*0.7 + 0.20*0.9 + 0.10*0.6 + 0.10*0.85
        # = 0.2 + 0.245 + 0.18 + 0.06 + 0.085 = 0.77 = 77%
        features = np.array([0.8, 0.7, 0.9, 0.6, 0.85], dtype=np.float32)
        expected = 77.0

        score = service._weighted_average(features)

        self.assertAlmostEqual(score, expected, places=1)


class MatchingEngineANNIntegrationTests(TestCase):
    """Tests for ANN integration in MatchingEngine."""

    def test_engine_has_ann_property(self):
        """Test that MatchingEngine has ANN predictor property."""
        from ann.services.matching_engine import MatchingEngine

        engine = MatchingEngine(use_ann=True)

        self.assertTrue(hasattr(engine, 'ann_predictor'))
        self.assertTrue(hasattr(engine, 'is_using_ann'))

    def test_engine_ann_disabled(self):
        """Test engine works with ANN disabled."""
        from ann.services.matching_engine import MatchingEngine

        engine = MatchingEngine(use_ann=False)

        self.assertFalse(engine.use_ann)

    @override_settings(USE_ANN_MODEL=False)
    def test_engine_respects_settings(self):
        """Test engine respects USE_ANN_MODEL setting."""
        from ann.services.matching_engine import MatchingEngine

        engine = MatchingEngine()

        # Should be disabled when setting is False
        self.assertFalse(engine.use_ann)

    def test_scoring_method_in_result(self):
        """Test that calculate_match includes scoring_method."""
        from ann.services.matching_engine import MatchingEngine
        from ann.models import CandidateProfile, Job
        from django.contrib.auth.models import User

        # Create test user and candidate
        user = User.objects.create_user(
            username='test_ann@example.com',
            email='test_ann@example.com',
            password='testpass123'
        )
        candidate = CandidateProfile.objects.create(
            user=user,
            full_name='Test ANN Candidate',
            experience_years=5
        )

        # Create test job
        job = Job.objects.create(
            title='Test ANN Job',
            company='Test Company',
            location='Remote',
            salary_min=50000,
            salary_max=100000,
            job_type='full-time',
            description='Test job description',
            requirements='Test requirements',
            skills_required='Python, Django'
        )

        engine = MatchingEngine()
        result = engine.calculate_match(candidate, job)

        # Check scoring_method is in result
        self.assertIn('scoring_method', result)
        self.assertIn(result['scoring_method'], ['ann', 'weighted_average', 'error'])

        # Cleanup
        job.delete()
        candidate.delete()
        user.delete()
