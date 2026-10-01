from django.apps import AppConfig


class QqConfig(AppConfig):
    name = 'qq'

    def ready(self):
        from . import signals  # noqa: F401
