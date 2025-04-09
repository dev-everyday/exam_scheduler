from django.apps import AppConfig
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger


class ExamslotsConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'examslots'
    verbose_name = 'Exam Slots'

    def ready(self):
        import sys
        if 'runserver' in sys.argv:
            from .daily_updater import add_next_day_slots
            from .initializer import initialize_exam_slots
            
            initialize_exam_slots()
            
            scheduler = BackgroundScheduler()
            scheduler.add_job(
                add_next_day_slots,
                trigger=CronTrigger(hour=0, minute=0),
                id='add_next_day_slots',
                name='Add next day slots',
                replace_existing=True
            )
            scheduler.start()