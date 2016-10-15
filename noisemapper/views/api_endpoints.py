from json import loads, dumps

from django.http.response import HttpResponseNotAllowed, HttpResponse
from django.views.decorators.csrf import csrf_exempt

__all__ = ('api_upload_recording',)


@csrf_exempt
def api_upload_recording(request):
    if request.method == 'POST':
        print('POST body: ' + repr(request.body))
        data = loads(request.body.decode("utf-8"))
        print(repr(data))

        return HttpResponse(dumps(data))
    else:
        return HttpResponseNotAllowed(['POST'])
