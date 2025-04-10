from django.db import models
from django.db import transaction
from django.core.exceptions import ValidationError
from django.core.validators import MinValueValidator, MaxValueValidator
from datetime import timedelta

class ExamSlot(models.Model):
    date = models.DateField()
    hour = models.IntegerField(validators=[MinValueValidator(0), MaxValueValidator(23)])
    max_capacity = models.IntegerField(default=50000)
    current_count = models.IntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'exam_slots'
        app_label = 'examslots'
        ordering = ['date', 'hour']
        unique_together = ('date', 'hour')

    def __str__(self):
        return f"Exam Slot: {self.date} - {self.hour}"

    def clean(self):
        if self.hour < 0 or self.hour > 23:
            raise ValidationError("시간은 0에서 23 사이여야 합니다.")

    def save(self, *args, **kwargs):
        self.clean()
        super().save(*args, **kwargs)

    @classmethod
    def check_and_get_available_slots(cls, start_time, end_time, count):
        available_slots = cls.get_available_slots(start_time, end_time)
        
        if not available_slots:
            raise ValidationError("해당 시간대에 예약 가능한 자리가 없습니다.")
            
        for slot in available_slots:
            available_count = slot.max_capacity - slot.current_count
            if available_count < count:
                raise ValidationError(f"{slot.date} {slot.hour}시에 {count}명을 수용할 수 없습니다. (가용 인원: {available_count}명)")
                
        return available_slots

    @classmethod
    def get_available_slots(cls, start_time, end_time):
        if start_time.date() == end_time.date():
            return cls.objects.filter(
                date=start_time.date(),
                hour__gte=start_time.hour,
                hour__lt=end_time.hour,
                current_count__lt=models.F('max_capacity')
            ).order_by('hour')
        
        slots = []
        current_date = start_time.date()
        end_date = end_time.date()
        
        while current_date <= end_date:
            if current_date == start_time.date():
                slots.extend(cls.objects.filter(
                    date=current_date,
                    hour__gte=start_time.hour,
                    current_count__lt=models.F('max_capacity')
                ).order_by('hour'))
            elif current_date == end_date:
                slots.extend(cls.objects.filter(
                    date=current_date,
                    hour__lt=end_time.hour,
                    current_count__lt=models.F('max_capacity')
                ).order_by('hour'))
            else:
                slots.extend(cls.objects.filter(
                    date=current_date,
                    current_count__lt=models.F('max_capacity')
                ).order_by('hour'))
            
            current_date += timedelta(days=1)
        
        return slots
    
    @classmethod
    @transaction.atomic
    def update_slots(cls, slots, count):
        updated_slots = []

        try:
            for slot in slots:
                slot.refresh_from_db() 

                if count > 0:
                    if slot.current_count + count > slot.max_capacity:
                        raise ValidationError(f"슬롯 {slot.id}의 최대 인원 수를 초과할 수 없습니다.")
                
                slot.current_count += count
                slot.save(update_fields=['current_count'])
                
                updated_slots.append(slot)
            return True
                
        except ValidationError as e:
            if updated_slots:
                for slot in updated_slots:
                    slot.refresh_from_db()
                    slot.current_count -= count
                    slot.save(update_fields=['current_count'])
            raise ValidationError(str(e))
            
        except Exception as e:
            if updated_slots:
                for slot in updated_slots:
                        slot.refresh_from_db()
                        slot.current_count -= count
                        slot.save(update_fields=['current_count'])
            raise ValidationError("예약 처리 중 오류가 발생했습니다.")