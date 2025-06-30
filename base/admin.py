from django.contrib import admin
from base.models import Device, VideoCall, CallQueue


@admin.register(Device)
class DeviceAdmin(admin.ModelAdmin):
    list_display = ['uuid', 'is_authenticated', 'token', 'created_at', 'last_seen', 'ip_address']
    list_filter = ['is_authenticated', 'created_at', 'last_seen']
    search_fields = ['uuid', 'token', 'ip_address']
    readonly_fields = ['uuid', 'created_at']
    ordering = ['-last_seen']


@admin.register(VideoCall)
class VideoCallAdmin(admin.ModelAdmin):
    list_display = ['id', 'participant1', 'participant2', 'status', 'started_at', 'ended_at', 'duration_seconds']
    list_filter = ['status', 'started_at', 'ended_at']
    search_fields = ['id', 'participant1__uuid', 'participant2__uuid']
    readonly_fields = ['id', 'started_at', 'ended_at', 'duration_seconds']
    ordering = ['-started_at']


@admin.register(CallQueue)
class CallQueueAdmin(admin.ModelAdmin):
    list_display = ['device', 'joined_at', 'is_active']
    list_filter = ['is_active', 'joined_at']
    search_fields = ['device__uuid', 'device__token']
    readonly_fields = ['joined_at']
    ordering = ['joined_at']
    
    def has_add_permission(self, request):
        # Prevent manual creation of devices through admin
        return False
