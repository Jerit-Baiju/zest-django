from django.urls import path

from base import views

urlpatterns = [
    path('admin/', views.live_users_dashboard, name='admin_dashboard'),
    path('api/status/', views.api_status, name='api_status'),
    path('api/auth/token/', views.authenticate_with_token, name='authenticate_token'),
    path('api/auth/get-device-uuid/', views.get_or_create_device, name='get_device_uuid'),
    path('api/auth/update-activity/', views.update_device_activity, name='update_activity'),
    path('api/live-users/', views.get_live_users, name='get_live_users'),
    path('api/devices/', views.get_all_devices, name='get_all_devices'),
    path('api/queue-status/', views.get_queue_status, name='get_queue_status'),
    path('api/call-history/', views.get_call_history, name='get_call_history'),
]
