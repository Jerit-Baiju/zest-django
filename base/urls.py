from django.urls import path

from base import views

urlpatterns = [
    path('', views.live_users_dashboard, name='live_users_dashboard'),
    path('api/status/', views.api_status, name='api_status'),
    path('api/auth/get-device-uuid/', views.get_or_create_device, name='get_device_uuid'),
    path('api/auth/update-activity/', views.update_device_activity, name='update_activity'),
    path('api/live-users/', views.get_live_users, name='get_live_users'),
    path('api/devices/', views.get_all_devices, name='get_all_devices'),
]
