"""
Model Training Pipeline

Training pipeline for the match prediction ANN model.
Phase 5 implementation 

Usage:
    python manage.py train_model --epochs 100 --samples 10000
"""

import logging
import os
from pathlib import Path
from typing import Tuple, Optional

import numpy as np

logger = logging.getLogger(__name__)

try:
    import torch
    import torch.nn as nn
    from torch.utils.data import DataLoader, TensorDataset
    TORCH_AVAILABLE = True
except ImportError:
    TORCH_AVAILABLE = False
    logger.warning("PyTorch not installed. Training will not be available.")

try:
    from sklearn.model_selection import train_test_split
    SKLEARN_AVAILABLE = True
except ImportError:
    SKLEARN_AVAILABLE = False
    logger.warning("scikit-learn not installed. Using manual train/test split.")


class ModelTrainer:
    """
    Train the match prediction model.

    Supports:
    - Synthetic data generation for initial training
    - Real data training from recruiter feedback (future)
    - Model checkpointing and early stopping
    """

    def __init__(self, model_path: Optional[str] = None):
        if not TORCH_AVAILABLE:
            raise RuntimeError("PyTorch is required for training. Install with: pip install torch")

        from .model import MatchPredictor

        self.model = MatchPredictor()
        self.model_path = Path(model_path or 'ann/ml/weights/match_predictor.pth')

        # MSELoss penalises extremes quadratically → forces model to cover 0-100
        # (SmoothL1 with beta=0.1 behaved like L1/median loss → score compression)
        self.criterion = nn.MSELoss()
        self.optimizer = torch.optim.Adam(
            self.model.parameters(), lr=0.001, weight_decay=1e-4
        )

        # Training history
        self.history = {
            'train_loss': [],
            'val_loss': [],
            'best_val_loss': float('inf'),
            'epochs_trained': 0,
        }

    def generate_synthetic_data(self, n_samples: int = 10000, seed: int = 42) -> Tuple[np.ndarray, np.ndarray]:
        """
        Generate synthetic training data.

        Simulates realistic match scenarios where:
        - High skill + high semantic similarity = high match
        - Low experience for senior roles = lower match
        - Various combinations with controlled noise

        In production, this would be replaced with real recruiter feedback:
        - Hired candidates = high match (0.8-1.0)
        - Rejected candidates = low match (0.0-0.4)
        - Shortlisted = medium match (0.5-0.8)

        Returns:
            X: Feature array (n_samples, 5)
            y: Target match scores (n_samples,)
        """
        np.random.seed(seed)

        # Scenario-based generation: sample label ranges directly so labels are
        # uniformly spread across [0.0, 1.0]. The old formula approach clustered
        # labels around 0.55-0.65, causing the model to collapse to predicting
        # the mean for every input.
        #
        # Each scenario defines plausible feature ranges for that quality tier.
        # (label_lo, label_hi, [(sem_lo,sem_hi), (skl_lo,skl_hi),
        #                        (exp_lo,exp_hi), (edu_lo,edu_hi), (pro_lo,pro_hi)])
        scenarios = [
            (0.85, 1.00, [(0.80, 1.0), (0.80, 1.0), (0.70, 1.0), (0.60, 1.0), (0.65, 1.0)]),  # Excellent
            (0.68, 0.85, [(0.60, 0.90), (0.60, 0.90), (0.55, 0.85), (0.45, 0.80), (0.50, 0.85)]),  # Good
            (0.48, 0.68, [(0.35, 0.70), (0.35, 0.70), (0.30, 0.70), (0.25, 0.65), (0.30, 0.70)]),  # Average
            (0.25, 0.48, [(0.15, 0.55), (0.10, 0.50), (0.10, 0.50), (0.10, 0.55), (0.10, 0.55)]),  # Low
            (0.08, 0.25, [(0.00, 0.35), (0.00, 0.30), (0.00, 0.35), (0.00, 0.35), (0.00, 0.40)]),  # Poor
            (0.00, 0.08, [(0.00, 0.15), (0.00, 0.12), (0.00, 0.15), (0.00, 0.15), (0.00, 0.20)]),  # Clearly Bad
        ]

        n_per_scenario = n_samples // len(scenarios)
        remainder = n_samples - n_per_scenario * len(scenarios)

        X = []
        y = []

        for i, (label_lo, label_hi, feat_ranges) in enumerate(scenarios):
            count = n_per_scenario + (1 if i < remainder else 0)
            for _ in range(count):
                features = []
                for (lo, hi) in feat_ranges:
                    val = np.random.uniform(lo, hi)
                    # Small noise simulates real-world measurement variance
                    val = float(np.clip(val + np.random.normal(0, 0.03), 0.0, 1.0))
                    features.append(val)
                label = np.random.uniform(label_lo, label_hi)
                X.append(features)
                y.append(label)

        # Shuffle to remove scenario-ordering bias in DataLoader
        indices = np.random.permutation(len(X))
        X = np.array(X, dtype=np.float32)[indices]
        y = np.array(y, dtype=np.float32)[indices]

        return X, y

    def generate_real_data_from_db(self) -> Tuple[Optional[np.ndarray], Optional[np.ndarray]]:
        """
        Generate training data from real recruiter decisions.

        Maps application statuses to match scores:
        - 'hired': 0.90-1.00
        - 'interview': 0.70-0.85
        - 'reviewed': 0.50-0.70
        - 'applied': 0.40-0.60 (neutral, not scored)
        - 'rejected': 0.10-0.35

        Returns:
            X, y if sufficient data exists, else None, None
        """
        try:
            from ann.models import MatchScore, Application

            # Get applications with decisions
            applications = Application.objects.exclude(
                status='applied'  # Exclude pending applications
            ).select_related('candidate', 'job')

            if applications.count() < 100:
                logger.info(f"Only {applications.count()} decided applications. Need 100+ for real data training.")
                return None, None

            X = []
            y = []

            status_to_score = {
                'hired': (0.90, 1.00),
                'interview': (0.70, 0.85),
                'reviewed': (0.50, 0.70),
                'rejected': (0.10, 0.35),
            }

            for app in applications:
                try:
                    # Get the match score for this candidate-job pair
                    match = MatchScore.objects.get(
                        candidate=app.candidate.candidateprofile,
                        job=app.job
                    )

                    # Features (normalized to 0-1)
                    features = [
                        match.semantic_similarity / 100,
                        match.skill_match_score / 100,
                        match.experience_match_score / 100,
                        match.education_match_score / 100,
                        match.profile_completeness_score / 100,
                    ]

                    # Target from recruiter decision
                    score_range = status_to_score.get(app.status)
                    if score_range:
                        target = np.random.uniform(*score_range)
                        X.append(features)
                        y.append(target)

                except Exception:
                    continue

            if len(X) < 50:
                logger.info(f"Only {len(X)} valid samples. Need 50+ for training.")
                return None, None

            logger.info(f"Generated {len(X)} training samples from real recruiter decisions")
            return np.array(X, dtype=np.float32), np.array(y, dtype=np.float32)

        except Exception as e:
            logger.warning(f"Failed to generate real data: {e}")
            return None, None

    def load_external_data_csv(
        self, path: str = 'ann/ml/data/external_training_data.csv'
    ) -> Tuple[Optional[np.ndarray], Optional[np.ndarray]]:
        """
        Load pre-processed external dataset from CSV.

        The CSV is produced by: python manage.py load_external_data

        Returns:
            X (n, 5) float32 normalized to 0-1, y (n,) float32
            or (None, None) if the file doesn't exist.
        """
        try:
            import pandas as pd
        except ImportError:
            logger.warning("pandas not installed — cannot load external CSV")
            return None, None

        p = Path(path)
        if not p.exists():
            logger.info(
                f"No external data CSV at {path}. "
                "Run: python manage.py load_external_data"
            )
            return None, None

        try:
            df = pd.read_csv(p)
            feature_cols = [
                'semantic_similarity', 'skill_match', 'experience_match',
                'education_match', 'profile_completeness',
            ]
            missing = [c for c in feature_cols if c not in df.columns]
            if missing:
                logger.warning(f"External CSV missing columns: {missing}. Skipping.")
                return None, None

            # Features are stored in 0-100 range → normalize to 0-1
            X = (df[feature_cols].values / 100.0).astype(np.float32)
            y = df['label'].values.astype(np.float32)

            # Sanity-clip
            X = np.clip(X, 0.0, 1.0)
            y = np.clip(y, 0.0, 1.0)

            logger.info(f"Loaded {len(X)} external training samples from {path}")
            return X, y

        except Exception as e:
            logger.warning(f"Failed to load external CSV {path}: {e}")
            return None, None

    # Sentinel used by retrain_model_task to skip CSV auto-merge
    _NO_EXTERNAL_CSV = '__none__'

    def train(
        self,
        X: Optional[np.ndarray] = None,
        y: Optional[np.ndarray] = None,
        epochs: int = 100,
        batch_size: int = 64,
        validation_split: float = 0.2,
        early_stopping_patience: int = 10,
        verbose: bool = True,
        external_csv_path: Optional[str] = None,
    ) -> dict:
        """
        Train the model.

        Args:
            X: Feature array (n_samples, 5). If None, generates synthetic data.
            y: Target array (n_samples,). If None, generates synthetic data.
            epochs: Number of training epochs
            batch_size: Training batch size
            validation_split: Fraction of data for validation
            early_stopping_patience: Stop if no improvement for N epochs
            verbose: Print progress
            external_csv_path: Path to external CSV. Pass ModelTrainer._NO_EXTERNAL_CSV
                               to skip CSV loading entirely (e.g., when caller has
                               already merged external data into X/y).

        Returns:
            Training history dict
        """
        # Load and merge external CSV unless caller opted out
        if external_csv_path != self._NO_EXTERNAL_CSV:
            X_ext, y_ext = self.load_external_data_csv(
                external_csv_path or 'ann/ml/data/external_training_data.csv'
            )
        else:
            X_ext, y_ext = None, None

        # Generate / merge data sources
        if X is None or y is None:
            if verbose:
                print("Generating synthetic training data...")
            X_syn, y_syn = self.generate_synthetic_data()
            if X_ext is not None:
                if verbose:
                    print(f"Merging {len(X_ext)} external samples with {len(X_syn)} synthetic samples.")
                X = np.concatenate([X_ext, X_syn])
                y = np.concatenate([y_ext, y_syn])
            else:
                X, y = X_syn, y_syn
        elif X_ext is not None:
            # Caller passed explicit data — still merge external CSV in
            if verbose:
                print(f"Merging {len(X_ext)} external samples with {len(X)} provided samples.")
            X = np.concatenate([X, X_ext])
            y = np.concatenate([y, y_ext])

        # Split data
        if SKLEARN_AVAILABLE:
            X_train, X_val, y_train, y_val = train_test_split(
                X, y, test_size=validation_split, random_state=42
            )
        else:
            # Manual split
            split_idx = int(len(X) * (1 - validation_split))
            indices = np.random.permutation(len(X))
            X, y = X[indices], y[indices]
            X_train, X_val = X[:split_idx], X[split_idx:]
            y_train, y_val = y[:split_idx], y[split_idx:]

        if verbose:
            print(f"Training samples: {len(X_train)}, Validation samples: {len(X_val)}")

        # Create data loaders
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

        # Cosine annealing scheduler — gradually reduces LR to near-zero,
        # helping the model settle into sharper minima without oscillating.
        scheduler = torch.optim.lr_scheduler.CosineAnnealingLR(
            self.optimizer, T_max=epochs, eta_min=1e-5
        )

        # Training loop
        best_val_loss = float('inf')
        patience_counter = 0

        for epoch in range(epochs):
            # Training phase
            self.model.train()
            train_loss = 0.0

            for X_batch, y_batch in train_loader:
                self.optimizer.zero_grad()
                outputs = self.model(X_batch)
                loss = self.criterion(outputs, y_batch)
                loss.backward()
                self.optimizer.step()
                train_loss += loss.item()

            train_loss /= len(train_loader)
            scheduler.step()

            # Validation phase
            self.model.eval()
            val_loss = 0.0

            with torch.no_grad():
                for X_batch, y_batch in val_loader:
                    outputs = self.model(X_batch)
                    val_loss += self.criterion(outputs, y_batch).item()

            val_loss /= len(val_loader)

            # Record history
            self.history['train_loss'].append(train_loss)
            self.history['val_loss'].append(val_loss)

            # Check for improvement
            if val_loss < best_val_loss:
                best_val_loss = val_loss
                patience_counter = 0
                self.save_model()
                if verbose and (epoch + 1) % 10 == 0:
                    print(f"  [Checkpoint saved - new best]")
            else:
                patience_counter += 1

            # Logging
            if verbose and (epoch + 1) % 10 == 0:
                print(f"Epoch {epoch + 1}/{epochs} - Train Loss: {train_loss:.4f}, Val Loss: {val_loss:.4f}")

            # Early stopping
            if patience_counter >= early_stopping_patience:
                if verbose:
                    print(f"\nEarly stopping at epoch {epoch + 1} (no improvement for {early_stopping_patience} epochs)")
                break

        self.history['best_val_loss'] = best_val_loss
        self.history['epochs_trained'] = epoch + 1

        if verbose:
            print(f"\nTraining complete. Best validation loss: {best_val_loss:.4f}")

        return self.history

    def save_model(self):
        """Save model weights to disk."""
        # Create directory if it doesn't exist
        self.model_path.parent.mkdir(parents=True, exist_ok=True)

        torch.save(self.model.state_dict(), self.model_path)
        logger.info(f"Model saved to {self.model_path}")

    def load_model(self):
        """Load model weights from disk."""
        if self.model_path.exists():
            self.model.load_state_dict(torch.load(self.model_path, weights_only=True))
            self.model.eval()
            logger.info(f"Model loaded from {self.model_path}")
            return True
        else:
            logger.warning(f"No model found at {self.model_path}")
            return False

    def evaluate(self, X: np.ndarray, y: np.ndarray) -> dict:
        """
        Evaluate model performance.

        Returns:
            Dict with MSE, MAE, and accuracy metrics
        """
        self.model.eval()

        with torch.no_grad():
            X_tensor = torch.FloatTensor(X)
            predictions = self.model(X_tensor).numpy().flatten()

        # Scale predictions to 0-100 for interpretability
        predictions_scaled = predictions * 100
        y_scaled = y * 100

        # Calculate metrics
        mse = np.mean((predictions_scaled - y_scaled) ** 2)
        mae = np.mean(np.abs(predictions_scaled - y_scaled))
        rmse = np.sqrt(mse)

        # Accuracy within thresholds
        within_5 = np.mean(np.abs(predictions_scaled - y_scaled) <= 5) * 100
        within_10 = np.mean(np.abs(predictions_scaled - y_scaled) <= 10) * 100

        return {
            'mse': mse,
            'mae': mae,
            'rmse': rmse,
            'accuracy_within_5pct': within_5,
            'accuracy_within_10pct': within_10,
        }
