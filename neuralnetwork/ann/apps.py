from django.apps import AppConfig


class AnnConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'ann'

    def ready(self):
        """Import signals when app is ready."""
        import ann.signals  # noqa: F401
