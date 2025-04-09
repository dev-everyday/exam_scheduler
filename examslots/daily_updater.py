from datetime import timedelta
from .models import ExamSlot


def add_next_day_slots():
    last_slot = ExamSlot.objects.order_by('-date', '-hour').first()
    
    if last_slot:
        current_date = last_slot.date
        next_date = current_date + timedelta(days=1)
        
        slots_to_create = []
        for hour in range(24):
            slots_to_create.append(
                ExamSlot(
                    date=next_date,
                    hour=hour
                )
            )
        
        if slots_to_create:
            ExamSlot.objects.bulk_create(slots_to_create)