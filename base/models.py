import uuid
from django.db import models
from django.utils import timezone


class Device(models.Model):
    """Model to track devices/users by UUID"""
    uuid = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    created_at = models.DateTimeField(auto_now_add=True)
    last_seen = models.DateTimeField(auto_now=True)
    user_agent = models.TextField(blank=True, null=True)
    ip_address = models.GenericIPAddressField(blank=True, null=True)
    is_authenticated = models.BooleanField(default=False)
    token = models.CharField(max_length=255, blank=True, null=True)
    
    class Meta:
        ordering = ['-created_at']
    
    def __str__(self):
        return f"Device {str(self.uuid)[:8]}"


class VideoCall(models.Model):
    """Model to track video calls between users"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    participant1 = models.ForeignKey(Device, on_delete=models.CASCADE, related_name='calls_as_participant1')
    participant2 = models.ForeignKey(Device, on_delete=models.CASCADE, related_name='calls_as_participant2')
    started_at = models.DateTimeField(auto_now_add=True)
    ended_at = models.DateTimeField(null=True, blank=True)
    duration_seconds = models.IntegerField(default=0)
    status = models.CharField(max_length=20, choices=[
        ('connecting', 'Connecting'),
        ('active', 'Active'),
        ('ended', 'Ended'),
        ('failed', 'Failed')
    ], default='connecting')
    
    class Meta:
        ordering = ['-started_at']
    
    def __str__(self):
        return f"Call {str(self.id)[:8]} - {self.participant1} & {self.participant2}"
    
    def end_call(self):
        """End the call and calculate duration"""
        if not self.ended_at:
            self.ended_at = timezone.now()
            self.duration_seconds = int((self.ended_at - self.started_at).total_seconds())
            self.status = 'ended'
            self.save()


class CallQueue(models.Model):
    """Model to track users waiting for a call"""
    device = models.OneToOneField(Device, on_delete=models.CASCADE, related_name='queue_entry')
    joined_at = models.DateTimeField(auto_now_add=True)
    is_active = models.BooleanField(default=True)
    
    class Meta:
        ordering = ['joined_at']
    
    def __str__(self):
        return f"Queue entry for {self.device}"
