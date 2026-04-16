"""
Management command to re-extract skills for all candidates.

Run after fixing skill extraction logic to clean up garbage skills.

Usage:
    python manage.py reprocess_candidate_skills
    python manage.py reprocess_candidate_skills --username tanisha@gmail.com
"""

from django.core.management.base import BaseCommand
from ann.models import CandidateProfile, ParsedResume, CandidateSkill


class Command(BaseCommand):
    help = 'Re-extract skills for all candidates using the current extraction logic'

    def add_arguments(self, parser):
        parser.add_argument(
            '--username',
            type=str,
            help='Re-process only a specific user (by username/email)',
        )

    def handle(self, *args, **options):
        from ann.services.skill_extractor import DynamicSkillExtractor
        from ann.views import _infer_experience_years, _infer_education_from_sections

        extractor = DynamicSkillExtractor()
        username = options.get('username')

        profiles = CandidateProfile.objects.all()
        if username:
            profiles = profiles.filter(user__username=username)

        processed = 0
        skipped = 0

        # Only extract from real content sections
        VALID_SECTIONS = {
            'skills': 'skills_section',
            'experience': 'experience',
            'projects': 'projects',
            'summary': 'summary',
            'certifications': 'skills_section',
            'awards': 'skills_section',
        }

        for profile in profiles:
            pr = ParsedResume.objects.filter(
                candidate=profile,
                parsing_status='completed'
            ).first()

            if not pr or not pr.sections_json:
                skipped += 1
                self.stdout.write(
                    self.style.WARNING(f'  SKIP {profile.user.username}: no parsed resume')
                )
                continue

            sections = pr.sections_json
            full_text = pr.cleaned_text or pr.raw_text or ''

            all_skills = []
            seen_normalized = set()

            for section_name, section_text in sections.items():
                if section_name not in VALID_SECTIONS:
                    continue
                if not section_text or not section_text.strip():
                    continue

                source = VALID_SECTIONS[section_name]
                try:
                    skills = extractor.extract_skills(section_text, section_name)
                except Exception as e:
                    self.stdout.write(self.style.WARNING(f'    Error in section {section_name}: {e}'))
                    continue

                for skill in skills:
                    normalized = skill['normalized']
                    if normalized not in seen_normalized:
                        seen_normalized.add(normalized)
                        skill['db_source'] = source
                        all_skills.append(skill)

            # Delete old skills and re-insert
            old_count = CandidateSkill.objects.filter(candidate=profile).count()
            CandidateSkill.objects.filter(candidate=profile).delete()

            MIN_CONFIDENCE = 0.75
            skills_created = 0
            for skill_data in all_skills:
                if skill_data.get('confidence', 0.7) < MIN_CONFIDENCE:
                    continue
                try:
                    proficiency = extractor.estimate_proficiency(
                        skill_data['skill'],
                        full_text
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
                    pass

            # Re-infer experience years and education from stored sections
            inferred_exp = _infer_experience_years(sections)
            inferred_edu_level, inferred_edu_field = _infer_education_from_sections(sections)
            profile_changed = False
            if inferred_exp > 0 and profile.experience_years != inferred_exp:
                profile.experience_years = inferred_exp
                profile_changed = True
            if inferred_edu_level and not profile.education_level:
                profile.education_level = inferred_edu_level
                profile_changed = True
            if inferred_edu_field and not profile.education_field:
                profile.education_field = inferred_edu_field
                profile_changed = True
            if profile_changed:
                profile.save(update_fields=['experience_years', 'education_level', 'education_field'])

            processed += 1
            self.stdout.write(
                self.style.SUCCESS(
                    f'  OK  {profile.user.username}: {old_count} -> {skills_created} skills'
                    + (f', exp={inferred_exp}yr, edu={inferred_edu_level}' if profile_changed else '')
                )
            )

        self.stdout.write('')
        self.stdout.write(self.style.SUCCESS(
            f'Done: {processed} processed, {skipped} skipped'
        ))
