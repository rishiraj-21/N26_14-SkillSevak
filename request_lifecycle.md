# SkillSevak — Request Lifecycle

End-to-end flow of every major request through the system.

---

## 1. Candidate — Resume Upload & Matching

```
Browser
  │
  │  POST /candidate/upload-resume  (multipart/form-data)
  │
  ▼
┌──────────────────────────────────────────────────────┐
│  Django Middleware Stack                             │
│  SecurityMiddleware → SessionMiddleware →            │
│  AuthenticationMiddleware → CSRFMiddleware           │
└──────────────────────┬───────────────────────────────┘
                       │  request.user verified
                       ▼
┌──────────────────────────────────────────────────────┐
│  candidate_view  (ann/views.py)                      │
│  @login_required                                     │
│  ├─ validate file type (PDF / DOCX)                  │
│  ├─ save to media/resumes/<user>/                    │
│  └─ trigger resume processing                        │
└──────────────────────┬───────────────────────────────┘
                       │
                       ▼
┌──────────────────────────────────────────────────────┐
│  ResumeParser  (ann/services/resume_parser.py)       │
│  ├─ PDF  → pdfplumber  → raw text                    │
│  └─ DOCX → python-docx → raw text                   │
│                                                      │
│  Output: cleaned_text (stored in ParsedResume)       │
└──────────────────────┬───────────────────────────────┘
                       │
                       ▼
┌──────────────────────────────────────────────────────┐
│  DynamicSkillExtractor  (ann/services/               │
│                          skill_extractor.py)         │
│  ├─ spaCy NLP pipeline (en_core_web_sm)              │
│  ├─ Named entity recognition                         │
│  ├─ Noun chunk extraction                            │
│  └─ Zero hardcoded skills — purely NLP-driven        │
│                                                      │
│  Output: List[CandidateSkill] → saved to DB          │
└──────────────────────┬───────────────────────────────┘
                       │
                       ▼
┌──────────────────────────────────────────────────────┐
│  EmbeddingService  (ann/services/embedding_service.py│
│  ├─ sentence-transformers: all-MiniLM-L6-v2          │
│  ├─ Encode cleaned_text → 384-dim vector             │
│  └─ Serialize + store in ParsedResume.embedding      │
└──────────────────────┬───────────────────────────────┘
                       │
                       ▼
┌──────────────────────────────────────────────────────┐
│  MatchingEngine  (ann/services/matching_engine.py)   │
│  Runs for every open Job in DB                       │
│                                                      │
│  Per job:                                            │
│  ├─ semantic_score  = cosine_sim(resume_emb, job_emb)│
│  ├─ skill_score     = weighted overlap               │
│  │    technical 70% + domain 20% + soft 10%          │
│  │    fuzzy match threshold: 80% SequenceMatcher     │
│  ├─ experience_score = gap analysis vs job range     │
│  ├─ education_score  = level + field relevance       │
│  └─ profile_score   = completeness %                │
│                                                      │
│  Scoring:                                            │
│  ┌─ ANN available? ──YES──► MatchPredictor.predict() │
│  │                           PyTorch inference       │
│  │                           5 features → score 0-100│
│  └─ ANN missing?  ──NO───► weighted average formula  │
│       0.25·sem + 0.35·ski + 0.20·exp                 │
│         + 0.10·edu + 0.10·pro                        │
│                                                      │
│  Output: MatchScore upserted to DB per (candidate,job│
└──────────────────────┬───────────────────────────────┘
                       │
                       ▼
              JsonResponse / render
              Ranked job list with scores,
              matched_skills, missing_skills,
              suggestions sent to browser
```

---

## 2. ANN Inference Detail

```
5 normalised features (0–1 each)
[semantic, skill, experience, education, profile]
          │
          ▼
  ┌───────────────────────────────┐
  │  Linear(5 → 128)              │
  │  ReLU  +  LayerNorm           │
  │  Dropout(p=0.15)              │
  ├───────────────────────────────┤
  │  Linear(128 → 64)             │
  │  ReLU  +  LayerNorm           │
  │  Dropout(p=0.10)              │
  ├───────────────────────────────┤
  │  Linear(64 → 32)              │
  │  ReLU  +  LayerNorm           │
  ├───────────────────────────────┤
  │  Linear(32 → 1)               │
  │  Sigmoid  →  × 100            │
  └───────────────────────────────┘
          │
          ▼
   Match Score  0 – 100

  Fallback (no weights file):
  score = 0.25·sem + 0.35·ski + 0.20·exp
          + 0.10·edu + 0.10·pro
```

---

## 3. Recruiter — Job Post & Candidate Ranking

```
Browser
  │
  │  POST /recruiter/jobs/create
  │
  ▼
┌──────────────────────────────────────────────────────┐
│  recruiter_view  (ann/views.py)                      │
│  @login_required  +  CompanyProfile check            │
│  ├─ validate form fields                             │
│  ├─ create Job record (status='open')                │
│  └─ trigger skill extraction for job description     │
└──────────────────────┬───────────────────────────────┘
                       │
                       ▼
┌──────────────────────────────────────────────────────┐
│  DynamicSkillExtractor  (same pipeline as resume)    │
│  Applied to: job.description + job.requirements      │
│  Output: List[JobSkill] → saved to DB                │
└──────────────────────┬───────────────────────────────┘
                       │
                       ▼
┌──────────────────────────────────────────────────────┐
│  EmbeddingService                                    │
│  Encode job text → 384-dim vector                    │
│  Stored in Job.embedding (cached for future matches) │
└──────────────────────┬───────────────────────────────┘
                       │
          GET /recruiter/jobs/<id>/candidates
                       │
                       ▼
┌──────────────────────────────────────────────────────┐
│  MatchingEngine.calculate_all_matches_for_job()      │
│  ├─ query all CandidateProfile with resume_file      │
│  ├─ run calculate_match() for each                   │
│  ├─ upsert MatchScore records                        │
│  └─ return sorted by overall_score DESC              │
└──────────────────────┬───────────────────────────────┘
                       │
                       ▼
              Recruiter sees ranked candidates
              with scores + skill gap per applicant
```

---

## 4. Async Processing Path (Celery)

When `USE_ASYNC_PROCESSING=True`:

```
resume upload / job post
        │
        │  .delay()
        ▼
┌───────────────────────────┐
│  Celery Worker            │
│  (ann/tasks.py)           │
│                           │
│  retrain_model_task()     │
│  ├─ load_external_data    │
│  ├─ generate_synthetic    │
│  └─ ModelTrainer.train()  │
└───────────┬───────────────┘
            │  result stored via
            │  django-celery-results
            ▼
        Redis (broker + backend)
```

Synchronous path (default, `USE_ASYNC_PROCESSING=False`):
same pipeline runs inline inside the view before returning the response.

---

## 5. Authentication Flow

```
GET/POST /login
     │
     ▼
┌────────────────────────────────────┐
│  login_view                        │
│  ├─ email/password → authenticate()│
│  │    → User.objects.get(username= │
│  │      email) + check_password    │
│  │                                 │
│  └─ Google OAuth (django-allauth)  │
│       /accounts/google/login/      │
│       callback → SocialAccount     │
│       linked to User               │
└──────────────┬─────────────────────┘
               │
               │  session set
               ▼
     Smart redirect:
     CompanyProfile exists? → /recruiter
     CandidateProfile exists? → /candidate
     Neither?               → /
```

---

## 6. Match Score Caching

```
calculate_match() called
        │
        ▼
MatchScore.objects.get(candidate, job, is_valid=True)
        │
  found?─── YES ──► return cached result (no ML inference)
        │
       NO
        │
        ▼
  run full pipeline → upsert MatchScore(is_valid=True)

Invalidation triggers:
  • resume re-upload  → invalidate_candidate_matches()
  • job edit          → invalidate_job_matches()
  Both set is_valid=False → next request recomputes
```

---

## 7. URL → View Map

| Method | URL | View | Auth |
|--------|-----|------|------|
| GET | `/` | `index` | — |
| GET/POST | `/login` | `login_view` | — |
| GET/POST | `/register` | `register_view` | — |
| GET | `/candidate` | `candidate_view` | login |
| POST | `/candidate/upload-resume` | `upload_resume` | login |
| GET | `/recruiter` | `recruiter_view` | login + company |
| GET/POST | `/recruiter/jobs/create` | `create_job` | login + company |
| GET | `/recruiter/jobs/<id>` | `job_detail` | login + company |
| GET | `/accounts/google/login/` | allauth | — |

---

## 8. Data Models Involved Per Request

```
CandidateProfile ──┐
ParsedResume       ├──► MatchScore ◄──┬── Job
CandidateSkill ────┘                  └── JobSkill
                                          CompanyProfile
```

All reads/writes go through Django ORM → SQLite (dev) / PostgreSQL (prod).
