from json import dumps, loads

import decimal as dec
from django.shortcuts import render

from noisemapper.models.recording import Recording
from noisemapper.utils import sjs
from .api_endpoints import *


def index(request):
    rounding = dec.Decimal('0.01')  # 1° lat = 110.5 km | 1° lon (in Oslo) = 55.6 km
    avg_or_max = 'avg'

    def _calc_key(loc: dict) -> (dec.Decimal, dec.Decimal):
        lat = dec.Decimal(loc['lat']).quantize(rounding, dec.ROUND_HALF_UP)
        lon = dec.Decimal(loc['lon']).quantize(rounding, dec.ROUND_HALF_UP)
        return lat, lon

    def _map_values(values, lower, higher, getter, setter):
        """
        Maps a range of values onto another range. Values should be encapsulated in something,
         and the getter will be used to extract the value, and the setter to write back the new one.

        :param values:
        :type values: [T]
        :param lower:
        :type lower: int | float
        :param higher:
        :type higher: int | float
        :param getter:
        :type getter: func(T) -> (int | float)
        :param setter:
        :type setter: func(T, int | float)
        :return:
        """
        minval = getter(min(values, key=getter))
        maxval = getter(max(values, key=getter))
        slope = (higher - lower) / (maxval - minval)
        for obj in values:
            val = getter(obj)
            new_val = lower + slope * (val - minval)
            setter(obj, new_val)


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


    clustered2 = []
    for key, datas in clustered.items():
        avg_avg = sum([data['avg'] for data in datas]) / len(datas)
        avg_max = sum([data['max'] for data in datas]) / len(datas)
        clustered2.append({
            'coordinates': {'lat': key[0], 'lon': key[1]},
            'avg': avg_avg,
            'max': avg_max,
        })
    def setter(obj, val):
        obj['display'] = val
    _map_values(clustered2, 1, 2, lambda x: x[avg_or_max], setter)

    args = dict(
        noise_data=dumps(data, default=sjs),
        clustered_data=dumps(clustered2, default=sjs),
        clustered_display=dumps(clustered2, default=sjs, indent=2)
    )
    return render(request, 'noisemapper/index.html', args)
