from django.db import models
from django.core.exceptions import ValidationError
from datetime import timedelta

# Create your models here.

class ExamSlot(models.Model):
    start_time = models.DateTimeField()
    end_time = models.DateTimeField()
    max_capacity = models.IntegerField(default=50000)
    current_count = models.IntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'exam_slots'
        app_label = 'examslots'
        ordering = ['start_time']

    def __str__(self):
        return f"Exam Slot: {self.start_time} - {self.end_time}"

    def clean(self):
        if self.end_time <= self.start_time:
            raise ValidationError("종료 시간은 시작 시간보다 이후여야 합니다.")

    def save(self, *args, **kwargs):
        self.clean()
        super().save(*args, **kwargs)