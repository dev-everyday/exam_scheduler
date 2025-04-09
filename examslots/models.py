from django.db import models
from django.db import transaction
from django.core.exceptions import ValidationError
from django.core.validators import MinValueValidator, MaxValueValidator
from .utils import with_distributed_lock

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
    def get_available_slots(cls, date):
        return cls.objects.filter(
            date=date,
            current_count__lt=models.F('max_capacity')
        ).order_by('hour')

    @transaction.atomic
    @with_distributed_lock('exam_slot', blocking_timeout=10)
    def update_capacity(self, count, status='pending'):
        self.refresh_from_db()
        
        if status == 'accepted':
            if self.current_count + count > self.max_capacity:
                raise ValidationError("최대 인원 수를 초과할 수 없습니다.")
            self.current_count += count
            self.save()
        return True

    @classmethod
    @transaction.atomic
    def reserve_slots(cls, slots, count, status='pending'):
        success = True
        updated_slots = []

        for slot in slots:
            try:
                if slot.update_capacity(count, status):
                    updated_slots.append(slot)
                else:
                    success = False
                    break
            except ValidationError:
                success = False
                break

        if not success:
            for slot in updated_slots:
                slot.update_capacity(-count, status)
            raise ValidationError("예약 처리 중 오류가 발생했습니다.")