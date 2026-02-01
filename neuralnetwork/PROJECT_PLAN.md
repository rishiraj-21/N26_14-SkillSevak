# SkillSevak - Project Implementation Plan
## Phase-wise Development Roadmap

> **Project Status:** Early MVP with UI/Auth complete, AI/ML pipeline NOT started
> **Last Updated:** January 2026

---

## Current State Summary

### What's Already Built

| Component | Status | Details |
|-----------|--------|---------|
| Django Setup | DONE | Django 5.2, SQLite, proper project structure |
| Authentication | DONE | Email-based login, separate candidate/recruiter registration |
| Database Models | DONE | User, CandidateProfile, CompanyProfile, Job, Application |
| Job Management | DONE | Create, edit, list, filter, search jobs |
| Applications | DONE | Apply to jobs, track status (applied/reviewed/interview/rejected/hired) |
| UI/Templates | DONE | 22 Tailwind CSS templates, responsive design |
| Recruiter Dashboard | PARTIAL | Views exist but analytics/pipeline not functional |

### What's Missing (Critical for SkillSevak Vision)

| Component | Status | Priority |
|-----------|--------|----------|
| Resume Parsing | NOT STARTED | HIGH |
| Skill Extraction (NLP) | NOT STARTED | HIGH |
| Semantic Embeddings | NOT STARTED | HIGH |
| Match Scoring Algorithm | NOT STARTED | HIGH |
| ANN Model Training | NOT STARTED | HIGH |
| Background Tasks (Celery) | NOT STARTED | MEDIUM |
| Real-time Recommendations | NOT STARTED | MEDIUM |
| Email Notifications | NOT STARTED | MEDIUM |
| Tests | NOT STARTED | MEDIUM |

---

## Phase-wise Implementation Plan

```
Phase 1: Foundation Fixes      (Week 1)     - Fix critical gaps, add requirements
Phase 2: Resume Processing     (Week 2-3)   - Parse PDFs, extract text
Phase 3: Dynamic Skill Extract (Week 3-4)   - NLP-based skill extraction
Phase 4: Semantic Matching     (Week 5-6)   - Embeddings + similarity
Phase 5: ANN Integration       (Week 7-8)   - Train model, integrate
Phase 6: Real-time Pipeline    (Week 9-10)  - Celery, caching, async
Phase 7: Recommendations       (Week 11-12) - Skill gaps, suggestions
Phase 8: Polish & Deploy       (Week 13-14) - Testing, production
```

---

## PHASE 1: Foundation Fixes (Week 1)

### Goal
Stabilize the existing codebase and prepare for AI/ML integration.

### Tasks

#### 1.1 Create Requirements File
```
File: requirements.txt

# Core
Django==5.2
python-decouple==3.8
gunicorn==21.2.0

# Database
psycopg2-binary==2.9.9

# ML/NLP
spacy==3.7.2
sentence-transformers==2.2.2
torch==2.1.0
scikit-learn==1.3.2

# Resume Parsing
pdfplumber==0.10.3
python-docx==1.1.0

# Background Tasks
celery==5.3.4
redis==5.0.1

# Utilities
numpy==1.26.2
pandas==2.1.3
```

#### 1.2 Fix Security Issues
- [ ] Move SECRET_KEY to environment variable
- [ ] Set DEBUG=False for production
- [ ] Configure ALLOWED_HOSTS
- [ ] Add django-cors-headers

#### 1.3 Add Missing Models
```python
# ann/models.py - ADD these new models

class ParsedResume(models.Model):
    """Stores extracted resume data"""
    candidate = models.OneToOneField(CandidateProfile, on_delete=models.CASCADE)
    raw_text = models.TextField(blank=True)
    cleaned_text = models.TextField(blank=True)
    sections_json = models.JSONField(default=dict)  # {"skills": "...", "experience": "..."}
    embedding = models.BinaryField(null=True)  # Store as binary, decode when needed
    parsing_status = models.CharField(max_length=20, default='pending')
    parsed_at = models.DateTimeField(null=True)

class CandidateSkill(models.Model):
    """Dynamically extracted skills - NO HARDCODING"""
    candidate = models.ForeignKey(CandidateProfile, on_delete=models.CASCADE, related_name='extracted_skills')
    skill_text = models.CharField(max_length=200)  # Original text: "Machine Learning"
    normalized_text = models.CharField(max_length=200)  # Lowercase: "machine learning"
    proficiency_level = models.IntegerField(default=3)  # 1-5 scale
    source = models.CharField(max_length=50)  # 'skills_section', 'experience', 'projects'
    context = models.TextField(blank=True)  # Sentence where found
    confidence_score = models.FloatField(default=0.8)

class JobSkill(models.Model):
    """Skills extracted from job descriptions"""
    job = models.ForeignKey(Job, on_delete=models.CASCADE, related_name='extracted_skills')
    skill_text = models.CharField(max_length=200)
    normalized_text = models.CharField(max_length=200)
    importance = models.CharField(max_length=20, default='required')  # required/preferred/nice_to_have

class MatchScore(models.Model):
    """Pre-computed match scores between candidates and jobs"""
    candidate = models.ForeignKey(CandidateProfile, on_delete=models.CASCADE)
    job = models.ForeignKey(Job, on_delete=models.CASCADE)
    overall_score = models.FloatField()  # 0-100
    semantic_similarity = models.FloatField()
    skill_match_score = models.FloatField()
    experience_match_score = models.FloatField()
    matched_skills = models.JSONField(default=list)
    missing_skills = models.JSONField(default=list)
    suggestions = models.JSONField(default=list)
    calculated_at = models.DateTimeField(auto_now=True)
    is_valid = models.BooleanField(default=True)

    class Meta:
        unique_together = ['candidate', 'job']
```

#### 1.4 Create Services Directory Structure
```
ann/
├── services/
│   ├── __init__.py
│   ├── resume_parser.py      # PDF/DOCX text extraction
│   ├── skill_extractor.py    # NLP-based skill extraction
│   ├── embedding_service.py  # Generate semantic embeddings
│   ├── matching_engine.py    # Calculate match scores
│   └── recommendations.py    # Generate suggestions
├── ml/
│   ├── __init__.py
│   ├── model.py              # ANN model definition
│   ├── train.py              # Training pipeline
│   └── inference.py          # Prediction service
└── tasks.py                  # Celery async tasks
```

### Deliverables
- [ ] requirements.txt created
- [ ] Security settings fixed
- [ ] New models added and migrated
- [ ] Service directory structure created
- [ ] Git commit: "Phase 1: Foundation fixes"

---

## PHASE 2: Resume Processing (Week 2-3)

### Goal
Extract text from uploaded PDF/DOCX resumes and store structured data.

### Tasks

#### 2.1 Resume Parser Service
```python
# ann/services/resume_parser.py

import pdfplumber
from docx import Document
import re

class ResumeParser:
    """
    Extract text from PDF/DOCX resumes.
    Phase 2 focuses on text extraction only.
    """

    def extract_text(self, file_path: str) -> str:
        """Main entry point for text extraction."""
        if file_path.lower().endswith('.pdf'):
            return self._extract_pdf(file_path)
        elif file_path.lower().endswith('.docx'):
            return self._extract_docx(file_path)
        else:
            raise ValueError(f"Unsupported file type: {file_path}")

    def _extract_pdf(self, path: str) -> str:
        """Extract text from PDF using pdfplumber."""
        text = ""
        with pdfplumber.open(path) as pdf:
            for page in pdf.pages:
                page_text = page.extract_text()
                if page_text:
                    text += page_text + "\n"
        return text

    def _extract_docx(self, path: str) -> str:
        """Extract text from DOCX."""
        doc = Document(path)
        text = ""
        for para in doc.paragraphs:
            text += para.text + "\n"
        return text

    def clean_text(self, text: str) -> str:
        """Clean and normalize extracted text."""
        # Remove extra whitespace
        text = re.sub(r'\s+', ' ', text)
        # Remove special characters but keep punctuation
        text = re.sub(r'[^\w\s.,;:!?@#$%&*()\-+=/]', '', text)
        return text.strip()

    def detect_sections(self, text: str) -> dict:
        """Detect resume sections using keyword matching."""
        sections = {
            'contact': '',
            'summary': '',
            'skills': '',
            'experience': '',
            'education': '',
            'projects': '',
            'certifications': ''
        }

        # Section headers to look for
        section_patterns = {
            'summary': r'(?i)(summary|objective|profile|about)',
            'skills': r'(?i)(skills|technical skills|technologies|expertise)',
            'experience': r'(?i)(experience|work history|employment)',
            'education': r'(?i)(education|academic|qualification)',
            'projects': r'(?i)(projects|portfolio)',
            'certifications': r'(?i)(certifications|certificates|licenses)'
        }

        # Split by common section patterns
        lines = text.split('\n')
        current_section = 'contact'

        for line in lines:
            for section, pattern in section_patterns.items():
                if re.search(pattern, line):
                    current_section = section
                    break
            sections[current_section] += line + '\n'

        return sections
```

#### 2.2 Update Resume Upload View
```python
# ann/views.py - UPDATE upload_resume function

from ann.services.resume_parser import ResumeParser
from ann.models import ParsedResume

@csrf_exempt
@login_required
def upload_resume(request):
    if request.method == 'POST' and request.FILES.get('resume'):
        resume_file = request.FILES['resume']

        # Validate file type
        allowed_types = ['.pdf', '.docx']
        ext = os.path.splitext(resume_file.name)[1].lower()
        if ext not in allowed_types:
            return JsonResponse({'error': 'Only PDF and DOCX files allowed'}, status=400)

        # Validate file size (max 5MB)
        if resume_file.size > 5 * 1024 * 1024:
            return JsonResponse({'error': 'File size must be under 5MB'}, status=400)

        # Save file
        candidate = request.user.candidateprofile
        candidate.resume_file = resume_file
        candidate.save()

        # Trigger async parsing (Phase 6) or sync parsing (now)
        try:
            parser = ResumeParser()
            file_path = candidate.resume_file.path

            # Extract and clean text
            raw_text = parser.extract_text(file_path)
            cleaned_text = parser.clean_text(raw_text)
            sections = parser.detect_sections(raw_text)

            # Store parsed data
            parsed_resume, created = ParsedResume.objects.update_or_create(
                candidate=candidate,
                defaults={
                    'raw_text': raw_text,
                    'cleaned_text': cleaned_text,
                    'sections_json': sections,
                    'parsing_status': 'completed',
                    'parsed_at': timezone.now()
                }
            )

            return JsonResponse({
                'message': 'Resume uploaded and parsed successfully',
                'sections_found': list(k for k, v in sections.items() if v.strip())
            })

        except Exception as e:
            return JsonResponse({'error': f'Parsing failed: {str(e)}'}, status=500)

    return JsonResponse({'error': 'No file provided'}, status=400)
```

#### 2.3 Download spaCy Model
```bash
# Add to setup instructions
python -m spacy download en_core_web_sm
```

### Deliverables
- [ ] ResumeParser service created
- [ ] PDF extraction working
- [ ] DOCX extraction working
- [ ] Section detection implemented
- [ ] ParsedResume model populated on upload
- [ ] Git commit: "Phase 2: Resume text extraction"

---

## PHASE 3: Dynamic Skill Extraction (Week 3-4)

### Goal
Extract skills from resume text using NLP - NO HARDCODED SKILL DICTIONARY.

### Why Dynamic Extraction?
```
Hardcoded: skills = ["Python", "Java", "React"...]
├── Only works for predefined industries
├── Misses "Patent Law", "Sous Chef", "SEO Marketing"
└── Requires constant manual updates

Dynamic (SkillSevak):
├── NLP extracts skills from ANY text
├── Works for tech, law, healthcare, hospitality, marketing...
└── Self-improving with more data
```

### Tasks

#### 3.1 Dynamic Skill Extractor
```python
# ann/services/skill_extractor.py

import spacy
from typing import List, Dict, Tuple
import re

class DynamicSkillExtractor:
    """
    Extract skills from text WITHOUT hardcoded dictionary.
    Works for ANY industry by using NLP techniques.
    """

    def __init__(self):
        self.nlp = spacy.load("en_core_web_sm")

        # Minimal stopwords for skill context (not skill dictionary!)
        self.stopwords = {
            'and', 'or', 'the', 'a', 'an', 'in', 'on', 'at', 'to', 'for',
            'with', 'by', 'from', 'as', 'is', 'was', 'are', 'were', 'been',
            'be', 'have', 'has', 'had', 'do', 'does', 'did', 'will', 'would',
            'could', 'should', 'may', 'might', 'must', 'shall', 'can',
            'of', 'that', 'this', 'these', 'those', 'it', 'its'
        }

    def extract_skills(self, text: str, section: str = 'general') -> List[Dict]:
        """
        Extract skills from text using multiple NLP methods.

        Returns list of dicts: [{'skill': 'Python', 'confidence': 0.9, 'source': 'skills'}]
        """
        doc = self.nlp(text)
        skills = []
        seen = set()

        # Method 1: Noun phrases (catches "machine learning", "project management")
        for chunk in doc.noun_chunks:
            skill = self._clean_skill(chunk.text)
            if skill and skill.lower() not in seen and self._is_valid_skill(skill):
                skills.append({
                    'skill': skill,
                    'normalized': skill.lower(),
                    'confidence': 0.7,
                    'source': section,
                    'context': chunk.sent.text[:200]
                })
                seen.add(skill.lower())

        # Method 2: Proper nouns (catches "Python", "Docker", "Salesforce")
        for token in doc:
            if token.pos_ == "PROPN" and len(token.text) > 1:
                skill = token.text
                if skill.lower() not in seen and self._is_valid_skill(skill):
                    skills.append({
                        'skill': skill,
                        'normalized': skill.lower(),
                        'confidence': 0.8,
                        'source': section,
                        'context': token.sent.text[:200] if token.sent else ''
                    })
                    seen.add(skill.lower())

        # Method 3: Named entities (catches organizations, products)
        for ent in doc.ents:
            if ent.label_ in ['ORG', 'PRODUCT', 'WORK_OF_ART']:
                skill = self._clean_skill(ent.text)
                if skill and skill.lower() not in seen and self._is_valid_skill(skill):
                    skills.append({
                        'skill': skill,
                        'normalized': skill.lower(),
                        'confidence': 0.85,
                        'source': section,
                        'context': ent.sent.text[:200] if hasattr(ent, 'sent') else ''
                    })
                    seen.add(skill.lower())

        # Method 4: Pattern-based extraction for skills section
        if section == 'skills':
            pattern_skills = self._extract_from_list_patterns(text)
            for skill in pattern_skills:
                if skill.lower() not in seen:
                    skills.append({
                        'skill': skill,
                        'normalized': skill.lower(),
                        'confidence': 0.9,  # High confidence for skills section
                        'source': section,
                        'context': ''
                    })
                    seen.add(skill.lower())

        return skills

    def _clean_skill(self, text: str) -> str:
        """Clean and normalize skill text."""
        # Remove extra whitespace
        text = ' '.join(text.split())
        # Remove leading/trailing punctuation
        text = text.strip('.,;:!?()[]{}"\'-')
        # Skip if too short or too long
        if len(text) < 2 or len(text) > 50:
            return ''
        return text

    def _is_valid_skill(self, skill: str) -> bool:
        """Check if extracted text is likely a valid skill."""
        # Skip stopwords
        if skill.lower() in self.stopwords:
            return False
        # Skip pure numbers
        if skill.isdigit():
            return False
        # Skip single characters
        if len(skill) < 2:
            return False
        # Skip overly long phrases
        if len(skill.split()) > 5:
            return False
        return True

    def _extract_from_list_patterns(self, text: str) -> List[str]:
        """Extract skills from comma/bullet separated lists."""
        skills = []

        # Split by common delimiters
        delimiters = [',', '•', '|', '/', '\n', ';']
        pattern = '|'.join(map(re.escape, delimiters))
        parts = re.split(pattern, text)

        for part in parts:
            part = part.strip()
            # Skill-like entries are usually 1-4 words
            if 1 <= len(part.split()) <= 4 and len(part) > 1:
                skills.append(self._clean_skill(part))

        return [s for s in skills if s]

    def estimate_proficiency(self, skill: str, full_text: str) -> int:
        """
        Estimate proficiency level (1-5) based on context.

        Looks for: years of experience, adjectives (expert, proficient, basic)
        """
        skill_lower = skill.lower()
        text_lower = full_text.lower()

        # Find sentences mentioning this skill
        sentences = [s for s in full_text.split('.') if skill_lower in s.lower()]

        # Expert indicators
        expert_keywords = ['expert', 'advanced', 'extensive', 'lead', 'architect', 'senior', '5+ years', '10+ years']
        for keyword in expert_keywords:
            if any(keyword in sent.lower() for sent in sentences):
                return 5

        # Proficient indicators
        proficient_keywords = ['proficient', 'experienced', 'strong', '3+ years', '4+ years']
        for keyword in proficient_keywords:
            if any(keyword in sent.lower() for sent in sentences):
                return 4

        # Intermediate indicators
        intermediate_keywords = ['intermediate', 'familiar', '1-2 years', '2+ years']
        for keyword in intermediate_keywords:
            if any(keyword in sent.lower() for sent in sentences):
                return 3

        # Beginner indicators
        beginner_keywords = ['basic', 'beginner', 'learning', 'exposure', 'familiar with']
        for keyword in beginner_keywords:
            if any(keyword in sent.lower() for sent in sentences):
                return 2

        # Default to intermediate
        return 3
```

#### 3.2 Integrate Skill Extraction with Resume Upload
```python
# ann/views.py - UPDATE to include skill extraction

from ann.services.skill_extractor import DynamicSkillExtractor
from ann.models import CandidateSkill

def process_resume_skills(candidate, parsed_resume):
    """Extract and store skills from parsed resume."""
    extractor = DynamicSkillExtractor()

    # Clear old skills
    CandidateSkill.objects.filter(candidate=candidate).delete()

    # Extract from each section
    sections = parsed_resume.sections_json
    all_skills = []

    for section_name, section_text in sections.items():
        if section_text.strip():
            skills = extractor.extract_skills(section_text, section_name)
            all_skills.extend(skills)

    # Also extract from full text
    full_text_skills = extractor.extract_skills(parsed_resume.cleaned_text, 'full_text')
    all_skills.extend(full_text_skills)

    # Deduplicate by normalized text
    seen = set()
    unique_skills = []
    for skill in all_skills:
        if skill['normalized'] not in seen:
            seen.add(skill['normalized'])
            unique_skills.append(skill)

    # Store in database
    for skill_data in unique_skills:
        proficiency = extractor.estimate_proficiency(
            skill_data['skill'],
            parsed_resume.cleaned_text
        )

        CandidateSkill.objects.create(
            candidate=candidate,
            skill_text=skill_data['skill'],
            normalized_text=skill_data['normalized'],
            proficiency_level=proficiency,
            source=skill_data['source'],
            context=skill_data['context'],
            confidence_score=skill_data['confidence']
        )

    return len(unique_skills)
```

#### 3.3 Extract Skills from Job Descriptions
```python
# ann/services/skill_extractor.py - ADD to DynamicSkillExtractor class

def extract_job_requirements(self, description: str, requirements: str) -> List[Dict]:
    """
    Extract skills from job description and requirements.
    Also determines importance level (required/preferred/nice_to_have).
    """
    all_skills = []

    # Extract from description
    desc_skills = self.extract_skills(description, 'description')
    for skill in desc_skills:
        skill['importance'] = 'preferred'
    all_skills.extend(desc_skills)

    # Extract from requirements (higher importance)
    req_skills = self.extract_skills(requirements, 'requirements')
    for skill in req_skills:
        skill['importance'] = self._determine_importance(skill['skill'], requirements)
    all_skills.extend(req_skills)

    # Deduplicate
    seen = set()
    unique = []
    for skill in all_skills:
        if skill['normalized'] not in seen:
            seen.add(skill['normalized'])
            unique.append(skill)

    return unique

def _determine_importance(self, skill: str, text: str) -> str:
    """Determine if skill is required, preferred, or nice-to-have."""
    text_lower = text.lower()
    skill_lower = skill.lower()

    # Find context around the skill
    idx = text_lower.find(skill_lower)
    if idx == -1:
        return 'preferred'

    # Check 50 chars before and after
    context = text_lower[max(0, idx-50):idx+len(skill)+50]

    required_indicators = ['must have', 'required', 'essential', 'mandatory', 'need']
    preferred_indicators = ['preferred', 'desired', 'ideally', 'advantage', 'plus']
    nice_indicators = ['nice to have', 'bonus', 'optional', 'familiarity']

    for indicator in required_indicators:
        if indicator in context:
            return 'required'

    for indicator in nice_indicators:
        if indicator in context:
            return 'nice_to_have'

    for indicator in preferred_indicators:
        if indicator in context:
            return 'preferred'

    return 'required'  # Default to required
```

### Deliverables
- [ ] DynamicSkillExtractor service created
- [ ] Skills extracted from resumes automatically
- [ ] Skills extracted from job descriptions
- [ ] CandidateSkill and JobSkill models populated
- [ ] Proficiency estimation working
- [ ] Git commit: "Phase 3: Dynamic NLP skill extraction"

---

## PHASE 4: Semantic Matching (Week 5-6)

### Goal
Use sentence embeddings to understand meaning, not just keywords.

### Why Semantic Matching?
```
Keyword Matching:
"Built data pipelines" vs "ETL experience" = NO MATCH (different words)

Semantic Matching:
"Built data pipelines" ≈ "ETL experience" = 85% MATCH (similar meaning!)
```

### Tasks

#### 4.1 Embedding Service
```python
# ann/services/embedding_service.py

from sentence_transformers import SentenceTransformer
import numpy as np
from typing import List, Union

class EmbeddingService:
    """
    Generate semantic embeddings for text.
    Uses sentence-transformers for high-quality embeddings.
    """

    _instance = None
    _model = None

    def __new__(cls):
        """Singleton pattern to avoid loading model multiple times."""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        if self._model is None:
            # Load model once
            self._model = SentenceTransformer('all-MiniLM-L6-v2')

    def generate_embedding(self, text: str) -> np.ndarray:
        """Generate embedding for a single text."""
        if not text or not text.strip():
            return np.zeros(384)  # Model outputs 384 dimensions

        embedding = self._model.encode(text, convert_to_numpy=True)
        return embedding

    def generate_embeddings_batch(self, texts: List[str]) -> np.ndarray:
        """Generate embeddings for multiple texts efficiently."""
        texts = [t if t else '' for t in texts]
        embeddings = self._model.encode(texts, convert_to_numpy=True)
        return embeddings

    def serialize_embedding(self, embedding: np.ndarray) -> bytes:
        """Convert embedding to bytes for database storage."""
        return embedding.tobytes()

    def deserialize_embedding(self, data: bytes) -> np.ndarray:
        """Convert bytes back to embedding array."""
        return np.frombuffer(data, dtype=np.float32)
```

#### 4.2 Matching Engine
```python
# ann/services/matching_engine.py

import numpy as np
from sklearn.metrics.pairwise import cosine_similarity
from typing import Dict, List, Tuple
from difflib import SequenceMatcher

from ann.services.embedding_service import EmbeddingService
from ann.models import CandidateProfile, Job, CandidateSkill, JobSkill, ParsedResume, MatchScore

class MatchingEngine:
    """
    Calculate match scores between candidates and jobs.
    Uses multiple factors: semantic similarity, skills, experience, education.
    """

    def __init__(self):
        self.embedding_service = EmbeddingService()

        # MVP weights (fixed) - will be learned by ANN in Phase 5
        self.weights = {
            'semantic': 0.25,      # Overall text similarity
            'skills': 0.35,        # Skill overlap (Technical 70%, Domain 20%, Soft 10%)
            'experience': 0.20,    # Experience match
            'education': 0.10,     # Education relevance
            'profile': 0.10        # Profile completeness
        }

    def calculate_match(self, candidate: CandidateProfile, job: Job) -> Dict:
        """
        Calculate comprehensive match score between candidate and job.

        Returns dict with overall score and breakdown.
        """
        # Get component scores
        semantic_score = self._calculate_semantic_similarity(candidate, job)
        skill_score, matched, missing = self._calculate_skill_match(candidate, job)
        experience_score = self._calculate_experience_match(candidate, job)
        education_score = self._calculate_education_match(candidate, job)
        profile_score = candidate.profile_strength / 100 if candidate.profile_strength else 0.5

        # Weighted combination (MVP formula)
        overall = (
            self.weights['semantic'] * semantic_score +
            self.weights['skills'] * skill_score +
            self.weights['experience'] * experience_score +
            self.weights['education'] * education_score +
            self.weights['profile'] * profile_score
        ) * 100  # Convert to 0-100 scale

        # Generate suggestions
        suggestions = self._generate_suggestions(missing, skill_score, overall)

        return {
            'overall_score': round(overall, 1),
            'breakdown': {
                'semantic_similarity': round(semantic_score * 100, 1),
                'skill_match': round(skill_score * 100, 1),
                'experience_match': round(experience_score * 100, 1),
                'education_match': round(education_score * 100, 1),
                'profile_completeness': round(profile_score * 100, 1)
            },
            'matched_skills': matched,
            'missing_skills': missing,
            'suggestions': suggestions
        }

    def _calculate_semantic_similarity(self, candidate: CandidateProfile, job: Job) -> float:
        """Calculate cosine similarity between resume and job embeddings."""
        try:
            # Get resume text
            parsed_resume = ParsedResume.objects.filter(candidate=candidate).first()
            if not parsed_resume:
                return 0.5  # Default if no resume

            resume_text = parsed_resume.cleaned_text
            job_text = f"{job.title} {job.description} {job.requirements}"

            # Generate embeddings
            resume_emb = self.embedding_service.generate_embedding(resume_text)
            job_emb = self.embedding_service.generate_embedding(job_text)

            # Calculate cosine similarity
            similarity = cosine_similarity(
                resume_emb.reshape(1, -1),
                job_emb.reshape(1, -1)
            )[0][0]

            return max(0, min(1, float(similarity)))

        except Exception as e:
            print(f"Semantic similarity error: {e}")
            return 0.5

    def _calculate_skill_match(self, candidate: CandidateProfile, job: Job) -> Tuple[float, List, List]:
        """
        Calculate skill overlap with fuzzy matching.

        Returns: (score, matched_skills, missing_skills)
        """
        # Get candidate skills
        candidate_skills = list(
            CandidateSkill.objects.filter(candidate=candidate)
            .values_list('normalized_text', flat=True)
        )

        # Get job skills
        job_skills = list(
            JobSkill.objects.filter(job=job)
            .values_list('normalized_text', 'importance')
        )

        if not job_skills:
            # Fallback to skills_required JSON field
            skills_json = job.skills_required
            if isinstance(skills_json, str):
                job_skills = [(s.lower().strip(), 'required') for s in skills_json.split(',')]
            elif isinstance(skills_json, list):
                job_skills = [(s.lower().strip(), 'required') for s in skills_json]
            else:
                return 0.5, [], []

        matched = []
        missing = []

        for job_skill, importance in job_skills:
            found = False
            for cand_skill in candidate_skills:
                # Fuzzy match (0.8 threshold)
                similarity = SequenceMatcher(None, job_skill, cand_skill).ratio()
                if similarity >= 0.8:
                    matched.append({
                        'skill': job_skill,
                        'matched_with': cand_skill,
                        'importance': importance
                    })
                    found = True
                    break

            if not found:
                missing.append({
                    'skill': job_skill,
                    'importance': importance
                })

        # Calculate score (required skills weighted higher)
        total_weight = 0
        matched_weight = 0

        for skill, importance in job_skills:
            weight = 3 if importance == 'required' else (2 if importance == 'preferred' else 1)
            total_weight += weight

            if any(m['skill'] == skill for m in matched):
                matched_weight += weight

        score = matched_weight / total_weight if total_weight > 0 else 0.5

        return score, matched, missing

    def _calculate_experience_match(self, candidate: CandidateProfile, job: Job) -> float:
        """Calculate how well candidate's experience matches job requirements."""
        cand_exp = candidate.experience_years or 0

        # Get job experience requirements
        job_min = job.experience_min if hasattr(job, 'experience_min') and job.experience_min else 0
        job_max = job.experience_max if hasattr(job, 'experience_max') and job.experience_max else 99

        if job_min <= cand_exp <= job_max:
            return 1.0  # Perfect match
        elif cand_exp < job_min:
            # Under-qualified
            gap = job_min - cand_exp
            return max(0, 1 - (gap * 0.15))  # 15% penalty per year short
        else:
            # Over-qualified (slight penalty)
            gap = cand_exp - job_max
            return max(0.7, 1 - (gap * 0.05))  # 5% penalty per year over

    def _calculate_education_match(self, candidate: CandidateProfile, job: Job) -> float:
        """Calculate education relevance (placeholder for V1)."""
        # In MVP, just check if education field is filled
        if hasattr(candidate, 'education_level') and candidate.education_level:
            return 0.8
        return 0.5

    def _generate_suggestions(self, missing_skills: List, skill_score: float, overall: float) -> List[str]:
        """Generate actionable improvement suggestions."""
        suggestions = []

        # Suggest missing required skills
        required_missing = [m for m in missing_skills if m.get('importance') == 'required']
        if required_missing:
            top_3 = required_missing[:3]
            skills_text = ', '.join([s['skill'] for s in top_3])
            suggestions.append(f"Add these required skills to boost your match: {skills_text}")

        # Suggest preferred skills
        preferred_missing = [m for m in missing_skills if m.get('importance') == 'preferred']
        if preferred_missing and len(suggestions) < 3:
            skill = preferred_missing[0]['skill']
            estimated_boost = min(15, (1 - skill_score) * 20)
            suggestions.append(f"Adding '{skill}' could improve your match by ~{int(estimated_boost)}%")

        # General suggestions based on score
        if overall < 50:
            suggestions.append("Consider roles more aligned with your current skill set")
        elif overall < 70:
            suggestions.append("You're a potential match - highlight relevant project experience")
        elif overall >= 85:
            suggestions.append("Strong match! Emphasize your most relevant experience in your application")

        return suggestions[:3]  # Max 3 suggestions

    def calculate_all_matches_for_candidate(self, candidate: CandidateProfile) -> List[Dict]:
        """Calculate match scores for all active jobs."""
        jobs = Job.objects.filter(status='open')
        results = []

        for job in jobs:
            match_data = self.calculate_match(candidate, job)

            # Store in database
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
                    'is_valid': True
                }
            )

            results.append({
                'job_id': job.id,
                'job_title': job.title,
                **match_data
            })

        return sorted(results, key=lambda x: x['overall_score'], reverse=True)
```

#### 4.3 Update Views to Use Real Matching
```python
# ann/views.py - UPDATE candidate_page and recommended_jobs

from ann.services.matching_engine import MatchingEngine

@login_required
def candidate_page(request):
    candidate = request.user.candidateprofile

    # Calculate matches for all jobs
    engine = MatchingEngine()
    matches = engine.calculate_all_matches_for_candidate(candidate)

    # Get filter parameter
    sort_by = request.GET.get('sort', 'match')

    # Sort jobs by match score
    job_ids = [m['job_id'] for m in matches]
    jobs = Job.objects.filter(id__in=job_ids, status='open')

    # Create a mapping of job_id to match score
    match_map = {m['job_id']: m for m in matches}

    # Add match data to jobs
    jobs_with_matches = []
    for job in jobs:
        job.match_data = match_map.get(job.id, {})
        job.match_score = job.match_data.get('overall_score', 0)
        jobs_with_matches.append(job)

    # Sort based on filter
    if sort_by == 'match':
        jobs_with_matches.sort(key=lambda x: x.match_score, reverse=True)
    elif sort_by == 'newest':
        jobs_with_matches.sort(key=lambda x: x.posted_at, reverse=True)
    elif sort_by == 'salary':
        jobs_with_matches.sort(key=lambda x: x.salary_max or 0, reverse=True)

    context = {
        'jobs': jobs_with_matches,
        'candidate': candidate,
        'total_matches': len([j for j in jobs_with_matches if j.match_score >= 70]),
    }
    return render(request, 'candidate.html', context)
```

### Deliverables
- [ ] EmbeddingService created with sentence-transformers
- [ ] MatchingEngine with semantic + skill + experience scoring
- [ ] Fuzzy skill matching implemented
- [ ] MatchScore model populated
- [ ] Improvement suggestions generated
- [ ] Views updated to show real match scores
- [ ] Git commit: "Phase 4: Semantic matching engine"

---

## PHASE 5: ANN Model Integration (Week 7-8)

### Goal
Train a neural network to learn optimal matching weights from data.

### Why ANN?
```
MVP (Fixed Weights):
Match = 0.25×Semantic + 0.35×Skills + 0.20×Experience + 0.10×Education + 0.10×Profile

Skills Score = 0.70×Technical + 0.20×Domain + 0.10×Soft Skills

ANN (Learned Weights):
Match = ANN([semantic, skills, experience, education, profile])
        ↓
    Learns that for "Software Engineer" jobs, skills matter more (0.45)
    Learns that for "Manager" jobs, experience matters more (0.35)
```

### Tasks

#### 5.1 ANN Model Definition
```python
# ann/ml/model.py

import torch
import torch.nn as nn
import numpy as np

class MatchPredictor(nn.Module):
    """
    Neural network to predict match scores.

    Input:  5 features (semantic, skill, experience, education, profile)
    Hidden: 64 → 32 → 16 (with ReLU activation)
    Output: Match probability (0-1, scaled to 0-100)
    """

    def __init__(self, input_size=5):
        super().__init__()

        self.network = nn.Sequential(
            nn.Linear(input_size, 64),
            nn.ReLU(),
            nn.BatchNorm1d(64),
            nn.Dropout(0.3),

            nn.Linear(64, 32),
            nn.ReLU(),
            nn.BatchNorm1d(32),
            nn.Dropout(0.2),

            nn.Linear(32, 16),
            nn.ReLU(),

            nn.Linear(16, 1),
            nn.Sigmoid()
        )

    def forward(self, x):
        """Forward pass returns match probability 0-1."""
        return self.network(x)

    def predict(self, features: np.ndarray) -> float:
        """
        Predict match score for a single candidate-job pair.

        Args:
            features: [semantic, skill, experience, education, profile] (0-1 scaled)

        Returns:
            Match score 0-100
        """
        self.eval()
        with torch.no_grad():
            x = torch.FloatTensor(features).unsqueeze(0)
            output = self.forward(x)
            return float(output.item() * 100)
```

#### 5.2 Training Pipeline
```python
# ann/ml/train.py

import torch
import torch.nn as nn
from torch.utils.data import DataLoader, TensorDataset
import numpy as np
from sklearn.model_selection import train_test_split

from ann.ml.model import MatchPredictor

class ModelTrainer:
    """Train the match prediction model."""

    def __init__(self, model_path='ann/ml/weights/match_predictor.pth'):
        self.model = MatchPredictor()
        self.model_path = model_path
        self.criterion = nn.MSELoss()
        self.optimizer = torch.optim.Adam(self.model.parameters(), lr=0.001)

    def generate_synthetic_data(self, n_samples=10000):
        """
        Generate synthetic training data.

        In production, this would be replaced with real recruiter feedback:
        - Hired candidates = high match (0.8-1.0)
        - Rejected candidates = low match (0.0-0.4)
        - Shortlisted = medium match (0.5-0.8)
        """
        np.random.seed(42)

        X = []
        y = []

        for _ in range(n_samples):
            # Generate random feature values (0-1)
            semantic = np.random.uniform(0.3, 1.0)
            skill = np.random.uniform(0.2, 1.0)
            experience = np.random.uniform(0.3, 1.0)
            education = np.random.uniform(0.4, 1.0)
            profile = np.random.uniform(0.5, 1.0)

            # Synthetic "ground truth" based on weighted combination
            # with some noise to simulate real hiring decisions
            true_match = (
                0.25 * semantic +
                0.40 * skill +      # Skills weighted higher
                0.20 * experience +
                0.08 * education +
                0.07 * profile +
                np.random.normal(0, 0.05)  # Noise
            )
            true_match = np.clip(true_match, 0, 1)

            X.append([semantic, skill, experience, education, profile])
            y.append(true_match)

        return np.array(X), np.array(y)

    def train(self, X=None, y=None, epochs=100, batch_size=64):
        """Train the model."""
        if X is None or y is None:
            X, y = self.generate_synthetic_data()

        # Split data
        X_train, X_val, y_train, y_val = train_test_split(
            X, y, test_size=0.2, random_state=42
        )

        # Create dataloaders
        train_dataset = TensorDataset(
            torch.FloatTensor(X_train),
            torch.FloatTensor(y_train).unsqueeze(1)
        )
        train_loader = DataLoader(train_dataset, batch_size=batch_size, shuffle=True)

        val_dataset = TensorDataset(
            torch.FloatTensor(X_val),
            torch.FloatTensor(y_val).unsqueeze(1)
        )
        val_loader = DataLoader(val_dataset, batch_size=batch_size)

        best_val_loss = float('inf')

        for epoch in range(epochs):
            # Training
            self.model.train()
            train_loss = 0
            for X_batch, y_batch in train_loader:
                self.optimizer.zero_grad()
                outputs = self.model(X_batch)
                loss = self.criterion(outputs, y_batch)
                loss.backward()
                self.optimizer.step()
                train_loss += loss.item()

            # Validation
            self.model.eval()
            val_loss = 0
            with torch.no_grad():
                for X_batch, y_batch in val_loader:
                    outputs = self.model(X_batch)
                    val_loss += self.criterion(outputs, y_batch).item()

            train_loss /= len(train_loader)
            val_loss /= len(val_loader)

            # Save best model
            if val_loss < best_val_loss:
                best_val_loss = val_loss
                self.save_model()

            if (epoch + 1) % 10 == 0:
                print(f"Epoch {epoch+1}/{epochs} - Train Loss: {train_loss:.4f}, Val Loss: {val_loss:.4f}")

        return best_val_loss

    def save_model(self):
        """Save model weights."""
        import os
        os.makedirs(os.path.dirname(self.model_path), exist_ok=True)
        torch.save(self.model.state_dict(), self.model_path)

    def load_model(self):
        """Load model weights."""
        self.model.load_state_dict(torch.load(self.model_path))
        return self.model
```

#### 5.3 Inference Service
```python
# ann/ml/inference.py

import torch
import numpy as np
from pathlib import Path

from ann.ml.model import MatchPredictor

class MatchPredictorService:
    """Service for making match predictions."""

    _instance = None
    _model = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        if self._model is None:
            self._model = MatchPredictor()
            self._load_weights()

    def _load_weights(self):
        """Load trained weights if available."""
        weight_path = Path('ann/ml/weights/match_predictor.pth')
        if weight_path.exists():
            self._model.load_state_dict(torch.load(weight_path))
            self._model.eval()
            self._using_trained = True
        else:
            self._using_trained = False

    def predict(self, features: dict) -> float:
        """
        Predict match score.

        Args:
            features: {
                'semantic_similarity': 0.82,
                'skill_match': 0.75,
                'experience_match': 0.90,
                'education_match': 0.70,
                'profile_completeness': 0.85
            }

        Returns:
            Match score 0-100
        """
        feature_array = np.array([
            features.get('semantic_similarity', 0.5) / 100,  # Normalize to 0-1
            features.get('skill_match', 0.5) / 100,
            features.get('experience_match', 0.5) / 100,
            features.get('education_match', 0.5) / 100,
            features.get('profile_completeness', 0.5) / 100
        ])

        if self._using_trained:
            return self._model.predict(feature_array)
        else:
            # Fallback to weighted average if no trained model
            return self._weighted_average(feature_array)

    def _weighted_average(self, features: np.ndarray) -> float:
        """Fallback calculation using fixed weights per PRD.md."""
        # semantic=0.25, skills=0.35, experience=0.20, education=0.10, profile=0.10
        weights = np.array([0.25, 0.35, 0.20, 0.10, 0.10])
        return float(np.dot(features, weights) * 100)
```

#### 5.4 Management Command for Training
```python
# ann/management/commands/train_model.py

from django.core.management.base import BaseCommand
from ann.ml.train import ModelTrainer

class Command(BaseCommand):
    help = 'Train the match prediction model'

    def add_arguments(self, parser):
        parser.add_argument('--epochs', type=int, default=100)
        parser.add_argument('--samples', type=int, default=10000)

    def handle(self, *args, **options):
        self.stdout.write('Starting model training...')

        trainer = ModelTrainer()
        X, y = trainer.generate_synthetic_data(options['samples'])

        best_loss = trainer.train(X, y, epochs=options['epochs'])

        self.stdout.write(
            self.style.SUCCESS(f'Training complete. Best validation loss: {best_loss:.4f}')
        )
```

### Deliverables
- [ ] MatchPredictor neural network defined
- [ ] ModelTrainer with synthetic data generation
- [ ] Training pipeline working
- [ ] Model weights saved and loaded
- [ ] MatchPredictorService singleton created
- [ ] Management command for training
- [ ] MatchingEngine updated to use ANN predictions
- [ ] Git commit: "Phase 5: ANN model integration"

---

## PHASE 6: Real-time Pipeline (Week 9-10)

### Goal
Make resume processing and matching async with Celery for better UX.

### Tasks

#### 6.1 Celery Configuration
```python
# neuralnetwork/celery.py

import os
from celery import Celery

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'neuralnetwork.settings')

app = Celery('skillsevak')
app.config_from_object('django.conf:settings', namespace='CELERY')
app.autodiscover_tasks()
```

```python
# neuralnetwork/settings.py - ADD

# Celery Configuration
CELERY_BROKER_URL = 'redis://localhost:6379/0'
CELERY_RESULT_BACKEND = 'redis://localhost:6379/0'
CELERY_ACCEPT_CONTENT = ['json']
CELERY_TASK_SERIALIZER = 'json'
CELERY_RESULT_SERIALIZER = 'json'
```

#### 6.2 Async Tasks
```python
# ann/tasks.py

from celery import shared_task
from django.core.cache import cache

@shared_task
def process_resume_async(candidate_id: int):
    """
    Async task to process resume after upload.

    Steps:
    1. Extract text from PDF/DOCX
    2. Extract skills using NLP
    3. Generate embeddings
    4. Calculate matches for all jobs
    """
    from ann.models import CandidateProfile, ParsedResume
    from ann.services.resume_parser import ResumeParser
    from ann.services.skill_extractor import DynamicSkillExtractor
    from ann.services.embedding_service import EmbeddingService
    from ann.services.matching_engine import MatchingEngine

    candidate = CandidateProfile.objects.get(id=candidate_id)

    # Update status
    ParsedResume.objects.update_or_create(
        candidate=candidate,
        defaults={'parsing_status': 'processing'}
    )

    try:
        # 1. Parse resume
        parser = ResumeParser()
        file_path = candidate.resume_file.path
        raw_text = parser.extract_text(file_path)
        cleaned_text = parser.clean_text(raw_text)
        sections = parser.detect_sections(raw_text)

        # 2. Extract skills
        extractor = DynamicSkillExtractor()
        # ... skill extraction logic ...

        # 3. Generate embedding
        embedding_service = EmbeddingService()
        embedding = embedding_service.generate_embedding(cleaned_text)

        # 4. Save parsed resume
        parsed_resume, _ = ParsedResume.objects.update_or_create(
            candidate=candidate,
            defaults={
                'raw_text': raw_text,
                'cleaned_text': cleaned_text,
                'sections_json': sections,
                'embedding': embedding_service.serialize_embedding(embedding),
                'parsing_status': 'completed'
            }
        )

        # 5. Calculate all matches
        engine = MatchingEngine()
        matches = engine.calculate_all_matches_for_candidate(candidate)

        # 6. Cache results
        cache.set(f'matches:{candidate_id}', matches, timeout=3600)

        return {'status': 'success', 'matches_calculated': len(matches)}

    except Exception as e:
        ParsedResume.objects.filter(candidate=candidate).update(
            parsing_status='failed'
        )
        return {'status': 'error', 'message': str(e)}


@shared_task
def recalculate_matches_for_job(job_id: int):
    """Recalculate all candidate matches when a job is created/updated."""
    from ann.models import Job, CandidateProfile
    from ann.services.matching_engine import MatchingEngine

    job = Job.objects.get(id=job_id)
    candidates = CandidateProfile.objects.filter(resume_file__isnull=False)

    engine = MatchingEngine()

    for candidate in candidates:
        match_data = engine.calculate_match(candidate, job)
        # Store match score...

    return {'status': 'success', 'candidates_processed': candidates.count()}
```

#### 6.3 Update Views for Async
```python
# ann/views.py - UPDATE upload_resume

@csrf_exempt
@login_required
def upload_resume(request):
    if request.method == 'POST' and request.FILES.get('resume'):
        # ... validation ...

        # Save file
        candidate = request.user.candidateprofile
        candidate.resume_file = resume_file
        candidate.save()

        # Trigger async processing
        from ann.tasks import process_resume_async
        task = process_resume_async.delay(candidate.id)

        return JsonResponse({
            'message': 'Resume uploaded. Processing in background.',
            'task_id': task.id,
            'status_url': f'/api/resume-status/{task.id}/'
        })
```

### Deliverables
- [ ] Celery configured with Redis
- [ ] process_resume_async task created
- [ ] recalculate_matches_for_job task created
- [ ] Views updated for async processing
- [ ] Status endpoint for checking task progress
- [ ] docker-compose.yml with Redis
- [ ] Git commit: "Phase 6: Celery async pipeline"

---

## PHASE 7: Recommendations & Polish (Week 11-12)

### Goal
Add skill gap analysis, improvement suggestions, and UI polish.

### Tasks

#### 7.1 Recommendation Service
```python
# ann/services/recommendations.py

class RecommendationService:
    """Generate personalized recommendations for candidates."""

    def get_skill_gaps(self, candidate, job) -> dict:
        """Analyze skill gaps and suggest improvements."""
        # ... implementation ...
        return {
            'missing_required': ['Docker', 'Kubernetes'],
            'missing_preferred': ['GraphQL'],
            'improvement_potential': 12,  # percentage points
            'suggested_courses': [
                {'skill': 'Docker', 'resource': 'Docker Mastery on Udemy'},
                {'skill': 'Kubernetes', 'resource': 'K8s The Hard Way'}
            ]
        }

    def get_career_insights(self, candidate) -> dict:
        """Suggest career paths based on current skills."""
        # ... implementation ...
        pass
```

#### 7.2 UI Enhancements
- [ ] Match score breakdown visualization (pie chart)
- [ ] Skill gap cards with improvement suggestions
- [ ] Before/after match simulation ("Add X skill → +Y%")
- [ ] Email notification templates
- [ ] Recruiter analytics with real data

### Deliverables
- [ ] RecommendationService created
- [ ] Skill gap UI components
- [ ] Match breakdown visualization
- [ ] Email templates functional
- [ ] Git commit: "Phase 7: Recommendations and UI polish"

---

## PHASE 8: Testing & Deployment (Week 13-14)

### Goal
Ensure stability and prepare for production.

### Tasks

#### 8.1 Testing
```python
# ann/tests/test_matching.py

from django.test import TestCase
from ann.services.matching_engine import MatchingEngine

class MatchingEngineTests(TestCase):
    def test_semantic_similarity_returns_float(self):
        # ... test implementation ...
        pass

    def test_skill_match_fuzzy_matching(self):
        # ... test implementation ...
        pass
```

#### 8.2 Production Configuration
```yaml
# docker-compose.prod.yml

version: '3.8'
services:
  web:
    build: .
    command: gunicorn neuralnetwork.wsgi:application --bind 0.0.0.0:8000
    environment:
      - DEBUG=False
      - DATABASE_URL=postgres://...
    depends_on:
      - db
      - redis

  db:
    image: postgres:15
    volumes:
      - postgres_data:/var/lib/postgresql/data

  redis:
    image: redis:7-alpine

  celery:
    build: .
    command: celery -A neuralnetwork worker -l info
    depends_on:
      - redis
```

#### 8.3 Documentation
- [ ] README.md with setup instructions
- [ ] API documentation
- [ ] Deployment guide
- [ ] User manual

### Deliverables
- [ ] Unit tests for all services
- [ ] Integration tests for workflows
- [ ] Production docker-compose
- [ ] Environment variable configuration
- [ ] README documentation
- [ ] Git commit: "Phase 8: Testing and deployment"

---

## Quick Reference: Commands

```bash
# Setup
pip install -r requirements.txt
python -m spacy download en_core_web_sm

# Database
python manage.py makemigrations
python manage.py migrate

# Train ML Model
python manage.py train_model --epochs 100

# Run Development
python manage.py runserver

# Run Celery Worker
celery -A neuralnetwork worker -l info

# Run Tests
python manage.py test ann.tests
```

---

## Success Criteria

| Metric | MVP Target | V1 Target |
|--------|-----------|-----------|
| Match Accuracy | > 60% | > 75% |
| Resume Parse Time | < 10s | < 5s |
| Match Calculation | < 5s | < 2s |
| API Response | < 500ms | < 200ms |

---

## Risk Mitigation

| Risk | Mitigation |
|------|------------|
| ML model poor accuracy | Use weighted average fallback |
| Resume parsing fails | Return graceful error, allow retry |
| Celery down | Sync fallback for critical paths |
| Skills not extracted | Allow manual skill entry |

---

*Last Updated: January 2026*
*Total Estimated Effort: 14 weeks*
