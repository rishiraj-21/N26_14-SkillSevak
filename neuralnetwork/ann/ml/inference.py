"""
Model Inference Service

Service for making match predictions using trained model.
Falls back to weighted average if no trained model available.

Phase 5 implementation per PROJECT_PLAN.md.
"""

import logging
from pathlib import Path

import numpy as np

logger = logging.getLogger(__name__)


class MatchPredictorService:
    """
    Service for making match predictions.

    Singleton pattern - loads model once.
    Falls back to weighted average if no trained model.

    Full implementation in Phase 5.
    """

    _instance = None
    _model = None
    _using_trained = False

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        if self._model is None:
            self._load_model()

    def _load_model(self):
        """Load trained weights if available."""
        from django.conf import settings

        weight_path = Path(getattr(
            settings,
            'ANN_MODEL_PATH',
            'ann/ml/weights/match_predictor.pth'
        ))

        if weight_path.exists():
            try:
                import torch
                from .model import MatchPredictor

                self._model = MatchPredictor()
                self._model.load_state_dict(torch.load(weight_path, weights_only=True))
                self._model.eval()
                self._using_trained = True
                logger.info(f"Loaded trained model from {weight_path}")
            except Exception as e:
                logger.warning(f"Failed to load model: {e}. Using weighted average.")
                self._using_trained = False
        else:
            logger.info("No trained model found. Using weighted average fallback.")
            self._using_trained = False

    def predict(self, features: dict) -> float:
        """
        Predict match score.

        Args:
            features: {
                'semantic_similarity': 0-100,
                'skill_match': 0-100,
                'experience_match': 0-100,
                'education_match': 0-100,
                'profile_completeness': 0-100
            }

        Returns:
            Match score 0-100
        """
        # Normalize to 0-1 scale
        feature_array = np.array([
            features.get('semantic_similarity', 50) / 100,
            features.get('skill_match', 50) / 100,
            features.get('experience_match', 50) / 100,
            features.get('education_match', 50) / 100,
            features.get('profile_completeness', 50) / 100,
        ], dtype=np.float32)

        if self._using_trained and self._model is not None:
            return self._model.predict(feature_array)
        else:
            return self._weighted_average(feature_array)

    def _weighted_average(self, features: np.ndarray) -> float:
        """Fallback calculation using fixed weights per PRD.md."""
        # Weights: semantic=0.25, skills=0.35, experience=0.20, education=0.10, profile=0.10
        weights = np.array([0.25, 0.35, 0.20, 0.10, 0.10])
        return float(np.dot(features, weights) * 100)

    @property
    def is_using_trained_model(self) -> bool:
        """Check if using trained ANN or fallback."""
        return self._using_trained
