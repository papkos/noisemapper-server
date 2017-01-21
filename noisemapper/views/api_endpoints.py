import base64
import datetime as dt
import decimal as dec
import logging
import os
from json import loads, dumps

from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.http.request import HttpRequest
from django.http.response import HttpResponseNotAllowed, HttpResponse, JsonResponse

from noisemapper.models.recording import Recording
from noisemapper.utils import sjs, api_protect

__all__ = ('api_upload_recording', 'api_upload_recording_batch',
           'api_get_clustered_data', 'api_get_nonclustered_data',
           'api_manual', 'api_echo')


@api_protect
def api_upload_recording(request):
    device_name = _get_device_name(request)

    if request.method == 'POST':
        data = loads(request.body.decode("utf-8"))

        recording = _create_recording(data)
        recording.device_name = device_name
        recording.save()

        response = dict(
            success=True,
            server_id=recording.pk,
        )
        return HttpResponse(dumps(response, default=sjs))
    else:
        return HttpResponseNotAllowed(['POST'])


def _create_recording(json_data) -> Recording:
    location = json_data['state']['location']

    recording = Recording()

    if 'uuid' in json_data:
        recording.uuid = json_data['uuid']

    recording.timestamp = dt.datetime.strptime(json_data['timestamp'], '%Y-%m-%d %H:%M:%S')
    recording.process_result = dumps(json_data['processResult'], default=sjs)
    recording.device_state = dumps(json_data['state'], default=sjs)
    recording.lat = float(location['lat'])
    recording.lon = float(location['lon'])
    return recording


def _get_device_name(request: HttpRequest) -> str:
    device_name = request.META.get('HTTP_X_NOISEMAPPER_API_DEVICE_NAME', '')
    if device_name:
        device_name = base64.b64decode(device_name).decode('utf-8')

    return device_name


@api_protect
def api_upload_recording_batch(request):
    device_name = _get_device_name(request)

    if request.method == 'POST':
        data = loads(request.body.decode("utf-8"))
        logging.info("Received %d ProcessedRecords" % len(data))

        uuids_processed = []
        for processed_record in data:
            recording = _create_recording(processed_record)
            recording.device_name = device_name
            recording.save()

            if 'file' in processed_record:
                try:
                    full_filename = settings.FILENAME_PATTERN % recording.uuid
                    full_filename = os.path.join(settings.SNIPPET_STORAGE_DIR, full_filename)
                    with open(full_filename, "wb") as fh:
                        fh.write(base64.b64decode(processed_record['file']))
                except:
                    logging.exception("Couldn't decode or save the uploaded file for %s" % recording.uuid)

            uuids_processed.append(recording.uuid)

        response = dict(
            success=True,
            uuids_processed=uuids_processed,
        )
        return HttpResponse(dumps(response, default=sjs))
    else:
        return HttpResponseNotAllowed(['POST'])


def map_values(values, lower, higher, getter, setter) -> None:
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
    """
    minval = getter(min(values, key=getter))
    maxval = getter(max(values, key=getter))
    try:
        slope = (higher - lower) / (maxval - minval)
    except ZeroDivisionError:
        slope = 0
    for obj in values:
        val = getter(obj)
        new_val = lower + slope * (val - minval)
        setter(obj, new_val)


def func_sum(iterable):
    return sum(iterable)


def func_avg(iterable):
    return sum(iterable) / len(iterable)


def func_max(iterable):
    return max(iterable)


FUNCS = {
    'sum': (lambda it: sum(it)),
    'avg': (lambda it: sum(it) / len(it)),
    'max': (lambda it: max(it)),
}


@login_required
def api_get_clustered_data(request):
    max_or_avg = request.GET['maxOrAvg']
    resolution = dec.Decimal(request.GET['resolution'])
    func = FUNCS[request.GET['func']]

    def _calc_key(loc: dict) -> (dec.Decimal, dec.Decimal):
        lat = dec.Decimal(loc['lat']).quantize(resolution, dec.ROUND_HALF_UP)
        lon = dec.Decimal(loc['lon']).quantize(resolution, dec.ROUND_HALF_UP)
        return lat, lon

    filter_criteria = dict(
        lat__gt=float(request.GET['south']),
        lat__lt=float(request.GET['north']),
        lon__gt=float(request.GET['west']),
        lon__lt=float(request.GET['east']),
    )

    clustered = {}
    for recording in Recording.objects.filter(**filter_criteria):
        state = loads(recording.device_state)
        location = state['location']
        values = loads(recording.process_result)

        clustered.setdefault(_calc_key(location), []).append({
            'coordinates': {'lat': location['lat'], 'lon': location['lon']},
            'avg': values['avg'],
            'max': values['max'],
        })

    clustered2 = []
    for key, datas in clustered.items():
        avg_avg = func([data['avg'] for data in datas])
        avg_max = func([data['max'] for data in datas])
        clustered2.append({
            'coordinates': {'lat': key[0], 'lon': key[1]},
            'avg': avg_avg,
            'max': avg_max,
        })
    if len(clustered2) > 0:
        def setter(obj, val):
            obj['display'] = val
        map_values(clustered2, 1, 2, lambda x: x[max_or_avg], setter)

    data = dict(
        success=True,
        data=clustered2,
    )

    return JsonResponse(data, json_dumps_params=dict(default=sjs))


@login_required
def api_get_nonclustered_data(request):
    max_or_avg = request.GET['maxOrAvg']

    filter_criteria = dict(
        lat__gt=float(request.GET['south']),
        lat__lt=float(request.GET['north']),
        lon__gt=float(request.GET['west']),
        lon__lt=float(request.GET['east']),
    )

    data = []
    q = Recording.objects.filter(**filter_criteria)
    for recording in q:
        state = loads(recording.device_state)
        location = state['location']
        values = loads(recording.process_result)

        data.append({
            'coordinates': {'lat': location['lat'], 'lon': location['lon']},
            'avg': values['avg'],
            'max': values['max'],
        })

    if len(data) > 0:
        def setter(obj, val):
            obj['display'] = val
        map_values(data, 2, 3, lambda x: x[max_or_avg], setter)

    data = dict(
        success=True,
        data=data,
    )

    return JsonResponse(data, json_dumps_params=dict(default=sjs))


@api_protect
def api_manual(request):
    return "Not implemented"


@api_protect
def api_echo(request):
    data = loads(request.body.decode("utf-8"))
    return HttpResponse(status=200, content=dumps(data))
