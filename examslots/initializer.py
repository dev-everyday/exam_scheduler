from datetime import timedelta
from django.utils import timezone
from .models import ExamSlot

def initialize_exam_slots():
    ExamSlot.objects.all().delete()
    
    now = timezone.now()
    next_hour = now.replace(minute=0, second=0, microsecond=0) + timedelta(hours=1)
    three_months_later = next_hour + timedelta(days=90)
    
    slots_to_create = []

    current_time = next_hour
    while current_time < three_months_later:
        slots_to_create.append(
            ExamSlot(
                date=current_time.date(),
                hour=current_time.hour
            )
        )
        current_time += timedelta(hours=1)
    
    if slots_to_create:
        ExamSlot.objects.bulk_create(slots_to_create) 