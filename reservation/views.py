from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi
from django.db import transaction
from django.utils import timezone
from django.core.exceptions import ValidationError
import pytz
from datetime import timedelta
from .models import Reservation
from .serializers import ReservationCreateSerializer, ReservationSerializer
from examslots.models import ExamSlot
from django.db import models
import redis_lock

# Create your views here.

@swagger_auto_schema(
    method='get',
    operation_summary="예약 목록 조회 API",
    operation_description="로그인한 사용자의 권한에 따라 예약 목록을 조회합니다. 관리자는 모든 예약을, 일반 사용자는 자신의 예약만 조회할 수 있습니다.",
    responses={
        200: openapi.Response(
            description="예약 목록 조회 성공",
            schema=openapi.Schema(
                type=openapi.TYPE_OBJECT,
                properties={
                    'reservations': openapi.Schema(
                        type=openapi.TYPE_ARRAY,
                        items=openapi.Schema(
                            type=openapi.TYPE_OBJECT,
                            properties={
                                'id': openapi.Schema(type=openapi.TYPE_INTEGER),
                                'user': openapi.Schema(type=openapi.TYPE_INTEGER),
                                'username': openapi.Schema(type=openapi.TYPE_STRING),
                                'start_time': openapi.Schema(type=openapi.TYPE_STRING),
                                'end_time': openapi.Schema(type=openapi.TYPE_STRING),
                                'status': openapi.Schema(type=openapi.TYPE_STRING),
                                'created_at': openapi.Schema(type=openapi.TYPE_STRING),
                                'count': openapi.Schema(type=openapi.TYPE_INTEGER)
                            }
                        )
                    )
                }
            )
        ),
        401: openapi.Response(
            description="인증 실패",
            schema=openapi.Schema(
                type=openapi.TYPE_OBJECT,
                properties={
                    'detail': openapi.Schema(type=openapi.TYPE_STRING)
                }
            )
        )
    }
)
@swagger_auto_schema(
    method='post',
    operation_summary="시험 예약 API",
    operation_description="시험 예약을 신청합니다. 로그인이 필요하며, 현재 시간에서 3일 이상 이후부터 3개월 이내의 날짜만 신청 가능합니다. 최대 5만명까지 예약할 수 있습니다.",
    request_body=openapi.Schema(
        type=openapi.TYPE_OBJECT,
        required=['start_time', 'end_time', 'count'],
        properties={
            'start_time': openapi.Schema(
                type=openapi.TYPE_STRING,
                format='date-time',
                example='2025-04-15 09:00',
                description='예약 시작 시간 (YYYY-MM-DD HH:MM 형식, 예: 2025-04-15 09:00)'
            ),
            'end_time': openapi.Schema(
                type=openapi.TYPE_STRING,
                format='date-time',
                example='2025-04-15 11:00',
                description='예약 종료 시간 (YYYY-MM-DD HH:MM 형식, 예: 2025-04-15 11:00)'
            ),
            'count': openapi.Schema(
                type=openapi.TYPE_INTEGER,
                example=1,
                description='예약 인원 수'
            )
        }
    ),
    responses={
        201: openapi.Response(
            description="예약 신청 성공",
            schema=openapi.Schema(
                type=openapi.TYPE_OBJECT,
                properties={
                    'message': openapi.Schema(type=openapi.TYPE_STRING),
                    'reservation': openapi.Schema(
                        type=openapi.TYPE_OBJECT,
                        properties={
                            'id': openapi.Schema(type=openapi.TYPE_INTEGER),
                            'user': openapi.Schema(type=openapi.TYPE_INTEGER),
                            'start_time': openapi.Schema(type=openapi.TYPE_STRING),
                            'end_time': openapi.Schema(type=openapi.TYPE_STRING),
                            'status': openapi.Schema(type=openapi.TYPE_STRING),
                            'created_at': openapi.Schema(type=openapi.TYPE_STRING),
                            'count': openapi.Schema(type=openapi.TYPE_INTEGER)
                        }
                    )
                }
            )
        ),
        400: openapi.Response(
            description="잘못된 요청",
            schema=openapi.Schema(
                type=openapi.TYPE_OBJECT,
                properties={
                    'error': openapi.Schema(type=openapi.TYPE_STRING)
                }
            )
        ),
        401: openapi.Response(
            description="인증 실패",
            schema=openapi.Schema(
                type=openapi.TYPE_OBJECT,
                properties={
                    'detail': openapi.Schema(type=openapi.TYPE_STRING)
                }
            )
        )
    }
)
@api_view(['GET', 'POST'])
@permission_classes([IsAuthenticated])
@transaction.atomic
def reservation_view(request):
    """
    예약 API
    
    GET: 예약 목록 조회
    - 로그인이 필요합니다.
    - 관리자는 모든 예약을 조회할 수 있습니다.
    - 일반 사용자는 자신의 예약만 조회할 수 있습니다.
    
    POST: 예약 신청
    - 로그인이 필요합니다.
    - 현재 시간에서 3일 이상 이후부터 3개월 이내의 날짜만 신청 가능합니다.
    - 최대 5만명까지 예약할 수 있습니다.
    """
    if request.method == 'GET':
        if request.user.is_staff:
            reservations = Reservation.objects.all()
        else:
            reservations = Reservation.objects.filter(user=request.user)
        
        reservations = reservations.order_by('-created_at')
        serializer = ReservationSerializer(reservations, many=True)
        
        return Response({
            'reservations': serializer.data
        })
    
    elif request.method == 'POST':
        serializer = ReservationCreateSerializer(data=request.data)
        if serializer.is_valid():
            start_time = serializer.validated_data['start_time']
            end_time = serializer.validated_data['end_time']
            count = serializer.validated_data['count']
            
            korea_tz = pytz.timezone('Asia/Seoul')
            current_datetime = timezone.now().astimezone(korea_tz)
            
            min_datetime = current_datetime + timedelta(days=3)
            if start_time < min_datetime:
                return Response(
                    {'error': '현재 시간에서 3일 이상 이후의 날짜만 신청이 가능합니다.'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            max_datetime = current_datetime + timedelta(days=90)
            if start_time > max_datetime:
                return Response(
                    {'error': '3개월 이내의 날짜만 신청이 가능합니다.'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            try:
                available_slots = list(ExamSlot.objects.filter(
                    date=start_time.date(),
                    hour__gte=start_time.hour,
                    hour__lt=end_time.hour,
                    current_count__lt=models.F('max_capacity')
                ).order_by('hour'))
                
                if not available_slots:
                    return Response(
                        {'error': '해당 시간대에 예약 가능한 자리가 없습니다.'},
                        status=status.HTTP_400_BAD_REQUEST
                    )
                
                for slot in available_slots:
                    if slot.max_capacity - slot.current_count < count:
                        return Response(
                            {'error': f'{slot.hour}시에 예약 가능한 자리가 부족합니다. (남은 자리: {slot.max_capacity - slot.current_count}명)'},
                            status=status.HTTP_400_BAD_REQUEST
                        )
                
                reservation = Reservation.objects.create(
                    user=request.user,
                    start_time=start_time,
                    end_time=end_time,
                    count=count,
                    status='pending'
                )
                
                try:
                    ExamSlot.reserve_slots(available_slots, count)
                    reservation.exam_slots.add(*available_slots)
                except ValidationError as e:
                    reservation.delete()
                    return Response(
                        {'error': str(e)},
                        status=status.HTTP_400_BAD_REQUEST
                    )
                
                reservation_serializer = ReservationSerializer(reservation)
                
                return Response({
                    'message': '예약이 성공적으로 신청되었습니다.',
                    'reservation': reservation_serializer.data
                }, status=status.HTTP_201_CREATED)
                
            except redis_lock.NotAcquired:
                return Response(
                    {'error': '현재 다른 예약이 처리 중입니다. 잠시 후 다시 시도해주세요.'},
                    status=status.HTTP_409_CONFLICT
                )
            except Exception as e:
                return Response(
                    {'error': '예약 처리 중 오류가 발생했습니다. 다시 시도해주세요.'},
                    status=status.HTTP_500_INTERNAL_SERVER_ERROR
                )
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
