from django.apps import AppConfig


class AbsenceConfig(AppConfig):
    name = 'absence'
    default_auto_field = 'django.db.models.AutoField'

    def ready(self):
        import absence.signals  # noqa: F401
