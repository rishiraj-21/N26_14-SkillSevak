"""
ANN Model Definition

Neural network for predicting match scores.
phase 5
Architecture :
- Input: 5 features (semantic, skill, experience, education, profile)
- Hidden: 64 → 32 → 16 neurons with ReLU
- Output: Match probability (0-1, scaled to 0-100)
"""

import logging

logger = logging.getLogger(__name__)

try:
    import torch
    import torch.nn as nn
    TORCH_AVAILABLE = True
except ImportError:
    TORCH_AVAILABLE = False
    logger.warning("PyTorch not installed. ANN model will not be available.")


if TORCH_AVAILABLE:
    class MatchPredictor(nn.Module):
        """
        Neural network to predict match scores.

        Input:  5 features (semantic, skill, experience, education, profile)
        Hidden: 64 → 32 → 16 (with ReLU activation)
        Output: Match probability (0-1, scaled to 0-100)

        Full implementation in Phase 5.
        """

        def __init__(self, input_size: int = 5):
            super().__init__()

            # Wider first layer + lighter dropout for better range coverage.
            # MSELoss in training (see train.py) + lower dropout fixes the
            # score-compression bug (model was predicting 35-70 instead of 0-100).
            self.network = nn.Sequential(
                nn.Linear(input_size, 128),
                nn.ReLU(),
                nn.LayerNorm(128),
                nn.Dropout(0.15),

                nn.Linear(128, 64),
                nn.ReLU(),
                nn.LayerNorm(64),
                nn.Dropout(0.10),

                nn.Linear(64, 32),
                nn.ReLU(),
                nn.LayerNorm(32),

                nn.Linear(32, 1),
                nn.Sigmoid()
            )

        def forward(self, x):
            """Forward pass returns match probability 0-1."""
            return self.network(x)

        def predict(self, features) -> float:
            """
            Predict match score for a single candidate-job pair.

            Args:
                features: [semantic, skill, experience, education, profile] (0-1 scaled)

            Returns:
                Match score 0-100
            """
            import numpy as np

            self.eval()
            with torch.no_grad():
                if isinstance(features, np.ndarray):
                    x = torch.FloatTensor(features)
                else:
                    x = torch.FloatTensor(features)

                if x.dim() == 1:
                    x = x.unsqueeze(0)

                output = self.forward(x)
                return float(output.item() * 100)
else:
    # Fallback when PyTorch is not available
    class MatchPredictor:
        """Placeholder when PyTorch is not installed."""

        def __init__(self, *args, **kwargs):
            logger.warning("PyTorch not available. Using weighted average fallback.")

        def predict(self, features) -> float:
            """Fallback to weighted average per PRD.md scoring formula."""
            import numpy as np
            # Weights: semantic=0.25, skills=0.35, experience=0.20, education=0.10, profile=0.10
            weights = np.array([0.25, 0.35, 0.20, 0.10, 0.10])
            features = np.array(features)
            return float(np.dot(features, weights) * 100)
