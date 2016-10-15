from django.shortcuts import render

from .api_endpoints import *


def index(request):
    return render(request, 'noisemapper/index.html')
