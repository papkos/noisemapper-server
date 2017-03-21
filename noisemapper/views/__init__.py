from django.contrib.auth.decorators import login_required
from django.shortcuts import render

from noisemapper.models.recording import MIC_SOURCE_CHOICES
from .api_endpoints import *
from noisemapper.models import Recording


@login_required
def index(request):
    device_name_list = list(Recording.objects.all().values_list('device_name', flat=True).distinct())

    args = dict(
        device_name_list=device_name_list,
        mic_source_list=MIC_SOURCE_CHOICES,
    )
    return render(request, 'noisemapper/index.html', args)
