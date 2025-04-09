from django.db import models
from django.core.exceptions import ValidationError
from django.core.validators import MinValueValidator, MaxValueValidator

# Create your models here.

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