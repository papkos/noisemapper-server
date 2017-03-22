import base64
import datetime
import datetime as dt
import decimal as dec
import logging
import os
import shutil
import tempfile
from json import loads, dumps

from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.db.models import Avg
from django.db.models.expressions import F
from django.http.request import HttpRequest
from django.http.response import HttpResponseNotAllowed, HttpResponse, JsonResponse

from noisemapper.models.recording import Recording, MIC_SOURCE_CHOICES
from noisemapper.utils import sjs, api_protect, cluster_data, distance, recording_to_json, GeoWeightedMiddle

__all__ = ('api_upload_recording', 'api_upload_recording_batch',
           'api_get_actual_data', 'api_get_deviation_from_average_data',
           'download_selection',
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

    process_result = json_data['processResult']
    recording.process_result = dumps(process_result, default=sjs)
    recording.measurement_avg = process_result.get('avg', None)
    recording.measurement_max = process_result.get('max', None)

    device_state = json_data['state']
    recording.device_state = dumps(device_state, default=sjs)
    recording.mic_source = device_state.get('micSource', MIC_SOURCE_CHOICES[0][0]).lower()

    recording.lat = float(location['lat'])
    recording.lon = float(location['lon'])
    return recording


def _get_device_name(request: HttpRequest) -> str:
    device_name = request.META.get('HTTP_X_NOISEMAPPER_API_DEVICE_NAME', '')
    if device_name:
        device_name = base64.b64decode(device_name).decode('utf-8')

    return device_name


def _make_is_same(resolution):
    try:
        resolution = dec.Decimal(resolution)
    except:
        resolution = False
    if resolution:
        return lambda a, b: distance(a, b) < resolution
    else:
        return lambda a, b: False


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


def _build_filters(request: HttpRequest):
    device_names = request.GET.get('deviceNames', '').split('|')
    mic_sources = request.GET.get('micSources', '').split('|')
    is_cropping = request.GET['is_cropping'] == 'true'

    filter_criteria = dict()
    if is_cropping:
        filter_criteria.update(
            lat__gt=float(request.GET['south']),
            lat__lt=float(request.GET['north']),
            lon__gt=float(request.GET['west']),
            lon__lt=float(request.GET['east']),
        )

    filter_criteria.update(
        device_name__in=device_names,
    )

    filter_criteria.update(
        mic_source__in=mic_sources,
    )

    filter_criteria.update(
        # 2017-01-24 21:31:09 -- ??
        timestamp__gte=datetime.datetime(year=2017, month=1, day=24, hour=20, minute=00),
        # # 2017-03-19 10:10:00 -- Started using a headset
        # timestamp__gte=datetime.datetime(year=2017, month=3, day=19, hour=10, minute=10),
    )

    return filter_criteria


def _build_excludes(request: HttpRequest):
    exclude_criteria = dict()

    exclude_criteria.update(
        # In this period, the app was set to use `MediaRecorder.AudioSource.VOICE_RECOGNITION`
        # which resulted in incorrect (too high) values.
        timestamp__gte=datetime.datetime(year=2017, month=3, day=5, hour=0, minute=00),
        timestamp__lte=datetime.datetime(year=2017, month=3, day=5, hour=23, minute=59),
    )

    return exclude_criteria


@login_required
def api_get_actual_data(request):
    resolution = request.GET['resolution']
    max_or_avg = request.GET['maxOrAvg']

    filter_criteria = _build_filters(request)
    exclude_criteria = _build_excludes(request)

    data = Recording.objects.filter(**filter_criteria).exclude(**exclude_criteria)
    return _common_prepare_response_data(
        data,
        is_same_func=_make_is_same(resolution),
        aggregator_factory=(lambda: GeoWeightedMiddle(extractor=(lambda r: (r.lat, r.lon, getattr(r, max_or_avg))))),
        range=(2, 3),
    )


@login_required
def api_get_deviation_from_average_data(request):
    resolution = request.GET['resolution']
    max_or_avg = request.GET['maxOrAvg']

    filter_criteria = _build_filters(request)
    exclude_criteria = _build_excludes(request)
    queryset = Recording.objects.filter(**filter_criteria).exclude(**exclude_criteria)
    average_values = queryset.values('device_name').annotate(average_value=Avg(max_or_avg))
    average_values = {x['device_name']: x['average_value'] for x in average_values}

    annotated = []
    for recording in queryset:
        recording.deviation = getattr(recording, max_or_avg) - average_values[recording.device_name]
        annotated.append(recording)

    return _common_prepare_response_data(
        annotated,
        is_same_func=_make_is_same(resolution),
        aggregator_factory=(lambda: GeoWeightedMiddle(extractor=(lambda r: (r.lat, r.lon, getattr(r, 'deviation'))))),
        range=(-1, +1),
    )


def _common_prepare_response_data(data, is_same_func, aggregator_factory, range):
    clustered = cluster_data(
        data,
        key_func=(lambda r: (r.lat, r.lon)),
        is_same_func=is_same_func,
        aggregator_factory=aggregator_factory,
        retain_original=True,
    )
    clustered = [
        dict(
            coordinates={'lat': key[0], 'lon': key[1]},
            value=value['aggregated_value'],
            original=[recording_to_json(x) for x in value['original']],
        )
        for key, value
        in clustered.items()
        ]

    range_min, range_max = range

    if len(clustered) > 0:
        def setter(obj, val):
            obj['display'] = val

        map_values(clustered, range_min, range_max, lambda x: x['value'], setter)
    data = dict(
        success=True,
        data=clustered,
        min=range_min,
        max=range_max,
    )
    return JsonResponse(data, json_dumps_params=dict(default=sjs))


@login_required
def download_selection(request: HttpRequest):

    filter_criteria = _build_filters(request)
    exclude_criteria = _build_excludes(request)

    data = Recording.objects.filter(**filter_criteria).exclude(**exclude_criteria)

    with tempfile.TemporaryFile() as tmpfile:
        for recording in data:
            full_filename = settings.FILENAME_PATTERN % recording.uuid
            full_filename = os.path.join(settings.SNIPPET_STORAGE_DIR, full_filename)
            with open(full_filename, 'rb') as infile:
                shutil.copyfileobj(infile, tmpfile)

        tmpfile.seek(0)
        response = HttpResponse(tmpfile.read(), content_type='audio/pcm')

    response['Content-Disposition'] = 'attachment; filename="merged.pcm"'
    return response


@login_required
def api_manual(request):
    # cnt = 0
    # for r in Recording.objects.all():
    #     results = loads(r.process_result)
    #     r.measurement_avg = results.get('avg', None)
    #     r.measurement_max = results.get('max', None)
    #     r.save()
    #     cnt += 1
    # print("Processed %d records" % cnt)

    return HttpResponse("Not implemented")


@api_protect
def api_echo(request):
    data = loads(request.body.decode("utf-8"))
    return HttpResponse(status=200, content=dumps(data))
