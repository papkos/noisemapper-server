
from django.db import models

from noisemapper.models.base import NoiseMapperBase

__all__ = ('Recording',)


class Recording(NoiseMapperBase, models.Model):

    timestamp = models.DateTimeField()
    process_result = models.TextField()
    device_state = models.TextField(blank=True, null=True)
    lat = models.FloatField(blank=True, null=True)
    lon = models.FloatField(blank=True, null=True)

    uploaded_at = models.DateTimeField(auto_now_add=True)
    misc_data = models.TextField(blank=True, null=True)
