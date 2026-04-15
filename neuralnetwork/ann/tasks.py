"""
Celery Tasks for SkillSevak

Phase 6: Async background tasks for heavy ML operations.

Tasks:
- parse_resume_task: Extract text from PDF/DOCX
- extract_skills_task: NLP skill extraction
- generate_embedding_task: Semantic embedding generation
- calculate_matches_task: Calculate match scores for all jobs
- process_resume_complete_task: Full pipeline (parse → extract → embed → match)
- retrain_model_task: Retrain ANN with recruiter feedback
- recalculate_stale_matches_task: Refresh invalid match scores

Usage:
    # Async call (returns immediately):
    process_resume_complete_task.delay(candidate_id)

    # Sync call (waits for result):
    result = process_resume_complete_task.apply(args=[candidate_id])
"""

import logging
from celery import shared_task
from django.utils import timezone

logger = logging.getLogger(__name__)


# =============================================================================
# RESUME PROCESSING TASKS
# =============================================================================

@shared_task(
    bind=True,
    autoretry_for=(Exception,),
    retry_kwargs={'max_retries': 3, 'countdown': 60},
    soft_time_limit=120,
    time_limit=180,
)
def parse_resume_task(self, candidate_id: int) -> dict:
    """
    Parse resume file and extract text.

    Args:
        candidate_id: CandidateProfile ID

    Returns:
        Dict with parsing results
    """
    from ann.models import CandidateProfile, ParsedResume
    from ann.services.resume_parser import ResumeParser

    logger.info(f"[Task {self.request.id}] Parsing resume for candidate {candidate_id}")

    try:
        profile = CandidateProfile.objects.get(id=candidate_id)

        if not profile.resume_file:
            return {'success': False, 'error': 'No resume file uploaded'}

        parser = ResumeParser()
        file_path = profile.resume_file.path

        # Extract and parse
        raw_text = parser.extract_text(file_path)
        cleaned_text = parser.clean_text(raw_text)
        sections = parser.detect_sections(raw_text)
        completeness_score = parser.calculate_completeness_score(sections)

        # Update or create ParsedResume
        parsed_resume, created = ParsedResume.objects.update_or_create(
            candidate=profile,
            defaults={
                'raw_text': raw_text,
                'cleaned_text': cleaned_text,
                'sections_json': sections,
                'parsing_status': 'completed',
                'parsed_at': timezone.now(),
                'error_message': '',
            }
        )

        # Update profile strength
        profile.profile_strength = completeness_score
        profile.save(update_fields=['profile_strength'])

        logger.info(f"[Task {self.request.id}] Resume parsed: {len(cleaned_text)} chars")

        return {
            'success': True,
            'candidate_id': candidate_id,
            'chars_extracted': len(cleaned_text),
            'sections_found': [k for k, v in sections.items() if v.strip()],
            'completeness_score': completeness_score,
        }

    except CandidateProfile.DoesNotExist:
        logger.error(f"Candidate {candidate_id} not found")
        return {'success': False, 'error': 'Candidate not found'}

    except Exception as e:
        logger.error(f"Resume parsing failed: {e}")
        # Mark as failed in database
        try:
            profile = CandidateProfile.objects.get(id=candidate_id)
            ParsedResume.objects.update_or_create(
                candidate=profile,
                defaults={
                    'parsing_status': 'failed',
                    'error_message': str(e),
                }
            )
        except Exception:
            pass
        raise  # Re-raise for retry


@shared_task(
    bind=True,
    autoretry_for=(Exception,),
    retry_kwargs={'max_retries': 2, 'countdown': 30},
    soft_time_limit=90,
    time_limit=120,
)
def extract_skills_task(self, candidate_id: int) -> dict:
    """
    Extract skills from parsed resume using NLP.

    Args:
        candidate_id: CandidateProfile ID

    Returns:
        Dict with extraction results
    """
    from ann.models import CandidateProfile, ParsedResume, CandidateSkill
    from ann.services.skill_extractor import DynamicSkillExtractor

    logger.info(f"[Task {self.request.id}] Extracting skills for candidate {candidate_id}")

    try:
        profile = CandidateProfile.objects.get(id=candidate_id)
        parsed_resume = ParsedResume.objects.filter(candidate=profile).first()

        if not parsed_resume or parsed_resume.parsing_status != 'completed':
            return {'success': False, 'error': 'Resume not parsed yet'}

        extractor = DynamicSkillExtractor()
        sections = parsed_resume.sections_json or {}
        cleaned_text = parsed_resume.cleaned_text or ''

        all_skills = []
        seen_normalized = set()

        # Map resume sections to source choices
        section_mapping = {
            'skills': 'skills_section',
            'experience': 'experience',
            'projects': 'projects',
            'education': 'education',
            'summary': 'summary',
        }

        # Extract from each section
        for section_name, section_text in sections.items():
            if not section_text or not section_text.strip():
                continue

            source = section_mapping.get(section_name, 'full_text')
            skills = extractor.extract_skills(section_text, section_name)

            for skill in skills:
                normalized = skill['normalized']
                if normalized not in seen_normalized:
                    seen_normalized.add(normalized)
                    skill['db_source'] = source
                    all_skills.append(skill)

        # Extract from full text
        full_text_skills = extractor.extract_skills(cleaned_text, 'full_text')
        for skill in full_text_skills:
            normalized = skill['normalized']
            if normalized not in seen_normalized:
                seen_normalized.add(normalized)
                skill['db_source'] = 'full_text'
                all_skills.append(skill)

        # Clear existing and save new skills
        CandidateSkill.objects.filter(candidate=profile).delete()

        skills_created = 0
        for skill_data in all_skills:
            try:
                proficiency = extractor.estimate_proficiency(
                    skill_data['skill'],
                    cleaned_text
                )

                CandidateSkill.objects.create(
                    candidate=profile,
                    skill_text=skill_data['skill'][:200],
                    normalized_text=skill_data['normalized'][:200],
                    proficiency_level=proficiency,
                    source=skill_data.get('db_source', 'full_text'),
                    context=skill_data.get('context', '')[:500],
                    confidence_score=skill_data.get('confidence', 0.7),
                    category=skill_data.get('category', 'domain'),
                )
                skills_created += 1
            except Exception as e:
                logger.warning(f"Failed to save skill: {e}")
                continue

        logger.info(f"[Task {self.request.id}] Extracted {skills_created} skills")

        return {
            'success': True,
            'candidate_id': candidate_id,
            'skills_extracted': skills_created,
        }

    except CandidateProfile.DoesNotExist:
        return {'success': False, 'error': 'Candidate not found'}

    except Exception as e:
        logger.error(f"Skill extraction failed: {e}")
        raise


@shared_task(
    bind=True,
    autoretry_for=(Exception,),
    retry_kwargs={'max_retries': 2, 'countdown': 30},
    soft_time_limit=60,
    time_limit=90,
)
def generate_embedding_task(self, candidate_id: int) -> dict:
    """
    Generate semantic embedding for candidate resume.

    Args:
        candidate_id: CandidateProfile ID

    Returns:
        Dict with embedding status
    """
    from ann.models import CandidateProfile, ParsedResume
    from ann.services.embedding_service import EmbeddingService

    logger.info(f"[Task {self.request.id}] Generating embedding for candidate {candidate_id}")

    try:
        profile = CandidateProfile.objects.get(id=candidate_id)
        parsed_resume = ParsedResume.objects.filter(candidate=profile).first()

        if not parsed_resume or not parsed_resume.cleaned_text:
            return {'success': False, 'error': 'No parsed resume text'}

        embedding_service = EmbeddingService()
        embedding = embedding_service.generate_embedding(parsed_resume.cleaned_text)
        serialized = embedding_service.serialize_embedding(embedding)

        # Update parsed resume with embedding
        parsed_resume.embedding = serialized
        parsed_resume.save(update_fields=['embedding'])

        logger.info(f"[Task {self.request.id}] Embedding generated (384 dims)")

        return {
            'success': True,
            'candidate_id': candidate_id,
            'embedding_dims': 384,
        }

    except CandidateProfile.DoesNotExist:
        return {'success': False, 'error': 'Candidate not found'}

    except Exception as e:
        logger.error(f"Embedding generation failed: {e}")
        raise


@shared_task(
    bind=True,
    autoretry_for=(Exception,),
    retry_kwargs={'max_retries': 2, 'countdown': 60},
    soft_time_limit=300,
    time_limit=360,
)
def calculate_matches_task(self, candidate_id: int) -> dict:
    """
    Calculate match scores for all active jobs.

    Args:
        candidate_id: CandidateProfile ID

    Returns:
        Dict with match calculation results
    """
    from ann.models import CandidateProfile
    from ann.services.matching_engine import MatchingEngine

    logger.info(f"[Task {self.request.id}] Calculating matches for candidate {candidate_id}")

    try:
        profile = CandidateProfile.objects.get(id=candidate_id)
        engine = MatchingEngine()

        results = engine.calculate_all_matches_for_candidate(profile)

        logger.info(f"[Task {self.request.id}] Calculated {len(results)} matches")

        return {
            'success': True,
            'candidate_id': candidate_id,
            'matches_calculated': len(results),
            'top_match': results[0]['overall_score'] if results else 0,
        }

    except CandidateProfile.DoesNotExist:
        return {'success': False, 'error': 'Candidate not found'}

    except Exception as e:
        logger.error(f"Match calculation failed: {e}")
        raise


@shared_task(
    bind=True,
    autoretry_for=(Exception,),
    retry_kwargs={'max_retries': 2, 'countdown': 60},
    soft_time_limit=600,
    time_limit=720,
)
def process_resume_complete_task(self, candidate_id: int) -> dict:
    """
    Complete resume processing pipeline.

    Runs all steps in sequence:
    1. Parse resume (extract text)
    2. Extract skills (NLP)
    3. Generate embedding (ML)
    4. Calculate matches (all jobs)

    This is the main task to call after resume upload.

    Args:
        candidate_id: CandidateProfile ID

    Returns:
        Dict with complete pipeline results
    """
    from ann.models import CandidateProfile

    logger.info(f"[Task {self.request.id}] Starting complete pipeline for candidate {candidate_id}")

    results = {
        'candidate_id': candidate_id,
        'steps_completed': [],
        'errors': [],
    }

    try:
        # Verify candidate exists
        profile = CandidateProfile.objects.get(id=candidate_id)

        # Step 1: Parse resume
        try:
            parse_result = parse_resume_task.apply(args=[candidate_id]).get()
            if parse_result.get('success'):
                results['steps_completed'].append('parse')
                results['parsing'] = parse_result
            else:
                results['errors'].append(f"Parse: {parse_result.get('error')}")
        except Exception as e:
            results['errors'].append(f"Parse: {str(e)}")

        # Step 2: Extract skills
        try:
            skills_result = extract_skills_task.apply(args=[candidate_id]).get()
            if skills_result.get('success'):
                results['steps_completed'].append('skills')
                results['skills'] = skills_result
            else:
                results['errors'].append(f"Skills: {skills_result.get('error')}")
        except Exception as e:
            results['errors'].append(f"Skills: {str(e)}")

        # Step 3: Generate embedding
        try:
            embed_result = generate_embedding_task.apply(args=[candidate_id]).get()
            if embed_result.get('success'):
                results['steps_completed'].append('embedding')
                results['embedding'] = embed_result
            else:
                results['errors'].append(f"Embedding: {embed_result.get('error')}")
        except Exception as e:
            results['errors'].append(f"Embedding: {str(e)}")

        # Step 4: Calculate matches
        try:
            match_result = calculate_matches_task.apply(args=[candidate_id]).get()
            if match_result.get('success'):
                results['steps_completed'].append('matches')
                results['matches'] = match_result
            else:
                results['errors'].append(f"Matches: {match_result.get('error')}")
        except Exception as e:
            results['errors'].append(f"Matches: {str(e)}")

        results['success'] = len(results['steps_completed']) == 4

        logger.info(
            f"[Task {self.request.id}] Pipeline complete: "
            f"{len(results['steps_completed'])}/4 steps, "
            f"{len(results['errors'])} errors"
        )

        return results

    except CandidateProfile.DoesNotExist:
        return {'success': False, 'error': 'Candidate not found'}

    except Exception as e:
        logger.error(f"Pipeline failed: {e}")
        results['success'] = False
        results['errors'].append(str(e))
        return results


# =============================================================================
# MODEL RETRAINING TASKS
# =============================================================================

@shared_task(
    bind=True,
    soft_time_limit=1800,  # 30 min
    time_limit=2400,       # 40 min
)
def retrain_model_task(self, use_real_data: bool = True) -> dict:
    """
    Retrain the ANN model using all available data sources:
      1. Real recruiter decisions from the DB (grows over time)
      2. Pre-computed external CSV  (HuggingFace datasets, ~8k rows)
      3. Synthetic data             (5,000 rows, always included for coverage)

    Called automatically by Celery Beat weekly, or triggered manually.

    Args:
        use_real_data: If True, attempt to include real DB decisions.

    Returns:
        Dict with training results.
    """
    import numpy as np
    logger.info(f"[Task {self.request.id}] Starting model retraining (multi-source)")

    try:
        from ann.ml.train import ModelTrainer

        trainer = ModelTrainer()
        X_all = np.array([], dtype=np.float32)
        y_all = np.array([], dtype=np.float32)
        sources = []

        # ------------------------------------------------------------------
        # Source 1: Real website data (recruiter decisions from DB)
        # ------------------------------------------------------------------
        if use_real_data:
            X_db, y_db = trainer.generate_real_data_from_db()
            if X_db is not None and len(X_db) > 0:
                X_all = X_db
                y_all = y_db
                sources.append(f'db:{len(X_db)}')
                logger.info(f"[retrain] DB data: {len(X_db)} samples")
            else:
                logger.info("[retrain] DB data: insufficient, skipping")

        # ------------------------------------------------------------------
        # Source 2: External dataset CSV (pre-computed from HuggingFace)
        # Only loaded when use_real_data=True (skipped for synthetic-only runs)
        # ------------------------------------------------------------------
        X_ext, y_ext = trainer.load_external_data_csv() if use_real_data else (None, None)
        if X_ext is not None and len(X_ext) > 0:
            if len(X_all):
                X_all = np.concatenate([X_all, X_ext])
                y_all = np.concatenate([y_all, y_ext])
            else:
                X_all = X_ext
                y_all = y_ext
            sources.append(f'external:{len(X_ext)}')
            logger.info(f"[retrain] External CSV: {len(X_ext)} samples")
        else:
            logger.info("[retrain] No external CSV found — run: python manage.py load_external_data")

        # ------------------------------------------------------------------
        # Source 3: Synthetic data (always included for coverage balance)
        # ------------------------------------------------------------------
        X_syn, y_syn = trainer.generate_synthetic_data(n_samples=5000)
        if len(X_all):
            X_all = np.concatenate([X_all, X_syn])
            y_all = np.concatenate([y_all, y_syn])
        else:
            X_all = X_syn
            y_all = y_syn
        sources.append('synthetic:5000')
        logger.info(f"[retrain] Synthetic: 5000 samples")

        total_samples = len(X_all)
        data_source = 'mixed' if len(sources) > 1 else sources[0].split(':')[0]
        logger.info(
            f"[retrain] Total training data: {total_samples} samples "
            f"({', '.join(sources)})"
        )

        # ------------------------------------------------------------------
        # Train on combined data (pass X/y directly; train() skips CSV re-load)
        # ------------------------------------------------------------------
        history = trainer.train(
            X=X_all,
            y=y_all,
            epochs=150,
            batch_size=64,
            early_stopping_patience=15,
            verbose=False,
            external_csv_path=trainer._NO_EXTERNAL_CSV,  # already merged above
        )

        logger.info(
            f"[Task {self.request.id}] Training complete: "
            f"{history['epochs_trained']} epochs, "
            f"best val loss: {history['best_val_loss']:.6f}"
        )

        return {
            'success': True,
            'data_source': data_source,
            'sources': sources,
            'samples': total_samples,
            'epochs_trained': history['epochs_trained'],
            'best_val_loss': history['best_val_loss'],
            'model_path': str(trainer.model_path),
        }

    except Exception as e:
        logger.error(f"Model retraining failed: {e}")
        return {'success': False, 'error': str(e)}


@shared_task(
    bind=True,
    soft_time_limit=600,
    time_limit=900,
)
def recalculate_stale_matches_task(self) -> dict:
    """
    Recalculate invalid/stale match scores.

    Called daily by Celery Beat to refresh outdated matches.

    Returns:
        Dict with recalculation results
    """
    from ann.models import MatchScore, CandidateProfile
    from ann.services.matching_engine import MatchingEngine

    logger.info(f"[Task {self.request.id}] Recalculating stale matches")

    try:
        # Find stale matches
        stale_matches = MatchScore.objects.filter(is_valid=False).select_related(
            'candidate', 'job'
        )[:100]  # Limit to 100 per run

        engine = MatchingEngine()
        recalculated = 0

        for match in stale_matches:
            try:
                new_match_data = engine.calculate_match(match.candidate, match.job)

                match.overall_score = new_match_data['overall_score']
                match.semantic_similarity = new_match_data['breakdown']['semantic_similarity']
                match.skill_match_score = new_match_data['breakdown']['skill_match']
                match.experience_match_score = new_match_data['breakdown']['experience_match']
                match.matched_skills = new_match_data['matched_skills']
                match.missing_skills = new_match_data['missing_skills']
                match.suggestions = new_match_data['suggestions']
                match.is_valid = True
                match.save()

                recalculated += 1

            except Exception as e:
                logger.warning(f"Failed to recalculate match {match.id}: {e}")
                continue

        logger.info(f"[Task {self.request.id}] Recalculated {recalculated} matches")

        return {
            'success': True,
            'stale_found': len(stale_matches),
            'recalculated': recalculated,
        }

    except Exception as e:
        logger.error(f"Stale match recalculation failed: {e}")
        return {'success': False, 'error': str(e)}


# =============================================================================
# JOB PROCESSING TASKS
# =============================================================================

@shared_task(
    bind=True,
    autoretry_for=(Exception,),
    retry_kwargs={'max_retries': 2, 'countdown': 30},
    soft_time_limit=60,
    time_limit=90,
)
def generate_job_embedding_task(self, job_id: int) -> dict:
    """
    Generate semantic embedding for a job posting.

    Args:
        job_id: Job ID

    Returns:
        Dict with embedding status
    """
    from ann.models import Job
    from ann.services.embedding_service import EmbeddingService

    logger.info(f"[Task {self.request.id}] Generating embedding for job {job_id}")

    try:
        job = Job.objects.get(id=job_id)

        # Build job text
        job_text = f"{job.title} {job.description} {job.requirements}"
        if job.skills_required:
            job_text += f" {job.skills_required}"
        if job.category:
            job_text += f" {job.category}"

        embedding_service = EmbeddingService()
        embedding = embedding_service.generate_embedding(job_text)
        serialized = embedding_service.serialize_embedding(embedding)

        job.embedding = serialized
        job.save(update_fields=['embedding'])

        logger.info(f"[Task {self.request.id}] Job embedding generated")

        return {
            'success': True,
            'job_id': job_id,
            'embedding_dims': 384,
        }

    except Job.DoesNotExist:
        return {'success': False, 'error': 'Job not found'}

    except Exception as e:
        logger.error(f"Job embedding generation failed: {e}")
        raise


@shared_task(
    bind=True,
    soft_time_limit=300,
    time_limit=360,
)
def calculate_job_matches_task(self, job_id: int) -> dict:
    """
    Calculate match scores for all candidates for a job.

    Useful for recruiters to see ranked candidates.

    Args:
        job_id: Job ID

    Returns:
        Dict with match calculation results
    """
    from ann.models import Job
    from ann.services.matching_engine import MatchingEngine

    logger.info(f"[Task {self.request.id}] Calculating candidate matches for job {job_id}")

    try:
        job = Job.objects.get(id=job_id)
        engine = MatchingEngine()

        results = engine.calculate_all_matches_for_job(job)

        logger.info(f"[Task {self.request.id}] Calculated {len(results)} candidate matches")

        return {
            'success': True,
            'job_id': job_id,
            'candidates_matched': len(results),
            'top_match': results[0]['overall_score'] if results else 0,
        }

    except Job.DoesNotExist:
        return {'success': False, 'error': 'Job not found'}

    except Exception as e:
        logger.error(f"Job match calculation failed: {e}")
        raise


# =============================================================================
# UTILITY FUNCTIONS
# =============================================================================

def process_resume_sync(candidate_id: int) -> dict:
    """
    Synchronous resume processing (fallback when Celery unavailable).

    Use this in views when Redis/Celery is not running.
    """
    logger.info(f"Processing resume synchronously for candidate {candidate_id}")

    return process_resume_complete_task.apply(args=[candidate_id]).get()


def is_celery_available() -> bool:
    """
    Check if Celery worker is available.

    Returns True if a worker responds to ping.
    """
    try:
        from neuralnetwork.celery import app
        inspect = app.control.inspect()
        stats = inspect.stats()
        return stats is not None and len(stats) > 0
    except Exception:
        return False
