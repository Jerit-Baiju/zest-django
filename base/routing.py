from django.urls import re_path

from base import consumers

websocket_urlpatterns = [
    re_path(r'ws/live-users/$', consumers.LiveUsersConsumer.as_asgi()),
    re_path(r'ws/video-call/$', consumers.VideoCallConsumer.as_asgi()),
]
