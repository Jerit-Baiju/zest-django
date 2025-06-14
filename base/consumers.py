import json
import uuid
from datetime import datetime, timedelta

from channels.db import database_sync_to_async
from channels.generic.websocket import AsyncWebsocketConsumer
from django.utils import timezone

from base.models import Device


class LiveUsersConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        # Join the live users group
        self.group_name = "live_users"
        await self.channel_layer.group_add(
            self.group_name,
            self.channel_name
        )
        
        await self.accept()
        
        # Send current active users count
        await self.send_active_users_count()
    
    async def disconnect(self, close_code):
        # Leave the live users group
        await self.channel_layer.group_discard(
            self.group_name,
            self.channel_name
        )
        
        # Update user activity if device_uuid was provided
        if hasattr(self, 'device_uuid') and self.device_uuid:
            await self.update_device_offline(self.device_uuid)
    
    async def receive(self, text_data):
        try:
            text_data_json = json.loads(text_data)
            message_type = text_data_json.get('type')
            
            if message_type == 'user_online':
                device_uuid = text_data_json.get('device_uuid')
                if device_uuid:
                    self.device_uuid = device_uuid
                    await self.update_device_activity(device_uuid)
                    await self.broadcast_user_update()
            
            elif message_type == 'ping':
                # Handle ping to keep connection alive and update activity
                if hasattr(self, 'device_uuid') and self.device_uuid:
                    await self.update_device_activity(self.device_uuid)
                    
                await self.send(text_data=json.dumps({
                    'type': 'pong',
                    'timestamp': timezone.now().isoformat()
                }))
        
        except json.JSONDecodeError:
            await self.send(text_data=json.dumps({
                'type': 'error',
                'message': 'Invalid JSON'
            }))
    
    async def user_count_update(self, event):
        """
        Handler for user_count_update messages from the group
        """
        await self.send(text_data=json.dumps({
            'type': 'user_count_update',
            'active_users': event['active_users'],
            'timestamp': event['timestamp']
        }))
    
    @database_sync_to_async
    def get_active_users_count(self):
        """Get count of users active in the last 30 seconds"""
        cutoff_time = timezone.now() - timedelta(seconds=30)
        return Device.objects.filter(last_seen__gte=cutoff_time).count()
    
    @database_sync_to_async
    def get_active_users_list(self):
        """Get list of active users with their details"""
        cutoff_time = timezone.now() - timedelta(seconds=30)
        devices = Device.objects.filter(last_seen__gte=cutoff_time).order_by('-last_seen')
        
        return [
            {
                'uuid': str(device.uuid),
                'last_seen': device.last_seen.isoformat(),
                'created_at': device.created_at.isoformat(),
                'user_agent': device.user_agent[:100] if device.user_agent else None,  # Truncate for privacy
                'ip_address': device.ip_address
            }
            for device in devices
        ]
    
    @database_sync_to_async
    def update_device_activity(self, device_uuid):
        """Update device last_seen timestamp"""
        try:
            device = Device.objects.get(uuid=device_uuid)
            device.save()  # This updates last_seen due to auto_now=True
            return True
        except Device.DoesNotExist:
            return False
    
    @database_sync_to_async
    def update_device_offline(self, device_uuid):
        """Mark device as offline by updating last_seen to a past time"""
        try:
            device = Device.objects.get(uuid=device_uuid)
            # Update last_seen to indicate user went offline
            device.last_seen = timezone.now() - timedelta(seconds=60)
            device.save(update_fields=['last_seen'])
            return True
        except Device.DoesNotExist:
            return False
    
    async def send_active_users_count(self):
        """Send the current active users count to this connection"""
        active_count = await self.get_active_users_count()
        active_users = await self.get_active_users_list()
        
        await self.send(text_data=json.dumps({
            'type': 'active_users',
            'count': active_count,
            'users': active_users,
            'timestamp': timezone.now().isoformat()
        }))
    
    async def broadcast_user_update(self):
        """Broadcast user count update to all connections in the group"""
        active_count = await self.get_active_users_count()
        active_users = await self.get_active_users_list()
        
        await self.channel_layer.group_send(
            self.group_name,
            {
                'type': 'user_count_update',
                'active_users': {
                    'count': active_count,
                    'users': active_users
                },
                'timestamp': timezone.now().isoformat()
            }
        )
