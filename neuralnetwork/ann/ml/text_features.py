"""
Text Feature Extractor

Computes all 5 ANN input features directly from raw resume + job description text,
without needing Django ORM objects (CandidateProfile, Job).

Used by the external data loading pipeline to compute features from HuggingFace datasets.
"""

import re
import logging
from typing import Optional, Tuple, List

import numpy as np

logger = logging.getLogger(__name__)


DEGREE_LEVELS = {
    'phd': 5, 'doctorate': 5, 'ph.d': 5, 'ph d': 5,
    'master': 4, 'masters': 4, 'mba': 4, 'm.s': 4, 'msc': 4, 'm.tech': 4,
    'bachelor': 3, 'bachelors': 3, 'b.s': 3, 'b.tech': 3, 'undergraduate': 3,
    'degree': 3, 'b.e': 3, 'b.sc': 3,
    'diploma': 2, 'associate': 2,
    'high school': 1, 'secondary': 1, 'hs': 1,
}


def _extract_years(text: str) -> Optional[int]:
    """Extract max years-of-experience from text."""
    text = text.lower()
    patterns = [
        r'(\d+)\+?\s*years?\s+of\s+experience',
        r'(\d+)\+?\s*years?\s+experience',
        r'(\d+)\+?\s*yrs?\s+of\s+experience',
        r'(\d+)\+?\s*yrs?\s+experience',
        r'(\d+)\+?\s*years?',
        r'(\d+)\+?\s*yrs?',
    ]
    all_values = []
    for p in patterns:
        matches = re.findall(p, text)
        all_values.extend(int(m) for m in matches if 0 < int(m) <= 50)
    return max(all_values) if all_values else None


def _get_degree_level(text: str) -> int:
    """Return highest degree level found in text (1–5)."""
    text = text.lower()
    highest = 0
    for keyword, level in DEGREE_LEVELS.items():
        if keyword in text and level > highest:
            highest = level
    return highest


class TextFeatureExtractor:
    """
    Compute all 5 match-prediction features from raw (resume_text, job_text) strings.

    Features (all returned in 0–100 range):
        1. semantic_similarity  — embedding cosine similarity
        2. skill_match          — overlap of extracted skills
        3. experience_match     — years-of-exp vs requirement
        4. education_match      — degree level comparison
        5. profile_completeness — richness of resume text
    """

    def __init__(self):
        self._embedding_service = None
        self._skill_extractor = None

    # ------------------------------------------------------------------
    # Lazy singletons — avoid loading heavy models at import time
    # ------------------------------------------------------------------

    def _get_embedding_service(self):
        if self._embedding_service is None:
            from ann.services.embedding_service import EmbeddingService
            self._embedding_service = EmbeddingService()
        return self._embedding_service

    def _get_skill_extractor(self):
        if self._skill_extractor is None:
            from ann.services.skill_extractor import DynamicSkillExtractor
            self._skill_extractor = DynamicSkillExtractor()
        return self._skill_extractor

    # ------------------------------------------------------------------
    # Individual feature methods
    # ------------------------------------------------------------------

    def semantic_similarity(self, resume_text: str, job_text: str) -> float:
        """Cosine similarity between resume and job embeddings → 0–100."""
        try:
            emb_svc = self._get_embedding_service()
            resume_emb = emb_svc.generate_embedding(resume_text)
            job_emb = emb_svc.generate_embedding(job_text)

            # Cosine similarity
            dot = np.dot(resume_emb, job_emb)
            norm = np.linalg.norm(resume_emb) * np.linalg.norm(job_emb)
            if norm == 0:
                return 50.0
            sim = float(dot / norm)
            # Clamp to [0, 1] then scale
            return float(np.clip(sim, 0.0, 1.0) * 100)
        except Exception as e:
            logger.warning(f"semantic_similarity failed: {e}")
            return 50.0

    def skill_match(self, resume_text: str, job_text: str) -> float:
        """Skill overlap score → 0–100."""
        try:
            extractor = self._get_skill_extractor()

            resume_raw = extractor.extract_skills(resume_text)
            job_raw = extractor.extract_skills(job_text)

            # extract_skills returns list of dicts or list of strings
            def _to_set(raw) -> set:
                result = set()
                for item in raw:
                    if isinstance(item, dict):
                        result.add(item.get('normalized', item.get('skill', '')).lower())
                    else:
                        result.add(str(item).lower())
                result.discard('')
                return result

            resume_skills = _to_set(resume_raw)
            job_skills = _to_set(job_raw)

            if not job_skills:
                return 50.0

            overlap = len(resume_skills & job_skills) / len(job_skills)
            return float(min(overlap * 100 * 1.2, 100.0))
        except Exception as e:
            logger.warning(f"skill_match failed: {e}")
            return 50.0

    def experience_match(self, resume_text: str, job_text: str) -> float:
        """Experience score based on years-of-exp extraction → 0–100."""
        try:
            candidate_exp = _extract_years(resume_text) or 2
            required_min = _extract_years(job_text) or 0
            required_max = required_min + 3  # assume 3-year window

            if required_min <= candidate_exp <= required_max:
                return 100.0
            elif candidate_exp < required_min:
                return float(max(0.0, 100.0 - (required_min - candidate_exp) * 25))
            else:
                return float(max(40.0, 100.0 - (candidate_exp - required_max) * 10))
        except Exception as e:
            logger.warning(f"experience_match failed: {e}")
            return 50.0

    def education_match(self, resume_text: str, job_text: str) -> float:
        """Education level comparison → 0–100."""
        try:
            candidate_level = _get_degree_level(resume_text)
            required_level = _get_degree_level(job_text)

            if required_level == 0:
                # No requirement specified — full score if candidate has any degree
                return 85.0 if candidate_level > 0 else 60.0

            if candidate_level == 0:
                # No education found in resume
                return 30.0

            diff = candidate_level - required_level
            if diff >= 0:
                # Meets or exceeds requirement
                return min(100.0, 80.0 + diff * 10.0)
            else:
                # Below requirement
                return max(0.0, 70.0 + diff * 20.0)
        except Exception as e:
            logger.warning(f"education_match failed: {e}")
            return 50.0

    def profile_completeness(self, resume_text: str) -> float:
        """Estimate profile completeness from resume text richness → 0–100."""
        try:
            score = 0.0
            text_lower = resume_text.lower()

            # Has contact info (email / phone)
            if re.search(r'[\w.+-]+@[\w-]+\.\w+', resume_text):
                score += 20.0
            elif re.search(r'\b\d{10}\b|\(\d{3}\)\s*\d{3}[-.\s]\d{4}', resume_text):
                score += 20.0

            # Has skills section keyword
            if any(kw in text_lower for kw in ['skills', 'technologies', 'tools', 'tech stack']):
                score += 20.0

            # Has experience section keyword
            if any(kw in text_lower for kw in ['experience', 'employment', 'work history', 'career']):
                score += 25.0

            # Has education section keyword
            if any(kw in text_lower for kw in ['education', 'university', 'college', 'school', 'degree']):
                score += 20.0

            # Text length > 300 words
            word_count = len(resume_text.split())
            if word_count >= 300:
                score += 15.0
            elif word_count >= 100:
                score += 7.0

            return min(score, 100.0)
        except Exception as e:
            logger.warning(f"profile_completeness failed: {e}")
            return 50.0

    # ------------------------------------------------------------------
    # Main entry point
    # ------------------------------------------------------------------

    def extract(self, resume_text: str, job_text: str) -> Tuple[float, float, float, float, float]:
        """
        Compute all 5 features.

        Returns:
            (semantic_similarity, skill_match, experience_match,
             education_match, profile_completeness)  — all in 0–100 range
        """
        sem = self.semantic_similarity(resume_text, job_text)
        skl = self.skill_match(resume_text, job_text)
        exp = self.experience_match(resume_text, job_text)
        edu = self.education_match(resume_text, job_text)
        pro = self.profile_completeness(resume_text)
        return sem, skl, exp, edu, pro

    def extract_batch(
        self,
        pairs: List[Tuple[str, str]],
        batch_size: int = 50,
    ) -> List[Tuple[float, float, float, float, float]]:
        """
        Extract features for a list of (resume_text, job_text) pairs.

        Prints progress every batch to avoid timeout confusion.
        """
        results = []
        total = len(pairs)

        for start in range(0, total, batch_size):
            batch = pairs[start: start + batch_size]
            for resume_text, job_text in batch:
                results.append(self.extract(resume_text, job_text))

            done = min(start + batch_size, total)
            print(f"  Feature extraction: {done}/{total} rows processed...", flush=True)

        return results
