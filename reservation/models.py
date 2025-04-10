from django.db import models
from django.contrib.auth import get_user_model
from examslots.models import ExamSlot
from django.db import transaction
from django.core.exceptions import ValidationError

User = get_user_model()

class Reservation(models.Model):
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('cancelled', 'Cancelled'),
        ('accepted', 'Accepted'),
    ]

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='reservations')
    exam_slots = models.ManyToManyField(ExamSlot, related_name='reservations')
    start_time = models.DateTimeField()
    end_time = models.DateTimeField()
    count = models.IntegerField(default=1, help_text="예약 인원 수")
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'reservations'
        app_label = 'reservation'

    def __str__(self):
        return f"Reservation: {self.user.username} - {self.start_time} to {self.end_time}"

    @transaction.atomic
    def confirm(self):
        if self.status != 'pending':
            raise ValidationError("대기 중인 예약만 확정할 수 있습니다.")
            
        exam_slots = list(self.exam_slots.all())
        if not exam_slots:
            raise ValidationError("예약에 해당하는 시간대가 없습니다.")
            
        slot_ids = [slot.id for slot in exam_slots]
        locked_slots = ExamSlot.objects.select_for_update().filter(id__in=slot_ids)
        
        ExamSlot.update_slots(locked_slots, self.count)
        
        Reservation.objects.filter(id=self.id).update(status='accepted')
        
        self.refresh_from_db()
        return self
        
    @transaction.atomic
    def modify(self, start_time=None, end_time=None, count=None):
        start_time = start_time or self.start_time
        end_time = end_time or self.end_time
        count = count if count is not None else self.count
        
        if start_time >= end_time:
            raise ValidationError("예약 시작 시간이 종료 시간보다 크거나 같을 수 없습니다.")
        
        if self.status == 'accepted':
            current_slots = list(self.exam_slots.select_for_update().all())
            
            ExamSlot.update_slots(current_slots, -self.count)
            
            try:
                new_slots = ExamSlot.check_and_get_available_slots(start_time, end_time, count)
                
                self.start_time = start_time
                self.end_time = end_time
                self.count = count
                self.save(update_fields=['start_time', 'end_time', 'count', 'updated_at'])
                
                self.exam_slots.set(new_slots)
                
                ExamSlot.update_slots(new_slots, count)
                
            except ValidationError as e:
                raise ValidationError(f"예약 변경이 불가능합니다: {str(e)}")
                
        else:
            new_slots = ExamSlot.check_and_get_available_slots(start_time, end_time, count)
            
            self.start_time = start_time
            self.end_time = end_time
            self.count = count
            self.save(update_fields=['start_time', 'end_time', 'count', 'updated_at'])
            
            self.exam_slots.set(new_slots)
            
        return self
        
    @transaction.atomic
    def cancel(self):
        if self.status == 'cancelled':
            return self
            
        if self.status == 'accepted':
            current_slots = list(self.exam_slots.select_for_update().all())
            ExamSlot.update_slots(current_slots, -self.count)
            
        self.exam_slots.clear()
        
        self.status = 'cancelled'
        self.save(update_fields=['status', 'updated_at'])
        
        return self
