from datetime import timedelta

from django.shortcuts import render
from django.utils import timezone
from rest_framework import status
from rest_framework.decorators import api_view
from rest_framework.response import Response

from base.models import Device, VideoCall, CallQueue
from base.serializers import DeviceSerializer


@api_view(['POST'])
def authenticate_with_token(request):
    """
    Authenticate user with Marian College token
    """
    try:
        token = request.data.get('token')
        
        if not token:
            return Response({
                'error': 'Token is required'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Validate Marian College token format
        if not token.startswith('MC_') or len(token) < 10:
            return Response({
                'error': 'Invalid Marian College token format'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Get client info for tracking
        user_agent = request.META.get('HTTP_USER_AGENT', '')
        ip_address = request.META.get('REMOTE_ADDR')
        
        # Get or create device with token
        device, created = Device.objects.get_or_create(
            token=token,
            defaults={
                'is_authenticated': True,
                'user_agent': user_agent,
                'ip_address': ip_address
            }
        )
        
        if not created:
            device.is_authenticated = True
            device.user_agent = user_agent
            device.ip_address = ip_address
            device.save()
        
        serializer = DeviceSerializer(device)
        
        return Response({
            'device_uuid': str(device.uuid),
            'message': 'Authentication successful! Welcome to onlyMC 💖',
            'device_info': serializer.data
        }, status=status.HTTP_200_OK)
        
    except Exception as e:
        return Response({
            'error': 'Authentication failed',
            'details': str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['POST'])
def get_or_create_device(request):
    """
    Legacy endpoint - Create a device UUID for tracking
    """
    try:
        # Get client info for tracking
        user_agent = request.META.get('HTTP_USER_AGENT', '')
        ip_address = request.META.get('REMOTE_ADDR')
        
        # Create a new device
        device = Device.objects.create(
            user_agent=user_agent,
            ip_address=ip_address
        )
        
        serializer = DeviceSerializer(device)
        
        return Response({
            'uuid': str(device.uuid),
            'message': 'Device UUID generated successfully'
        }, status=status.HTTP_201_CREATED)
        
    except Exception as e:
        return Response({
            'error': 'Failed to generate device UUID',
            'details': str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['POST'])
def update_device_activity(request):
    """
    Update device last seen timestamp
    """
    uuid_str = request.data.get('uuid')
    
    if not uuid_str:
        return Response({
            'error': 'UUID is required'
        }, status=status.HTTP_400_BAD_REQUEST)
    
    try:
        device = Device.objects.get(uuid=uuid_str)
        device.save()  # This will update the last_seen field due to auto_now=True
        
        return Response({
            'message': 'Device activity updated successfully'
        }, status=status.HTTP_200_OK)
        
    except Device.DoesNotExist:
        return Response({
            'error': 'Device not found'
        }, status=status.HTTP_404_NOT_FOUND)
    except Exception as e:
        return Response({
            'error': 'Failed to update device activity',
            'details': str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['GET'])
def api_status(request):
    """
    Simple API status endpoint
    """
    return Response({
        'status': 'ok',
        'message': 'ZEST Django API is running',
        'version': '1.0.0'
    }, status=status.HTTP_200_OK)


@api_view(['GET'])
def get_live_users(request):
    """
    Get list of currently active authenticated users (last seen within 30 seconds)
    """
    try:
        # Get devices active in the last 30 seconds and authenticated
        cutoff_time = timezone.now() - timedelta(seconds=30)
        active_devices = Device.objects.filter(
            last_seen__gte=cutoff_time,
            is_authenticated=True
        ).order_by('-last_seen')
        
        # Serialize the data
        serializer = DeviceSerializer(active_devices, many=True)
        
        return Response({
            'count': active_devices.count(),
            'users': serializer.data,
            'timestamp': timezone.now().isoformat()
        }, status=status.HTTP_200_OK)
        
    except Exception as e:
        return Response({
            'error': 'Failed to get live users',
            'details': str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['GET'])
def get_all_devices(request):
    """
    Get list of all devices with pagination
    """
    try:
        devices = Device.objects.all().order_by('-last_seen')
        serializer = DeviceSerializer(devices, many=True)
        
        return Response({
            'count': devices.count(),
            'devices': serializer.data,
            'timestamp': timezone.now().isoformat()
        }, status=status.HTTP_200_OK)
        
    except Exception as e:
        return Response({
            'error': 'Failed to get devices',
            'details': str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['GET'])
def get_queue_status(request):
    """
    Get current queue status and statistics
    """
    try:
        queue_count = CallQueue.objects.filter(is_active=True).count()
        active_calls = VideoCall.objects.filter(status='active').count()
        
        return Response({
            'queue_count': queue_count,
            'active_calls': active_calls,
            'timestamp': timezone.now().isoformat()
        }, status=status.HTTP_200_OK)
        
    except Exception as e:
        return Response({
            'error': 'Failed to get queue status',
            'details': str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['GET'])
def get_call_history(request):
    """
    Get call history for admin dashboard
    """
    try:
        calls = VideoCall.objects.all().order_by('-started_at')[:50]  # Last 50 calls
        
        call_data = []
        for call in calls:
            call_data.append({
                'id': str(call.id),
                'participant1': str(call.participant1.uuid)[:8],
                'participant2': str(call.participant2.uuid)[:8],
                'started_at': call.started_at.isoformat(),
                'ended_at': call.ended_at.isoformat() if call.ended_at else None,
                'duration_seconds': call.duration_seconds,
                'status': call.status
            })
        
        return Response({
            'calls': call_data,
            'total_calls': VideoCall.objects.count(),
            'timestamp': timezone.now().isoformat()
        }, status=status.HTTP_200_OK)
        
    except Exception as e:
        return Response({
            'error': 'Failed to get call history',
            'details': str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


def live_users_dashboard(request):
    """
    Render the onlyMC admin dashboard
    """
    return render(request, 'admin_dashboard.html')
