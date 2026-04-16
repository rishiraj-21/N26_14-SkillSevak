"""
Dynamic Skill Extractor Service

CRITICAL: NO HARDCODED SKILL DICTIONARY!
Extracts skills from text using NLP techniques.
Works for ANY industry - tech, law, healthcare, marketing, etc.

Phase 3 implementation per PROJECT_PLAN.md.

Scoring per PRD.md Section 8.3:
Skills Score = (0.70 × Technical) + (0.20 × Domain) + (0.10 × Soft)

Dependencies:
- spacy: NLP processing
"""

import re
import logging
from typing import List, Dict, Set, Tuple, Optional
from enum import Enum

logger = logging.getLogger(__name__)


class SkillCategory(Enum):
    """Skill categories for weighted scoring."""
    TECHNICAL = "technical"   # 70% weight - Programming, frameworks, tools
    DOMAIN = "domain"         # 20% weight - Industry-specific knowledge
    SOFT = "soft"             # 10% weight - Communication, leadership


class DynamicSkillExtractor:
    """
    Extract skills from text WITHOUT hardcoded dictionary.

    Per PRD.md Section 8.1:
    - Uses NLP (spaCy) for extraction
    - Works for any industry
    - Self-improving with data

    Methods:
    1. Noun phrase extraction - "machine learning", "project management"
    2. Proper noun extraction - "Python", "Docker", "AWS"
    3. Named Entity Recognition - organizations, products
    4. Pattern-based extraction - comma/bullet lists in skills section
    5. Skill categorization - Technical (70%), Domain (20%), Soft (10%)
    """

    # Stopwords to filter out non-skills (NOT a skill dictionary!)
    STOPWORDS = {
        'and', 'or', 'the', 'a', 'an', 'in', 'on', 'at', 'to', 'for',
        'with', 'by', 'from', 'as', 'is', 'was', 'are', 'were', 'been',
        'be', 'have', 'has', 'had', 'do', 'does', 'did', 'will', 'would',
        'could', 'should', 'may', 'might', 'must', 'shall', 'can',
        'of', 'that', 'this', 'these', 'those', 'it', 'its', 'i', 'me',
        'my', 'we', 'our', 'you', 'your', 'he', 'she', 'they', 'them',
        'who', 'which', 'what', 'where', 'when', 'why', 'how',
        'all', 'each', 'every', 'both', 'few', 'more', 'most', 'other',
        'some', 'such', 'no', 'nor', 'not', 'only', 'own', 'same', 'so',
        'than', 'too', 'very', 'just', 'also', 'now', 'here', 'there',
        'am', 'being', 'if', 'then', 'else', 'but', 'because', 'about',
        'into', 'through', 'during', 'before', 'after', 'above', 'below',
        'between', 'under', 'over', 'again', 'further', 'once', 'any',
        # Common resume words that aren't skills
        'work', 'worked', 'working', 'experience', 'experienced',
        'year', 'years', 'month', 'months', 'day', 'days',
        'company', 'companies', 'team', 'teams', 'project', 'projects',
        'role', 'roles', 'position', 'positions', 'job', 'jobs',
        'responsible', 'responsibilities', 'duties', 'duty',
        'including', 'include', 'includes', 'included',
        'using', 'use', 'used', 'utilize', 'utilized',
        'various', 'multiple', 'several', 'many', 'new',
        'based', 'related', 'including', 'within', 'across',
        # Job titles - NOT skills
        'intern', 'interns', 'internship', 'internships',
        'manager', 'managers', 'management', 'managing',
        'director', 'directors', 'executive', 'executives',
        'engineer', 'engineers', 'engineering',
        'developer', 'developers', 'development',
        'analyst', 'analysts', 'analysis',
        'designer', 'designers', 'design',
        'consultant', 'consultants', 'consulting',
        'specialist', 'specialists', 'coordinator', 'coordinators',
        'associate', 'associates', 'assistant', 'assistants',
        'senior', 'junior', 'lead', 'principal', 'staff',
        'head', 'chief', 'officer', 'president', 'vice',
        # Common non-skill words
        'candidate', 'candidates', 'applicant', 'applicants',
        'employer', 'employers', 'employee', 'employees',
        'client', 'clients', 'customer', 'customers',
        'business', 'businesses', 'industry', 'industries',
        'market', 'markets', 'sector', 'sectors',
        'service', 'services', 'product', 'products',
        'solution', 'solutions', 'system', 'systems',
        'process', 'processes', 'procedure', 'procedures',
        'requirement', 'requirements', 'qualification', 'qualifications',
        'ability', 'abilities', 'skill', 'skills',
        'knowledge', 'understanding', 'expertise',
        'degree', 'degrees', 'bachelor', 'master', 'phd', 'diploma',
        'university', 'college', 'school', 'institute', 'education',
        'certified', 'certification', 'certificate', 'license',
        'salary', 'compensation', 'benefits', 'bonus',
        'remote', 'onsite', 'hybrid', 'location', 'office',
        'full-time', 'part-time', 'contract', 'temporary', 'permanent',
    }

    # Soft skill indicators (for categorization, NOT extraction)
    SOFT_SKILL_PATTERNS = [
        r'\b(communication|communicate|communicating)\b',
        r'\b(leadership|leader|leading|lead)\b',
        r'\b(teamwork|team\s*work|collaboration|collaborative)\b',
        r'\b(problem[\s-]*solving|analytical|critical\s*thinking)\b',
        r'\b(time\s*management|organized|organization)\b',
        r'\b(adaptability|adaptable|flexible|flexibility)\b',
        r'\b(creativity|creative|innovative|innovation)\b',
        r'\b(interpersonal|negotiation|presentation)\b',
        r'\b(attention\s*to\s*detail|detail[\s-]*oriented)\b',
        r'\b(self[\s-]*motivated|proactive|initiative)\b',
        r'\b(mentoring|coaching|training)\b',
        r'\b(conflict\s*resolution|decision[\s-]*making)\b',
    ]

    # Technical skill patterns (for categorization)
    TECHNICAL_PATTERNS = [
        r'\b(programming|coding|development|developer)\b',
        r'\b(software|hardware|system|database|server)\b',
        r'\b(api|sdk|framework|library|platform)\b',
        r'\b(cloud|devops|ci[\s/]*cd|deployment)\b',
        r'\b(frontend|backend|fullstack|full[\s-]*stack)\b',
        r'\b(mobile|web|desktop|embedded)\b',
        r'\b(testing|qa|automation|scripting)\b',
        r'\b(security|networking|infrastructure)\b',
        r'\b(data\s*(science|engineering|analysis|analytics))\b',
        r'\b(machine\s*learning|deep\s*learning|ai|ml)\b',
    ]

    def __init__(self):
        self._nlp = None
        self._soft_patterns_compiled = [re.compile(p, re.IGNORECASE) for p in self.SOFT_SKILL_PATTERNS]
        self._tech_patterns_compiled = [re.compile(p, re.IGNORECASE) for p in self.TECHNICAL_PATTERNS]

    @property
    def nlp(self):
        """Lazy load spaCy model."""
        if self._nlp is None:
            try:
                import spacy
                self._nlp = spacy.load("en_core_web_sm")
                logger.info("spaCy model loaded successfully")
            except OSError:
                logger.error("spaCy model not found. Run: python -m spacy download en_core_web_sm")
                raise
        return self._nlp

    def extract_skills(self, text: str, section: str = 'general') -> List[Dict]:
        """
        Extract skills from text using multiple NLP methods.

        Args:
            text: Text to extract skills from
            section: Source section (skills, experience, projects, etc.)

        Returns:
            List of skill dicts with keys:
            - skill: Original extracted text
            - normalized: Lowercase normalized form
            - confidence: 0.0-1.0 confidence score
            - source: Which section it came from
            - context: Surrounding text for proficiency detection
            - category: technical/domain/soft
        """
        if not text or not text.strip():
            return []

        doc = self.nlp(text)
        all_raw_skills: List[Dict] = []

        # Run each extraction method with its own seen set so they don't
        # block each other. _deduplicate_skills keeps the highest-confidence version.

        # Method 1: Noun phrases (catches "machine learning", "project management")
        all_raw_skills.extend(self._extract_noun_phrases(doc, section, set()))

        # Method 2: Proper nouns (catches "Python", "Docker", "AWS") — confidence 0.80
        all_raw_skills.extend(self._extract_proper_nouns(doc, section, set()))

        # Method 3: Named entities (catches organizations, products, technologies)
        all_raw_skills.extend(self._extract_named_entities(doc, section, set()))

        # Method 4: Pattern-based extraction for skills section — confidence 0.90 (highest)
        if section.lower() in ['skills', 'technical skills', 'core competencies']:
            all_raw_skills.extend(self._extract_from_patterns(text, section, set()))

        # Deduplicate: keeps highest-confidence version of each normalized skill
        skills = self._deduplicate_skills(all_raw_skills)

        logger.info(f"Extracted {len(skills)} skills from section: {section}")
        return skills

    def _extract_noun_phrases(self, doc, section: str, seen: Set[str]) -> List[Dict]:
        """Extract skills from noun phrases."""
        skills = []

        for chunk in doc.noun_chunks:
            skill_text = self._clean_skill_text(chunk.text)
            normalized = skill_text.lower()

            if not skill_text or normalized in seen:
                continue

            if not self._is_valid_skill(skill_text, normalized):
                continue

            seen.add(normalized)

            # Get context (sentence containing the skill)
            context = chunk.sent.text[:300] if chunk.sent else ""

            skills.append({
                'skill': skill_text,
                'normalized': normalized,
                'confidence': 0.70,
                'source': section,
                'context': context,
                'category': self._categorize_skill(skill_text, context),
                'extraction_method': 'noun_phrase'
            })

        return skills

    def _extract_proper_nouns(self, doc, section: str, seen: Set[str]) -> List[Dict]:
        """Extract skills from proper nouns (tools, technologies, frameworks)."""
        skills = []

        for token in doc:
            if token.pos_ != "PROPN":
                continue

            skill_text = token.text.strip()
            normalized = skill_text.lower()

            if len(skill_text) < 2 or normalized in seen:
                continue

            if not self._is_valid_skill(skill_text, normalized):
                continue

            seen.add(normalized)

            # Get context
            context = token.sent.text[:300] if token.sent else ""

            skills.append({
                'skill': skill_text,
                'normalized': normalized,
                'confidence': 0.80,
                'source': section,
                'context': context,
                'category': self._categorize_skill(skill_text, context),
                'extraction_method': 'proper_noun'
            })

        return skills

    def _extract_named_entities(self, doc, section: str, seen: Set[str]) -> List[Dict]:
        """Extract skills from named entities."""
        skills = []

        # Entity types likely to be skills/tools
        # NOTE: Removed 'ORG' - it captures company names like CISCO, Google, Microsoft
        # which are NOT skills
        skill_entity_types = {'PRODUCT', 'WORK_OF_ART', 'LAW'}

        for ent in doc.ents:
            if ent.label_ not in skill_entity_types:
                continue

            skill_text = self._clean_skill_text(ent.text)
            normalized = skill_text.lower()

            if not skill_text or normalized in seen:
                continue

            if not self._is_valid_skill(skill_text, normalized):
                continue

            seen.add(normalized)

            # Get context
            context = ent.sent.text[:300] if hasattr(ent, 'sent') and ent.sent else ""

            skills.append({
                'skill': skill_text,
                'normalized': normalized,
                'confidence': 0.85,
                'source': section,
                'context': context,
                'category': self._categorize_skill(skill_text, context),
                'extraction_method': 'named_entity',
                'entity_type': ent.label_
            })

        return skills

    def _extract_from_patterns(self, text: str, section: str, seen: Set[str]) -> List[Dict]:
        """Extract skills from comma/bullet separated lists."""
        skills = []

        # Split by common delimiters
        delimiters = r'[,•|/\n;]|\band\b'
        parts = re.split(delimiters, text)

        for part in parts:
            # Strip "Header: " prefix (e.g., "Languages: Python" → "Python")
            if ':' in part:
                after_colon = part.split(':', 1)[1].strip()
                if after_colon:
                    part = after_colon

            skill_text = self._clean_skill_text(part)
            normalized = skill_text.lower()

            if not skill_text or normalized in seen:
                continue

            # Skills in lists are usually 1-4 words
            word_count = len(skill_text.split())
            if word_count < 1 or word_count > 5:
                continue

            if not self._is_valid_skill(skill_text, normalized):
                continue

            seen.add(normalized)

            skills.append({
                'skill': skill_text,
                'normalized': normalized,
                'confidence': 0.90,  # High confidence for skills section
                'source': section,
                'context': '',
                'category': self._categorize_skill(skill_text, ''),
                'extraction_method': 'pattern'
            })

        return skills

    def _clean_skill_text(self, text: str) -> str:
        """Clean and normalize skill text."""
        if not text:
            return ''

        # Remove extra whitespace
        text = ' '.join(text.split())

        # Remove leading/trailing punctuation
        text = text.strip('.,;:!?()[]{}"\'-–—•·')

        # Remove leading articles
        text = re.sub(r'^(the|a|an)\s+', '', text, flags=re.IGNORECASE)

        # Skip if too short or too long
        if len(text) < 2 or len(text) > 60:
            return ''

        return text

    def _is_valid_skill(self, skill: str, normalized: str) -> bool:
        """Check if extracted text is likely a valid skill."""
        # Skip stopwords
        if normalized in self.STOPWORDS:
            return False

        # Skip pure numbers
        if skill.replace('.', '').replace(',', '').isdigit():
            return False

        # Skip single characters
        if len(skill) < 2:
            return False

        # Skip if mostly numbers
        digit_ratio = sum(c.isdigit() for c in skill) / len(skill)
        if digit_ratio > 0.5:
            return False

        # Skip overly long phrases (more than 5 words)
        if len(skill.split()) > 5:
            return False

        # Skip header/label patterns (e.g., "Languages: Python", "Skills: Python")
        if ':' in skill:
            return False

        # Skip common non-skill patterns
        non_skill_patterns = [
            r'^\d+\+?\s*(years?|months?|days?)$',  # "5 years"
            r'^(jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)',  # Months
            r'^\d{4}$',  # Years like "2023"
            r'^(mr|mrs|ms|dr)\.?\s',  # Titles
            r'@|\.com|\.org|\.net',  # Emails/URLs
        ]

        for pattern in non_skill_patterns:
            if re.search(pattern, normalized, re.IGNORECASE):
                return False

        return True

    def _categorize_skill(self, skill: str, context: str) -> str:
        """
        Categorize skill as technical, domain, or soft.

        Per PRD.md Section 8.3:
        - Technical (70%): Programming, frameworks, tools
        - Domain (20%): Industry-specific knowledge
        - Soft (10%): Communication, leadership, teamwork
        """
        combined_text = f"{skill} {context}".lower()

        # Check for soft skills first
        for pattern in self._soft_patterns_compiled:
            if pattern.search(combined_text):
                return SkillCategory.SOFT.value

        # Check for technical skills
        for pattern in self._tech_patterns_compiled:
            if pattern.search(combined_text):
                return SkillCategory.TECHNICAL.value

        # Default to domain (industry-specific)
        return SkillCategory.DOMAIN.value

    def _deduplicate_skills(self, skills: List[Dict]) -> List[Dict]:
        """Remove duplicate skills, keeping highest confidence version."""
        seen = {}

        for skill in skills:
            normalized = skill['normalized']
            if normalized not in seen:
                seen[normalized] = skill
            elif skill['confidence'] > seen[normalized]['confidence']:
                seen[normalized] = skill

        return list(seen.values())

    def estimate_proficiency(self, skill: str, full_text: str) -> int:
        """
        Estimate proficiency level (1-5) based on context.

        Levels:
        5 - Expert: "expert", "advanced", "extensive", "10+ years"
        4 - Proficient: "proficient", "strong", "5+ years"
        3 - Intermediate: "intermediate", "familiar", "2+ years"
        2 - Beginner: "basic", "beginner", "learning"
        1 - Novice: "exposure", "awareness"
        """
        skill_lower = skill.lower()
        text_lower = full_text.lower()

        # Find sentences mentioning this skill
        sentences = [s for s in full_text.split('.') if skill_lower in s.lower()]
        context = ' '.join(sentences).lower()

        # Expert indicators (Level 5)
        expert_patterns = [
            r'\b(expert|mastery|extensive|advanced)\b',
            r'\b(architect|principal|senior\s*staff|lead)\b',
            r'\b(8|9|10|\d{2})\+?\s*years?\b',
        ]
        for pattern in expert_patterns:
            if re.search(pattern, context):
                return 5

        # Proficient indicators (Level 4)
        proficient_patterns = [
            r'\b(proficient|strong|solid|deep)\b',
            r'\b(senior|lead|specialist)\b',
            r'\b(4|5|6|7)\+?\s*years?\b',
        ]
        for pattern in proficient_patterns:
            if re.search(pattern, context):
                return 4

        # Intermediate indicators (Level 3)
        intermediate_patterns = [
            r'\b(intermediate|familiar|comfortable|good)\b',
            r'\b(mid[\s-]?level|experienced)\b',
            r'\b(2|3)\+?\s*years?\b',
        ]
        for pattern in intermediate_patterns:
            if re.search(pattern, context):
                return 3

        # Beginner indicators (Level 2)
        beginner_patterns = [
            r'\b(basic|beginner|learning|developing)\b',
            r'\b(junior|entry[\s-]?level|associate)\b',
            r'\b(1|one)\+?\s*years?\b',
            r'\b(recently\s*(learned|started))\b',
        ]
        for pattern in beginner_patterns:
            if re.search(pattern, context):
                return 2

        # Novice indicators (Level 1)
        novice_patterns = [
            r'\b(exposure|awareness|introduction)\b',
            r'\b(familiar\s*with\s*concepts?)\b',
            r'\b(coursework|academic|student)\b',
        ]
        for pattern in novice_patterns:
            if re.search(pattern, context):
                return 1

        # Default to intermediate
        return 3

    def extract_job_skills(self, description: str, requirements: str = '') -> List[Dict]:
        """
        Extract skills from job description and requirements.

        Also determines importance level:
        - required: Must have
        - preferred: Nice to have
        - nice_to_have: Bonus

        Args:
            description: Job description text
            requirements: Job requirements text

        Returns:
            List of skill dicts with 'importance' field added
        """
        all_skills = []

        # Extract from description (lower importance)
        if description:
            desc_skills = self.extract_skills(description, 'description')
            for skill in desc_skills:
                skill['importance'] = 'preferred'
            all_skills.extend(desc_skills)

        # Extract from requirements (higher importance)
        if requirements:
            req_skills = self.extract_skills(requirements, 'requirements')
            for skill in req_skills:
                skill['importance'] = self._determine_importance(
                    skill['skill'],
                    requirements
                )
            all_skills.extend(req_skills)

        # Deduplicate, preferring higher importance
        return self._deduplicate_job_skills(all_skills)

    def _determine_importance(self, skill: str, text: str) -> str:
        """
        Determine if skill is required, preferred, or nice-to-have.

        Analyzes context around the skill mention.
        """
        text_lower = text.lower()
        skill_lower = skill.lower()

        # Find context around the skill
        idx = text_lower.find(skill_lower)
        if idx == -1:
            return 'preferred'

        # Get 80 chars before and after
        start = max(0, idx - 80)
        end = min(len(text_lower), idx + len(skill) + 80)
        context = text_lower[start:end]

        # Required indicators
        required_patterns = [
            r'\b(must\s*have|required|essential|mandatory|need)\b',
            r'\b(minimum|at\s*least|necessary)\b',
            r'\b(strong\s*background|proven\s*experience)\b',
        ]
        for pattern in required_patterns:
            if re.search(pattern, context):
                return 'required'

        # Nice-to-have indicators
        nice_patterns = [
            r'\b(nice\s*to\s*have|bonus|optional|plus)\b',
            r'\b(familiarity|awareness|exposure)\b',
            r'\b(would\s*be\s*a?\s*plus)\b',
        ]
        for pattern in nice_patterns:
            if re.search(pattern, context):
                return 'nice_to_have'

        # Preferred indicators
        preferred_patterns = [
            r'\b(preferred|desired|ideally|advantage)\b',
            r'\b(experience\s*with|knowledge\s*of)\b',
        ]
        for pattern in preferred_patterns:
            if re.search(pattern, context):
                return 'preferred'

        # Default to required for requirements section
        return 'required'

    def _deduplicate_job_skills(self, skills: List[Dict]) -> List[Dict]:
        """Deduplicate job skills, keeping highest importance version."""
        importance_order = {'required': 3, 'preferred': 2, 'nice_to_have': 1}
        seen = {}

        for skill in skills:
            normalized = skill['normalized']
            if normalized not in seen:
                seen[normalized] = skill
            else:
                # Keep higher importance
                current_importance = importance_order.get(seen[normalized].get('importance', 'preferred'), 2)
                new_importance = importance_order.get(skill.get('importance', 'preferred'), 2)
                if new_importance > current_importance:
                    seen[normalized] = skill

        return list(seen.values())

    def calculate_skill_match_score(
        self,
        candidate_skills: List[Dict],
        job_skills: List[Dict]
    ) -> Tuple[float, List[Dict], List[Dict]]:
        """
        Calculate skill match score between candidate and job.

        Uses weighted scoring per PRD.md:
        Skills Score = (0.70 × Technical) + (0.20 × Domain) + (0.10 × Soft)

        Args:
            candidate_skills: Skills extracted from candidate resume
            job_skills: Skills extracted from job description

        Returns:
            Tuple of (score 0-100, matched_skills, missing_skills)
        """
        if not job_skills:
            return 50.0, [], []

        from difflib import SequenceMatcher

        # Category weights
        category_weights = {
            'technical': 0.70,
            'domain': 0.20,
            'soft': 0.10
        }

        # Importance weights
        importance_weights = {
            'required': 3.0,
            'preferred': 2.0,
            'nice_to_have': 1.0
        }

        matched = []
        missing = []

        # Build candidate skills lookup
        candidate_normalized = {s['normalized']: s for s in candidate_skills}

        # Calculate weighted scores
        total_weight = 0.0
        matched_weight = 0.0

        for job_skill in job_skills:
            job_norm = job_skill['normalized']
            category = job_skill.get('category', 'domain')
            importance = job_skill.get('importance', 'required')

            # Calculate weight for this skill
            cat_weight = category_weights.get(category, 0.20)
            imp_weight = importance_weights.get(importance, 2.0)
            skill_weight = cat_weight * imp_weight

            total_weight += skill_weight

            # Check for match (fuzzy)
            found = False
            matched_skill = None

            for cand_norm, cand_skill in candidate_normalized.items():
                # Fuzzy match with 0.8 threshold
                similarity = SequenceMatcher(None, job_norm, cand_norm).ratio()
                if similarity >= 0.80:
                    found = True
                    matched_skill = cand_skill
                    break

            if found:
                matched_weight += skill_weight
                matched.append({
                    'job_skill': job_skill['skill'],
                    'candidate_skill': matched_skill['skill'],
                    'category': category,
                    'importance': importance
                })
            else:
                missing.append({
                    'skill': job_skill['skill'],
                    'category': category,
                    'importance': importance
                })

        # Calculate final score
        score = (matched_weight / total_weight * 100) if total_weight > 0 else 50.0

        return score, matched, missing
