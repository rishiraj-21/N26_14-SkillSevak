"""
Dynamic Skill Extractor Service

CRITICAL: NO HARDCODED SKILL DICTIONARY!
Extracts skills from text using NLP techniques.
Works for ANY industry - tech, law, healthcare, marketing, etc.

Phase 3 implementation per PROJECT_PLAN.md.

Dependencies:
- spacy: NLP processing
"""

import logging
from typing import List, Dict

logger = logging.getLogger(__name__)


class DynamicSkillExtractor:
    """
    Extract skills from text WITHOUT hardcoded dictionary.

    Per PRD.md Section 8.1:
    - Uses NLP (spaCy) for extraction
    - Works for any industry
    - Self-improving with data

    Full implementation in Phase 3.
    """

    def __init__(self):
        self._nlp = None

    @property
    def nlp(self):
        """Lazy load spaCy model."""
        if self._nlp is None:
            try:
                import spacy
                self._nlp = spacy.load("en_core_web_sm")
            except OSError:
                logger.error("spaCy model not found. Run: python -m spacy download en_core_web_sm")
                raise
        return self._nlp

    def extract_skills(self, text: str, section: str = 'general') -> List[Dict]:
        """
        Extract skills from text using NLP.

        Args:
            text: Text to extract skills from
            section: Source section (skills, experience, etc.)

        Returns:
            List of skill dicts: [{skill, normalized, confidence, source, context}]

        Full implementation in Phase 3.
        """
        # Stub - full implementation in Phase 3
        logger.info(f"Skill extraction called for section: {section}")
        return []

    def estimate_proficiency(self, skill: str, full_text: str) -> int:
        """
        Estimate proficiency level (1-5) from context.

        Full implementation in Phase 3.
        """
        return 3  # Default to intermediate
