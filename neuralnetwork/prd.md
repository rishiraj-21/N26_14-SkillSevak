# SkillSevak – Complete Project Blueprint
## AI-Powered Resume Matching System (Dynamic & Scalable)

> **One-Line Summary:** SkillSevak is an AI-powered recruitment platform that matches candidates and jobs using semantic understanding—not keywords—working across ALL industries without hardcoded skill dictionaries.

---

## Table of Contents

1. [Project Vision](#1-project-vision)
2. [Problem & Solution](#2-problem--solution)
3. [Core Differentiators](#3-core-differentiators)
4. [User Roles & Features](#4-user-roles--features)
5. [Technology Architecture](#5-technology-architecture)
6. [Database Design](#6-database-design)
7. [Implementation Phases](#7-implementation-phases)
8. [AI/ML Pipeline Details](#8-aiml-pipeline-details)
9. [API Design](#9-api-design)
10. [Project Structure](#10-project-structure)
11. [Deployment Strategy](#11-deployment-strategy)
12. [Success Metrics](#12-success-metrics)

---

## 1. Project Vision

### What is SkillSevak?

SkillSevak is a **context-aware recruitment platform** that understands talent beyond keywords. Unlike traditional ATS systems that reject candidates for missing exact words, SkillSevak uses semantic AI to understand:

- "Built dashboards" = Data Visualization skills
- "Led team of 5" = Leadership experience  
- "Reduced costs by 20%" = Cost Optimization ability

### The Name

**Skill** (competency) + **Sevak** (servant in Hindi) = A system that serves both candidates and recruiters by understanding real skills.

### Project Context

- **Team:** 4 members from Amity University Mumbai
- **Type:** Academic project converting to startup
- **Supervisor:** Dr. Deepa Parasar

---

## 2. Problem & Solution

### The Problem with Current ATS Systems

```
Traditional ATS Flow:
Resume → Keyword Scanner → "Python" found? Yes/No → Decision

Problems:
├── "Machine Learning Engineer" ≠ "ML Engineer" (rejected!)
├── "Built data pipelines" doesn't match "ETL experience" (rejected!)
├── Qualified candidates rejected for vocabulary differences
├── Candidates apply blindly to 100+ jobs hoping for matches
├── Recruiters drowning in irrelevant applications
└── Bias based on college names, formatting, etc.
```

### SkillSevak's Solution

```
SkillSevak Flow:
Resume → Semantic Understanding → Context Analysis → Match Score

How it works:
├── "Machine Learning Engineer" ≈ "ML Engineer" (understood!)
├── "Built data pipelines" ≈ "ETL experience" (semantic match!)
├── Candidates SEE match % BEFORE applying
├── Apply to 10 relevant jobs instead of 100 random ones
├── Recruiters get pre-ranked, qualified candidates
└── Skills-based matching, not name/college based
```

### Before vs After Comparison

| Aspect | Traditional ATS | SkillSevak |
|--------|-----------------|------------|
| Matching Method | Keyword count | Semantic understanding |
| Skill Detection | Hardcoded dictionary | Dynamic NLP extraction |
| Industry Support | Tech-focused | Universal (any industry) |
| Candidate Experience | Apply blindly | See match % before applying |
| Recruiter Experience | Manual screening | Auto-ranked candidates |
| Bias | Name, college-based | Skills-based only |
| Transparency | Black box | Explainable scores |

---

## 3. Core Differentiators

### 3.1 For Candidates

| Feature | Description | Impact |
|---------|-------------|--------|
| **Pre-Application Match %** | See "87% match" BEFORE applying | No more blind applications |
| **Smart CV Optimization** | "Add 'Tableau' → match increases 68% → 82%" | Actionable improvement tips |
| **Context-Aware Understanding** | System knows "built dashboards" = data visualization | No keyword stuffing needed |
| **Skill Gap Analysis** | Know exactly what skills to develop | Career growth guidance |
| **Apply Smart, Not Hard** | 10 targeted applications > 100 random ones | Better success rate |

### 3.2 For Recruiters

| Feature | Description | Impact |
|---------|-------------|--------|
| **Auto-Ranked Candidates** | See candidates sorted: 95%, 87%, 76%... | No manual screening |
| **Skill Gap Visibility** | "Candidate A: 92% match, missing only Docker" | Informed decisions |
| **Time Savings** | Cut shortlisting from 2 weeks to 2 hours | 10x efficiency |
| **Bias-Free Hiring** | Skills-based, not college/name-based | Fair hiring |
| **Explainable AI** | See WHY each candidate matched | Trust in system |

### 3.3 Technical Differentiators

| Feature | Why It Matters |
|---------|---------------|
| **No Hardcoded Skills** | Works for law, medicine, marketing—any field |
| **Semantic Embeddings** | Understands meaning, not just words |
| **Dynamic Learning** | System improves with more data |
| **Explainable Scores** | Transparent matching logic |
| **Universal Industry Support** | Same system works for ALL job types |

---

## 4. User Roles & Features

### 4.1 Candidate Features

#### MVP (Must Have)
- [ ] User registration & authentication
- [ ] Resume upload (PDF/DOCX)
- [ ] View extracted skills from resume
- [ ] Browse available jobs
- [ ] See match percentage for each job
- [ ] Apply to jobs
- [ ] Track application status
- [ ] Basic profile management

#### V1.1 (Should Have)
- [ ] Skill gap analysis per job
- [ ] Resume optimization suggestions
- [ ] "Add skill X to improve match by Y%"
- [ ] Save jobs for later
- [ ] Application history with timeline
- [ ] Email notifications

#### V2.0 (Nice to Have)
- [ ] AI-powered resume rewrite
- [ ] Career path suggestions
- [ ] Skill trend insights
- [ ] Interview preparation tips
- [ ] Learning resource recommendations

### 4.2 Recruiter Features

#### MVP (Must Have)
- [ ] Company registration & authentication
- [ ] Post job with requirements
- [ ] View candidates ranked by match %
- [ ] See candidate skill breakdown
- [ ] Shortlist/reject candidates
- [ ] View candidate resumes
- [ ] Basic job management

#### V1.1 (Should Have)
- [ ] Skill gap analysis per candidate
- [ ] Bulk actions (shortlist multiple)
- [ ] Filter by match %, experience, skills
- [ ] Notes on candidates
- [ ] Email notifications
- [ ] Job analytics dashboard

#### V2.0 (Nice to Have)
- [ ] Team collaboration
- [ ] Interview scheduling
- [ ] Advanced analytics
- [ ] Candidate pipeline management
- [ ] ATS integrations

---

## 5. Technology Architecture

### 5.1 Tech Stack

| Layer | Technology | Why This Choice |
|-------|------------|-----------------|
| **Backend** | Django 4.2 + Python 3.11 | Rapid development, strong ORM, great ecosystem |
| **Frontend** | HTML + Tailwind CSS + JavaScript | Fast, responsive, low complexity for MVP |
| **Database** | SQLite (dev) → PostgreSQL (prod) | Scalable, supports vector operations |
| **AI/NLP** | spaCy + sentence-transformers | Dynamic skill extraction + semantic matching |
| **ML Model** | PyTorch | ANN for learning optimal match weights |
| **Background Tasks** | Celery + Redis | Async processing for heavy ML operations |
| **File Storage** | Local → AWS S3 | Scalable resume storage |
| **Caching** | Redis | Fast match score retrieval |
| **Search** | PostgreSQL Full-Text → Elasticsearch | Job and candidate search |

### 5.2 System Architecture Diagram

```
┌─────────────────────────────────────────────────────────────────────┐
│                         SKILLSEVAK ARCHITECTURE                      │
└─────────────────────────────────────────────────────────────────────┘

                              ┌─────────────┐
                              │   USERS     │
                              │ Candidates  │
                              │ Recruiters  │
                              └──────┬──────┘
                                     │
                                     ▼
                        ┌────────────────────────┐
                        │      WEB INTERFACE     │
                        │  HTML + Tailwind + JS  │
                        └───────────┬────────────┘
                                    │
                                    ▼
┌───────────────────────────────────────────────────────────────────┐
│                         DJANGO BACKEND                             │
├───────────────────────────────────────────────────────────────────┤
│                                                                   │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐               │
│  │   AUTH      │  │    JOBS     │  │  MATCHING   │               │
│  │   MODULE    │  │   MODULE    │  │   MODULE    │               │
│  └─────────────┘  └─────────────┘  └──────┬──────┘               │
│                                           │                       │
│                                           ▼                       │
│                              ┌─────────────────────┐              │
│                              │   AI/ML SERVICES    │              │
│                              ├─────────────────────┤              │
│                              │ • Resume Parser     │              │
│                              │ • Skill Extractor   │ ◄── DYNAMIC │
│                              │ • Embedding Engine  │     (No      │
│                              │ • Match Calculator  │     Hardcode)│
│                              │ • ANN Predictor     │              │
│                              └──────────┬──────────┘              │
│                                         │                         │
└─────────────────────────────────────────┼─────────────────────────┘
                                          │
                    ┌─────────────────────┼─────────────────────┐
                    │                     │                     │
                    ▼                     ▼                     ▼
           ┌──────────────┐      ┌──────────────┐      ┌──────────────┐
           │  PostgreSQL  │      │    Redis     │      │   Celery     │
           │  (Database)  │      │  (Cache +    │      │  (Async      │
           │              │      │   Queue)     │      │   Tasks)     │
           └──────────────┘      └──────────────┘      └──────────────┘
```

### 5.3 AI/ML Pipeline Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│                    AI/ML MATCHING PIPELINE                           │
│                    (Works for ANY Industry)                          │
└─────────────────────────────────────────────────────────────────────┘

RESUME UPLOAD                              JOB POSTING
     │                                          │
     ▼                                          ▼
┌─────────────┐                          ┌─────────────┐
│ PDF/DOCX    │                          │ Job Form    │
│ File        │                          │ Input       │
└──────┬──────┘                          └──────┬──────┘
       │                                        │
       ▼                                        ▼
┌─────────────────┐                      ┌─────────────────┐
│ TEXT EXTRACTION │                      │ TEXT PROCESSING │
│ PyPDF2/docx     │                      │ Clean & Format  │
└────────┬────────┘                      └────────┬────────┘
         │                                        │
         ▼                                        ▼
┌─────────────────┐                      ┌─────────────────┐
│ PREPROCESSING   │                      │ PREPROCESSING   │
│ • Clean text    │                      │ • Clean text    │
│ • Normalize     │                      │ • Normalize     │
│ • Section detect│                      │ • Extract reqs  │
└────────┬────────┘                      └────────┬────────┘
         │                                        │
         ▼                                        ▼
┌─────────────────────────────────────────────────────────┐
│              DYNAMIC SKILL EXTRACTION (NLP)              │
│  ┌─────────────────────────────────────────────────┐    │
│  │ NO HARDCODED DICTIONARY!                        │    │
│  │                                                 │    │
│  │ • NER (Named Entity Recognition)                │    │
│  │ • Noun phrase extraction                        │    │
│  │ • Context analysis                              │    │
│  │ • Works for: Tech, Law, Healthcare, Marketing.. │    │
│  └─────────────────────────────────────────────────┘    │
└────────────────────────┬────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────┐
│              EMBEDDING GENERATION                        │
│              (sentence-transformers)                     │
│                                                         │
│  Resume Text ──► [0.23, 0.45, ..., 0.89] (384 dims)    │
│  Job Text    ──► [0.31, 0.52, ..., 0.76] (384 dims)    │
│                                                         │
│  Similar meanings = Similar vectors                     │
└────────────────────────┬────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────┐
│                   MATCHING ENGINE                        │
├─────────────────────────────────────────────────────────┤
│                                                         │
│  1. Semantic Similarity (Cosine)     ──► 0.82          │
│  2. Skill Overlap (with fuzzy match) ──► 0.75          │
│  3. Experience Match                 ──► 0.90          │
│  4. Education Relevance              ──► 0.70          │
│  5. Profile Completeness             ──► 0.85          │
│                                                         │
└────────────────────────┬────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────┐
│                    ANN MODEL                             │
│         (Learns Optimal Weights Automatically)           │
│                                                         │
│  Input: [sem_sim, skill, exp, edu, profile] (5 features)│
│  Hidden Layers: 64 → 32 → 16 neurons                    │
│  Output: Match Probability (0-100%)                     │
│                                                         │
│  MVP: Use weighted average (fixed weights)              │
│  V1:  Use trained ANN (learned weights)                 │
└────────────────────────┬────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────┐
│                    OUTPUT                                │
│                                                         │
│  For Candidate:                                         │
│  • Match %: 87%                                         │
│  • Matched Skills: Python, SQL, ML                      │
│  • Missing Skills: Docker, Kubernetes                   │
│  • Suggestion: "Add Docker → improve to 92%"            │
│                                                         │
│  For Recruiter:                                         │
│  • Ranked candidate list                                │
│  • Skill breakdown per candidate                        │
│  • Gap analysis                                         │
└─────────────────────────────────────────────────────────┘
```

---

## 6. Database Design

### 6.1 Entity Relationship Overview

```
┌──────────────┐       ┌──────────────┐       ┌──────────────┐
│     User     │       │   Company    │       │     Job      │
├──────────────┤       ├──────────────┤       ├──────────────┤
│ id           │       │ id           │       │ id           │
│ email        │       │ name         │       │ company_id   │──┐
│ password     │       │ industry     │       │ title        │  │
│ user_type    │       │ website      │       │ description  │  │
└──────┬───────┘       └──────────────┘       │ embedding    │  │
       │                      ▲               └──────────────┘  │
       │                      │                      ▲          │
       ▼                      │                      │          │
┌──────────────┐              │               ┌──────┴───────┐  │
│  Candidate   │              │               │  JobSkill    │  │
├──────────────┤              │               │  (Dynamic)   │  │
│ id           │              │               ├──────────────┤  │
│ user_id      │──┐           │               │ skill_text   │  │
│ full_name    │  │           │               │ importance   │  │
│ experience   │  │    ┌──────┴───────┐       └──────────────┘  │
│ education    │  │    │  Recruiter   │                         │
└──────────────┘  │    └──────────────┘                         │
       │          │                                             │
       ▼          │                                             │
┌──────────────┐  │    ┌──────────────┐       ┌──────────────┐  │
│    Resume    │  │    │ Application  │       │  MatchScore  │  │
├──────────────┤  │    ├──────────────┤       ├──────────────┤  │
│ raw_text     │  │    │ candidate_id │◄──────│ candidate_id │  │
│ embedding    │  │    │ job_id       │◄──┬───│ job_id       │──┘
│ sections     │  │    │ status       │   │   │ overall_score│
└──────────────┘  │    └──────────────┘   │   │ breakdown    │
       │          │                       │   │ suggestions  │
       ▼          │                       │   └──────────────┘
┌──────────────┐  │                       │
│CandidateSkill│  │                       │
│ (Dynamic)    │◄─┘                       │
├──────────────┤                          │
│ skill_text   │                          │
│ proficiency  │                          │
│ source       │                          │
└──────────────┘                          │
```

### 6.2 Key Tables

#### Users & Authentication
```sql
-- Core User
User:
  - id (PK)
  - email (unique)
  - password_hash
  - user_type: 'candidate' | 'recruiter'
  - is_verified
  - created_at

-- Candidate Profile  
Candidate:
  - id (PK)
  - user_id (FK → User)
  - full_name
  - phone
  - location
  - years_of_experience
  - education_level
  - education_field
  - profile_completeness (0-100)

-- Recruiter Profile
Recruiter:
  - id (PK)
  - user_id (FK → User)
  - company_id (FK → Company)
  - full_name
  - designation
```

#### Resume & Skills (Dynamic - No Hardcoding!)
```sql
-- Resume Storage
Resume:
  - id (PK)
  - candidate_id (FK)
  - file_path
  - raw_text
  - cleaned_text
  - sections_json          -- {"skills": "...", "experience": "..."}
  - embedding (VECTOR 384) -- Semantic embedding
  - parsing_status

-- Extracted Skills (DYNAMIC - from NLP, not dictionary!)
CandidateSkill:
  - id (PK)
  - candidate_id (FK)
  - skill_text             -- "Machine Learning" (as extracted)
  - normalized_text        -- "machine learning" (for matching)
  - proficiency_level (1-5)
  - source                 -- 'skills_section' | 'experience' | 'projects'
  - context                -- Sentence where skill was found
  - confidence_score
```

#### Jobs
```sql
-- Job Posting
Job:
  - id (PK)
  - recruiter_id (FK)
  - company_id (FK)
  - title
  - description
  - requirements
  - location
  - work_type              -- 'remote' | 'hybrid' | 'onsite'
  - experience_min
  - experience_max
  - salary_range
  - embedding (VECTOR 384)
  - status                 -- 'active' | 'paused' | 'closed'

-- Extracted Job Skills (DYNAMIC - from job description!)
JobSkill:
  - id (PK)
  - job_id (FK)
  - skill_text
  - normalized_text
  - importance             -- 'required' | 'preferred' | 'nice_to_have'
```

#### Matching
```sql
-- Pre-computed Match Scores
MatchScore:
  - id (PK)
  - candidate_id (FK)
  - job_id (FK)
  - overall_score (0-100)
  - semantic_similarity
  - skill_match_score
  - experience_match_score
  - education_match_score
  - matched_skills (JSON)
  - missing_skills (JSON)
  - suggestions (JSON)
  - calculated_at
  - is_valid

-- Applications
Application:
  - id (PK)
  - candidate_id (FK)
  - job_id (FK)
  - match_score_id (FK)
  - status                 -- 'applied' | 'viewed' | 'shortlisted' | 'rejected'
  - applied_at
```

---

## 7. Implementation Phases

### Timeline Overview

```
Week 1-2:   Foundation (Auth, UI, Models)
Week 3-4:   Resume Processing (Upload, Parse, Extract)
Week 5-6:   Dynamic Skill Extraction (NLP - No Hardcoding!)
Week 7-8:   Semantic Matching (Embeddings, Similarity)
Week 9-10:  ANN Model (Training, Integration)
Week 11-12: Real-Time Pipeline (Celery, Caching)
Week 13-14: Recommendations & Polish
Week 15-16: Testing & Deployment
```

### Phase 1: Foundation (Week 1-2)

#### Tasks
- [ ] Django project setup with proper structure
- [ ] Environment configuration (dev/staging/prod)
- [ ] User authentication (candidates + recruiters)
- [ ] Database models creation
- [ ] Basic UI with Tailwind CSS
- [ ] Role-based dashboards

#### Deliverables
- Running Django app
- Working auth system
- Basic candidate dashboard
- Basic recruiter dashboard

### Phase 2: Resume Processing (Week 3-4)

#### Tasks
- [ ] File upload with validation (PDF/DOCX, max 5MB)
- [ ] Secure file storage
- [ ] Text extraction (PyPDF2, python-docx)
- [ ] Text cleaning and normalization
- [ ] Section detection (Skills, Experience, Education)
- [ ] Store structured data

#### Key Code: Text Extraction
```python
# services/resume_parser.py
import pdfplumber
from docx import Document

class ResumeParser:
    def extract_text(self, file_path: str) -> str:
        if file_path.endswith('.pdf'):
            return self._extract_pdf(file_path)
        elif file_path.endswith('.docx'):
            return self._extract_docx(file_path)
    
    def _extract_pdf(self, path: str) -> str:
        text = ""
        with pdfplumber.open(path) as pdf:
            for page in pdf.pages:
                text += (page.extract_text() or "") + "\n"
        return text
```

### Phase 3: Dynamic Skill Extraction (Week 5-6)

> **CRITICAL: No Hardcoded Skill Dictionary!**

#### Why Dynamic?
```
Hardcoded Dictionary:
├── skills = ["Python", "Java", "React"...]
├── Only works for tech jobs
├── "Patent Law" not in list = MISSED
└── Requires constant updates

Dynamic Extraction (SkillSevak):
├── NLP extracts skills from ANY text
├── Works for tech, law, healthcare, marketing...
├── "Patent Law" extracted automatically
└── Self-improving with more data
```

#### Tasks
- [ ] spaCy NLP setup
- [ ] Noun phrase extraction
- [ ] Named Entity Recognition
- [ ] Proper noun extraction (tools, technologies)
- [ ] Skill normalization using embeddings
- [ ] Proficiency estimation from context

#### Key Code: Dynamic Skill Extractor
```python
# services/skill_extractor.py
import spacy

class DynamicSkillExtractor:
    """
    Extract skills WITHOUT hardcoded dictionary.
    Works for ANY industry.
    """
    
    def __init__(self):
        self.nlp = spacy.load("en_core_web_sm")
    
    def extract_skills(self, text: str) -> list:
        doc = self.nlp(text)
        skills = set()
        
        # Method 1: Noun phrases
        for chunk in doc.noun_chunks:
            if self._is_valid_skill(chunk.text):
                skills.add(chunk.text.lower())
        
        # Method 2: Proper nouns (tools, technologies)
        for token in doc:
            if token.pos_ == "PROPN":
                skills.add(token.text)
        
        # Method 3: Named entities (ORG, PRODUCT)
        for ent in doc.ents:
            if ent.label_ in ['ORG', 'PRODUCT']:
                skills.add(ent.text)
        
        return list(skills)
```

### Phase 4: Semantic Matching (Week 7-8)

#### Tasks
- [ ] sentence-transformers setup
- [ ] Embedding generation for resumes
- [ ] Embedding generation for jobs
- [ ] Cosine similarity calculation
- [ ] Skill overlap with fuzzy matching
- [ ] Combined scoring

#### Key Code: Semantic Similarity
```python
# services/matching_engine.py
from sentence_transformers import SentenceTransformer
from sklearn.metrics.pairwise import cosine_similarity

class MatchingEngine:
    def __init__(self):
        self.model = SentenceTransformer('all-MiniLM-L6-v2')
    
    def calculate_semantic_similarity(self, resume_text: str, job_text: str) -> float:
        resume_emb = self.model.encode([resume_text])[0]
        job_emb = self.model.encode([job_text])[0]
        
        similarity = cosine_similarity(
            resume_emb.reshape(1, -1),
            job_emb.reshape(1, -1)
        )[0][0]
        
        return float(similarity)
```

### Phase 5: ANN Model (Week 9-10)

#### Tasks
- [ ] Feature engineering (5 input features)
- [ ] Synthetic training data generation
- [ ] PyTorch model implementation
- [ ] Training pipeline
- [ ] Model integration with Django

#### Model Architecture
```python
# ml/model.py
import torch.nn as nn

class MatchPredictor(nn.Module):
    """
    Input:  5 features (semantic, skill, exp, edu, profile)
    Hidden: 64 → 32 → 16
    Output: Match probability (0-1)
    """
    def __init__(self):
        super().__init__()
        self.network = nn.Sequential(
            nn.Linear(5, 64),
            nn.ReLU(),
            nn.Dropout(0.3),
            nn.Linear(64, 32),
            nn.ReLU(),
            nn.Linear(32, 16),
            nn.ReLU(),
            nn.Linear(16, 1),
            nn.Sigmoid()
        )
    
    def forward(self, x):
        return self.network(x) * 100  # Scale to 0-100%
```

### Phase 6: Real-Time Pipeline (Week 11-12)

#### Tasks
- [ ] Celery + Redis setup
- [ ] Async resume processing task
- [ ] Async match calculation task
- [ ] Caching layer (Redis)
- [ ] Event-driven updates

#### Key Code: Celery Tasks
```python
# tasks.py
from celery import shared_task

@shared_task
def process_resume(resume_id: int):
    """Parse resume, extract skills, generate embedding."""
    resume = Resume.objects.get(id=resume_id)
    
    # 1. Extract text
    text = ResumeParser().extract_text(resume.file_path)
    
    # 2. Extract skills (DYNAMIC!)
    skills = SkillExtractor().extract_skills(text)
    
    # 3. Generate embedding
    embedding = EmbeddingService().generate(text)
    
    # 4. Save
    resume.raw_text = text
    resume.embedding = embedding
    resume.save()
    
    # 5. Trigger matching
    calculate_all_matches.delay(resume.candidate_id)

@shared_task
def calculate_match(candidate_id: int, job_id: int):
    """Calculate and cache match score."""
    score = MatchingEngine().calculate(candidate_id, job_id)
    cache.set(f"match:{candidate_id}:{job_id}", score, timeout=3600)
    return score
```

### Phase 7: Recommendations & Polish (Week 13-14)

#### Tasks
- [ ] Skill gap analysis
- [ ] Improvement suggestions ("Add X to improve by Y%")
- [ ] Recruiter insights dashboard
- [ ] UI/UX refinement
- [ ] Email notifications

### Phase 8: Testing & Deployment (Week 15-16)

#### Tasks
- [ ] Unit tests
- [ ] Integration tests
- [ ] Load testing
- [ ] Security audit
- [ ] Production deployment

---

## 8. AI/ML Pipeline Details

### 8.1 Why No Hardcoded Skills?

| Hardcoded Approach | Dynamic Approach (SkillSevak) |
|-------------------|-------------------------------|
| `skills = ["Python", "Java"...]` | NLP extracts from text |
| Only works for predefined industries | Works for ANY industry |
| "Patent Law" missed if not in list | "Patent Law" auto-extracted |
| Needs constant manual updates | Self-improving |
| Limited to 500-1000 skills | Unlimited skills |

### 8.2 Semantic Matching Examples

```
Example 1: Tech Role
├── Resume: "Built data pipelines using Python"
├── Job: "ETL development experience required"
├── Traditional ATS: NO MATCH (different words)
└── SkillSevak: 85% MATCH (semantic understanding)

Example 2: Legal Role  
├── Resume: "Handled M&A due diligence for Fortune 500"
├── Job: "Corporate transactions and mergers experience"
├── Traditional ATS: NO MATCH
└── SkillSevak: 88% MATCH

Example 3: Healthcare Role
├── Resume: "ICU experience with ventilator management"
├── Job: "Critical care nursing, respiratory support"
├── Traditional ATS: NO MATCH
└── SkillSevak: 90% MATCH
```

### 8.3 Scoring Formula

**MVP (Fixed Weights):**
```
Match % = (0.25 × Semantic) + (0.35 × Skills) + (0.20 × Experience)
        + (0.10 × Education) + (0.10 × Profile)
```

**Skills Score Breakdown:**
```
Skills Score = (0.70 × Technical Skills)
             + (0.20 × Domain Skills)
             + (0.10 × Soft Skills)
```

Where:
- **Technical Skills**: Programming languages, frameworks, tools (Python, React, Docker)
- **Domain Skills**: Industry-specific knowledge (Machine Learning, Financial Analysis, Healthcare)
- **Soft Skills**: Communication, leadership, teamwork, problem-solving

**V1 (ANN Learned Weights):**
```
Match % = ANN([semantic, skills, experience, education, profile])
# ANN learns optimal weights from training data automatically
```

---

## 9. API Design

### Authentication
| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/v1/auth/register/candidate/` | Register candidate |
| POST | `/api/v1/auth/register/recruiter/` | Register recruiter |
| POST | `/api/v1/auth/login/` | Login |
| POST | `/api/v1/auth/logout/` | Logout |

### Candidate APIs
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/v1/candidates/profile/` | Get profile |
| PUT | `/api/v1/candidates/profile/` | Update profile |
| POST | `/api/v1/candidates/resume/` | Upload resume |
| GET | `/api/v1/candidates/skills/` | Get extracted skills |
| GET | `/api/v1/candidates/jobs/` | Get job matches |
| GET | `/api/v1/candidates/jobs/{id}/match/` | Get match details |
| POST | `/api/v1/applications/` | Apply to job |

### Recruiter APIs
| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/v1/jobs/` | Create job |
| GET | `/api/v1/jobs/` | List jobs |
| GET | `/api/v1/jobs/{id}/candidates/` | Get ranked candidates |
| PUT | `/api/v1/applications/{id}/` | Update status |

---

## 10. Project Structure

```
skillsevak/
├── config/                     # Settings
│   ├── settings/
│   │   ├── base.py
│   │   ├── development.py
│   │   └── production.py
│   ├── urls.py
│   └── celery.py
│
├── apps/
│   ├── accounts/              # Auth & profiles
│   ├── resumes/               # Resume processing
│   │   └── services/
│   │       ├── parser.py
│   │       └── skill_extractor.py  # DYNAMIC!
│   ├── jobs/                  # Job management
│   ├── matching/              # Core matching
│   │   └── services/
│   │       ├── matching_engine.py
│   │       └── recommendations.py
│   └── applications/          # Applications
│
├── ml/                        # Machine learning
│   ├── models/
│   │   └── match_predictor.py
│   ├── training/
│   └── inference/
│
├── services/                  # Shared services
│   ├── embedding_service.py
│   └── skill_normalizer.py
│
├── templates/
├── static/
└── tests/
```

---

## 11. Deployment Strategy

### Development
```yaml
# docker-compose.yml
services:
  web:
    build: .
    ports: ["8000:8000"]
  redis:
    image: redis:7-alpine
  celery:
    build: .
    command: celery -A config worker -l info
```

### Production Architecture
```
Users → Cloudflare (CDN) → Nginx → Gunicorn Workers
                                         ↓
                          ┌──────────────┼──────────────┐
                          ↓              ↓              ↓
                     PostgreSQL       Redis         Celery
                                                   Workers
```

### Scaling Path
| Users | Infrastructure |
|-------|---------------|
| 0-1K | Single VPS ($20/mo) |
| 1K-10K | 2 VPS + Managed DB ($100/mo) |
| 10K-100K | Load balanced + S3 ($500/mo) |
| 100K+ | Kubernetes |

---

## 12. Success Metrics

### Technical
| Metric | Target |
|--------|--------|
| API Response Time | < 200ms |
| Match Calculation | < 2s |
| Resume Parsing | < 5s |
| Uptime | 99.9% |

### Business
| Metric | Target |
|--------|--------|
| Match Accuracy | > 75% |
| Time-to-Hire Reduction | 40% |
| Application Quality | +60% |
| Candidate Satisfaction | 4.5/5 |

---

## Key Principles Summary

1. **NO HARDCODED SKILLS** — System works for any industry
2. **SEMANTIC UNDERSTANDING** — Match meaning, not keywords
3. **TRANSPARENCY** — Show WHY candidates matched
4. **SCALABILITY** — Design for 1M users from day 1
5. **SECURITY** — Validate everything, trust nothing
6. **EXPLAINABILITY** — AI decisions must be understandable

---

*Document Version: 2.0*
*Project: SkillSevak - AI-Powered Resume Matching System*
*Team: Amity University Mumbai (Rishi, Sidhika, Jinendra, Parth)*
*Supervisor: Dr. Deepa Parasar*
