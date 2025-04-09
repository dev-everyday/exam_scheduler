from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated, IsAdminUser
from rest_framework.response import Response
from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi
from django.db import transaction, connection
from django.utils import timezone
from django.core.exceptions import ValidationError, PermissionDenied
import pytz
from datetime import timedelta, datetime
from .models import Reservation
from .serializers import ReservationSerializer, ReservationDetailSerializer
from examslots.models import ExamSlot
from django.db import models
from django.shortcuts import get_object_or_404

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
        serializer = ReservationDetailSerializer(reservations, many=True)
        
        return Response({
            'reservations': serializer.data
        })
    
    elif request.method == 'POST':
        serializer = ReservationSerializer(data=request.data)
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
                available_slots = ExamSlot.check_and_get_available_slots(start_time, end_time, count)
                
                with transaction.atomic():
                    reservation = Reservation.objects.create(
                        user=request.user,
                        start_time=start_time,
                        end_time=end_time,
                        count=count,
                        status='pending'
                    )
                    
                    for slot in available_slots:
                        reservation.exam_slots.add(slot)
                    
                    response_serializer = ReservationDetailSerializer(reservation)
                    return Response({
                        'message': '예약이 성공적으로 신청되었습니다.',
                        'reservation': response_serializer.data
                    }, status=status.HTTP_201_CREATED)
                
            except ValidationError as e:
                return Response(
                    {'error': str(e)},
                    status=status.HTTP_400_BAD_REQUEST
                )
            except Exception as e:
                return Response(
                    {'error': '예약 처리 중 오류가 발생했습니다. 다시 시도해주세요.'},
                    status=status.HTTP_500_INTERNAL_SERVER_ERROR
                )
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

@swagger_auto_schema(
    method='get',
    operation_summary="예약 상세 조회 API",
    operation_description="예약 상세 정보를 조회합니다. 본인의 예약만 조회할 수 있습니다.",
    responses={
        200: openapi.Response(
            description="예약 상세 조회 성공",
            schema=openapi.Schema(
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
        ),
        401: openapi.Response(
            description="인증 실패",
            schema=openapi.Schema(
                type=openapi.TYPE_OBJECT,
                properties={
                    'detail': openapi.Schema(type=openapi.TYPE_STRING)
                }
            )
        ),
        403: openapi.Response(
            description="권한 없음",
            schema=openapi.Schema(
                type=openapi.TYPE_OBJECT,
                properties={
                    'detail': openapi.Schema(type=openapi.TYPE_STRING)
                }
            )
        ),
        404: openapi.Response(
            description="예약 없음",
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
    method='put',
    operation_summary="예약 수정 API",
    operation_description="예약 정보를 수정합니다. 대기 중인 예약만 수정할 수 있습니다.",
    request_body=openapi.Schema(
        type=openapi.TYPE_OBJECT,
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
        200: openapi.Response(
            description="예약 수정 성공",
            schema=openapi.Schema(
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
        ),
        403: openapi.Response(
            description="권한 없음",
            schema=openapi.Schema(
                type=openapi.TYPE_OBJECT,
                properties={
                    'detail': openapi.Schema(type=openapi.TYPE_STRING)
                }
            )
        ),
        404: openapi.Response(
            description="예약 없음",
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
    method='delete',
    operation_summary="예약 삭제 API",
    operation_description="예약을 삭제합니다. 대기 중인 예약만 삭제할 수 있습니다.",
    responses={
        204: openapi.Response(
            description="예약 삭제 성공"
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
        ),
        403: openapi.Response(
            description="권한 없음",
            schema=openapi.Schema(
                type=openapi.TYPE_OBJECT,
                properties={
                    'detail': openapi.Schema(type=openapi.TYPE_STRING)
                }
            )
        ),
        404: openapi.Response(
            description="예약 없음",
            schema=openapi.Schema(
                type=openapi.TYPE_OBJECT,
                properties={
                    'detail': openapi.Schema(type=openapi.TYPE_STRING)
                }
            )
        )
    }
)
@api_view(['GET', 'PUT', 'DELETE'])
@permission_classes([IsAuthenticated])
def reservation_detail_view(request, reservation_id):
    reservation = get_object_or_404(Reservation, id=reservation_id)
    
    if request.method == 'GET':
        if not request.user.is_staff and request.user != reservation.user:
            raise PermissionDenied("본인의 예약만 조회할 수 있습니다.")
        serializer = ReservationDetailSerializer(reservation)
        return Response(serializer.data)
    
    elif request.method == 'PUT':
        if not request.user.is_staff and request.user != reservation.user:
            raise PermissionDenied("본인의 예약만 수정할 수 있습니다.")
        
        if not request.user.is_staff and reservation.status != 'pending':
            return Response(
                {"error": "대기 중인 예약만 수정할 수 있습니다."},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        serializer = ReservationSerializer(data=request.data, partial=True)
        if serializer.is_valid():
            try:
                validated_data = serializer.validated_data
                
                start_time = validated_data.get('start_time', reservation.start_time)
                end_time = validated_data.get('end_time', reservation.end_time)
                count = validated_data.get('count', reservation.count)
                
                new_slots = ExamSlot.check_and_get_available_slots(
                    start_time,
                    end_time,
                    count
                )
                
                with transaction.atomic():
                    reservation.start_time = start_time
                    reservation.end_time = end_time
                    reservation.count = count
                    reservation.save()
                    
                    reservation.exam_slots.set(new_slots)
                    
                    response_serializer = ReservationDetailSerializer(reservation)
                    return Response(response_serializer.data)
                    
            except ValidationError as e:
                return Response(
                    {"error": str(e)},
                    status=status.HTTP_400_BAD_REQUEST
                )
            except Exception as e:
                return Response(
                    {'error': '예약 처리 중 오류가 발생했습니다. 다시 시도해주세요.'},
                    status=status.HTTP_500_INTERNAL_SERVER_ERROR
                )
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    elif request.method == 'DELETE':
        if not request.user.is_staff and request.user != reservation.user:
            raise PermissionDenied("본인의 예약만 삭제할 수 있습니다.")
        
        if not request.user.is_staff and reservation.status != 'pending':
            return Response(
                {"error": "대기 중인 예약만 삭제할 수 있습니다."},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            with transaction.atomic():
                if reservation.status == 'accepted':
                    ExamSlot.update_slots(reservation.exam_slots.all(), -reservation.count)
                
                reservation.status = 'cancelled'
                reservation.save()
                
                reservation.exam_slots.clear()

            return Response({'message': '예약이 성공적으로 취소되었습니다.'}, status=status.HTTP_204_NO_CONTENT)
        except ValidationError as e:
            return Response(
                {"error": str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )
        
@swagger_auto_schema(
    method='post',
    operation_summary="예약 확정 API",
    operation_description="관리자가 예약을 확정합니다. 확정 중에는 다른 예약 관련 작업이 불가능합니다.",
    responses={
        200: openapi.Response(
            description="예약 확정 성공",
            schema=openapi.Schema(
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
        403: openapi.Response(
            description="권한 없음",
            schema=openapi.Schema(
                type=openapi.TYPE_OBJECT,
                properties={
                    'detail': openapi.Schema(type=openapi.TYPE_STRING)
                }
            )
        ),
        404: openapi.Response(
            description="예약 없음",
            schema=openapi.Schema(
                type=openapi.TYPE_OBJECT,
                properties={
                    'detail': openapi.Schema(type=openapi.TYPE_STRING)
                }
            )
        )
    }
)
@api_view(['POST'])
@permission_classes([IsAdminUser])
def confirm_reservation_view(request, reservation_id):
    reservation = get_object_or_404(Reservation, id=reservation_id)
    
    exam_slots = list(reservation.exam_slots.all())
    if reservation.status != 'pending':
        return Response(
            {"error": "대기 중인 예약만 확정할 수 있습니다."},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    try:
        with transaction.atomic():
            reservation.status = 'accepted'
            reservation.save()
            
            ExamSlot.update_slots(exam_slots, reservation.count)
            
            for slot in exam_slots:
                slot.refresh_from_db()
            
            transaction.on_commit(lambda: check_reservation_status_after_confirm(reservation_id))
            
            serializer = ReservationDetailSerializer(reservation)
            return Response(serializer.data)
            
    except ValidationError as e:
        return Response(
            {"error": str(e)},
            status=status.HTTP_400_BAD_REQUEST
        )
    except Exception as e:
        return Response(
            {"error": "예약 확정 중 오류가 발생했습니다."},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )

def check_reservation_status_after_confirm(reservation_id):
    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT status FROM reservations WHERE id = %s", [reservation_id])
            result = cursor.fetchone()
            return result[0] if result else None
    except Exception as e:
        print(f"예약 상태 확인 중 오류: {e}")
        return None