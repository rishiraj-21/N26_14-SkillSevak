"""
Load External Training Data Command  —  Fixed & Production-Grade

Fixes vs v1:
  - Loads BOTH train+test splits so we don't get only one label class
  - Shuffles before limiting (avoids sorted-dataset bias)
  - Balanced sampling: equal Fit / No-Fit rows
  - Wider label noise ranges (Fit → 0.65-0.92, NoFit → 0.08-0.38)
  - Netsol loading with verification_mode='no_checks' + robust field probing
  - Prints class balance before saving

Usage:
    python manage.py load_external_data
    python manage.py load_external_data --dataset fit
    python manage.py load_external_data --dataset netsol
    python manage.py load_external_data --limit 2000
    python manage.py load_external_data --skip-features   # fast test (no embeddings)
"""

import re
import logging
import os
from pathlib import Path

import numpy as np

from django.core.management.base import BaseCommand, CommandError

logger = logging.getLogger(__name__)

OUTPUT_CSV = 'ann/ml/data/external_training_data.csv'

# ──────────────────────────────────────────────────────────────────────────────
# Label maps
# ──────────────────────────────────────────────────────────────────────────────

# Wide ranges so model sees varied labels, not just 2 point masses
FIT_LABEL_MAP = {
    'strong fit':   lambda: np.random.uniform(0.82, 0.95),
    'fit':          lambda: np.random.uniform(0.65, 0.90),
    'moderate fit': lambda: np.random.uniform(0.45, 0.65),
    'weak fit':     lambda: np.random.uniform(0.18, 0.40),
    'no fit':       lambda: np.random.uniform(0.05, 0.32),
}


def _label_from_string(raw: str) -> float:
    key = str(raw).lower().strip()
    fn = FIT_LABEL_MAP.get(key)
    if fn:
        return float(np.clip(fn(), 0.0, 1.0))
    # Unknown — neutral
    return 0.50


# ──────────────────────────────────────────────────────────────────────────────
# Text cleaning helpers
# ──────────────────────────────────────────────────────────────────────────────

def _strip_html(text: str) -> str:
    return re.sub(r'<[^>]+>', ' ', text)


def _clean(text) -> str:
    if not isinstance(text, str):
        return ''
    text = _strip_html(text)
    text = re.sub(r'\s+', ' ', text).strip()
    return text


def _valid(resume: str, job: str, min_len: int = 100) -> bool:
    return bool(resume) and bool(job) and len(resume) >= min_len and len(job) >= min_len


def _dedupe(rows: list) -> list:
    seen = set()
    out = []
    for r in rows:
        key = (r['resume'][:150], r['job'][:150])
        if key not in seen:
            seen.add(key)
            out.append(r)
    return out


# ──────────────────────────────────────────────────────────────────────────────
# Dataset A: cnamuangtoun/resume-job-description-fit
# ──────────────────────────────────────────────────────────────────────────────

def _load_fit_dataset(limit: int) -> list:
    from datasets import load_dataset, concatenate_datasets

    print("Downloading cnamuangtoun/resume-job-description-fit (train + test)...", flush=True)

    # Load BOTH splits — train split is sorted so first N rows = only one label
    train_ds = load_dataset(
        "cnamuangtoun/resume-job-description-fit", split="train",
        trust_remote_code=True,
    )
    test_ds = load_dataset(
        "cnamuangtoun/resume-job-description-fit", split="test",
        trust_remote_code=True,
    )
    ds = concatenate_datasets([train_ds, test_ds])
    ds = ds.shuffle(seed=42)

    print(f"  Total rows (both splits): {len(ds)}  |  columns: {ds.column_names}", flush=True)

    # Detect columns
    cols = ds.column_names
    resume_col = next((c for c in cols if 'resume' in c.lower()), None)
    job_col    = next((c for c in cols if 'job' in c.lower() or 'description' in c.lower()), None)
    label_col  = next((c for c in cols if 'label' in c.lower() or 'fit' in c.lower()), None)

    if not resume_col or not job_col:
        raise CommandError(f"Cannot detect resume/job columns. Columns: {cols}")

    # ── Build rows ──
    fit_rows    = []
    no_fit_rows = []

    for sample in ds:
        resume = _clean(sample.get(resume_col, ''))
        job    = _clean(sample.get(job_col, ''))
        if not _valid(resume, job):
            continue

        raw_label = sample.get(label_col, 'unknown') if label_col else 'unknown'

        # Try numeric first (handles Python int/float AND numpy int64/float32)
        try:
            val = float(raw_label)
            # Binary label (0/1): map to stochastic score ranges
            if val >= 0.9:
                label = float(np.clip(np.random.uniform(0.65, 0.90), 0.0, 1.0))
            elif val <= 0.1:
                label = float(np.clip(np.random.uniform(0.05, 0.32), 0.0, 1.0))
            else:
                label = float(np.clip(val, 0.0, 1.0))  # already a proper score
        except (ValueError, TypeError):
            label = _label_from_string(str(raw_label))

        row = {'resume': resume, 'job': job, 'label': label, 'source': 'hf_fit'}

        if label >= 0.50:
            fit_rows.append(row)
        else:
            no_fit_rows.append(row)

    print(f"  Before balance — Fit: {len(fit_rows)}, No-Fit: {len(no_fit_rows)}", flush=True)

    # ── Balance classes ──
    if fit_rows and no_fit_rows:
        n = min(len(fit_rows), len(no_fit_rows))
        if limit:
            n = min(n, limit // 2)
        rows = fit_rows[:n] + no_fit_rows[:n]
        np.random.default_rng(42).shuffle(rows)
    else:
        # Only one class found — use what we have (model will rely on synthetic data)
        rows = (fit_rows or no_fit_rows)[:limit or None]
        print(f"  WARNING: Only one label class found. "
              f"Check dataset on HuggingFace.", flush=True)

    rows = _dedupe(rows)
    print(f"  Final rows (balanced): {len(rows)}", flush=True)
    return rows


# ──────────────────────────────────────────────────────────────────────────────
# Dataset B: netsol/resume-score-details
# ──────────────────────────────────────────────────────────────────────────────

def _load_netsol_dataset(limit: int) -> list:
    from datasets import load_dataset

    print("Downloading netsol/resume-score-details ...", flush=True)

    # verification_mode='no_checks' bypasses the strict JSON schema check
    try:
        ds = load_dataset(
            "netsol/resume-score-details", split="train",
            trust_remote_code=True,
            verification_mode='no_checks',
        )
    except Exception as e1:
        print(f"  Standard load failed ({e1}), trying alternative...", flush=True)
        try:
            ds = load_dataset(
                "netsol/resume-score-details",
                trust_remote_code=True,
                verification_mode='no_checks',
            )
            # If no split arg, take the first available split
            if hasattr(ds, 'keys'):
                split_name = list(ds.keys())[0]
                ds = ds[split_name]
        except Exception as e2:
            raise CommandError(f"Could not load netsol dataset: {e2}")

    print(f"  Downloaded {len(ds)} rows. Columns: {ds.column_names}", flush=True)

    rows = []
    skipped_invalid = 0

    for sample in ds:
        if limit and len(rows) >= limit:
            break

        if not sample.get('valid_resume_and_jd', True):
            skipped_invalid += 1
            continue

        # ── Extract resume + job from 'input' field ──
        inp = sample.get('input', {})
        if isinstance(inp, dict):
            resume = _clean(inp.get('resume') or inp.get('resume_text', ''))
            job    = _clean(inp.get('job_description') or inp.get('job_description_text', ''))
        elif isinstance(inp, str) and '|||' in inp:
            # Some versions encode as "resume ||| job"
            parts  = inp.split('|||', 1)
            resume = _clean(parts[0])
            job    = _clean(parts[1])
        else:
            continue

        if not _valid(resume, job):
            continue

        # ── Extract label from 'output' field ──
        output = sample.get('output', {})
        macro  = None

        if isinstance(output, dict):
            # Try multiple paths
            macro = (
                output.get('scores', {})
                      .get('aggregated_scores', {})
                      .get('macro_scores')
                or output.get('macro_scores')
                or output.get('score')
                or output.get('overall_score')
            )
        elif isinstance(output, (int, float)):
            macro = output

        if macro is None:
            continue

        try:
            label = float(np.clip(float(macro) / 5.0, 0.0, 1.0))
        except (TypeError, ValueError):
            continue

        rows.append({'resume': resume, 'job': job, 'label': label, 'source': 'hf_netsol'})

    rows = _dedupe(rows)
    print(f"  Skipped {skipped_invalid} invalid entries.", flush=True)
    print(f"  Final rows: {len(rows)}", flush=True)
    return rows


# ──────────────────────────────────────────────────────────────────────────────
# Management command
# ──────────────────────────────────────────────────────────────────────────────

class Command(BaseCommand):
    help = 'Download, clean, and preprocess HuggingFace datasets for ANN training'

    def add_arguments(self, parser):
        parser.add_argument('--dataset', type=str, default='all',
                            choices=['all', 'fit', 'netsol'])
        parser.add_argument('--limit',  type=int, default=0,
                            help='Max rows per dataset (0 = no limit)')
        parser.add_argument('--skip-features', action='store_true',
                            help='Skip embedding extraction (fast test)')
        parser.add_argument('--output', type=str, default=OUTPUT_CSV)
        parser.add_argument('--append', action='store_true')

    def handle(self, *args, **options):
        try:
            import pandas as pd
        except ImportError:
            raise CommandError('pandas required: pip install pandas')
        try:
            from datasets import load_dataset  # noqa
        except ImportError:
            raise CommandError('datasets required: pip install "datasets>=2.14.0"')

        dataset_choice = options['dataset']
        limit          = options['limit']
        skip_features  = options['skip_features']
        output_path    = Path(options['output'])
        append_mode    = options['append']

        output_path.parent.mkdir(parents=True, exist_ok=True)

        self.stdout.write(self.style.NOTICE('=' * 60))
        self.stdout.write(self.style.NOTICE('  SkillSevak — External Data Loader (v2)'))
        self.stdout.write(self.style.NOTICE('=' * 60))
        self.stdout.write(f"  Dataset : {dataset_choice}")
        self.stdout.write(f"  Limit   : {limit or 'none (all)'}")
        self.stdout.write(f"  Output  : {output_path}")
        self.stdout.write('')

        # ── 1. Download ──────────────────────────────────────────────────────
        all_rows = []

        if dataset_choice in ('all', 'fit'):
            try:
                rows = _load_fit_dataset(limit)
                all_rows.extend(rows)
                self.stdout.write(self.style.SUCCESS(
                    f"Dataset A (resume-job-fit): {len(rows)} balanced rows"
                ))
            except Exception as e:
                self.stdout.write(self.style.ERROR(f"Dataset A failed: {e}"))
                logger.exception("fit dataset load failed")

        if dataset_choice in ('all', 'netsol'):
            try:
                rows = _load_netsol_dataset(limit)
                all_rows.extend(rows)
                self.stdout.write(self.style.SUCCESS(
                    f"Dataset B (netsol-scores): {len(rows)} rows"
                ))
            except Exception as e:
                self.stdout.write(self.style.ERROR(f"Dataset B failed: {e}"))
                logger.exception("netsol dataset load failed")

        if not all_rows:
            raise CommandError('No data loaded.')

        self.stdout.write(f"\nTotal clean rows: {len(all_rows)}")

        # ── 2. Label sanity check ────────────────────────────────────────────
        labels = np.array([r['label'] for r in all_rows])
        self.stdout.write(f"Label distribution — "
                          f"min: {labels.min():.3f}, max: {labels.max():.3f}, "
                          f"mean: {labels.mean():.3f}, std: {labels.std():.3f}")
        high = (labels >= 0.5).sum()
        low  = (labels <  0.5).sum()
        self.stdout.write(f"High-score (>=0.5): {high} | Low-score (<0.5): {low}")

        if labels.std() < 0.10:
            self.stdout.write(self.style.WARNING(
                "WARNING: Label std < 0.10 — labels are very clustered. "
                "Training on this alone will hurt accuracy."
            ))

        # ── 3. Feature extraction ────────────────────────────────────────────
        if skip_features:
            self.stdout.write(self.style.WARNING('\n--skip-features: saving placeholder 50.0'))
            records = [{
                'semantic_similarity': 50.0, 'skill_match': 50.0,
                'experience_match': 50.0, 'education_match': 50.0,
                'profile_completeness': 50.0,
                'label': r['label'], 'source': r['source'],
            } for r in all_rows]
        else:
            self.stdout.write(self.style.NOTICE(
                f'\nExtracting features for {len(all_rows)} rows...'
            ))
            from ann.ml.text_features import TextFeatureExtractor
            extractor = TextFeatureExtractor()
            pairs = [(r['resume'], r['job']) for r in all_rows]
            feature_list = extractor.extract_batch(pairs, batch_size=50)
            records = []
            for row, feats in zip(all_rows, feature_list):
                sem, skl, exp, edu, pro = feats
                records.append({
                    'semantic_similarity':   round(sem, 2),
                    'skill_match':           round(skl, 2),
                    'experience_match':      round(exp, 2),
                    'education_match':       round(edu, 2),
                    'profile_completeness':  round(pro, 2),
                    'label':  round(float(row['label']), 4),
                    'source': row['source'],
                })

        # ── 4. Save ──────────────────────────────────────────────────────────
        df_new = pd.DataFrame(records)

        if append_mode and output_path.exists():
            df_old = pd.read_csv(output_path)
            df_out = pd.concat([df_old, df_new], ignore_index=True)
        else:
            df_out = df_new

        df_out.to_csv(output_path, index=False)

        # ── 5. Summary ───────────────────────────────────────────────────────
        self.stdout.write('')
        self.stdout.write(self.style.SUCCESS('=' * 60))
        self.stdout.write(self.style.SUCCESS('  Done!'))
        self.stdout.write(self.style.SUCCESS('=' * 60))
        self.stdout.write(f"Rows saved: {len(df_out)}")
        self.stdout.write(f"Output:     {output_path}")
        self.stdout.write('')
        for src, cnt in df_out['source'].value_counts().items():
            self.stdout.write(f"  {src}: {cnt}")
        self.stdout.write('')
        self.stdout.write('Label stats:')
        self.stdout.write(f"  mean={df_out['label'].mean():.3f} "
                          f"std={df_out['label'].std():.3f} "
                          f"min={df_out['label'].min():.3f} "
                          f"max={df_out['label'].max():.3f}")
        self.stdout.write('')
        self.stdout.write(self.style.SUCCESS(
            'Next: python manage.py train_model --use-real-data --epochs 150 --evaluate'
        ))
