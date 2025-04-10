시험 일정을 예약하고 관리할 수 있는 REST API 서비스입니다.

## 1. 설치 및 실행 방법

### 필수 요구사항

- Python 3.8 이상
- PostgreSQL
- Redis

### 설치 방법

1. 저장소 클론

```bash
git clone https://github.com/dev-everyday/exam_scheduler.git
cd exam_scheduler
```

2. 가상환경 생성 및 활성화

```bash
python -m venv venv
source venv/bin/activate  # Linux/Mac
venv\Scripts\activate     # Windows
```

3. 의존성 패키지 설치

```bash
pip install -r requirements.txt
```

4. PostgreSQL 데이터베이스 생성

```bash
# PostgreSQL 접속
psql -U postgres

# 데이터베이스 생성
CREATE DATABASE exam_scheduler;

# 데이터베이스 생성 확인
\l
```

5. 환경 변수 설정
   `.env` 파일을 생성하고 다음 내용을 입력합니다:

```
DB_NAME=exam_scheduler
DB_USER=postgres
DB_PASSWORD=your_db_password
DB_HOST=localhost
DB_PORT=5432
SECRET_KEY=your_secret_key
```

6. Redis 설치 및 실행

```bash
# Redis 설치 및 실행 (Windows)
# Window의 경우 https://github.com/microsoftarchive/redis/releases 에서 Redis-x64-xxx.msi 다운로드 및 설치
redis-server

# Redis 서버 상태 확인
redis-cli ping
```

7. 데이터베이스 마이그레이션

```bash
python manage.py migrate
```

8. 관리자 계정 생성

```bash
python manage.py createsuperuser
# 사용자 이름, 이메일, 비밀번호를 입력하세요
```

9. 서버 실행

```bash
python manage.py runserver
```

## 2. 주요 기능 요약

- 시험 일정 예약

  - 현재 시간에서 3일 이상 이후부터 3개월 이내의 날짜만 예약 가능
  - 시간대별 최대 5만명까지 예약 가능
  - 예약 가능한 시간대 조회 기능(1시간 단위로 신청 가능)

- 예약 관리

  - 본인 예약 조회/수정/취소(수정, 취소는 대기 중일 경우에만 가능)
  - 관리자 사용자 예약 관리

- 자동화된 기능

  - 초기 시험 시간대 생성(3일 후부터 3개월 후까지 24시간 기준으로 자동 추가)
  - 매일 자동으로 다음 날의 시험 시간대 생성(마지막 시간으로부터 24시간)
  - 분산 락을 통한 동시성 제어

## 3. Swagger 기반 API 문서 활용 가이드

1. 서버 실행 후 다음 URL에 접속:

```
http://localhost:8000/swagger/
```

2. API 문서 확인

   - 각 API의 요청/응답 형식 확인 가능
   - API 테스트 가능

3. 인증

   - 맨 처음 Login을 통해서 생성한 유저의 token 발급
   - 우측 상단의 'Authorize' 버튼 클릭
   - 토큰 입력 (형식: Token your\_token\_here)
   - 'Authorize' 버튼 클릭하여 인증 완료

## 4. API 목록

| 메서드 | 엔드포인트 | 설명 |
|--------|-------------|------|
| GET    | /examslots/available/          | 특정 날짜의 예약 가능한 시간대 조회 |
| POST   | /reservation/                  | 시험 예약 생성 |
| GET    | /reservation/my/               | 본인의 예약 조회 |
| PATCH  | /reservation/my/               | 본인의 예약 수정 (대기 중일 경우) |
| DELETE | /reservation/my/               | 본인의 예약 삭제 (대기 중일 경우) |
| GET    | /reservation/admin/            | 관리자 - 전체 예약 목록 조회 |
| GET  | /reservation/admin/{id}          | 관리자 - 해당 예약 조회 |
| PATCH  | /reservation/admin/{id}        | 관리자 - 해당 예약 수정 |
| DELETE | /reservation/admin/{id}        | 관리자 - 해당 예약 삭제 |
| POST   | /reservation/admin/{id}/confirm| 관리자 - 해당 예약 확정 |
| POST   | /users/login/                  | 로그인 (Token 발급) |
| POST   | /users/signup/                 | 회원 가입 |
| GET    | /users/my/                     | 본인 정보 조회 |
| PUT    | /users/my/                     | 본인 정보 수정 |
| DELETE | /users/my/                     | 본인 정보 삭제 |
| GET    | /users/admin/                  | 관리자 - 전체 사용자 목록 조회 |
| GET    | /users/admin/{id}              | 관리자- 해당 사용자 조회 |
| PUT    | /users/admin/{id}              | 관리자- 해당 사용자 수정 |
| DELETE | /users/admin/{id}              | 관리자- 해당 사용자 삭제 |

## 5. 기술 스택

- **Backend**

  - Django 5.2
  - Django REST Framework 3.16.0
  - PostgreSQL
  - Redis
  - APScheduler 3.11.0

- **인증/인가**

  - Token Authentication
  - Django Authentication System

- **문서화**

  - drf-yasg (Swagger/OpenAPI)

- **동시성 제어**

  - Redis Distributed Lock
  - Django Transaction

## 6. DB 스키마

### users

| 필드            | 타입             | 설명          |
| ------------- | -------------- | ----------- |
| id            | BigAutoField   | Primary Key |
| username      | CharField(150) | 사용자 아이디     |
| password      | CharField(128) | 비밀번호        |
| is\_superuser | BooleanField   | 관리자 여부      |
| created\_at   | DateTimeField  | 생성 시간       |
| updated\_at   | DateTimeField  | 수정 시간       |

### exam\_slots

| 필드             | 타입            | 설명          |
| -------------- | ------------- | ----------- |
| id             | BigAutoField  | Primary Key |
| date           | DateField     | 날짜          |
| hour           | IntegerField  | 시간 (0-23)   |
| max\_capacity  | IntegerField  | 최대 수용 인원    |
| current\_count | IntegerField  | 현재 예약 인원    |
| created\_at    | DateTimeField | 생성 시간       |
| updated\_at    | DateTimeField | 수정 시간       |

### reservations

| 필드          | 타입            | 설명                              |
| ----------- | ------------- | ------------------------------- |
| id          | BigAutoField  | Primary Key                     |
| user        | ForeignKey    | 사용자 ID                          |
| start\_time | DateTimeField | 시작 시간                           |
| end\_time   | DateTimeField | 종료 시간                           |
| count       | IntegerField  | 예약 인원 수                         |
| status      | CharField     | 상태 (pending/cancelled/accepted) |
| created\_at | DateTimeField | 생성 시간                           |
| updated\_at | DateTimeField | 수정 시간                           |

### reservations\_exam\_slots (중간 테이블)

| 필드              | 타입           | 설명          |
| --------------- | ------------ | ----------- |
| id              | BigAutoField | Primary Key |
| reservation\_id | ForeignKey   | 예약 ID       |
| examslot\_id    | ForeignKey   | 시험 시간대 ID   |

## 7. 고려했던 상황과 해결방안

### 동시성 제어 문제

- **상황**: 여러 관리자가가 동시에 같은 시간대를 예약을 확정할 때 발생할 수 있는 경쟁 상태 문제
- **해결방안**:
  - Redis 분산 락(Distributed Lock)을 사용하여 동시 접근 제어
  - Django의 트랜잭션 관리와 함께 사용하여 데이터 일관성 보장
  - 락 획득 시도 시 타임아웃 설정으로 데드락 방지

### 예약 시간대 자동 생성

- **상황**: 매일 새로운 예약 시간대를 수동으로 생성하는 것은 비효율적
- **해결방안**:
  - APScheduler를 사용하여 매일 자동으로 다음 날의 시간대 생성
  - 서버 시작 시 초기 시간대 데이터 생성 로직 구현(시작일\~3달 뒤까지 1시간 단위로 생성함)
  - 시간대 생성 시 벌크 인서트(Bulk Insert)를 사용하여 성능 최적화

### 시간대 검증

- **상황**: 과거 시간대나 너무 먼 미래의 시간대 예약 방지 필요
- **해결방안**:
  - 예약 시 시작 시간과 종료 시간의 유효성 검증
  - 현재 시간에서 3일 이상 이후부터 3개월 이내의 날짜만 예약 가능하도록 제한

### API 문서화

- **상황**: 다양한 API를 제공하나 사용자(클라이언트 개발자, 운영자 등)들이 요청/응답 형식과 사용 방법을 명확히 이해하지 못할 수 있음
- **해결방안**:
  - drf-yasg를 활용한 Swagger 기반 자동 문서화 적용
  - 각 API에 대한 request/response 스펙 명시 및 테스트 기능 제공
  - 인증이 필요한 API 사용을 위한 Token 기반 인증 방식 가이드 제공

