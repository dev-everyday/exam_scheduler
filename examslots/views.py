from django.shortcuts import render
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi
from datetime import datetime, timedelta
from django.utils import timezone
import pytz
from .models import ExamSlot
from .serializers import AvailableSlotListResponseSerializer, ExamSlotSerializer
from django.db import models
from common.serializers import ErrorResponseSerializer

@swagger_auto_schema(
    method='get',
    operation_summary="예약 가능한 시간대 조회 API",
    operation_description="특정 날짜의 예약 가능한 시간대와 남은 인원을 조회합니다. 현재 시간에서 3일 이상 이후의 날짜만 조회 가능합니다. 또한 3개월 이내의 날짜만 조회 가능합니다.",
    manual_parameters=[
        openapi.Parameter(
            'date',
            openapi.IN_QUERY,
            description="조회할 날짜 (YYYY-MM-DD 형식)",
            type=openapi.TYPE_STRING,
            required=True
        )
    ],
    responses={
        200: AvailableSlotListResponseSerializer,
        400: ErrorResponseSerializer,
        401: ErrorResponseSerializer
    }
)
@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_available_slots(request):
    """
    특정 날짜의 예약 가능한 시간대 조회 API
    
    - 로그인이 필요합니다.
    - 현재 시간에서 3일 이상 이후의 날짜만 조회 가능합니다.
    - 3개월 이내의 날짜만 조회 가능합니다.
    - 남은 자리가 0인 시간대는 제외됩니다.
    """
    date_str = request.query_params.get('date')
    if not date_str:
        return Response(ErrorResponseSerializer({'error': '날짜를 입력해주세요.'}).data, status=status.HTTP_400_BAD_REQUEST)
    
    try:
        target_date = datetime.strptime(date_str, '%Y-%m-%d').date()
    except ValueError:
        return Response(ErrorResponseSerializer({'error': '올바른 날짜 형식이 아닙니다. (YYYY-MM-DD)'}).data, status=status.HTTP_400_BAD_REQUEST)
    
    korea_tz = pytz.timezone('Asia/Seoul')
    current_datetime = timezone.now().astimezone(korea_tz)
    current_date = current_datetime.date()
    current_hour = current_datetime.hour
    
    min_date = current_date + timedelta(days=3)
    max_date = current_date + timedelta(days=90)
    
    if target_date < min_date:
        return Response(ErrorResponseSerializer({'error': '현재 날짜에서 3일 이상 이후의 날짜만 신청이 가능합니다.'}).data)
    
    if target_date > max_date:
        return Response(ErrorResponseSerializer({'error': '3개월 이내의 날짜만 신청이 가능합니다.'}).data)
    
    available_slots = ExamSlot.objects.filter(
        date=target_date,
        current_count__lt=models.F('max_capacity')
    ).order_by('hour')
    
    if target_date == min_date:
        available_slots = available_slots.filter(hour__gt=current_hour)
    
    serializer = ExamSlotSerializer(available_slots, many=True)
    
    return Response(AvailableSlotListResponseSerializer({'message': '예약 가능한 시간대를 조회했습니다.', 
                                                         'available_slots': serializer.data}).data)
