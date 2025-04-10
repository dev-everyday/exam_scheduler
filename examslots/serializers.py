from rest_framework import serializers
from .models import ExamSlot

class ExamSlotSerializer(serializers.ModelSerializer):
    remaining_capacity = serializers.SerializerMethodField()

    class Meta:
        model = ExamSlot
        fields = ['date', 'hour', 'remaining_capacity']

    def get_remaining_capacity(self, obj):
        return obj.max_capacity - obj.current_count 

class AvailableSlotSerializer(serializers.Serializer):
    date = serializers.DateField()
    hour = serializers.IntegerField()
    remaining_capacity = serializers.IntegerField()

class AvailableSlotListResponseSerializer(serializers.Serializer):
    message = serializers.CharField()
    available_slots = AvailableSlotSerializer(many=True)