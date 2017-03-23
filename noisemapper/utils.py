import base64
import datetime as dt
import decimal as dec
import json
import logging
from collections import OrderedDict
from functools import wraps
from typing import Callable, Iterable, Any, T, Tuple, List, Optional

import gpxpy.geo
from django.conf import settings
from django.http.response import HttpResponse
from django.views.decorators.csrf import csrf_exempt

from noisemapper.models.recording import Recording

__all__ = ('sjs',)


class SmartJsonSerializer(object):
    def __init__(self):
        self._type_processors = {}

    def __call__(self, obj):
        obj_type = type(obj)
        if obj_type in self._type_processors:
            return self._type_processors[obj_type](obj)

    def register(self, obj_type, **options):
        def decorator(f):
            self._type_processors[obj_type] = f
            return f
        return decorator


sjs = SmartJsonSerializer()


@sjs.register(dt.datetime)
def _datetime_processor(obj: dt.datetime):
    return obj.strftime('%Y-%m-%d %H:%M:%S')


@sjs.register(dec.Decimal)
def _decimal_processor(obj: dec.Decimal):
    return str(obj)


def settings_exposer_context_processor(request):
    from django.conf import settings

    defaults = {}

    exposed = getattr(settings, 'EXPOSED_TO_TEMPLATES', None)
    if exposed:
        defaults.update(exposed)

    return defaults


def api_protect(function=None):
    """
    Decorator for views that are API-usage only. Checks for the custom
    HTTP header ``X-Noisemapper-Api-Auth`` and its value, which should match
    the settings.API_SECRET value.
    Also switches off CSRF protection for the view.
    """

    api_secret = settings.API_SECRET

    def decorator(view_func):
        @wraps(view_func)
        def _wrapped_view(request, *args, **kwargs):
            try:
                api_auth = request.META.get('HTTP_X_NOISEMAPPER_API_AUTH', '')
                if api_auth:
                    api_auth = base64.b64decode(api_auth).decode('utf-8')
                if api_auth == api_secret:
                    logging.info("Auth'd request to %s" % request.path_info)
                    return view_func(request, *args, **kwargs)

            except Exception as e:
                logging.exception("Unauthorized request to %s" % request.path_info)
                return HttpResponse(status=401, content="Unauthorized!")

        return _wrapped_view

    if function:
        return decorator(csrf_exempt(function))
    return csrf_exempt(decorator)


class RequestLoggerMiddleware(object):
    def __init__(self, get_response):
        self.get_response = get_response
        # One-time configuration and initialization.

    def __call__(self, request):
        # Code to be executed for each request before
        # the view (and later middleware) are called.

        logging.info("Processing request to %s" % request.path_info)

        response = self.get_response(request)

        # Code to be executed for each request/response after
        # the view is called.

        return response


class Aggregator(object):

    def __call__(self, new):
        raise NotImplementedError

    def get(self) -> Tuple[Any, float, Optional[List[dict]]]:
        raise NotImplementedError


def cluster_data(data: Iterable[T], key_func: Callable[[T], Any], is_same_func: Callable[[T, T], bool],
                 aggregator_factory: Callable[[], Aggregator], retain_original=False):
    clustered = {}

    for datapoint in data:
        key = key_func(datapoint)
        for existing_key in clustered.keys():
            if is_same_func(existing_key, key):
                key = existing_key
                break
        clustered.setdefault(key, []).append(datapoint)

    clustered_2 = dict()
    for key, values in clustered.items():
        aggregator = aggregator_factory()  # Create a new one for each cluster
        for x in values:
            aggregator(x)

        new_key, new_value, extra_attrs = aggregator.get()
        if not new_key:
            # For simple aggregators that don't modify the key
            new_key = key
        if retain_original:
            if extra_attrs:
                for value, extra_attr in zip(values, extra_attrs):
                    for k, v in extra_attr.items():
                        setattr(value, k, v)
            clustered_2[new_key] = dict(original=values, aggregated_value=new_value)
        else:
            clustered_2[new_key] = new_value

    return clustered_2


def distance(point_a: Tuple[float, float], point_b: Tuple[float, float]) -> float:
    dist_m = gpxpy.geo.haversine_distance(point_a[0], point_a[1], point_b[0], point_b[1])
    return dist_m


class Averager(Aggregator):

    def __init__(self, extractor):
        self.count = 0
        self.sum = 0.0
        self.extractor = extractor

    def __call__(self, new):
        extracted = self.extractor(new)
        if isinstance(extracted, tuple):
            suminc, countinc = extracted
        else:
            suminc = extracted
            countinc = 1
        self.sum += suminc
        self.count += countinc
        return self

    def get(self):
        return None, dec.Decimal(self.sum) / dec.Decimal(self.count), None


class GeoWeightedMiddle(Aggregator):

    def __init__(self, extractor):
        self.extractor = extractor
        self.locations = []  # (lat, lon)
        self.values = []

    def __call__(self, new):
        lat, lon, value = self.extractor(new)
        self.locations.append((lat, lon))
        self.values.append(value)
        return self

    def get(self):
        avg_lat = avg_lon = 0
        for loc in self.locations:
            avg_lat += loc[0]
            avg_lon += loc[1]
        avg_lat /= len(self.locations)
        avg_lon /= len(self.locations)
        geo_mid = (avg_lat, avg_lon)

        avg_value = total_weight = 0
        weights = []
        for loc, value in zip(self.locations, self.values):
            dist = distance(geo_mid, loc)
            if dist == 0:
                dist = 1
            weight = 1 / dist
            weights.append(weight)
            avg_value += value * weight
            total_weight += weight
        avg_value /= total_weight
        return geo_mid, avg_value, [{'weight': weight} for weight in weights]


def recording_to_json(recording: Recording) -> dict:
    ret = dict(
        uuid=recording.uuid,
        lat=recording.lat,
        lon=recording.lon,
        avg=recording.measurement_avg,
        max=recording.measurement_max,
        device_name=recording.device_name,
        timestamp=recording.timestamp.strftime('%Y-%m-%d %H:%M:%S'),
        proximity=json.loads(recording.device_state).get('proximityText', ''),
    )

    if hasattr(recording, 'weight'):
        ret.update(weight=getattr(recording, 'weight'))

    if hasattr(recording, 'deviation'):
        ret.update(deviation=getattr(recording, 'deviation'))

    return ret


def recording_to_json2(recording: Recording) -> dict:
    ret = OrderedDict()
    ret.update(timestamp=recording.timestamp.strftime('%Y-%m-%d %H:%M:%S'))
    ret.update(uuid=recording.uuid)
    ret.update(avg=recording.measurement_avg)
    ret.update(max=recording.measurement_max)
    ret.update(device_name=recording.device_name)
    ret.update(mic_source=recording.mic_source)
    ret.update(proximity=json.loads(recording.device_state).get('proximityText', ''))

    if hasattr(recording, 'weight'):
        ret.update(weight=getattr(recording, 'weight'))

    if hasattr(recording, 'deviation'):
        ret.update(deviation=getattr(recording, 'deviation'))

    return ret
