from json import dumps, loads

from django.shortcuts import render

from noisemapper.models.recording import Recording
from noisemapper.utils import sjs
from .api_endpoints import *


def index(request):

    data = []
    for recording in Recording.objects.all():
        state = loads(recording.device_state)
        location = state['location']
        values = loads(recording.process_result)

        data.append({
            'coordinates': {'lat': location['lat'], 'lon': location['lon']},
            'avg': values['avg'],
            'max': values['max'],
        })

    args = dict(noise_data=dumps(data, default=sjs))
    return render(request, 'noisemapper/index.html', args)
