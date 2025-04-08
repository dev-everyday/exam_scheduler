from django.db import models
from users.models import User
from examslots.models import ExamSlot

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
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='pending')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'reservations'
        app_label = 'reservation'

    def __str__(self):
        return f"Reservation: {self.user.username} - {self.start_time} to {self.end_time}"

    def get_exam_slot_ids(self):
        """예약된 시간대 ID 목록을 반환합니다."""
        return list(self.exam_slots.values_list('id', flat=True).order_by('start_time'))
