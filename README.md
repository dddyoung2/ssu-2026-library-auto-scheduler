# ssu-2026-library-auto-scheduler
도서관 교내 근로를 디지털틱하게 빠르고, 간편하게

> v3 (방향 전환): 기존 Streamlit/Supabase(BaaS)/OR-Tools/OpenAI 계획을 폐기하고, 검증된 프로토타입(FastAPI + SQLite)을 그대로 기반으로 삼는다. 범위도 **전체 시간표 생성 → 데스크 시간표 생성 → 엑셀 다운로드**까지로 축소한다.
> v3.1 (사실상 최종본): 다중 관리자 계정(`data/admins.csv`), 학생 개별 등록/수정, 생성 전 "전원 제출완료" 체크가 추가됨. DB는 **Supabase PostgreSQL을 순수 DB 호스팅으로 연결**하면 구현 종료(Auth/RLS 미사용). 배포는 **Render.com**(서비스명 `lissurary`, Singapore 리전) — Streamlit Community Cloud는 사용하지 않는다. ⚠️ 현재 `render.yaml`은 결제 없이 기능 검증부터 하려고 `plan: free`로 임시 설정되어 있음(실사용 전 `starter`로 되돌릴 것).
> v3.3 (v4.7): **학생 입력기간(시작~마감) 관리**와 **관리자의 학생별 시간표 열람/대리수정** 기능이 추가됨. 자세한 내용은 `docs/spec.md`, `docs/architecture.md` 참고.
> v3.4 (프로젝트 구조 재동기화): 프로젝트 구조 트리에서 누락됐던 `app/admin_auth.py`, `pytest.ini`, `run_windows.bat` 등을 추가하고, CI가 실제로 pytest를 실행하도록 고친 내용(PR #14)을 반영.

---

## 개요

- **프로젝트명:** Lissurary (구 Library Auto Scheduler)
- **참여 대회/목적:** 숭실대 AI 업무 혁신 챌린지 (2026)
- **핵심 기능 요약:** 도서관 근로장학생의 희망 스케줄(1~3순위)을 취합해, 스왑 휴리스틱 알고리즘으로 전체 근로표와 데스크 근로표를 자동 생성하고 엑셀로 내려받는 웹 애플리케이션

---

## 팀 (Contributors)

| 이름 | 역할 | GitHub |
|---|---|---|
| 송민호 | **팀장**, 프론트엔드 및 규칙 알고리즘 설계 | [![Github](https://img.shields.io/badge/minhosong-181717?style=flat&logo=github&logoColor=white)](https://github.com/minhosong-mse) |
| 김도영 | DB 설계 및 AI 엔지니어링 | [![Github](https://img.shields.io/badge/dddyoung2-181717?style=flat&logo=github&logoColor=white)](https://github.com/dddyoung2) |

---

## 핵심 기능

| 기능명 | 설명 |
|---|---|
| 근로생 – 로그인 | 이름 + 학번으로 로그인 |
| 근로생 – 근로유형 선택 | A형(월 56~80h)/B형(월 28~40h) 선택·저장 |
| 근로생 – 희망 스케줄 입력 | 요일×시간 그리드에서 1~3순위/불가능/수업 입력(PC 드래그, 모바일 터치 드래그), 연속 4시간·1순위 하루 8시간 제한 검증, 임시저장/최종 제출. **관리자가 지정한 입력기간 내에서만 가능** |
| 관리자 – 학생 입력기간 관리 | 학생이 로그인·수정할 수 있는 시작~마감 시각 설정, 즉시 잠금, 설정 해제 |
| 관리자 – 명단 관리 | CSV 업로드(merge/sync 모드) · 개별 학생 등록/수정 · 40명 더미데이터 생성, 학생별 제출 상태·근로유형 조회/수정 |
| 관리자 – 학생별 시간표 열람/대리수정 | 개별 학생 시간표 팝업 조회(언제나 가능), 입력기간이 잠긴 상태에서만 브러시 방식으로 직접 대리수정 가능(수정 이력은 감사 로그로 기록) |
| 관리자 – 전체 시간표 생성 | 활성 학생 전원 최종제출+유형지정 완료 확인 → 시간당 최소 인원 설정 → 1순위 전량 배정 후 부족분만 2·3순위와 스왑하는 휴리스틱으로 자동 생성 |
| 관리자 – 데스크 시간표 생성 | 전체 시간표 기준으로 A/B형 주간·일일 데스크 상한, 2인 허용 시간대를 반영해 자동 생성(2시간 블록 우선) |
| 관리자 – 결과 다운로드 | 전체시간표/데스크시간표/학생별요약/생성정보 4개 시트 엑셀 다운로드 |

**이번 버전에서 하지 않는 것** (follow-up, `docs/spec.md` 9번 참고): 근로표 확정/배포 워크플로우, 주간 추가·제외 요청, **학생이 사유를 적어 신청하는** 수정요청·이의제기(관리자가 여는 대리수정과는 다름), LLM 연동, 상태 대시보드, 공휴일 API 연동, 학기/방학별 영업시간 차등.

---

## 시스템 아키텍처

FastAPI(웹 서버) + Jinja2(서버사이드 템플릿) + SQLAlchemy(SQLite 로컬 / Postgres 운영) + openpyxl(엑셀 출력) 구조. 상세 계층 구조는 `docs/architecture.md` 참고.

---

## 기술 스택

**Web / Backend**
- FastAPI, Uvicorn, Starlette(SessionMiddleware)

**DB**
- SQLAlchemy — SQLite(로컬) / PostgreSQL(운영, Supabase — 순수 DB 호스팅, Auth/RLS 미사용)

**프론트**
- Jinja2 서버사이드 템플릿 + 바닐라 JS/CSS

**엑셀 출력**
- openpyxl

**배포**
- Render.com (서비스명 `lissurary`, Singapore 리전, `/health` 헬스체크). Streamlit Community Cloud는 사용하지 않음. ⚠️ 현재 `plan: free`로 임시 배포 중(실사용 전 `starter`로 전환 예정, 위 배너 참고)

---

## 프로젝트 구조
```
ssu-2026-library-auto-scheduler/
├── .github/                     # GitHub 설정 및 자동화
│   ├── pull_request_template.md # PR 템플릿
│   └── workflows/
│       └── ci.yml               # CI 워크플로우(의존성 설치 + pytest 실행)
├── app/                          # 애플리케이션 코드
│   ├── main.py                   # FastAPI 라우트/API
│   ├── config.py                 # 영업시간·상태코드·환경변수 등 상수
│   ├── database.py               # SQLAlchemy 모델 및 DB 접근
│   ├── admin_auth.py             # admins.csv 기반 다중 관리자 인증
│   ├── validators.py             # 스케줄 검증
│   ├── demo_scheduler.py         # 전체/데스크 시간표 생성 알고리즘
│   ├── exports.py                # 엑셀 워크북 생성
│   ├── templates/                # Jinja2 HTML 템플릿
│   └── static/                   # JS/CSS
├── data/                          # 로컬 시드 명단, SQLite DB, 산출물
├── docs/                          # 프로젝트 관련 문서 파일
│   ├── architecture.md          # 시스템 아키텍처 문서
│   ├── components.md            # 폴더/파일별 책임 및 의존 관계 문서
│   ├── spec.md                  # 기능 명세 문서
│   └── team-tasks.md            # 팀 역할 및 작업 분담 문서
├── supabase/
│   ├── config.toml               # Supabase CLI 로컬 설정
│   └── migrations/               # app/database.py 모델과 1:1 대응하는 선택적 DDL
├── tests/                        # 테스트 코드
├── .env.example                 # 환경변수 파일 양식
├── .gitignore                   # 깃허브 업로드 금지 명시 파일
├── AGENTS.md                    # AI-Agent(CODEX) 전용 규칙 문서
├── CHANGELOG.md                 # 변경 이력
├── CLAUDE.md                    # AI-Agent(Claude Code) 전용 규칙 문서
├── CONTRIBUTING.md              # 규칙 규정 파일
├── LISSURARY_배포가이드.md       # Render+Supabase 배포 절차 가이드
├── 관리자계정_수정방법.txt        # 운영 관리자 계정(admins.csv) 수정 방법 안내
├── pytest.ini                   # pytest 설정(testpaths=tests)
├── render.yaml                  # Render.com 배포 설정
├── requirements.txt             # 런타임 의존성 파일
├── requirements-dev.txt         # 테스트/개발 의존성 파일
├── run_windows.bat              # Windows 로컬 실행 스크립트
└── README.md                    # 프로젝트 개요
```
---

## 설치 방법 (Installation)

### 저장소 클론

``` bash
git clone https://github.com/dddyoung2/ssu-2026-library-auto-scheduler.git

cd {repo}
```
### 가상 환경(venv)
#### Install
``` bash
py -3.10 -m venv .venv
```

#### Execute
``` bash
.venv\Scripts\activate
```

#### DeExecute
``` bash
deactivate
```

### 의존성 설치

```bash
# 가상 환경(venv)를 활성화 한 후 실행할 것.
pip install -r requirements.txt
```

---

## 실행 방법 (Usage)

```bash
uvicorn app.main:app --reload
```
브라우저: `http://127.0.0.1:8000`

**관리자 계정**은 CSV 파일로 관리합니다(개수 제한 없음, 로그인마다 파일을 다시 읽으므로 서버 재시작 불필요). 파일 위치는 다음 순서로 결정됩니다: ①환경변수 `ADMINS_CSV_PATH` ②Render Secret File(`/etc/secrets/admins.csv`, 파일이 존재하면 자동 사용) ③로컬 `data/admins.csv`.

```csv
user_id,password,active
admin01,Admin1234!,1
admin02,Admin2345!,1
```
- `active`가 `1`이면 로그인 가능, `0`이면 비활성(이미 로그인 중이어도 다음 요청에서 즉시 세션 해제)
- ⚠️ 비밀번호가 평문으로 들어 있으므로 `data/admins.csv`는 공개 저장소에 절대 커밋하지 않습니다(`.gitignore` 대상). **운영(Render) 배포에서는 로컬 CSV 대신 Render Secret File로 관리**합니다 — Render 서비스 → `Environment` → `Secret Files`에 파일명 `admins.csv`로 등록
- CSV가 없거나 활성 계정이 하나도 없을 때만 아래 환경변수(`ADMIN_ID`/`ADMIN_PASSWORD`, `ADMIN2_ID`/`ADMIN2_PASSWORD`)를 fallback으로 사용합니다 — 단, 기본값이 없으므로 값을 직접 설정하지 않으면 로그인 가능한 관리자가 아예 없는 상태가 됩니다

---

## 환경 변수 설정

`.env.example` 파일을 참고하여 `.env` 파일을 생성하세요.

```env
# 비워 두면 SQLite(data/app.db)를 사용합니다.
# 운영에서는 Supabase 프로젝트의 Session pooler 연결 문자열(포트 5432)을 권장합니다.
# 예: postgres://postgres.PROJECT_REF:DB_PASSWORD@aws-REGION.pooler.supabase.com:5432/postgres
DATABASE_URL=
SESSION_SECRET=change-this-to-a-long-random-string
COOKIE_SECURE=false

# 관리자 계정은 기본적으로 admins.csv(로컬 data/admins.csv 또는 Render Secret File)를 사용합니다.
# 아래 값은 그 CSV를 사용할 수 없을 때만 fallback으로 쓰이며, 기본값이 없으므로 운영에서는 보통 비워둡니다.
ADMIN_ID=
ADMIN_PASSWORD=
ADMIN2_ID=
ADMIN2_PASSWORD=
```

### Supabase + Render 배포 요약 (운영)
1. Supabase에서 새 프로젝트 생성 → `Connect` → **Session pooler** 연결 문자열 복사
2. Render → `New` → `Blueprint` → 저장소의 `render.yaml` 선택 → `DATABASE_URL`에 Supabase 연결 문자열 입력 → 배포(앱 기동 시 테이블 자동 생성)
3. Render 서비스 → `Environment` → `Secret Files` → 파일명 `admins.csv`로 관리자 계정 등록
4. 배포 후 `/health` 확인 → 관리자 로그인 → 학생 등록(개별 또는 CSV) → 학생 로그인/제출 테스트 → 더미 40명으로 자동배정 테스트
5. Supabase Free 플랜은 장기간 미사용 시 프로젝트가 일시 정지될 수 있으므로, 상시 접속이 필요하면 유료 플랜 고려

---

## 성능 / 벤치마크

*(계획서의 "정량적 목표" 대신, 실제 측정된 결과 수치로 대체)*

| 지표 | 결과 |
|---|---|
| 관리자 수기 작성 소요 시간 | None |
| 프로그램 자동 생성 소요 시간 | None |
| 정확도 | None |
| 완전도 | None |
| 응답 속도 | None |
