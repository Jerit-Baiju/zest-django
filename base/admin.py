from django.contrib import admin
from base.models import Device


@admin.register(Device)
class DeviceAdmin(admin.ModelAdmin):
    list_display = ['uuid', 'created_at', 'last_seen', 'ip_address']
    list_filter = ['created_at', 'last_seen']
    search_fields = ['uuid', 'ip_address']
    readonly_fields = ['uuid', 'created_at', 'last_seen']
    
    def has_add_permission(self, request):
        # Prevent manual creation of devices through admin
        return False
