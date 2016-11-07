from json import dumps, loads

import decimal as dec
from django.shortcuts import render

from noisemapper.models.recording import Recording
from noisemapper.utils import sjs
from .api_endpoints import *


def index(request):
    rounding = dec.Decimal('0.0001')
    avg_or_max = 'max'

    def _calc_key(loc: dict) -> (dec.Decimal, dec.Decimal):
        lat = dec.Decimal(loc['lat']).quantize(rounding, dec.ROUND_HALF_UP)
        lon = dec.Decimal(loc['lon']).quantize(rounding, dec.ROUND_HALF_UP)
        return lat, lon

    data = []
    clustered = {}
    avg_min = 10000
    avg_max = 1
    for recording in Recording.objects.all():
        state = loads(recording.device_state)
        location = state['location']
        values = loads(recording.process_result)
        if values[avg_or_max] < avg_min:
            avg_min = values[avg_or_max]
        if values[avg_or_max] > avg_max:
            avg_max = values[avg_or_max]

        data.append({
            'coordinates': {'lat': location['lat'], 'lon': location['lon']},
            'avg': values['avg'],
            'max': values['max'],
        })
        clustered.setdefault(_calc_key(location), []).append({
            'coordinates': {'lat': location['lat'], 'lon': location['lon']},
            'avg': values['avg'],
            'max': values['max'],
        })

    for x in data:  # type: dict
        x['display'] = (x[avg_or_max] - avg_min) / avg_max

    clustered2 = []
    for key, datas in clustered.items():
        avg = sum([data[avg_or_max] for data in datas]) / len(datas)
        clustered2.append({
            'coordinates': {'lat': key[0], 'lon': key[1]},
            'display': (avg - avg_min) / avg_max
        })

    args = dict(noise_data=dumps(data, default=sjs), clustered_data=dumps(clustered2, default=sjs))
    return render(request, 'noisemapper/index.html', args)
