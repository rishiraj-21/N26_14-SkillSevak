"""
Matching Engine Service

Core matching logic between candidates and jobs.
Combines semantic similarity, skill overlap, experience, and education.

Phase 4 implementation per PROJECT_PLAN.md.

Per PRD.md Section 8.3 (Scoring Formula):
MVP: Match % = (0.30*Semantic) + (0.35*Skills) + (0.20*Exp) + (0.10*Edu) + (0.05*Profile)
V1:  Match % = ANN([semantic, skills, experience, education, profile])
"""

import logging
from typing import Dict, List, Tuple

logger = logging.getLogger(__name__)


class MatchingEngine:
    """
    Calculate match scores between candidates and jobs.

    Uses multiple factors:
    - Semantic similarity (embeddings)
    - Skill overlap (fuzzy matching)
    - Experience match
    - Education relevance
    - Profile completeness

    Full implementation in Phase 4.
    """

    def __init__(self):
        from django.conf import settings
        self.weights = getattr(settings, 'MATCH_WEIGHTS', {
            'semantic': 0.30,
            'skills': 0.35,
            'experience': 0.20,
            'education': 0.10,
            'profile': 0.05,
        })

    def calculate_match(self, candidate, job) -> Dict:
        """
        Calculate comprehensive match score.

        Args:
            candidate: CandidateProfile instance
            job: Job instance

        Returns:
            Dict with overall_score, breakdown, matched_skills, missing_skills, suggestions

        Full implementation in Phase 4.
        """
        # Stub - returns placeholder data
        logger.info(f"Match calculation called: {candidate} <-> {job}")

        return {
            'overall_score': 0.0,
            'breakdown': {
                'semantic_similarity': 0.0,
                'skill_match': 0.0,
                'experience_match': 0.0,
                'education_match': 0.0,
                'profile_completeness': 0.0,
            },
            'matched_skills': [],
            'missing_skills': [],
            'suggestions': ['Complete Phase 4 to enable matching'],
        }

    def calculate_all_matches_for_candidate(self, candidate) -> List[Dict]:
        """
        Calculate matches for all active jobs.

        Full implementation in Phase 4.
        """
        return []

    def calculate_all_matches_for_job(self, job) -> List[Dict]:
        """
        Calculate matches for all candidates.

        Full implementation in Phase 4.
        """
        return []
