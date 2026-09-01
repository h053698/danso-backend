# danso-backend

단소(Danso) 타이핑 게임의 백엔드 API 서버. Django + DRF 기반, Google OAuth 인증, 실시간 1v1 매칭, 문장 팩 관리, 리더보드를 제공한다.

## 기술 스택

- **Python 3.12** / **Django 5.2** / **Django REST Framework**
- **adrf** — async Django view 지원
- **PostgreSQL** — 메인 데이터베이스
- **Gunicorn + Uvicorn Worker** — ASGI 프로덕션 서버
- **uv** — 패키지 관리

## 프로젝트 구조

```
danso-backend/
├── danso/          # 프로젝트 설정 (settings, urls, wsgi, asgi)
├── user/           # 유저 모델, Google OAuth 인증
├── sentence/       # 문장 팩, 리더보드, 좋아요
└── realtime/       # 실시간 1v1 매칭 및 게임 세션 관리
```

## 인증

모든 인증이 필요한 엔드포인트는 `X-Login-Code` 헤더를 사용한다.

로그인 플로우:
1. `GET /login/oauth/` → Google OAuth 리다이렉트
2. Google 인증 완료 → `/login/result?login_code=X000000` 리다이렉트
3. 이후 모든 요청에 `X-Login-Code: X000000` 헤더 포함

## API 엔드포인트

### 인증

| Method | Path | 설명 |
|--------|------|------|
| GET | `/login/oauth/` | Google OAuth 로그인 URL로 리다이렉트 |
| GET | `/login/callback` | Google OAuth 콜백 처리 |
| GET | `/login/result` | 로그인 결과 페이지 (login_code 발급) |
| GET | `/user/me` | 내 정보 조회 `🔒` |
| POST | `/user/logout` | 로그아웃 `🔒` |

### 문장 팩

| Method | Path | 설명 |
|--------|------|------|
| GET | `/sentences/` | 전체 문장 팩 목록 |
| GET | `/sentences/random` | 랜덤 문장 팩 10개 |
| GET | `/sentences/search?keyword=&level=&author=` | 문장 팩 검색 |
| GET | `/sentences/<id>` | 문장 팩 상세 + 리더보드 `🔒` |
| GET | `/sentences/<id>/game` | 게임용 문장 팩 데이터 |
| POST | `/sentences/<id>/set-score` | 점수 등록/갱신 `🔒` |
| POST | `/sentences/<id>/interact-like` | 좋아요 토글 `🔒` |

**레벨 옵션:** `A`(상) / `B`(중상) / `C`(중) / `D`(중하) / `E`(하)

### 실시간 매칭

| Method | Path | 설명 |
|--------|------|------|
| POST | `/realtime/match/player` | 랜덤 매칭 참가 `🔒` |
| POST | `/realtime/match/join` | 특정 방 입장 (room_id) `🔒` |
| GET | `/realtime/match/status?room_id=` | 매칭 상태 확인 `🔒` |
| POST | `/realtime/game/<room_id>/heartbeat` | 인게임 상태 동기화 `🔒` |
| POST | `/realtime/game/<room_id>/missed` | 단어 미스 처리 `🔒` |
| POST | `/realtime/game/<room_id>/leave` | 방 나가기 `🔒` |

`🔒` — `X-Login-Code` 헤더 필요

## 환경 변수

`.env` 파일을 프로젝트 루트에 생성:

```env
DEBUG=false

DB_NAME=danso
DB_USER=postgres
DB_PASSWORD=yourpassword
DB_HOST=db
DB_PORT=5432

GOOGLE_CLIENT_ID=your_google_client_id
GOOGLE_CLIENT_SECRET=your_google_client_secret
GOOGLE_REDIRECT_URI=https://your-domain.com/login/callback
```

## 실행

### Docker (권장)

```bash
# 환경 변수 파일 준비
cp .env.example .env
# .env 값 채우기

docker compose up -d
```

### 로컬 개발

```bash
# uv 설치 (https://docs.astral.sh/uv/)
uv sync

# DB 마이그레이션
uv run manage.py migrate

# 개발 서버
uv run manage.py runserver
```

## 배포 (Dokploy)

1. Dokploy에서 새 Application 생성
2. Git 저장소 연결
3. Build Type: **Dockerfile**
4. 환경 변수 설정 (위 목록 참고)
5. Port: `8000`
6. Deploy

`ALLOWED_HOSTS`에 도메인 추가가 필요하면 `danso/settings.py`를 수정하거나 환경 변수로 오버라이드한다.
