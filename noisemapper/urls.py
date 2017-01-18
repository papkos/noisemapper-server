from django.conf.urls import url

from . import views

urlpatterns = [
    url(r'^$', views.index, name='index'),

    url(r'^api/upload_recording/$', views.api_upload_recording, name='api_upload_recording'),
    url(r'^api/upload_recording_batch/$', views.api_upload_recording_batch, name='api_upload_recording'),
    url(r'^api/get_clustered_data/$', views.api_get_clustered_data, name='api_get_clustered_data'),

    url(r'^api/manual', views.api_manual),
    url(r'^api/echo', views.api_echo),
]
