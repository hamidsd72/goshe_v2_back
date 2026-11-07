from django.apps import AppConfig


class ConsultantAccountingConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'consultant_accounting'
    verbose_name = 'حسابداری مشاوران'

    def ready(self):
        from . import signals  # noqa: F401
