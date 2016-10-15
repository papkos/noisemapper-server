from django.conf.urls import url

from . import views

urlpatterns = [
    url(r'^$', views.index, name='index'),

    url(r'^api/upload_recording/$', views.api_upload_recording, name='api_upload_recording'),
]
