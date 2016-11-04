import datetime as dt


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


def settings_exposer_context_processor(request):
    from django.conf import settings

    defaults = {}

    exposed = getattr(settings, 'EXPOSED_TO_TEMPLATES', None)
    if exposed:
        defaults.update(exposed)

    return defaults
