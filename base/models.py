import uuid
from django.db import models
from django.utils import timezone


class MarianStudent(models.Model):
    """Model to track authenticated Marian College students"""
    uuid = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    token = models.CharField(max_length=255, unique=True, help_text="Marian College authentication token")
    student_id = models.CharField(max_length=20, blank=True, null=True, help_text="Student ID from token")
    year = models.CharField(max_length=10, blank=True, null=True, help_text="Academic year")
    department = models.CharField(max_length=100, blank=True, null=True)
    
    # Session tracking
    created_at = models.DateTimeField(auto_now_add=True)
    last_seen = models.DateTimeField(auto_now=True)
    is_online = models.BooleanField(default=False)
    
    # Technical details (optional for debugging)
    user_agent = models.TextField(blank=True, null=True)
    ip_address = models.GenericIPAddressField(blank=True, null=True)
    
    class Meta:
        ordering = ['-last_seen']
        verbose_name = "Marian Student"
        verbose_name_plural = "Marian Students"
    
    def __str__(self):
        return f"Student {str(self.uuid)[:8]} ({self.student_id or 'Unknown ID'})"
    
    @property
    def is_active(self):
        """Check if student was active in the last 5 minutes"""
        return (timezone.now() - self.last_seen).total_seconds() < 300


class VideoCall(models.Model):
    """Model to track OnlyMC video calls between students"""
    STATUS_CHOICES = [
        ('waiting', 'Waiting for Connection'),
        ('connecting', 'Connecting'),
        ('active', 'Active Call'),
        ('ended', 'Call Ended'),
        ('failed', 'Connection Failed')
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    student1 = models.ForeignKey(MarianStudent, on_delete=models.CASCADE, related_name='calls_as_student1')
    student2 = models.ForeignKey(MarianStudent, on_delete=models.CASCADE, related_name='calls_as_student2')
    
    # Call timing
    created_at = models.DateTimeField(auto_now_add=True, help_text="When the call was initiated")
    connected_at = models.DateTimeField(null=True, blank=True, help_text="When students actually connected")
    ended_at = models.DateTimeField(null=True, blank=True)
    duration_seconds = models.IntegerField(default=0)
    
    # Call status
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='waiting')
    
    # Call quality metrics (optional)
    connection_quality = models.CharField(max_length=20, blank=True, null=True, 
                                         choices=[('poor', 'Poor'), ('good', 'Good'), ('excellent', 'Excellent')])
    ended_by = models.ForeignKey(MarianStudent, on_delete=models.SET_NULL, null=True, blank=True, 
                                related_name='calls_ended')
    
    class Meta:
        ordering = ['-created_at']
        verbose_name = "OnlyMC Video Call"
        verbose_name_plural = "OnlyMC Video Calls"
    
    def __str__(self):
        return f"OnlyMC Call {str(self.id)[:8]} - {self.student1} ❤️ {self.student2}"
    
    def end_call(self, ended_by_student=None):
        """End the call and calculate duration"""
        if not self.ended_at:
            self.ended_at = timezone.now()
            if self.connected_at:
                self.duration_seconds = int((self.ended_at - self.connected_at).total_seconds())
            self.status = 'ended'
            if ended_by_student:
                self.ended_by = ended_by_student
            self.save()
    
    def mark_connected(self):
        """Mark the call as successfully connected"""
        if not self.connected_at:
            self.connected_at = timezone.now()
            self.status = 'active'
            self.save()
    
    @property
    def duration_formatted(self):
        """Return formatted duration string"""
        if self.duration_seconds:
            minutes = self.duration_seconds // 60
            seconds = self.duration_seconds % 60
            return f"{minutes:02d}:{seconds:02d}"
        return "00:00"


class CallQueue(models.Model):
    """Model to track students waiting for a video call - minimal DB storage"""
    student = models.OneToOneField(MarianStudent, on_delete=models.CASCADE, related_name='queue_entry')
    joined_at = models.DateTimeField(auto_now_add=True)
    is_active = models.BooleanField(default=True)
    
    # Queue preferences (future features)
    preferred_year = models.CharField(max_length=10, blank=True, null=True, help_text="Preferred academic year to match with")
    preferred_department = models.CharField(max_length=100, blank=True, null=True)
    
    class Meta:
        ordering = ['joined_at']
        verbose_name = "Call Queue Entry"
        verbose_name_plural = "Call Queue Entries"
    
    def __str__(self):
        return f"💫 {self.student} waiting for love since {self.joined_at.strftime('%H:%M')}"


class CallFeedback(models.Model):
    """Optional model to collect call quality feedback"""
    RATING_CHOICES = [(i, f"{i} ❤️") for i in range(1, 6)]
    
    call = models.OneToOneField(VideoCall, on_delete=models.CASCADE, related_name='feedback')
    student = models.ForeignKey(MarianStudent, on_delete=models.CASCADE)
    rating = models.IntegerField(choices=RATING_CHOICES, help_text="Rate your OnlyMC experience")
    comment = models.TextField(blank=True, null=True, help_text="Share your thoughts (optional)")
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        verbose_name = "Call Feedback"
        verbose_name_plural = "Call Feedback"
    
    def __str__(self):
        return f"Feedback: {self.rating}❤️ from {self.student}"
