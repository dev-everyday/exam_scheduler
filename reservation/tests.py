from datetime import datetime, timezone
from django.test import TestCase
from django.conf import settings
from redis import Redis
from rest_framework.test import APIClient
from django.contrib.auth import get_user_model
from django.utils import timezone
import datetime
from reservation.models import Reservation, ExamSlot
import threading
import time
import json

from exam_scheduler import settings
from reservation.models import User

User = get_user_model()

class RedisDistributedLockIntegrationTest(TestCase):
    # 분산 락 통합 테스트
    
    def setUp(self):
        from redis import Redis
        from django.conf import settings
        
        redis_url = settings.CACHES['default']['LOCATION']
        self.redis_client = Redis.from_url(redis_url)
        
        for key in self.redis_client.keys("lock:test:*"):
            self.redis_client.delete(key)
    
    def tearDown(self):
        for key in self.redis_client.keys("lock:test:*"):
            self.redis_client.delete(key)
            
        self.redis_client.close()
    
    def test_real_lock_acquisition_and_release(self):
        # 락 획득 및 해제 테스트
        from common.distributed_lock import acquire_lock, release_lock
        import time

        # 락 획득
        lock_key = "test:real:lock:1"
        lock = acquire_lock(lock_key, timeout=10, blocking_timeout=5)
        self.assertIsNotNone(lock)
        
        # 동일한 락 키로 다시 락 획득 시도 (실패해야 함)
        lock2 = acquire_lock(lock_key, timeout=10, blocking_timeout=1)
        self.assertIsNone(lock2) 
        
        # 락 해제
        try:
            release_lock(lock)
        except Exception as e:
            pass
       
    def test_real_concurrent_lock_acquisition(self):
        # 동시 락 획득 테스트
        from common.distributed_lock import acquire_lock, release_lock
        import threading
        import time
        
        lock_key = "test:real:concurrent:lock"
        results = []
        
        def try_acquire_lock():
            lock = acquire_lock(lock_key, timeout=5, blocking_timeout=1)
            results.append(lock is not None)
            
            if lock:
                time.sleep(1)
                release_lock(lock)
        
        # 3개의 스레드 생성 후 동시에 실행
        threads = []
        for _ in range(3):
            t = threading.Thread(target=try_acquire_lock)
            threads.append(t)
        
        for t in threads:
            t.start()
        
        for t in threads:
            t.join()
        
        self.assertTrue(any(results))
    
    def test_real_lock_expiration(self):
        # 락 만료 테스트
        from common.distributed_lock import acquire_lock, release_lock
        import time
        
        lock = acquire_lock("test:real:expiration:lock", timeout=1, blocking_timeout=1)
        self.assertIsNotNone(lock)
        
        time.sleep(2)
        
        lock2 = acquire_lock("test:real:expiration:lock", timeout=5, blocking_timeout=1)
        self.assertIsNotNone(lock2)
        release_lock(lock2)
    
class APIDistributedLockTest(TestCase):
    # API 분산 락 테스트
    def setUp(self):
        # 관리자 유저 생성
        self.admin = User.objects.create_superuser(
            username='admin', password='adminpassword'
        )
        
        # 테스트용 시간대 생성(00시~02시시)
        base_date = timezone.now().date() + datetime.timedelta(days=4)
        self.slot1_start = timezone.make_aware(
            datetime.datetime.combine(base_date, datetime.time(0, 0))
        )
        self.slot1_end = timezone.make_aware(
            datetime.datetime.combine(base_date, datetime.time(2, 0))
        )
        
        # 테스트용 ExamSlot 생성
        self.exam_slot1 = ExamSlot.objects.create(
            date=self.slot1_start.date(),
            hour=self.slot1_start.hour,
            max_capacity=50000,
            current_count=0
        )
        
        self.exam_slot2 = ExamSlot.objects.create(
            date=self.slot1_start.date(),
            hour=self.slot1_start.hour + 1,
            max_capacity=50000,
            current_count=0
        )
        
        from redis import Redis
        self.redis_client = Redis.from_url(settings.CACHES['default']['LOCATION'])
        self.redis_client.flushall()
        
    def test_api_lock_contention(self):
        # 관리자가 두 개의 요청을 동시에 보내는 테스트
        client1 = APIClient()
        client2 = APIClient()
        client1.force_authenticate(user=self.admin)
        client2.force_authenticate(user=self.admin)
        
        # 테스트용 예약 데이터 생성
        test_user = User.objects.create_user(username='testuser')
        reservation = Reservation.objects.create(
            user=test_user,
            start_time=self.slot1_start,
            end_time=self.slot1_end,
            count=100,
            status='pending'
        )
        reservation.exam_slots.add(self.exam_slot1, self.exam_slot2)
        
        from django.urls import reverse
        try:
            admin_url = reverse('admin_reservation_detail', args=[reservation.id])
        except Exception as e:
            admin_url = f"/reservation/admin/{reservation.id}/"
        
        results = {'client1': None, 'client2': None}
        
        def call_api_client1():
            results['client1'] = client1.patch(
                admin_url,
                data=json.dumps({'count': 20000}),
                content_type='application/json'
            )
            
        def call_api_client2():
            time.sleep(0.1)
            results['client2'] = client2.patch(
                admin_url,
                data=json.dumps({'count': 30000}),
                content_type='application/json'
            )
        
        t1 = threading.Thread(target=call_api_client1)
        t2 = threading.Thread(target=call_api_client2)
        t1.start()
        t2.start()
        t1.join()
        t2.join()
        
        has_404 = False
        has_409 = False
        
        if results['client1'].status_code == 404:
            has_404 = True
        elif results['client1'].status_code == 409:
            has_409 = True
            
        if results['client2'].status_code == 404:
            has_404 = True
        elif results['client2'].status_code == 409:
            has_409 = True
        
        self.assertTrue(has_409, "분산 락 작동 X")