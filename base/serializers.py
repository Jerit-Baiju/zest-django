from datetime import timedelta

from django.utils import timezone
from rest_framework import serializers

from base.models import Device


class DeviceSerializer(serializers.ModelSerializer):
    is_online = serializers.SerializerMethodField()
    time_since_last_seen = serializers.SerializerMethodField()
    
    class Meta:
        model = Device
        fields = ['uuid', 'created_at', 'last_seen', 'user_agent', 'ip_address', 'is_online', 'time_since_last_seen']
        read_only_fields = ['uuid', 'created_at', 'last_seen', 'user_agent', 'ip_address']
    
    def get_is_online(self, obj):
        """Consider a device online if last seen within 30 seconds"""
        cutoff_time = timezone.now() - timedelta(seconds=30)
        return obj.last_seen >= cutoff_time
    
    def get_time_since_last_seen(self, obj):
        """Get seconds since last seen"""
        time_diff = timezone.now() - obj.last_seen
        return int(time_diff.total_seconds())
