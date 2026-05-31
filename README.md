# 🛒 최저가 알림 서비스 (Price Alert Service)

> 관심 상품의 **목표가**를 등록해두면, 백엔드가 **주기적으로 최저가를 감시**하다가
> 조건이 충족되면 **AI 코멘트와 함께 알림**을 보내주는 서비스.

게시판 같은 단순 CRUD가 아니라, **백엔드가 스스로 도는 "엔진형" 프로젝트**입니다.
스케줄러 · 외부 API 연동 · 조건 평가 · 멱등성(중복 알림 방지)이 핵심이에요.

---

## ✨ 주요 기능

- 🔐 **회원가입 / 로그인** (JWT 인증)
- 👀 **감시(Watch) 등록·수정·삭제** — "에어팟 프로, 27만원 이하면 알림"
- ⏰ **자동 모니터링** — 스케줄러가 N분마다 최저가를 확인
- 🔔 **조건 충족 시 알림** — AI가 만든 한 줄 코멘트 포함
- 🧯 **중복 알림 방지** — 쿨다운(멱등성)으로 스팸 방지
- 📜 **알림 이력 조회**
- 🖥️ **웹 화면 제공** — 브라우저에서 바로 등록·확인 (별도 빌드 없는 가벼운 UI)

---

## 🧰 기술 스택

| 영역 | 사용 기술 |
|------|-----------|
| 언어/프레임워크 | Python 3.12, **FastAPI** |
| DB / ORM | SQLite(기본) · PostgreSQL, **SQLAlchemy 2.0**, **Alembic** |
| 검증 | **Pydantic v2** (+ pydantic-settings) |
| 인증 | **JWT** (PyJWT), passlib(pbkdf2_sha256) |
| 스케줄러 | **APScheduler** |
| 외부 연동 | **네이버 쇼핑 검색 API**, **OpenAI**, 디스코드 웹훅 |
| 프론트엔드 | 바닐라 **HTML/CSS/JS** (FastAPI가 정적 서빙, 빌드 불필요) |
| 테스트 | **pytest** |
| 배포 | Docker, AWS/Render/Railway (uvicorn) |

> 💡 **핵심 설계 원칙**: 외부 키(네이버/OpenAI/디스코드)가 없으면 자동으로 **mock 모드**로 동작합니다.
> 그래서 키 없이도 `clone → 설치 → 실행`만으로 전체 흐름이 돌아가고, 테스트도 외부 의존 없이 통과합니다.

---

## 🏗️ 아키텍처

```
 사용자 ──(감시 조건 등록)──► FastAPI ──► DB(watches)
                                 │
   ┌─────────────────────────────┘
   ▼
 APScheduler (N분마다)            ← 백엔드가 "스스로" 도는 엔진
   ▼
 모니터링 엔진(monitor)
   ├─ 가격 조회   ── PriceSource ─┬─ NaverShoppingSource (키 있을 때)
   │                              └─ MockPriceSource     (키 없을 때)
   ├─ 조건 평가 (lte/gte)
   ├─ 쿨다운 검사 (멱등성)        ← 중복 알림 방지
   ├─ AI 코멘트   ── OpenAI / 템플릿 폴백
   └─ 알림 발송   ── 디스코드 / 콘솔   →  DB(alerts)
```

**어댑터 패턴**: 엔진은 `PriceSource` 인터페이스에만 의존하고, 실제 구현(네이버/mock)은
`get_price_source()`가 결정합니다. 덕분에 나중에 **데이터 소스만 갈아끼우면** 쇼핑→채용공고→코인으로 확장됩니다.

---

## 🚀 빠른 시작 (Windows PowerShell)

```powershell
# 1) 가상환경 + 의존성
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt

# 2) (선택) 환경변수 — 안 해도 mock 모드로 동작
Copy-Item .env.example .env

# 3) 실행
uvicorn app.main:app --reload
```

브라우저에서 열어보세요:
- **http://127.0.0.1:8000/** → 🖥️ 웹 화면 (감시 등록·알림 확인 UI)
- **http://127.0.0.1:8000/docs** → Swagger UI (API 문서·테스트)

> macOS/Linux는 `source .venv/bin/activate` 만 다르고 나머지는 동일합니다.

---

## 🔌 API 한눈에 보기

| 메서드 | 경로 | 설명 | 인증 |
|--------|------|------|:---:|
| POST | `/auth/register` | 회원가입 | |
| POST | `/auth/login` | 로그인 → JWT 발급 | |
| POST | `/watches` | 감시 등록 | ✅ |
| GET | `/watches` | 내 감시 목록 | ✅ |
| GET | `/watches/{id}` | 감시 상세 | ✅ |
| PATCH | `/watches/{id}` | 감시 수정 | ✅ |
| DELETE | `/watches/{id}` | 감시 삭제 | ✅ |
| POST | `/watches/{id}/check` | **지금 즉시 점검**(데모용) | ✅ |
| GET | `/alerts` | 알림 이력 | ✅ |
| GET | `/health` | 현재 동작 모드 확인 | |

---

## 🎬 키 없이 바로 데모 (mock 모드)

스케줄러를 기다릴 필요 없이 `/watches/{id}/check`로 즉시 점검할 수 있어요.
**목표가를 아주 높게** 잡으면 mock 가격이 항상 그 이하라 알림이 바로 터집니다.

```powershell
# 1) 회원가입 & 로그인
$body = @{ email='me@test.com'; password='secret123' } | ConvertTo-Json
Invoke-RestMethod -Method Post http://127.0.0.1:8000/auth/register -ContentType 'application/json' -Body $body
$tok = (Invoke-RestMethod -Method Post http://127.0.0.1:8000/auth/login `
        -ContentType 'application/x-www-form-urlencoded' `
        -Body @{username='me@test.com';password='secret123'}).access_token
$H = @{ Authorization = "Bearer $tok" }

# 2) 감시 등록 (목표가를 크게)
$w = Invoke-RestMethod -Method Post http://127.0.0.1:8000/watches -Headers $H `
     -ContentType 'application/json' -Body (@{query='에어팟 프로';target_price=99999999}|ConvertTo-Json)

# 3) 즉시 점검 → 알림 생성 확인
Invoke-RestMethod -Method Post "http://127.0.0.1:8000/watches/$($w.id)/check" -Headers $H

# 4) 알림 이력
Invoke-RestMethod http://127.0.0.1:8000/alerts -Headers $H
```

---

## 🔑 실제 키 연결하기

`.env` 파일에 채워 넣으면 자동으로 실제 모드로 전환됩니다.

| 키 | 발급처 | 없으면 |
|----|--------|--------|
| `NAVER_CLIENT_ID/SECRET` | [네이버 개발자센터](https://developers.naver.com) → 검색>쇼핑 | mock 가격 사용 |
| `OPENAI_API_KEY` | OpenAI | 템플릿 코멘트 사용 |
| `DISCORD_WEBHOOK_URL` | 디스코드 채널 설정 → 연동 → 웹훅 | 콘솔 출력 |

---

## 🧪 테스트

```powershell
pytest -q
```

- `test_auth.py` — 회원가입/로그인/중복/인증 가드
- `test_watches.py` — 감시 CRUD + **소유권 격리**(남의 감시 접근 차단)
- `test_monitor.py` — **엔진 단위 테스트**: 조건 충족 시 알림 생성 / 미충족 시 무알림 / **쿨다운으로 중복 방지**
  (가짜 가격 소스와 시각을 주입해 외부 의존 없이 빠르게 검증)

---

## 🗄️ 데이터베이스 / 마이그레이션

개발 편의를 위해 기본값(`AUTO_CREATE_TABLES=true`)에서는 앱 시작 시 테이블을 자동 생성합니다.
**스키마를 코드로 관리**하려면 Alembic을 쓰세요.

```powershell
# 새 마이그레이션 자동 생성
alembic revision --autogenerate -m "메시지"
# 적용
alembic upgrade head
```

> PostgreSQL로 바꾸려면 `.env`의 `DATABASE_URL`만 교체하면 됩니다.
> 예: `postgresql+psycopg://user:pass@localhost:5432/pricewatch`

---

## 📁 프로젝트 구조

```
price-alert-bot/
├─ app/
│  ├─ main.py            # FastAPI 진입점 (lifespan: 테이블 생성 + 스케줄러 시작)
│  ├─ config.py          # 설정 (pydantic-settings)
│  ├─ database.py        # 엔진/세션/Base
│  ├─ models.py          # ORM 모델 (User, Watch, Alert)
│  ├─ schemas.py         # Pydantic 입출력 스키마
│  ├─ security.py        # 비밀번호 해싱 + JWT
│  ├─ deps.py            # 현재 사용자 의존성
│  ├─ scheduler.py       # APScheduler
│  ├─ routers/           # auth / watches / alerts
│  └─ services/
│     ├─ price_source.py # 네이버/Mock 가격 어댑터
│     ├─ ai.py           # OpenAI 코멘트 (+ 템플릿 폴백)
│     ├─ notifier.py     # 디스코드/콘솔 알림
│     └─ monitor.py      # ⭐ 모니터링 엔진 (조건 평가 + 멱등성)
├─ static/              # 웹 UI (index.html · app.js · styles.css)
├─ tests/                # pytest
├─ alembic/              # 마이그레이션
├─ requirements.txt
└─ .env.example
```

---

## 💼 백엔드 관점 포인트 (면접 어필)

이 프로젝트로 설명할 수 있는 것들:

- **스케줄러 기반 백그라운드 처리** — 요청-응답을 넘어, 시스템이 스스로 주기적으로 일함
- **멱등성 / 쿨다운** — 같은 조건으로 알림이 도배되지 않도록 상태(`last_notified_at`)로 제어
- **외부 API 연동의 견고성** — 네이버/OpenAI 호출 실패가 엔진 전체를 멈추지 않게 격리(폴백/로깅)
- **어댑터 패턴 + 의존성 주입** — 엔진이 인터페이스에만 의존 → 테스트 쉽고 소스 교체 자유
- **소유권 기반 권한** — 사용자는 자기 데이터만 접근(404 격리)
- **테스트 용이성** — 가격 소스/시각을 주입해 외부 없이 핵심 로직 검증

---

## 🔭 향후 확장 아이디어

- 데이터 소스 교체/추가 → **채용공고·코인·환율** 알림
- 알림 채널 추가 → 이메일/슬랙/텔레그램
- 가격 **추이 그래프** (시계열 저장 + 차트)
- 검색어가 아닌 **특정 상품 고정 추적**(productId)
- Self/Corrective 방식의 더 똑똑한 추천 코멘트
