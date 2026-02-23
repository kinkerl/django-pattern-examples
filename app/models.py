from django.db import models
from extended_choices import Choices
from django.utils.module_loading import import_string


BACKENDS = Choices(
    ("FIRSTBACKEND", "app.backends.FirstBackend", "First Backend"),
    ("SECONDBACKEND", "app.backends.SecondBackend", "Second Backend"),
)


class Account(models.Model):
    owner = models.CharField(max_length=100)
    balance = models.IntegerField(default=0)


class AccountWithDynamicBackend(models.Model):
    owner = models.CharField(max_length=100)
    balance = models.IntegerField(default=0)

    backend_class = models.CharField(max_length=255, choices=BACKENDS)
    backend_config = models.JSONField(blank=True, default=dict)

    @property
    def backend(self):
        AccountBackend = import_string(self.backend_class)
        return AccountBackend(**self.backend_config)
