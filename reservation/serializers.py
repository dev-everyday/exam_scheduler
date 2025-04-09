from rest_framework import serializers
from .models import Reservation
from datetime import timedelta
from django.utils import timezone
import pytz

class ReservationCreateSerializer(serializers.Serializer):
    start_time = serializers.DateTimeField(
        format="%Y-%m-%d %H:%M",
        input_formats=["%Y-%m-%d %H:%M"],
        help_text="예약 시작 시간 (YYYY-MM-DD HH:MM 형식, 예: 2025-04-15 09:00)"
    )
    end_time = serializers.DateTimeField(
        format="%Y-%m-%d %H:%M",
        input_formats=["%Y-%m-%d %H:%M"],
        help_text="예약 종료 시간 (YYYY-MM-DD HH:MM 형식, 예: 2025-04-15 11:00)"
    )
    count = serializers.IntegerField(
        min_value=1,
        help_text="예약 인원 수"
    )

    def validate(self, data):
        start_time = data.get('start_time')
        end_time = data.get('end_time')
        count = data.get('count')

        if start_time.minute != 0:
            raise serializers.ValidationError({
                'start_time': '시험 시작 시간은 정각(00분)이어야 합니다.'
            })
        
        if end_time.minute != 0:
            raise serializers.ValidationError({
                'end_time': '시험 종료 시간은 정각(00분)이어야 합니다.'
            })

        korea_tz = pytz.timezone('Asia/Seoul')
        current_datetime = timezone.now().astimezone(korea_tz)

        min_datetime = current_datetime + timedelta(days=3)
        if start_time < min_datetime:
            raise serializers.ValidationError({
                'start_time': '현재 시간에서 3일 이상 이후의 날짜만 신청이 가능합니다.'
            })

        max_datetime = current_datetime + timedelta(days=90)
        if start_time > max_datetime:
            raise serializers.ValidationError({
                'start_time': '3개월 이내의 날짜만 신청이 가능합니다.'
            })

        if start_time >= end_time:
            raise serializers.ValidationError({
                'end_time': '종료 시간은 시작 시간보다 이후여야 합니다.'
            })

        if count > 50000:
            raise serializers.ValidationError({
                'count': '최대 5만명까지만 예약할 수 있습니다.'
            })

        return data

class ReservationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Reservation
        fields = ['id', 'user', 'start_time', 'end_time', 'status', 'created_at', 'count']
        read_only_fields = ['id', 'user', 'status', 'created_at'] 