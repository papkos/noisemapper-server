from json import loads, dumps

import datetime as dt
from django.http.response import HttpResponseNotAllowed, HttpResponse
from django.views.decorators.csrf import csrf_exempt

from noisemapper.models.recording import Recording
from noisemapper.utils import sjs

__all__ = ('api_upload_recording',)


@csrf_exempt
def api_upload_recording(request):
    if request.method == 'POST':
        print('POST body: ' + repr(request.body))
        data = loads(request.body.decode("utf-8"))
        data['timestamp'] = dt.datetime.strptime(data['timestamp'], '%Y-%m-%d %H:%M:%S')
        print(repr(data))

        recording = Recording()
        recording.timestamp = data['timestamp']
        recording.process_result = dumps(data['processResult'], default=sjs)
        recording.device_state = dumps(data['state'], default=sjs)
        recording.save()

        response = dict(
            success=True,
            server_id=recording.pk,
        )
        return HttpResponse(dumps(response, default=sjs))
    else:
        return HttpResponseNotAllowed(['POST'])
