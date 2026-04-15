"""
Train Model Management Command

Train the ANN match prediction model.

Usage:
    python manage.py train_model
    python manage.py train_model --epochs 200 --samples 20000
    python manage.py train_model --use-real-data
"""

from django.core.management.base import BaseCommand, CommandError


class Command(BaseCommand):
    help = 'Train the ANN match prediction model'

    def add_arguments(self, parser):
        parser.add_argument(
            '--epochs',
            type=int,
            default=100,
            help='Number of training epochs (default: 100)'
        )
        parser.add_argument(
            '--samples',
            type=int,
            default=10000,
            help='Number of synthetic training samples (default: 10000)'
        )
        parser.add_argument(
            '--batch-size',
            type=int,
            default=128,
            help='Training batch size (default: 128)'
        )
        parser.add_argument(
            '--learning-rate',
            type=float,
            default=0.001,
            help='Learning rate (default: 0.001)'
        )
        parser.add_argument(
            '--use-real-data',
            action='store_true',
            help='Use real recruiter decisions for training (if available)'
        )
        parser.add_argument(
            '--model-path',
            type=str,
            default=None,
            help='Custom path to save trained model'
        )
        parser.add_argument(
            '--no-early-stopping',
            action='store_true',
            help='Disable early stopping'
        )
        parser.add_argument(
            '--evaluate',
            action='store_true',
            help='Evaluate model after training'
        )
        parser.add_argument(
            '--seed',
            type=int,
            default=42,
            help='Random seed for reproducibility (default: 42)'
        )

    def handle(self, *args, **options):
        try:
            import torch
        except ImportError:
            raise CommandError(
                'PyTorch is required for training. '
                'Install with: pip install torch'
            )

        from ann.ml.train import ModelTrainer

        self.stdout.write(self.style.NOTICE('=' * 60))
        self.stdout.write(self.style.NOTICE('  SkillSevak ANN Model Training'))
        self.stdout.write(self.style.NOTICE('  Phase 5: Match Prediction Model'))
        self.stdout.write(self.style.NOTICE('=' * 60))
        self.stdout.write('')

        # Initialize trainer
        trainer = ModelTrainer(model_path=options['model_path'])

        # Update learning rate if specified
        if options['learning_rate'] != 0.001:
            for param_group in trainer.optimizer.param_groups:
                param_group['lr'] = options['learning_rate']
            self.stdout.write(f"Learning rate: {options['learning_rate']}")

        # Get training data
        X, y = None, None

        if options['use_real_data']:
            self.stdout.write(self.style.NOTICE('Attempting to use real recruiter data...'))
            X, y = trainer.generate_real_data_from_db()
            if X is not None:
                self.stdout.write(self.style.SUCCESS(
                    f'Loaded {len(X)} samples from real recruiter decisions'
                ))
            else:
                self.stdout.write(self.style.WARNING(
                    'Insufficient real data. Falling back to synthetic data.'
                ))

        if X is None:
            self.stdout.write(self.style.NOTICE(
                f'Generating {options["samples"]} synthetic training samples...'
            ))
            X, y = trainer.generate_synthetic_data(
                n_samples=options['samples'],
                seed=options['seed']
            )
            self.stdout.write(self.style.SUCCESS(
                f'Generated {len(X)} synthetic samples'
            ))

        # Display data statistics
        self.stdout.write('')
        self.stdout.write('Data Statistics:')
        self.stdout.write(f'  Samples: {len(X)}')
        self.stdout.write(f'  Features: {X.shape[1]}')
        self.stdout.write(f'  Target range: {y.min():.3f} - {y.max():.3f}')
        self.stdout.write(f'  Target mean: {y.mean():.3f}')
        self.stdout.write('')

        # Training parameters
        self.stdout.write('Training Parameters:')
        self.stdout.write(f'  Epochs: {options["epochs"]}')
        self.stdout.write(f'  Batch size: {options["batch_size"]}')
        self.stdout.write(f'  Early stopping: {not options["no_early_stopping"]}')
        self.stdout.write('')

        # Start training
        self.stdout.write(self.style.NOTICE('Starting training...'))
        self.stdout.write('')

        try:
            history = trainer.train(
                X=X,
                y=y,
                epochs=options['epochs'],
                batch_size=options['batch_size'],
                early_stopping_patience=20 if not options['no_early_stopping'] else options['epochs'],
                verbose=True
            )

            self.stdout.write('')
            self.stdout.write(self.style.SUCCESS('=' * 60))
            self.stdout.write(self.style.SUCCESS('  Training Complete!'))
            self.stdout.write(self.style.SUCCESS('=' * 60))
            self.stdout.write('')
            self.stdout.write(f"Epochs trained: {history['epochs_trained']}")
            self.stdout.write(f"Best validation loss: {history['best_val_loss']:.6f}")
            self.stdout.write(f"Model saved to: {trainer.model_path}")

            # Evaluate if requested
            if options['evaluate']:
                self.stdout.write('')
                self.stdout.write(self.style.NOTICE('Evaluating model...'))

                # Load the best model
                trainer.load_model()

                # Evaluate on validation set (last 20%)
                split_idx = int(len(X) * 0.8)
                X_val, y_val = X[split_idx:], y[split_idx:]

                metrics = trainer.evaluate(X_val, y_val)

                self.stdout.write('')
                self.stdout.write('Evaluation Metrics:')
                self.stdout.write(f"  RMSE: {metrics['rmse']:.2f} points")
                self.stdout.write(f"  MAE: {metrics['mae']:.2f} points")
                self.stdout.write(f"  Accuracy (within 5%): {metrics['accuracy_within_5pct']:.1f}%")
                self.stdout.write(f"  Accuracy (within 10%): {metrics['accuracy_within_10pct']:.1f}%")

            self.stdout.write('')
            self.stdout.write(self.style.SUCCESS(
                'Model is now available for match predictions!'
            ))
            self.stdout.write(self.style.SUCCESS(
                'Run: python manage.py runserver to test'
            ))

        except Exception as e:
            raise CommandError(f'Training failed: {str(e)}')
