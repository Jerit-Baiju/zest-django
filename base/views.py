from datetime import timedelta

from django.shortcuts import render
from django.utils import timezone
from rest_framework import status
from rest_framework.decorators import api_view
from rest_framework.response import Response

from base.models import Device
from base.serializers import DeviceSerializer


@api_view(['POST'])
def get_or_create_device(request):
    """
    Get or create a device UUID for tracking
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
    Get list of currently active users (last seen within 30 seconds)
    """
    try:
        # Get devices active in the last 30 seconds
        cutoff_time = timezone.now() - timedelta(seconds=30)
        active_devices = Device.objects.filter(last_seen__gte=cutoff_time).order_by('-last_seen')
        
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


def live_users_dashboard(request):
    """
    Render the live users dashboard
    """
    return render(request, 'live_users.html')
