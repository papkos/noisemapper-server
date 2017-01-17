import base64
import datetime as dt
import decimal as dec
from functools import wraps

from django.conf import settings
from django.http.response import HttpResponse
from django.views.decorators.csrf import csrf_exempt

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
            api_auth = request.META.get('HTTP_X_NOISEMAPPER_API_AUTH', '')
            if api_auth:
                api_auth = base64.b64decode(api_auth).decode('utf-8')
            if api_auth == api_secret:
                return view_func(request, *args, **kwargs)

            else:
                return HttpResponse(status=401, content="Unauthorized!")
        return _wrapped_view

    if function:
        return decorator(csrf_exempt(function))
    return csrf_exempt(decorator)
