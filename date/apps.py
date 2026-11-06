from django.apps import AppConfig


class DateConfig(AppConfig):
    name = 'date'
    
    def ready(self):
        from . import signals