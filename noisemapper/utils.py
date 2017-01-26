import base64
import datetime as dt
import decimal as dec
import logging
from functools import wraps
from typing import Callable, Iterable, Any, T, Tuple

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

    def get(self):
        raise NotImplementedError


def cluster_data(data: Iterable[T], key_func: Callable[[T], Any], is_same_func: Callable[[T, T], bool],
                 aggregator: Aggregator, retain_original=False):
    clustered = {}

    for datapoint in data:
        key = key_func(datapoint)
        for existing_key in clustered.keys():
            if is_same_func(existing_key, key):
                key = existing_key
                break
        clustered.setdefault(key, []).append(datapoint)

    for key, values in clustered.items():
        for x in values:
            aggregator(x)
        if retain_original:
            clustered[key] = dict(original=values, aggregated_value=aggregator.get())
        else:
            clustered[key] = aggregator.get()

    return clustered


def distance(point_a: Tuple[float, float], point_b: Tuple[float, float]) -> float:
    dist_m = gpxpy.geo.haversine_distance(point_a[0], point_a[1], point_b[0], point_b[1])
    return dist_m


class Averager(Aggregator):

    def __init__(self, extractor):
        self.count = 0
        self.sum = 0.0
        self.extractor = extractor

    def __call__(self, new):
        self.count += 1
        self.sum += self.extractor(new)
        return self

    def get(self):
        return self.sum / self.count


def recording_to_json(recording: Recording) -> dict:
    return dict(
        uuid=recording.uuid,
        lat=recording.lat,
        lon=recording.lon,
        avg=recording.measurement_avg,
        max=recording.measurement_max,
        device_name=recording.device_name,
    )
