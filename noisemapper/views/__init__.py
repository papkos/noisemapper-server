from django.contrib.auth.decorators import login_required
from django.http.request import HttpRequest
from django.shortcuts import render

from noisemapper.models.recording import MIC_SOURCE_CHOICES
from noisemapper.permissions import can_download
from .api_endpoints import *
from noisemapper.models import Recording


@login_required
def index(request: HttpRequest):
    device_name_list = list(Recording.objects.all().values_list('device_name', flat=True).distinct())

    show_download = can_download(request.user)

    args = dict(
        device_name_list=device_name_list,
        mic_source_list=MIC_SOURCE_CHOICES,
        show_download=show_download,
    )
    return render(request, 'noisemapper/index.html', args)
