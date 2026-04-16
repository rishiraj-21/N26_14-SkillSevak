"""
Matching Engine Service

Core matching logic between candidates and jobs.
Combines semantic similarity, skill overlap, experience, and education.

Phase 4 & 5 implementation 

Per PRD.md Section 8.3 (Scoring Formula):
MVP: Match % = (0.25*Semantic) + (0.35*Skills) + (0.20*Exp) + (0.10*Edu) + (0.10*Profile)
     Skills  = (0.70*Technical) + (0.20*Domain) + (0.10*Soft)
V1:  Match % = ANN([semantic, skills, experience, education, profile])

Phase 5 Addition: ANN model integration for learned weights.
"""

import logging
from typing import Dict, List, Tuple, Optional
from difflib import SequenceMatcher
import numpy as np

logger = logging.getLogger(__name__)


class MatchingEngine:
    """
    Calculate match scores between candidates and jobs.

    Uses multiple factors:
    - Semantic similarity (embeddings) - 25%
    - Skill overlap (Technical 70%, Domain 20%, Soft 10%) - 35%
    - Experience match - 20%
    - Education relevance - 10%
    - Profile completeness - 10%

    Phase 5: Supports ANN-based scoring when trained model is available.
    Falls back to weighted average (MVP formula) if no model exists.

    Works for ANY industry - no hardcoded assumptions.
    """

    def __init__(self, use_ann: bool = True):
        """
        Initialize the matching engine.

        Args:
            use_ann: If True, use trained ANN model when available.
                     Falls back to weighted average if model not found.
        """
        from django.conf import settings

        # Main scoring weights (used as fallback if ANN not available)
        self.weights = getattr(settings, 'MATCH_WEIGHTS', {
            'semantic': 0.25,
            'skills': 0.35,
            'experience': 0.20,
            'education': 0.10,
            'profile': 0.10,
        })

        # Skill category weights
        self.skills_weights = getattr(settings, 'SKILLS_WEIGHTS', {
            'technical': 0.70,
            'domain': 0.20,
            'soft': 0.10,
        })

        # ANN configuration
        self.use_ann = use_ann and getattr(settings, 'USE_ANN_MODEL', True)

        # Lazy-loaded services
        self._embedding_service = None
        self._skill_extractor = None
        self._ann_predictor = None

    @property
    def ann_predictor(self):
        """Lazy load ANN predictor service."""
        if self._ann_predictor is None and self.use_ann:
            try:
                from ann.ml.inference import MatchPredictorService
                self._ann_predictor = MatchPredictorService()
                if self._ann_predictor.is_using_trained_model:
                    logger.info("Using trained ANN model for predictions")
                else:
                    logger.info("ANN model not trained, using weighted average")
            except Exception as e:
                logger.warning(f"Failed to load ANN predictor: {e}")
                self._ann_predictor = None
        return self._ann_predictor

    @property
    def is_using_ann(self) -> bool:
        """Check if engine is using trained ANN model."""
        predictor = self.ann_predictor
        return predictor is not None and predictor.is_using_trained_model

    @property
    def embedding_service(self):
        """Lazy load embedding service."""
        if self._embedding_service is None:
            from ann.services.embedding_service import EmbeddingService
            self._embedding_service = EmbeddingService()
        return self._embedding_service

    @property
    def skill_extractor(self):
        """Lazy load skill extractor."""
        if self._skill_extractor is None:
            from ann.services.skill_extractor import DynamicSkillExtractor
            self._skill_extractor = DynamicSkillExtractor()
        return self._skill_extractor

    def calculate_match(self, candidate, job) -> Dict:
        """
        Calculate comprehensive match score between candidate and job.

        Args:
            candidate: CandidateProfile instance
            job: Job instance

        Returns:
            Dict with:
            - overall_score: 0-100 match percentage
            - breakdown: Individual component scores
            - matched_skills: List of matched skills
            - missing_skills: List of missing skills
            - suggestions: Actionable improvement tips
        """
        try:
            # Calculate individual components
            semantic_score = self._calculate_semantic_similarity(candidate, job)
            skill_score, matched_skills, missing_skills = self._calculate_skill_match(candidate, job)
            experience_score = self._calculate_experience_match(candidate, job)
            education_score = self._calculate_education_match(candidate, job)
            profile_score = self._calculate_profile_completeness(candidate)

            # Calculate overall score
            # Phase 5: Use ANN if available, otherwise use weighted average
            if self.is_using_ann:
                # ANN prediction (learned weights)
                overall_score = self.ann_predictor.predict({
                    'semantic_similarity': semantic_score,
                    'skill_match': skill_score,
                    'experience_match': experience_score,
                    'education_match': education_score,
                    'profile_completeness': profile_score,
                })
                scoring_method = 'ann'
            else:
                # Weighted average (MVP formula)
                overall_score = (
                    self.weights['semantic'] * semantic_score +
                    self.weights['skills'] * skill_score +
                    self.weights['experience'] * experience_score +
                    self.weights['education'] * education_score +
                    self.weights['profile'] * profile_score
                )
                scoring_method = 'weighted_average'

            # Ensure score is in valid range
            overall_score = max(0, min(100, overall_score))

            # Generate suggestions
            suggestions = self._generate_suggestions(
                missing_skills,
                skill_score,
                experience_score,
                overall_score
            )

            result = {
                'overall_score': round(overall_score, 1),
                'scoring_method': scoring_method,  # 'ann' or 'weighted_average'
                'breakdown': {
                    'semantic_similarity': round(semantic_score, 1),
                    'skill_match': round(skill_score, 1),
                    'experience_match': round(experience_score, 1),
                    'education_match': round(education_score, 1),
                    'profile_completeness': round(profile_score, 1),
                },
                'matched_skills': matched_skills,
                'missing_skills': missing_skills,
                'suggestions': suggestions,
            }

            logger.info(
                f"Match calculated ({scoring_method}): "
                f"{candidate.user.username} <-> {job.title} = {overall_score:.1f}%"
            )

            return result

        except Exception as e:
            logger.error(f"Match calculation error: {e}")
            return {
                'overall_score': 0.0,
                'scoring_method': 'error',
                'breakdown': {
                    'semantic_similarity': 0.0,
                    'skill_match': 0.0,
                    'experience_match': 0.0,
                    'education_match': 0.0,
                    'profile_completeness': 0.0,
                },
                'matched_skills': [],
                'missing_skills': [],
                'suggestions': ['Unable to calculate match. Please try again.'],
                'error': str(e),
            }

    def _calculate_semantic_similarity(self, candidate, job) -> float:
        """
        Calculate semantic similarity between resume and job using embeddings.

        Uses cosine similarity between stored document embeddings.
        Falls back to generating embeddings if not stored.
        Returns score 0-100.
        """
        try:
            from ann.models import ParsedResume
            from sklearn.metrics.pairwise import cosine_similarity

            # Get candidate resume embedding (prefer stored, fallback to generate)
            parsed_resume = ParsedResume.objects.filter(candidate=candidate).first()
            if not parsed_resume:
                logger.warning(f"No parsed resume for candidate {candidate.id}")
                return 10.0  # Very low - no resume

            # Use stored embedding if available
            if parsed_resume.embedding:
                resume_embedding = self.embedding_service.deserialize_embedding(
                    parsed_resume.embedding
                )
            elif parsed_resume.cleaned_text:
                # Generate embedding if not stored
                resume_embedding = self.embedding_service.generate_embedding(
                    parsed_resume.cleaned_text
                )
            else:
                logger.warning(f"No resume text for candidate {candidate.id}")
                return 10.0  # Very low - no content

            # Get job embedding (prefer stored, fallback to generate and cache)
            if job.embedding:
                job_embedding = self.embedding_service.deserialize_embedding(job.embedding)
            else:
                # Generate embedding if not stored
                job_text = self._build_job_text(job)
                if not job_text.strip():
                    return 50.0
                job_embedding = self.embedding_service.generate_embedding(job_text)
                # Cache it for future calls
                try:
                    job.embedding = self.embedding_service.serialize_embedding(job_embedding)
                    job.save(update_fields=['embedding'])
                except Exception:
                    pass

            # Calculate cosine similarity
            similarity = cosine_similarity(
                resume_embedding.reshape(1, -1),
                job_embedding.reshape(1, -1)
            )[0][0]

            # Convert to 0-100 scale
            # Cosine similarity ranges from -1 to 1, but for text it's usually 0-1
            score = float(similarity) * 100

            # Clamp to valid range
            return max(0, min(100, score))

        except ImportError:
            logger.warning("sklearn not available, using fallback similarity")
            return self._fallback_text_similarity(candidate, job)
        except Exception as e:
            logger.error(f"Semantic similarity error: {e}")
            return 50.0

    def _build_job_text(self, job) -> str:
        """Build comprehensive text from job for embedding."""
        parts = []

        if job.title:
            parts.append(job.title)
        if job.description:
            parts.append(job.description)
        if job.requirements:
            parts.append(job.requirements)
        if hasattr(job, 'skills_required') and job.skills_required:
            parts.append(str(job.skills_required))
        if hasattr(job, 'category') and job.category:
            parts.append(job.category)

        return ' '.join(parts)

    def _fallback_text_similarity(self, candidate, job) -> float:
        """Fallback similarity using simple word overlap."""
        try:
            from ann.models import ParsedResume

            parsed_resume = ParsedResume.objects.filter(candidate=candidate).first()
            if not parsed_resume:
                return 50.0

            resume_words = set(parsed_resume.cleaned_text.lower().split())
            job_text = self._build_job_text(job)
            job_words = set(job_text.lower().split())

            if not job_words:
                return 50.0

            # Jaccard similarity
            intersection = len(resume_words & job_words)
            union = len(resume_words | job_words)

            if union == 0:
                return 50.0

            similarity = intersection / union
            return similarity * 100

        except Exception:
            return 50.0

    def _calculate_skill_match(self, candidate, job) -> Tuple[float, List[Dict], List[Dict]]:
        """
        Calculate skill match score with category weighting.

        Uses:
        - Technical skills: 70% weight
        - Domain skills: 20% weight
        - Soft skills: 10% weight

        Returns: (score 0-100, matched_skills, missing_skills)
        """
        from ann.models import CandidateSkill, JobSkill

        # Get candidate skills
        candidate_skills = list(CandidateSkill.objects.filter(candidate=candidate))

        # Get job skills (from extracted skills or fallback to skills_required field)
        job_skills = list(JobSkill.objects.filter(job=job))

        # If no extracted job skills, try to extract from skills_required field
        if not job_skills and hasattr(job, 'skills_required') and job.skills_required:
            job_skills = self._parse_skills_required(job)

        if not job_skills:
            # No skills to match against - can't evaluate
            return 20.0, [], []

        if not candidate_skills:
            # Candidate has no skills extracted - very low score
            missing = [{'skill': js.skill_text, 'category': getattr(js, 'category', 'domain'),
                       'importance': getattr(js, 'importance', 'required')} for js in job_skills]
            return 0.0, [], missing

        # Build lookup for candidate skills
        candidate_lookup = {}
        for cs in candidate_skills:
            candidate_lookup[cs.normalized_text] = {
                'skill': cs.skill_text,
                'category': getattr(cs, 'category', 'domain'),
                'proficiency': cs.proficiency_level,
            }

        matched = []
        missing = []

        # Importance weights for scoring
        importance_weights = {
            'required': 3.0,
            'preferred': 2.0,
            'nice_to_have': 1.0,
        }

        total_weight = 0.0
        matched_weight = 0.0

        for js in job_skills:
            job_norm = js.normalized_text
            category = getattr(js, 'category', 'domain')
            importance = getattr(js, 'importance', 'required')

            # Calculate weight for this skill
            cat_weight = self.skills_weights.get(category, 0.20)
            imp_weight = importance_weights.get(importance, 2.0)
            skill_weight = cat_weight * imp_weight

            total_weight += skill_weight

            # Try to find match (fuzzy matching)
            found = False
            matched_skill_data = None

            for cand_norm, cand_data in candidate_lookup.items():
                similarity = SequenceMatcher(None, job_norm, cand_norm).ratio()
                if similarity >= 0.80:  # 80% similarity threshold
                    found = True
                    matched_skill_data = cand_data
                    break

            if found:
                matched_weight += skill_weight
                matched.append({
                    'job_skill': js.skill_text,
                    'candidate_skill': matched_skill_data['skill'],
                    'category': category,
                    'importance': importance,
                    'proficiency': matched_skill_data.get('proficiency', 3),
                })
            else:
                missing.append({
                    'skill': js.skill_text,
                    'category': category,
                    'importance': importance,
                })

        # Calculate score
        if total_weight > 0:
            score = (matched_weight / total_weight) * 100
        else:
            score = 50.0

        return score, matched, missing

    def _parse_skills_required(self, job) -> List:
        """Parse skills from the skills_required field as fallback."""
        skills_text = job.skills_required
        if not skills_text:
            return []

        # Words that are NOT skills - filter these out
        non_skills = {
            'intern', 'interns', 'internship', 'manager', 'director', 'engineer',
            'developer', 'analyst', 'designer', 'consultant', 'specialist',
            'senior', 'junior', 'lead', 'associate', 'assistant', 'coordinator',
            'experience', 'years', 'required', 'preferred', 'must', 'have',
            'knowledge', 'understanding', 'ability', 'skills', 'strong',
            'excellent', 'good', 'work', 'team', 'company', 'business',
            'candidate', 'applicant', 'degree', 'bachelor', 'master',
        }

        def is_valid_skill(s):
            """Check if string is a valid skill."""
            s_lower = s.lower().strip()
            if len(s_lower) < 2:
                return False
            if s_lower in non_skills:
                return False
            # Skip if it's just numbers
            if s_lower.replace('.', '').replace('-', '').isdigit():
                return False
            return True

        # Try to parse as JSON first
        try:
            import json
            skills_list = json.loads(skills_text)
            if isinstance(skills_list, list):
                return [
                    type('JobSkillFallback', (), {
                        'skill_text': s.strip(),
                        'normalized_text': s.lower().strip(),
                        'category': 'technical',  # Assume technical by default
                        'importance': 'required',
                    })() for s in skills_list if s and is_valid_skill(s)
                ]
        except (json.JSONDecodeError, TypeError):
            pass

        # Parse as comma-separated
        skills = [s.strip() for s in skills_text.split(',') if s.strip() and is_valid_skill(s)]
        return [
            type('JobSkillFallback', (), {
                'skill_text': s,
                'normalized_text': s.lower().strip(),
                'category': 'technical',  # Assume technical by default
                'importance': 'required',
            })() for s in skills
        ]

    def _calculate_experience_match(self, candidate, job) -> float:
        """
        Calculate experience match score.

        Compares candidate's years of experience with job requirements.
        Returns score 0-100.
        """
        # Get candidate experience
        candidate_exp = getattr(candidate, 'experience_years', None)
        if candidate_exp is None:
            candidate_exp = 0

        # Get job experience requirements
        job_min = getattr(job, 'experience_min', None)
        job_max = getattr(job, 'experience_max', None)

        # If no experience requirements specified, infer from job title
        if job_min is None or job_min == 0:
            if job_max is None or job_max >= 99:
                job_title = (getattr(job, 'title', '') or '').lower()
                # Senior/management roles — infer 5+ years expected
                if any(w in job_title for w in ['senior', 'lead', 'principal', 'head', 'director', 'manager', 'architect']):
                    if candidate_exp < 5:
                        gap = 5 - candidate_exp
                        return max(20.0, 100.0 - gap * 15)
                    return 100.0
                # Entry-level roles — 0-2 years is perfect
                elif any(w in job_title for w in ['intern', 'internship', 'junior', 'entry', 'graduate', 'trainee', 'fresher', 'associate']):
                    if candidate_exp <= 2:
                        return 100.0
                    elif candidate_exp <= 5:
                        return max(70.0, 100.0 - (candidate_exp - 2) * 10)
                    return 60.0
                # Mid-level — neutral
                return 50.0

        # Apply defaults for calculation
        job_min = job_min or 0
        job_max = job_max if (job_max and job_max < 99) else 15

        # Perfect match: within range
        if job_min <= candidate_exp <= job_max:
            return 100.0

        # Under-qualified - penalty per year short (minimum score of 5)
        if candidate_exp < job_min:
            gap = job_min - candidate_exp
            # 25% penalty per year short, but never zero
            penalty = gap * 25
            return max(5, 100 - penalty)

        # Over-qualified (mild penalty - being experienced is not a big negative)
        if candidate_exp > job_max:
            gap = candidate_exp - job_max
            # 3% penalty per year over
            penalty = gap * 3
            return max(40, 100 - penalty)

        return 50.0

    def _calculate_education_match(self, candidate, job) -> float:
        """
        Calculate education relevance score.

        For MVP, checks if education fields are filled and relevant.
        Returns score 0-100.
        """
        score = 0.0  # No base — must have data to score

        # Check if candidate has education info
        education_level = getattr(candidate, 'education_level', None)
        education_field = getattr(candidate, 'education_field', None)

        if education_level:
            score += 50.0  # Has degree info

        if education_field:
            score += 20.0

            # Check if education field relates to job
            job_text = self._build_job_text(job).lower()
            if education_field.lower() in job_text:
                score += 30.0  # Big bonus for relevant education

        return min(100, score)

    def _calculate_profile_completeness(self, candidate) -> float:
        """
        Calculate profile completeness score.

        Uses the profile_strength field if available.
        Returns score 0-100.
        """
        profile_strength = getattr(candidate, 'profile_strength', None)

        if profile_strength is not None and profile_strength > 0:
            return float(profile_strength)

        # Fallback: Check individual fields
        score = 0.0
        fields_to_check = [
            ('full_name', 10),
            ('phone', 5),
            ('location', 10),
            ('experience_years', 20),
            ('education_level', 15),
            ('resume_file', 40),
        ]

        for field, points in fields_to_check:
            value = getattr(candidate, field, None)
            if value:
                score += points

        return min(100, score)

    def _generate_suggestions(
        self,
        missing_skills: List[Dict],
        skill_score: float,
        experience_score: float,
        overall_score: float
    ) -> List[str]:
        """
        Generate actionable improvement suggestions for candidates.

        Provides specific, helpful tips to improve match percentage.
        """
        suggestions = []

        # Skill-based suggestions
        if missing_skills:
            # Prioritize required skills
            required_missing = [s for s in missing_skills if s.get('importance') == 'required']
            preferred_missing = [s for s in missing_skills if s.get('importance') == 'preferred']

            if required_missing:
                top_skills = required_missing[:3]
                skills_text = ', '.join(s['skill'] for s in top_skills)
                suggestions.append(f"Add required skills to boost match: {skills_text}")

            if preferred_missing and len(suggestions) < 3:
                skill = preferred_missing[0]['skill']
                # Estimate improvement
                potential_boost = min(15, (100 - skill_score) * 0.15)
                suggestions.append(
                    f"Adding '{skill}' could improve your match by ~{int(potential_boost)}%"
                )

        # Experience-based suggestions
        if experience_score < 60:
            suggestions.append(
                "Highlight relevant projects or internships to strengthen experience"
            )

        # Overall score-based suggestions
        if overall_score < 40:
            suggestions.append(
                "This role may require skills outside your current profile. "
                "Consider roles more aligned with your experience."
            )
        elif overall_score < 60:
            suggestions.append(
                "You're a potential match. Tailor your resume to highlight relevant experience."
            )
        elif overall_score >= 80:
            suggestions.append(
                "Strong match! Emphasize your most relevant achievements in your application."
            )

        # Limit to 3 suggestions
        return suggestions[:3]

    def calculate_all_matches_for_candidate(self, candidate) -> List[Dict]:
        """
        Calculate match scores for all active jobs for a candidate.

        Stores results in MatchScore model and returns sorted list.
        """
        from ann.models import Job, MatchScore

        # Get all active jobs
        jobs = Job.objects.filter(status='open')

        results = []

        for job in jobs:
            match_data = self.calculate_match(candidate, job)

            # Store in database
            try:
                MatchScore.objects.update_or_create(
                    candidate=candidate,
                    job=job,
                    defaults={
                        'overall_score': match_data['overall_score'],
                        'semantic_similarity': match_data['breakdown']['semantic_similarity'],
                        'skill_match_score': match_data['breakdown']['skill_match'],
                        'experience_match_score': match_data['breakdown']['experience_match'],
                        'matched_skills': match_data['matched_skills'],
                        'missing_skills': match_data['missing_skills'],
                        'suggestions': match_data['suggestions'],
                        'is_valid': True,
                    }
                )
            except Exception as e:
                logger.error(f"Failed to save MatchScore: {e}")

            results.append({
                'job_id': job.id,
                'job_title': job.title,
                'company': job.company,
                **match_data
            })

        # Sort by overall score descending
        results.sort(key=lambda x: x['overall_score'], reverse=True)

        logger.info(f"Calculated {len(results)} matches for candidate {candidate.user.username}")

        return results

    def calculate_all_matches_for_job(self, job) -> List[Dict]:
        """
        Calculate match scores for all candidates for a job.

        Used by recruiters to see ranked candidates.
        """
        from ann.models import CandidateProfile, MatchScore

        # Get all candidates with resumes
        candidates = CandidateProfile.objects.filter(
            resume_file__isnull=False
        ).exclude(resume_file='')

        results = []

        for candidate in candidates:
            match_data = self.calculate_match(candidate, job)

            # Store in database
            try:
                MatchScore.objects.update_or_create(
                    candidate=candidate,
                    job=job,
                    defaults={
                        'overall_score': match_data['overall_score'],
                        'semantic_similarity': match_data['breakdown']['semantic_similarity'],
                        'skill_match_score': match_data['breakdown']['skill_match'],
                        'experience_match_score': match_data['breakdown']['experience_match'],
                        'matched_skills': match_data['matched_skills'],
                        'missing_skills': match_data['missing_skills'],
                        'suggestions': match_data['suggestions'],
                        'is_valid': True,
                    }
                )
            except Exception as e:
                logger.error(f"Failed to save MatchScore: {e}")

            results.append({
                'candidate_id': candidate.id,
                'candidate_name': candidate.full_name or candidate.user.username,
                **match_data
            })

        # Sort by overall score descending
        results.sort(key=lambda x: x['overall_score'], reverse=True)

        logger.info(f"Calculated {len(results)} matches for job {job.title}")

        return results

    def get_match_score(self, candidate, job) -> Optional[Dict]:
        """
        Get cached match score from database if valid.

        Returns None if no valid cached score exists.
        """
        from ann.models import MatchScore

        try:
            match = MatchScore.objects.get(
                candidate=candidate,
                job=job,
                is_valid=True
            )

            return {
                'overall_score': match.overall_score,
                'breakdown': {
                    'semantic_similarity': match.semantic_similarity,
                    'skill_match': match.skill_match_score,
                    'experience_match': match.experience_match_score,
                    'education_match': 0,  # Not stored separately
                    'profile_completeness': 0,  # Not stored separately
                },
                'matched_skills': match.matched_skills,
                'missing_skills': match.missing_skills,
                'suggestions': match.suggestions,
                'cached': True,
                'calculated_at': match.calculated_at,
            }
        except Exception:
            return None

    def invalidate_candidate_matches(self, candidate):
        """Invalidate all cached matches for a candidate (e.g., after resume update)."""
        from ann.models import MatchScore

        updated = MatchScore.objects.filter(candidate=candidate).update(is_valid=False)
        logger.info(f"Invalidated {updated} matches for candidate {candidate.id}")

    def invalidate_job_matches(self, job):
        """Invalidate all cached matches for a job (e.g., after job update)."""
        from ann.models import MatchScore

        updated = MatchScore.objects.filter(job=job).update(is_valid=False)
        logger.info(f"Invalidated {updated} matches for job {job.id}")
