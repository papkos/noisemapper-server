from django.contrib.auth.decorators import login_required
from django.shortcuts import render

from .api_endpoints import *


@login_required
def index(request):

    args = dict()
    return render(request, 'noisemapper/index.html', args)
