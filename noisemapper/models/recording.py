
from django.db import models

from noisemapper.models.base import NoiseMapperBase

__all__ = ('Recording',)


class Recording(NoiseMapperBase, models.Model):

    uuid = models.CharField(max_length=36, blank=True, null=True)
    device_name = models.CharField(max_length=200, blank=True, null=True)

    timestamp = models.DateTimeField()
    process_result = models.TextField()
    device_state = models.TextField(blank=True, null=True)
    lat = models.FloatField(blank=True, null=True)
    lon = models.FloatField(blank=True, null=True)

    uploaded_at = models.DateTimeField(auto_now_add=True)
    misc_data = models.TextField(blank=True, null=True)

    measurement_max = models.FloatField(blank=True, null=True)
    measurement_avg = models.FloatField(blank=True, null=True)
