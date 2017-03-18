from django.conf.urls import url
from django.contrib.auth import views as auth_views

from . import views

urlpatterns = [
    url(r'^$', views.index, name='index'),

    url(r'^api/upload_recording/$', views.api_upload_recording, name='api_upload_recording'),
    url(r'^api/upload_recording_batch/$', views.api_upload_recording_batch, name='api_upload_recording'),
    url(r'^api/get_actual_data/$', views.api_get_actual_data, name='api_get_actual_data'),
    url(r'^api/get_deviation_data/$', views.api_get_deviation_from_average_data, name='api_get_deviation_data'),

    url(r'^api/manual', views.api_manual),
    url(r'^api/echo', views.api_echo),

    url(r'^login/$', auth_views.login, {'template_name': 'login.html'}, name='login'),
]
