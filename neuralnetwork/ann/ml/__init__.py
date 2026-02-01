"""
SkillSevak ML Module

Neural network model for learning optimal match weights.

Per PRD.md:
- Input: 5 features (semantic, skill, experience, education, profile)
- Hidden: 64 → 32 → 16 neurons
- Output: Match probability (0-100%)

Phase 5 implementation per PROJECT_PLAN.md.
"""

from .model import MatchPredictor
from .inference import MatchPredictorService

__all__ = [
    'MatchPredictor',
    'MatchPredictorService',
]
