# Components

> 프로젝트의 폴더 구조, 파일별 책임, 의존(import) 관계를 정리한 문서.
> 코드가 추가/변경될 때마다 이 문서도 함께 갱신할 것 (CONTRIBUTING.md 문서 규칙 참고).

> ⚠️ v3 (방향 전환): 기존 `src/{core,db,pages,utils}` 스캐폴딩(Streamlit 대상)을 폐기하고, 검증된 프로토타입(FastAPI)의 `app/` 구조를 그대로 이식했다.
> ⚠️ v3.1 (`v4_6_final` 반영): `app/admin_auth.py`, `data/admins.csv` 추가(다중 관리자 계정). DB는 Supabase PostgreSQL(순수 호스팅)로 연결.
> ⚠️ v3.3 (v4.7 반영): 새 파일은 없음. `app/database.py`/`app/main.py`/`app/static/admin.js`/`app/templates/admin.html`에 학생 입력기간 관리·관리자 대리수정 로직이 추가됨(2번 표 참고).
> ⚠️ v3.4 (프로젝트 구조 재동기화): 루트에 이미 존재하던 `pytest.ini`/`run_windows.bat`/배포 가이드 문서 2종이 2번 표에서 누락되어 있던 것을 발견해 추가.

---

## 1. 폴더별 역할

| 폴더 | 역할 |
|---|---|
| `app/` | 애플리케이션 코드 전체. Streamlit 시절의 `src/pages`+`src/core`+`src/db`+`src/utils` 4분할 대신, 얇은 라우팅 계층(`main.py`) + 순수 로직 모듈(`database.py`/`demo_scheduler.py`/`validators.py`/`exports.py`/`config.py`) 구조를 쓴다. |
| `app/templates/` | Jinja2 HTML 템플릿 (로그인/학생/관리자/에러 화면). |
| `app/static/` | 바닐라 JS(그리드 드래그 입력, 관리자 화면 로직) + CSS. |
| `data/` | `users.csv`(로컬 시드 명단), `app.db`(SQLite, `.gitignore`), 엑셀 산출물 등. |
| `docs/` | 프로젝트 문서 (`spec.md`: 기능 명세, `architecture.md`: 아키텍처, `components.md`: 본 문서, `team-tasks.md`: 팀 역할/작업 분담). |
| `tests/` | 자동화 테스트. PR 전 `python -m pytest`로 실행. |
| `.github/` | GitHub 저장소 설정 (`pull_request_template.md`, `workflows/ci.yml`). |

---

## 2. 파일별 책임

| 파일 | 책임 |
|---|---|
| `app/main.py` | FastAPI 앱 생성, 세션 미들웨어, 로그인/로그아웃, 학생/관리자 페이지 라우트, REST API 엔드포인트(학생 CRUD, 스케줄 저장/조회, 명단 업로드, **학생 입력기간 CRUD**, **관리자 학생별 시간표 조회/대리수정**, 시간표 생성, 엑셀 다운로드), 예외 핸들러 |
| `app/config.py` | 앱 제목, 요일/영업시간 상수, 스케줄 상태코드 및 메타(색상/라벨), 근로유형별 월/주 한도, DB URL 정규화, 세션/관리자 계정 환경변수(fallback), `ADMINS_CSV` 경로 |
| `app/database.py` | SQLAlchemy 모델(`Student`/`Schedule`/`ScheduleRevision`/`SystemSetting`/`ScheduleAudit`/`ScheduleRun`), 엔진/세션 설정, CSV 동기화(`sync_students*`, merge/sync 모드), 학생 개별 등록/수정(`create_student`/`update_student`), 학생 인증, 스케줄 CRUD(+ 감사 기록), **학생 입력기간 조회/설정/잠금/해제**(`student_access_status`/`set_student_access_window`/`lock_student_access`/`clear_student_access_window`), 생성 readiness 체크(`schedule_generation_readiness`), 더미데이터 생성, 시간표 run 저장/조회/무효화 |
| `app/admin_auth.py` | `data/admins.csv` 로딩(로그인마다 재읽기) + 환경변수 fallback, 관리자 인증·활성여부 확인 |
| `app/validators.py` | 스케줄 정규화·기본값 생성, 연속 4시간 검증, 근로유형별 1순위 시간 경고 계산 |
| `app/demo_scheduler.py` | 전체 시간표 생성(스왑 휴리스틱), 데스크 시간표 생성(2시간 블록 우선 배정 + 다중 시드 중 최적 선택) |
| `app/exports.py` | `openpyxl` 워크북 생성 — 전체시간표/데스크시간표/학생별요약/생성정보 4개 시트 |
| `app/templates/*.html` | 로그인(입력기간 잠금 안내 포함), 학생 스케줄 입력, 관리자 대시보드(**입력기간 설정 카드**, **학생별 시간표 팝업/대리수정 모달**), 에러 페이지 |
| `app/static/schedule.js` | 학생 화면 요일×시간 그리드 드래그/터치 입력, 저장/제출 API 호출, 401/423 응답 시 로그인 화면으로 자동 리다이렉트 |
| `app/static/admin.js` | 관리자 화면 명단 업로드/개별 등록, **입력기간 설정/잠금/해제 UI**, **학생별 시간표 팝업 조회 및 브러시 방식 대리수정**, 시간표 생성 트리거, 결과 렌더링 |
| `data/users.csv`, `data/users_template_*.csv` | 로컬 개발용 명단 시드 / 업로드 양식 예시 |
| `data/admins.csv` | 관리자 계정 목록(`user_id,password,active`). 비밀번호 평문 포함 — `.gitignore` 대상, 절대 커밋 금지 |
| `tests/test_app.py` | FastAPI 엔드포인트 통합 테스트 (입력기간 잠금/해제, 관리자 대리수정 권한, 화면 요소 노출 포함) |
| `requirements.txt` | 런타임 의존성 (`fastapi`, `sqlalchemy`, `openpyxl` 등) |
| `requirements-dev.txt` | 테스트/개발 의존성(`requirements.txt` 상속 + `pytest`) |
| `pytest.ini` | pytest 설정. `testpaths = tests`로 `scripts/`의 구버전 테스트 스크립트가 함께 수집되지 않도록 제한 |
| `run_windows.bat` | Windows에서 가상환경 활성화 + 서버 실행을 한 번에 하는 로컬 실행 스크립트 |
| `render.yaml` | Render.com 배포 설정 |
| `.env.example` | 필요한 환경 변수 양식 (`DATABASE_URL`, `SESSION_SECRET`, `ADMIN_ID`, `ADMIN_PASSWORD`, `COOKIE_SECURE`) |
| `supabase/config.toml` | Supabase CLI 로컬 개발 설정(선택 사용) |
| `supabase/migrations/*.sql` | `app/database.py` 모델과 1:1 대응하는 선택적 DDL(배포 전 Supabase Studio에서 미리 검토·생성하고 싶을 때만 사용) |
| `LISSURARY_배포가이드.md` | Render+Supabase 실제 배포 절차를 단계별로 정리한 운영 가이드 |
| `관리자계정_수정방법.txt` | 운영(Render) 환경에서 관리자 계정(`admins.csv`, Secret File)을 수정하는 방법 안내 |
| `README.md` | 프로젝트 개요, 기능 요약, 기술 스택, 설치/실행 방법 |
| `CONTRIBUTING.md` | 브랜치/커밋/PR 규칙 |
| `AGENTS.md` / `CLAUDE.md` | AI 에이전트(Codex / Claude Code) 작업 규칙 |
| `CHANGELOG.md` | 버전별 변경 이력 |

---

## 3. import 관계

```
app/main.py
    │  imports
    ▼
app/database.py, app/admin_auth.py, app/demo_scheduler.py, app/validators.py, app/exports.py
    │  imports
    ▼
app/config.py
```

- **허용:** `main → database/admin_auth/demo_scheduler/validators/exports`, `exports → demo_scheduler`(그리드 렌더링에 `active_hours` 재사용), 모든 모듈 `→ config`
- **금지(역방향 import 금지):** `database/admin_auth/demo_scheduler/validators/exports/config`가 `main`을 알아서는 안 됨. `config`는 다른 어떤 모듈도 import하지 않음(최하위 계층)
- `admin_auth.py`/`demo_scheduler.py`/`validators.py`/`exports.py`는 서로 직접 의존하지 않는 순수 함수 모듈이며, `database.py`도 이들을 직접 호출하지 않는다 — 조합은 항상 `main.py`(라우트 핸들러)에서 이루어진다
- `tests/`는 계층 구분 없이 `app/` 전체를 import할 수 있다

---

## 4. 수정 시 함께 확인해야 하는 파일

| 수정 대상 | 함께 확인할 파일 |
|---|---|
| `app/` 최상위 구조 변경 | `README.md`(프로젝트 구조), 본 문서(`docs/components.md`) |
| `app/demo_scheduler.py` (배정 알고리즘) | `docs/spec.md` 6번(알고리즘 명세), `tests/`, `app/exports.py`(출력 포맷 영향 여부) |
| `app/database.py` (모델/DB 접근) | `.env.example`(필요 환경 변수), `requirements.txt`(DB 드라이버), `docs/architecture.md` |
| `app/config.py` (영업시간/상태코드/한도) | `app/validators.py`, `app/exports.py`, `app/templates/*.html`, `app/static/*.js` — 하드코딩된 값이 남아있지 않은지 확인 |
| `app/templates/*`, `app/static/*` | `app/main.py`(전달하는 context 변수 일치 여부), README 실행 방법 |
| `requirements.txt` | `.github/workflows/ci.yml`, `render.yaml`, README 설치 방법 |
| `.env.example` | `app/config.py`(실제 사용하는 환경 변수명과 일치하는지), 보안 규칙(실값 커밋 금지) |
| `docs/spec.md` | `docs/components.md`, README 핵심 기능 표 — 기능 추가/변경 시 3곳 동기화 |
| `docs/team-tasks.md` | `AGENTS.md`/`CLAUDE.md`의 역할 번호 매핑 — 역할 변경 시 함께 갱신 |
