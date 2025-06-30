import json
import uuid
from datetime import datetime, timedelta

from channels.db import database_sync_to_async
from channels.generic.websocket import AsyncWebsocketConsumer
from django.utils import timezone

from base.models import Device, VideoCall, CallQueue

# In-memory queue for real-time matching
WAITING_QUEUE = {}
ACTIVE_CALLS = {}


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


class VideoCallConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.device_uuid = None
        self.call_id = None
        self.partner_uuid = None
        
        await self.accept()
    
    async def disconnect(self, close_code):
        # Remove from queue
        if self.device_uuid and self.device_uuid in WAITING_QUEUE:
            del WAITING_QUEUE[self.device_uuid]
        
        # End call if in progress
        if self.call_id and self.call_id in ACTIVE_CALLS:
            await self.end_call_cleanup()
        
        # Remove from database queue
        if self.device_uuid:
            await self.remove_from_db_queue(self.device_uuid)
    
    async def receive(self, text_data):
        try:
            data = json.loads(text_data)
            message_type = data.get('type')
            
            if message_type == 'authenticate':
                await self.handle_authentication(data)
            elif message_type == 'join_queue':
                await self.handle_join_queue(data)
            elif message_type == 'leave_queue':
                await self.handle_leave_queue(data)
            elif message_type == 'webrtc_offer':
                await self.handle_webrtc_offer(data)
            elif message_type == 'webrtc_answer':
                await self.handle_webrtc_answer(data)
            elif message_type == 'webrtc_ice':
                await self.handle_webrtc_ice(data)
            elif message_type == 'end_call':
                await self.handle_end_call(data)
                
        except json.JSONDecodeError:
            await self.send_error('Invalid JSON')
    
    async def handle_authentication(self, data):
        """Authenticate user with Marian College token"""
        token = data.get('token')
        if not token:
            await self.send_error('Token required')
            return
        
        # Simple token validation for Marian College
        if not token.startswith('MC_') or len(token) < 10:
            await self.send_error('Invalid Marian College token')
            return
        
        device = await self.get_or_create_device(token)
        if device:
            self.device_uuid = device['uuid']
            await self.send_json({
                'type': 'authenticated',
                'device_uuid': self.device_uuid,
                'message': 'Welcome to onlyMC! 💖'
            })
        else:
            await self.send_error('Authentication failed')
    
    async def handle_join_queue(self, data):
        """Add user to video call queue"""
        if not self.device_uuid:
            await self.send_error('Not authenticated')
            return
        
        # Add to in-memory queue for instant matching
        WAITING_QUEUE[self.device_uuid] = {
            'channel_name': self.channel_name,
            'joined_at': timezone.now(),
            'consumer': self
        }
        
        # Also add to database for persistence
        await self.add_to_db_queue(self.device_uuid)
        
        # Try to find a match immediately
        match_uuid = None
        for uuid_key, info in WAITING_QUEUE.items():
            if uuid_key != self.device_uuid:
                match_uuid = uuid_key
                break
        
        if match_uuid:
            # Create a call between matched users
            call_id = str(uuid.uuid4())
            
            # Remove both from queue
            partner_info = WAITING_QUEUE.pop(match_uuid)
            del WAITING_QUEUE[self.device_uuid]
            
            # Store active call
            ACTIVE_CALLS[call_id] = {
                'participants': [self.device_uuid, match_uuid],
                'started_at': timezone.now(),
                'channels': {
                    self.device_uuid: self.channel_name,
                    match_uuid: partner_info['channel_name']
                }
            }
            
            self.call_id = call_id
            self.partner_uuid = match_uuid
            
            # Create call in database
            await self.create_db_call(self.device_uuid, match_uuid, call_id)
            
            # Notify both users
            await self.send_json({
                'type': 'match_found',
                'call_id': call_id,
                'partner_id': match_uuid,
                'message': 'Match found! Starting video call... 💕'
            })
            
            await self.channel_layer.send(partner_info['channel_name'], {
                'type': 'match_found_notification',
                'call_id': call_id,
                'partner_id': self.device_uuid
            })
        else:
            queue_count = len(WAITING_QUEUE)
            await self.send_json({
                'type': 'queued',
                'position': queue_count,
                'message': f'You are #{queue_count} in queue. Looking for someone special... 💫'
            })
    
    async def handle_leave_queue(self, data):
        """Remove user from queue"""
        if self.device_uuid and self.device_uuid in WAITING_QUEUE:
            del WAITING_QUEUE[self.device_uuid]
        
        await self.remove_from_db_queue(self.device_uuid)
        await self.send_json({
            'type': 'left_queue',
            'message': 'Left queue. Come back anytime! 👋'
        })
    
    async def handle_webrtc_offer(self, data):
        """Forward WebRTC offer to partner"""
        if self.call_id and self.call_id in ACTIVE_CALLS:
            call_info = ACTIVE_CALLS[self.call_id]
            partner_channel = call_info['channels'].get(self.partner_uuid)
            
            if partner_channel:
                await self.channel_layer.send(partner_channel, {
                    'type': 'webrtc_offer_notification',
                    'offer': data.get('offer')
                })
    
    async def handle_webrtc_answer(self, data):
        """Forward WebRTC answer to partner"""
        if self.call_id and self.call_id in ACTIVE_CALLS:
            call_info = ACTIVE_CALLS[self.call_id]
            partner_channel = call_info['channels'].get(self.partner_uuid)
            
            if partner_channel:
                await self.channel_layer.send(partner_channel, {
                    'type': 'webrtc_answer_notification',
                    'answer': data.get('answer')
                })
    
    async def handle_webrtc_ice(self, data):
        """Forward ICE candidate to partner"""
        if self.call_id and self.call_id in ACTIVE_CALLS:
            call_info = ACTIVE_CALLS[self.call_id]
            partner_channel = call_info['channels'].get(self.partner_uuid)
            
            if partner_channel:
                await self.channel_layer.send(partner_channel, {
                    'type': 'webrtc_ice_notification',
                    'candidate': data.get('candidate')
                })
    
    async def handle_end_call(self, data):
        """End the current call"""
        if self.call_id:
            await self.end_call_cleanup()
            await self.send_json({
                'type': 'call_ended',
                'message': 'Call ended. Thanks for using onlyMC! 💖'
            })
    
    async def end_call_cleanup(self):
        """Clean up call data"""
        if self.call_id and self.call_id in ACTIVE_CALLS:
            call_info = ACTIVE_CALLS[self.call_id]
            partner_channel = call_info['channels'].get(self.partner_uuid)
            
            # Notify partner
            if partner_channel:
                await self.channel_layer.send(partner_channel, {
                    'type': 'call_ended_notification'
                })
            
            # End call in database
            await self.end_db_call(self.call_id)
            
            # Remove from active calls
            del ACTIVE_CALLS[self.call_id]
            
            self.call_id = None
            self.partner_uuid = None
    
    # Channel layer message handlers
    async def match_found_notification(self, event):
        self.call_id = event['call_id']
        self.partner_uuid = event['partner_id']
        
        await self.send_json({
            'type': 'match_found',
            'call_id': event['call_id'],
            'partner_id': event['partner_id'],
            'message': 'Match found! Starting video call... 💕'
        })
    
    async def webrtc_offer_notification(self, event):
        await self.send_json({
            'type': 'webrtc_offer',
            'offer': event['offer']
        })
    
    async def webrtc_answer_notification(self, event):
        await self.send_json({
            'type': 'webrtc_answer',
            'answer': event['answer']
        })
    
    async def webrtc_ice_notification(self, event):
        await self.send_json({
            'type': 'webrtc_ice',
            'candidate': event['candidate']
        })
    
    async def call_ended_notification(self, event):
        self.call_id = None
        self.partner_uuid = None
        
        await self.send_json({
            'type': 'call_ended',
            'message': 'Your partner ended the call. 💔'
        })
    
    # Database operations
    @database_sync_to_async
    def get_or_create_device(self, token):
        try:
            device, created = Device.objects.get_or_create(
                token=token,
                defaults={
                    'is_authenticated': True,
                    'user_agent': self.scope.get('headers', {}).get('user-agent', ''),
                    'ip_address': self.scope.get('client', ['unknown', None])[0]
                }
            )
            if not created:
                device.is_authenticated = True
                device.save()
            
            return {
                'uuid': str(device.uuid),
                'created': created
            }
        except Exception:
            return None
    
    @database_sync_to_async
    def add_to_db_queue(self, device_uuid):
        try:
            device = Device.objects.get(uuid=device_uuid)
            CallQueue.objects.get_or_create(
                device=device,
                defaults={'is_active': True}
            )
            return True
        except Device.DoesNotExist:
            return False
    
    @database_sync_to_async
    def remove_from_db_queue(self, device_uuid):
        try:
            device = Device.objects.get(uuid=device_uuid)
            CallQueue.objects.filter(device=device).delete()
            return True
        except Device.DoesNotExist:
            return False
    
    @database_sync_to_async
    def create_db_call(self, device1_uuid, device2_uuid, call_id):
        try:
            device1 = Device.objects.get(uuid=device1_uuid)
            device2 = Device.objects.get(uuid=device2_uuid)
            
            # Create with the specific UUID
            call = VideoCall(
                id=call_id,
                participant1=device1,
                participant2=device2,
                status='connecting'
            )
            call.save()
            
            return True
        except Device.DoesNotExist:
            return False
    
    @database_sync_to_async
    def end_db_call(self, call_id):
        try:
            call = VideoCall.objects.get(id=call_id)
            call.end_call()
            return True
        except VideoCall.DoesNotExist:
            return False
    
    async def send_json(self, data):
        await self.send(text_data=json.dumps(data))
    
    async def send_error(self, message):
        await self.send_json({
            'type': 'error',
            'message': message
        })
