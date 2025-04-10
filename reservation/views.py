from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated, IsAdminUser
from rest_framework.response import Response
from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi
from django.db import transaction, connection
from django.core.exceptions import ValidationError, PermissionDenied
from common.serializers import ErrorResponseSerializer
from .models import Reservation
from .serializers import ReservationListResponseSerializer, ReservationSerializer, ReservationDetailSerializer
from examslots.models import ExamSlot
from django.shortcuts import get_object_or_404

@swagger_auto_schema(
    method='post',
    operation_summary="시험 예약 API",
    operation_description="시험 예약을 신청합니다. 로그인이 필요하며, 현재 시간에서 3일 이상 이후부터 3개월 이내의 날짜만 신청 가능합니다. 최대 5만명까지 예약할 수 있습니다.",
    request_body=ReservationSerializer,
    responses={
        201: ReservationDetailSerializer,
        400: ErrorResponseSerializer,
        401: ErrorResponseSerializer
    }
)
@api_view(['POST'])
@permission_classes([IsAuthenticated])
@transaction.atomic
def reservation_view(request):
    """
    예약 신청 API

    - 로그인이 필요합니다.
    - 현재 시간에서 3일 이상 이후부터 3개월 이내의 날짜만 신청 가능합니다.
    - 최대 5만명까지 예약할 수 있습니다.
    """
    serializer = ReservationSerializer(data=request.data)
    if serializer.is_valid():
        start_time = serializer.validated_data['start_time']
        end_time = serializer.validated_data['end_time']
        count = serializer.validated_data['count']

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
                return Response(response_serializer.data, status=status.HTTP_201_CREATED)
            
        except ValidationError as e:
            return Response(ErrorResponseSerializer({'error': str(e)}).data, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            return Response(ErrorResponseSerializer({'error': '예약 처리 중 오류가 발생했습니다. 다시 시도해주세요.'}).data, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    return Response(ErrorResponseSerializer(serializer.errors).data, status=status.HTTP_400_BAD_REQUEST)

@swagger_auto_schema(
    method='get',
    operation_summary="예약 목록 조회 API",
    operation_description="로그인한 사용자의 권한에 따라 예약 목록을 조회합니다. 관리자는 모든 예약을, 일반 사용자는 자신의 예약만 조회할 수 있습니다.",
    responses={
        200: ReservationListResponseSerializer,
        401: ErrorResponseSerializer
    }
)
@api_view(['GET'])
@permission_classes([IsAuthenticated, IsAdminUser])
@transaction.atomic
def admin_reservation_view(request):
    """ 
    예약 목록 조회 관리자 API
    
    관리자는 모든 예약을 조회할 수 있습니다.
    """
    reservations = Reservation.objects.all().order_by('-created_at')
    data = ReservationListResponseSerializer({'reservations': ReservationDetailSerializer(reservations, many=True).data})
    return Response(data.data)
            
@swagger_auto_schema(
    method='get',
    operation_summary="예약 상세 조회 API",
    operation_description="예약 상세 정보를 조회합니다. 본인의 예약만 조회할 수 있습니다.",
    responses={
        200: ReservationDetailSerializer,
        403: ErrorResponseSerializer,
        404: ErrorResponseSerializer
    }
)
@swagger_auto_schema(
    method='patch',
    operation_summary="예약 수정 API",
    operation_description="예약 정보를 수정합니다. 대기 중인 본인의 예약만 수정할 수 있습니다.",
    request_body=ReservationSerializer,
    responses={
        200: ReservationDetailSerializer,
        400: ErrorResponseSerializer,
        403: ErrorResponseSerializer,
        404: ErrorResponseSerializer,
        500: ErrorResponseSerializer
    }
)
@swagger_auto_schema(
    method='delete',
    operation_summary="예약 삭제 API",
    operation_description="예약을 삭제합니다. 대기 중인 본인의 예약만 삭제할 수 있습니다.",
    responses={
        204: None,
        400: ErrorResponseSerializer,
        401: ErrorResponseSerializer,
        403: ErrorResponseSerializer,
        404: ErrorResponseSerializer,
        500: ErrorResponseSerializer
    }
)
@api_view(['GET', 'PATCH', 'DELETE'])
@permission_classes([IsAuthenticated])
@transaction.atomic
def reservation_detail_view(request):
    reservation = get_object_or_404(Reservation, user=request.user)
    if request.user.is_superuser:
        return Response(ErrorResponseSerializer({'error': '관리자 전용 API를 이용해주세요.'}).data,
                         status=status.HTTP_403_FORBIDDEN)
    
    if request.method == 'GET':
        serializer = ReservationDetailSerializer(reservation)
        return Response(serializer.data, status=status.HTTP_200_OK)
    
    elif request.method == 'PATCH':
        if reservation.status != 'pending':
            return Response(ErrorResponseSerializer({'error': '대기 중인 예약만 수정할 수 있습니다.'}).data,
                             status=status.HTTP_400_BAD_REQUEST)
        
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
                    return Response(response_serializer.data, status=status.HTTP_200_OK)
                    
            except ValidationError as e:
                return Response(ErrorResponseSerializer({'error': str(e)}).data,
                                 status=status.HTTP_400_BAD_REQUEST)
            except Exception as e:
                return Response(ErrorResponseSerializer({'error': '예약 처리 중 오류가 발생했습니다. 다시 시도해주세요.'}).data,
                                 status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    elif request.method == 'DELETE':
        if reservation.status != 'pending':
            return Response(ErrorResponseSerializer({'error': '대기 중인 예약만 삭제할할 수 있습니다.'}).data,
                             status=status.HTTP_400_BAD_REQUEST)
        
        try:       
            reservation.status = 'cancelled'
            reservation.save()
            
            reservation.exam_slots.clear()

            return Response(status=status.HTTP_204_NO_CONTENT)
        except ValidationError as e:
            return Response(ErrorResponseSerializer({'error': str(e)}).data,
                             status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            return Response(ErrorResponseSerializer({'error': '예약 처리 중 오류가 발생했습니다. 다시 시도해주세요.'}).data,
                             status=status.HTTP_500_INTERNAL_SERVER_ERROR)

@swagger_auto_schema(
    method='get',
    operation_summary="관리자용 예약 상세 조회 API",
    operation_description="예약 상세 정보를 조회합니다.",
    responses={
        200: ReservationDetailSerializer,
        403: ErrorResponseSerializer,
        404: ErrorResponseSerializer
    }
)
@swagger_auto_schema(
    method='patch',
    operation_summary="관리자용 예약 수정 API",
    operation_description="예약 정보를 수정합니다.",
    request_body=ReservationSerializer,
    responses={
        200: ReservationDetailSerializer,
        400: ErrorResponseSerializer,
        403: ErrorResponseSerializer,
        404: ErrorResponseSerializer,
        500: ErrorResponseSerializer
    }
)
@swagger_auto_schema(
    method='delete',
    operation_summary="관리자용 예약 삭제 API",
    operation_description="예약을 삭제합니다.",
    responses={
        204: None,
        400: ErrorResponseSerializer,
        401: ErrorResponseSerializer,
        403: ErrorResponseSerializer,
        404: ErrorResponseSerializer,
        500: ErrorResponseSerializer
    }
)
@api_view(['GET', 'PATCH', 'DELETE'])
@permission_classes([IsAdminUser])
@transaction.atomic
def admin_reservation_detail_view(request, reservation_id):
    reservation = get_object_or_404(Reservation, id=reservation_id)
    
    if request.method == 'GET':
        serializer = ReservationDetailSerializer(reservation)
        return Response(serializer.data, status=status.HTTP_200_OK)
    
    elif request.method == 'PATCH':
        # if reservation.status == 'accepted':
            # TODO: 확정된 예약 수정 시 락 획득 필요요

        serializer = ReservationSerializer(data=request.data, partial=True)
        if serializer.is_valid():
            try:
                validated_data = serializer.validated_data
                
                start_time = validated_data.get('start_time', reservation.start_time)
                end_time = validated_data.get('end_time', reservation.end_time)
                count = validated_data.get('count', reservation.count)

                if(start_time >= end_time):
                    return Response(ErrorResponseSerializer({'error': '예약 시작 시간이 종료 시간보다 크거나 같을 수 없습니다.'}).data,
                                     status=status.HTTP_400_BAD_REQUEST)
                
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
                    return Response(response_serializer.data, status=status.HTTP_200_OK)
                    
            except ValidationError as e:
                return Response(ErrorResponseSerializer({'error': str(e)}).data,
                                 status=status.HTTP_400_BAD_REQUEST)
            except Exception as e:
                return Response(ErrorResponseSerializer({'error': '예약 처리 중 오류가 발생했습니다. 다시 시도해주세요.'}).data,
                                 status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    elif request.method == 'DELETE':
        try:
            with transaction.atomic():
                if reservation.status == 'accepted':
                    ExamSlot.update_slots(reservation.exam_slots.all(), -reservation.count)
                
                reservation.status = 'cancelled'
                reservation.save()
                
                reservation.exam_slots.clear()

            return Response(status=status.HTTP_204_NO_CONTENT)
        except ValidationError as e:
            return Response(ErrorResponseSerializer({'error': str(e)}).data,
                             status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            return Response(ErrorResponseSerializer({'error': '예약 처리 중 오류가 발생했습니다. 다시 시도해주세요.'}).data,
                             status=status.HTTP_500_INTERNAL_SERVER_ERROR)
            
        
@swagger_auto_schema(
    method='post',
    operation_summary="관리자용 예약 확정 API",
    operation_description="관리자가 예약을 확정합니다.",
    responses={
        200: ReservationDetailSerializer,
        400: ErrorResponseSerializer,
        403: ErrorResponseSerializer,
        404: ErrorResponseSerializer
    }
)
@api_view(['POST'])
@permission_classes([IsAdminUser])
def admin_reservation_confirm_view(request, reservation_id):
    reservation = get_object_or_404(Reservation, id=reservation_id)

    if reservation.status != 'pending':
        return Response(ErrorResponseSerializer({'error': '대기 중인 예약만 확정할 수 있습니다.'}).data,
                         status=status.HTTP_400_BAD_REQUEST)
    
    exam_slots = list(reservation.exam_slots.all())
    
    if not exam_slots:
        return Response(ErrorResponseSerializer({'error': '예약에 해당하는 시간대가 없습니다.'}).data,
                         status=status.HTTP_400_BAD_REQUEST)
    
    try:
        with transaction.atomic():
            reservation.status = 'accepted'
            reservation.save()
            
            ExamSlot.update_slots(exam_slots, reservation.count)
            
            for slot in exam_slots:
                slot.refresh_from_db()

            serializer = ReservationDetailSerializer(reservation)
            return Response(serializer.data)
            
    except ValidationError as e:
        return Response(ErrorResponseSerializer({'error': str(e)}).data,
                         status=status.HTTP_400_BAD_REQUEST)
    except Exception as e:
        return Response(ErrorResponseSerializer({'error': '예약 확정 중 오류가 발생했습니다.'}).data,
                         status=status.HTTP_500_INTERNAL_SERVER_ERROR)