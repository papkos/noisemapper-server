from django.shortcuts import render

from .api_endpoints import *


def index(request):

    args = dict()
    return render(request, 'noisemapper/index.html', args)
