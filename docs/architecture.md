# Lissurary (구 Library Auto Scheduler) — Architecture

> ⚠️ v3 (방향 전환): 기존 Streamlit + Supabase(BaaS) + OR-Tools + OpenAI 아키텍처를 폐기하고, 검증된 프로토타입(FastAPI)의 아키텍처를 그대로 채택한다. 관련 문서: `docs/spec.md`(기능 명세), `docs/components.md`(폴더/파일별 책임).
> ⚠️ v3.1 (`v4_6_final` 반영, 사실상 최종본): DB를 **Supabase PostgreSQL(순수 DB 호스팅)**로 연결하면 구현이 끝나는 단계. Supabase Auth/RLS 등 BaaS 기능은 쓰지 않는다. 그 외 다중 관리자 계정(`app/admin_auth.py` 신설), 학생 개별 등록/수정, 생성 전 readiness 체크가 추가됐다.
> ⚠️ v3.2 (`lissurary_deploy` 반영): 프로젝트/Render 서비스명이 **`lissurary`**로 확정. 배포는 **Render.com + Supabase**이며 **Streamlit Community Cloud는 사용하지 않는다**(이전에 구두로 언급됐던 "Streamlit 연결"은 이 zip 기준으로 정정됨). `admins.csv` 경로 해석 순서와 Render Secret File 운용 방식이 추가됨(4번 참고).
> ⚠️ v3.3 (v4.7 반영): 학생 입력기간(시작~마감, `system_settings` 테이블) 하드 게이트와 관리자 대리수정(`schedule_audits` 테이블) 기능 추가. 새 모듈은 없고 기존 `app/database.py`/`app/main.py`에 로직이 추가됨(5·7·8번 참고).
> ⚠️ v3.4 (프로젝트 구조 재동기화): 8번 설계 결정 표에 남아있던 "Starter 플랜 선택" 서술이 실제 `render.yaml`(`plan: free`, 임시)과 모순되던 것을 발견해 수정. CI(`ci.yml`)가 실제로 pytest를 실행하도록 고친 내용(PR #14) 반영.

---

## 1. 개요
전체 시간표(희망 스케줄 취합 → 스왑 휴리스틱 자동 배정) → 데스크 시간표(전체 시간표 기준 자동 배정) → 엑셀 다운로드까지를 제공하는 FastAPI 웹 애플리케이션. 별도 프론트엔드 프레임워크 없이 서버사이드 Jinja2 템플릿 + 바닐라 JS로 구성된다.

---

## 2. 기술 스택

| 영역 | 기술 |
|---|---|
| Web 프레임워크 | FastAPI (+ Uvicorn) |
| 템플릿/프론트 | Jinja2 서버사이드 렌더링 + 바닐라 JS(`static/admin.js`, `static/schedule.js`) + CSS |
| ORM / DB 접근 | SQLAlchemy 2.x |
| DB (로컬) | SQLite (`data/app.db`) |
| DB (운영) | **PostgreSQL — Supabase**(`psycopg` 드라이버). Supabase는 순수 DB 호스팅으로만 사용, Auth/RLS/Storage 등 BaaS 기능은 쓰지 않음 |
| 인증 | `starlette` `SessionMiddleware` 기반 세션 쿠키. 관리자는 `data/admins.csv` 기반 다중 계정(환경변수는 fallback), 학생은 이름+학번 매칭 |
| 엑셀 출력 | `openpyxl` |
| 배포 | Render.com (`render.yaml`, 서비스명 `lissurary`, Singapore 리전, `/health` 헬스체크) — 웹 서버만 Render, DB는 Supabase. ⚠️ 현재 `plan: free`로 임시 배포 중(3번 참고, 실사용 전 `starter`로 전환 예정) |

**폐기된 스택** (v2 spec에서 목표했던 것): Streamlit, Supabase Auth+RLS(BaaS로서의 Supabase), Google OR-Tools, OpenAI API, 공공데이터포털 공휴일 API. 전부 follow-up으로 이동(`docs/spec.md` 9번 참고). **Supabase 자체는 v3.1에서 순수 Postgres 호스팅으로 부활** — BaaS 기능만 폐기 상태 유지.

---

## 3. 배포 토폴로지

**로컬 개발 환경**
- `py -3.10 -m venv .venv` → `pip install -r requirements.txt` → `uvicorn app.main:app --reload`
- `DATABASE_URL`을 비워두면 자동으로 `sqlite:///data/app.db` 사용

**운영(프로덕션) 환경**
- Render.com Web Service(`render.yaml`에 정의, `New → Blueprint`로 저장소 연결): `pip install -r requirements.txt` → `uvicorn app.main:app --host 0.0.0.0 --port $PORT`. 서비스명 `lissurary`, Singapore 리전
- ⚠️ **현재 `render.yaml`은 테스트 단계라 `plan: free`로 임시 설정**(결제 없이 배포·기능 검증용). 유휴 시 자동으로 서버가 꺼졌다가 다음 요청에서 자동으로 다시 켜짐(수동 재시작 불필요, 첫 요청만 콜드 스타트로 수십 초 지연) — DB(Supabase)는 별도라 데이터 유실 없음. 실사용(40명 상시 접속) 전에는 반드시 `plan: starter`로 되돌릴 것(8번 "중요한 설계 결정" 참고)
- DB는 **Supabase 프로젝트의 PostgreSQL**(`DATABASE_URL`에 Supabase 연결 문자열을 수동 설정, `postgres://`/`postgresql://` prefix는 앱 기동 시 `postgresql+psycopg://`로 자동 변환). **Session pooler 연결 문자열(포트 5432)을 권장** — Render 등 서버리스가 아닌 상시 서비스에서 접속 안정성이 높음. Render 자체 Postgres 애드온은 쓰지 않음
- 운영 DB는 초기에 비어 있음(자동 시드 없음) — 최초 배포 후 관리자가 로그인해 학생을 등록해야 함
- 관리자 계정은 **Render Secret File**로 관리: `Environment → Secret Files`에 파일명 `admins.csv` 등록 → 앱에서 `/etc/secrets/admins.csv`로 접근(4번 참고). 로컬 `data/admins.csv`는 개발/테스트용으로만 사용
- Supabase Free 플랜은 장기간 미사용 시 프로젝트가 일시정지될 수 있음 — 상시 접속이 필요하면 유료 플랜 검토

```
[로컬]  uvicorn --reload ── SQLite(data/app.db)
[운영]  Render Web Service(lissurary) ── Supabase PostgreSQL(Session pooler, DATABASE_URL 수동 설정)
              └─ admins.csv ← Render Secret File
```

---

## 4. 비밀값 / 환경 변수 관리

| 변수 | 용도 | 로컬 기본값 |
|---|---|---|
| `DATABASE_URL` | DB 접속 문자열. 비우면 SQLite, 운영은 Supabase Session pooler 연결 문자열 설정 | (비움 → SQLite) |
| `SESSION_SECRET` | 세션 쿠키 서명 키 | 데모용 고정값(운영에서는 반드시 교체, Render는 `generateValue: true`로 자동 생성) |
| `ADMINS_CSV_PATH` | 관리자 CSV 파일 경로를 명시적으로 지정(선택) | (비움) |
| `ADMIN_ID`/`ADMIN_PASSWORD`, `ADMIN2_ID`/`ADMIN2_PASSWORD` | 관리자 로그인 **fallback** 계정(admins.csv를 쓸 수 없을 때만 사용) | 기본값 없음(빈 문자열) — 설정하지 않으면 fallback 로그인 자체가 불가능 |
| `COOKIE_SECURE` | HTTPS 전용 쿠키 여부 | `false`(로컬) / `true`(운영) |

- 실값 파일 `.env`는 `.gitignore` 처리, `.env.example`만 커밋
- **관리자 CSV 파일 경로는 우선순위대로 해석**: ①`ADMINS_CSV_PATH` 환경변수 ②`/etc/secrets/admins.csv`(존재하면 자동 사용 — Render Secret File 경로) ③로컬 `data/admins.csv`. 파일 형식은 `user_id,password,active` 열, 개수 제한 없음. 로그인마다 파일을 다시 읽으므로 서버 재시작 없이 계정 추가/변경/비활성화가 즉시 반영됨. 평문 비밀번호를 담고 있어 `.gitignore` 대상이며 공개 저장소에 절대 커밋하지 않는다(9번/10번 참고). **운영(Render)에서는 로컬 CSV 대신 Secret File을 사용**하는 것이 원칙
- 환경변수 fallback 계정은 기본값이 없으므로, admins.csv를 못 쓰는 상황에 대비해 운영에서 값을 채워둘지 여부를 판단해 결정할 것

---

## 5. 계층 구조 (모듈 의존 방향)

```
app/main.py        (FastAPI 라우트: 로그인, 학생/관리자 페이지, API 엔드포인트)
    │  imports
    ▼
app/database.py    (SQLAlchemy 모델 + DB 접근 함수)
app/admin_auth.py  (admins.csv 기반 다중 관리자 계정 로딩/인증, 순수 함수)
app/demo_scheduler.py  (전체/데스크 시간표 생성 알고리즘, 순수 함수)
app/validators.py  (스케줄 검증/정규화, 순수 함수)
app/exports.py     (엑셀 워크북 생성, 순수 함수)
    │  imports
    ▼
app/config.py      (상수: 영업시간, 상태코드, 근로유형 한도, 경로, 환경변수)
```

- `main.py`가 유일하게 HTTP 계층을 알고, 나머지 모듈은 FastAPI/Request에 의존하지 않는 순수 로직 + DB 접근으로 분리되어 있다.
- `demo_scheduler.py`/`validators.py`/`exports.py`/`admin_auth.py`는 상태를 갖지 않는 함수 모음이며 서로 직접 의존하지 않는다(단, `exports.py`는 `demo_scheduler.active_hours`를 시간표 그리드 렌더링에 재사용).
- `templates/`(Jinja2 HTML) + `static/`(JS/CSS)는 `main.py`가 마운트/렌더링한다.

---

## 6. 전체 알고리즘 절차

1. 관리자가 명단 CSV 업로드 또는 더미데이터 생성으로 대상자 확보, (선택) 학생 입력기간 설정
2. 근로생이 입력기간 내에 이름+학번으로 로그인 → 근로유형(A/B) 선택 → 요일×시간 그리드에서 1~3순위/불가능/수업 입력 → 임시저장 또는 최종 제출. 입력기간이 닫혀 있으면 이 단계 전체가 423으로 차단됨
3. (선택) 입력기간을 잠근 뒤, 관리자가 미제출·오류가 있는 개별 학생의 시간표를 직접 열람하고 대리수정 — 입력기간이 열려 있는 동안엔 학생 본인 입력과 충돌하지 않도록 대리수정이 409로 차단됨(`docs/spec.md` 5.4)
4. 관리자가 시간당 최소 인원을 지정해 **전체 시간표** 생성 — 스왑 휴리스틱(상세는 `docs/spec.md` 6.1)
5. 관리자가 A/B형 주간·일일 데스크 상한, 2인 허용 시간대를 지정해 **데스크 시간표** 생성 — 직전 전체 시간표를 반드시 입력으로 사용(상세는 `docs/spec.md` 6.2)
6. 관리자가 결과를 엑셀로 다운로드

각 생성 요청은 `schedule_runs`에 새 스냅샷으로 저장되며, 화면과 다운로드는 항상 최신 run을 기준으로 한다(과거 run은 DB에는 남지만 UI에서 직접 비교/조회하는 기능은 없음 — follow-up). 스케줄 저장은 주체(학생 본인/관리자)와 무관하게 매번 `schedule_revisions` + `schedule_audits`에 동시 기록되고, `schedule_runs`는 자동 폐기된다.

---

## 7. 컴포넌트별 역할 분담

| 컴포넌트 | 역할 |
|---|---|
| `app/main.py` | 세션 인증, 페이지 라우팅, REST API 엔드포인트(학생 입력기간 CRUD·관리자 대리수정 포함), 예외 처리 |
| `app/database.py` | SQLAlchemy 모델 정의(`Student`/`Schedule`/`ScheduleRevision`/`SystemSetting`/`ScheduleAudit`/`ScheduleRun`), CSV 동기화, 학생 개별 등록/수정, 스케줄 CRUD(+ 감사 기록), 학생 입력기간 조회/설정/잠금/해제, 더미데이터 생성, 생성 readiness 체크, run 저장/조회·무효화 |
| `app/admin_auth.py` | `data/admins.csv` 로딩(로그인마다 재읽기), 환경변수 fallback, 관리자 인증/활성여부 확인 |
| `app/demo_scheduler.py` | 전체 시간표 스왑 휴리스틱, 데스크 시간표 배정 알고리즘 |
| `app/validators.py` | 스케줄 정규화, 연속 4시간 검증, 근로유형별 주간 경고 계산 |
| `app/exports.py` | `openpyxl` 워크북 생성(4개 시트) |
| `app/config.py` | 영업시간/요일/상태코드/근로유형 한도 등 전역 상수, 환경변수 로딩 |
| `templates/`, `static/` | 로그인/학생/관리자 화면, 그리드 드래그 입력 JS |

---

## 8. 중요한 설계 결정

| 결정 | 이유 |
|---|---|
| OR-Tools 대신 **스왑 휴리스틱** 채택 | zip 프로토타입에서 실제 40명 데이터로 검증된 방식. "1순위 전량 배정 후 부족분만 2·3순위와 교환"이 구현 난도 대비 실사용 요구를 충분히 충족함을 확인 |
| Supabase 대신 **SQLAlchemy + SQLite(로컬)/Postgres(운영)** | 별도 BaaS 없이 단일 FastAPI 서비스로 배포 단순화. RLS 대신 애플리케이션 레벨에서 세션 기준 접근 제어 |
| Streamlit 대신 **FastAPI + Jinja2 + 바닐라 JS** | PC 드래그/모바일 터치 드래그 등 커스텀 인터랙션이 많아 Streamlit 위젯보다 직접 HTML/JS 제어가 필요 |
| 스케줄을 **JSON 컬럼**(`schedule_json`)에 저장 | 학생 1인 = row 1개, 요일×시간 그리드를 변환 없이 그대로 저장. 상태값은 문자열 상수(`first`/`second`/...)로 관리해 매직넘버 없이 가독성 확보 |
| 스케줄 저장 시마다 `schedule_revisions`에 이력 적재 | 감사(audit) 목적. 학생이 스케줄을 수정해도 이전 값을 조회할 수 있는 최소한의 이력 보존 |
| 학생 목표 시간을 **1순위 시간 수로 고정**하고 스왑으로만 조정 | 2·3순위가 실제 배정에 쓰여도 학생의 주간 총 근로시간이 임의로 늘거나 줄지 않도록 하는 불변식 보장 |
| "기준/확정" 근로표 구분 폐기 | 승인 워크플로우(주간 요청/수정요청/이의제기) 자체가 이번 버전 범위 밖이므로, 그 구분의 근거가 없어짐. 전체 시간표 자체가 유일한 산출물 |
| Supabase를 **순수 Postgres 호스팅**으로만 재도입 | Auth/RLS 같은 BaaS 기능 없이도 관리형 Postgres가 필요했고, 이미 SQLAlchemy+`psycopg` 경로가 Postgres를 지원하도록 되어 있어 `DATABASE_URL`만 바꾸면 추가 코드 변경 없이 연결 가능 |
| 관리자 계정을 **환경변수 대신 `admins.csv`**로 관리 | 계정 수 제한 없이(2개 이상) 운영 중 재배포 없이 계정을 추가/변경/비활성화할 수 있어야 한다는 요구를 반영. 로그인마다 파일을 다시 읽는 방식으로 서버 재시작 없는 즉시 반영을 구현 |
| 운영 DB **초기 무시드** + 관리자 화면에서 학생 개별 등록 지원 | CSV 일괄 업로드만으로는 소수 인원 추가/오탈자 수정이 번거로워, 1명 단위 등록·수정 경로를 추가. 운영 DB에 코드/CSV로 자동 주입되는 명단이 없도록 해 배포 환경마다 실제 명단을 관리자가 직접 등록하게 함 |
| 전체 시간표 생성 전 **readiness 체크**(전원 제출+유형지정) 하드 게이트 | 일부만 제출된 상태로 생성하면 결과가 실제 배포 가능한 근로표가 아니게 됨 — 생성 자체를 차단해 잘못된 결과물이 만들어지는 것을 방지 |
| 명단/스케줄 변경 시 `schedule_runs` 자동 폐기 | 오래된 생성 결과가 화면에 남아 있으면 관리자가 최신 명단 기준 결과로 착각할 위험이 있어, 입력이 바뀌면 무조건 재생성을 강제 |
| 운영 관리자 계정을 **Render Secret File**로 관리 | 로컬 `data/admins.csv`를 그대로 운영에 쓰면 저장소에 실비밀번호가 노출될 위험이 있음. Render Secret File은 저장소와 분리된 별도 채널로 배포되어, 코드는 동일하게 유지하면서(경로만 자동 전환) 운영 비밀값을 안전하게 분리 |
| Render **Singapore 리전** 선택 | 사용자가 한국이라 지리적으로 가장 가까운 리전으로 지연시간 최소화. 플랜은 결제 없는 기능 검증을 위해 현재 `free`로 임시 설정 중이며, 실사용(40명 상시 접속) 전에는 유휴 시 꺼지지 않는 `starter`로 전환 예정(3번 참고) |
| 학생 입력기간을 **테이블 추가 대신 `system_settings` 범용 key-value**로 저장 | 저장할 값이 시작·마감 시각, 수동잠금 여부 3개뿐이라 전용 테이블(컬럼 여러 개)까지는 과함. 나중에 다른 전역 설정이 필요해져도 새 컬럼/마이그레이션 없이 key만 추가하면 되도록 범용 구조로 설계 |
| 입력기간 값을 **한국시간으로 입력받아 UTC로 저장** | 서버·DB(Supabase)는 UTC 기준으로 동작하는 게 안전하지만, 관리자는 한국시간으로 생각하고 입력함 — 입력/표시 시점에만 `Asia/Seoul` 변환을 적용해 저장은 항상 UTC로 통일 |
| 감사 로그를 `schedule_revisions`와 **별도로 `schedule_audits` 신설** | `schedule_revisions`는 기존에도 있던 "저장할 때마다 이력 적재" 테이블이지만 누가(학생 본인 vs 관리자) 바꿨는지 구분하는 컬럼이 없었음. 기존 테이블에 컬럼을 추가하는 대신 별도 테이블로 분리해, 기존 `schedule_revisions` 소비 코드(있다면)에 영향 없이 감사 요구사항만 새로 충족 |
| 관리자 대리수정은 **입력기간이 잠긴 상태에서만** 허용(409로 차단) | 입력기간이 열려 있는 동안 관리자와 학생이 동시에 같은 스케줄을 수정하면 마지막 저장이 상대방 입력을 덮어쓰는 충돌이 생김 — "학생 입력 중엔 관리자 손대지 않음"을 코드로 강제 |

---

## 9. 수정 시 주의점

- **`demo_scheduler.py` 알고리즘 변경 시**: 6.3(하드 제약)의 불변식(연속 4시간, 학생별 총 배정시간 유지)이 깨지지 않는지 반드시 재검증한다.
- **`config.py`의 영업시간/상태코드 변경 시**: `validators.py`(연속시간 계산), `exports.py`(엑셀 그리드 렌더링), `templates/student.html`·`admin.html`(프론트 그리드)까지 함께 확인해야 한다. 하드코딩된 `range(9, 22)`가 `exports.py`에도 별도로 있어 `config.HOURS`와 동기화가 깨지지 않도록 주의.
- **DB 스키마(`database.py`의 모델) 변경 시**: 로컬 SQLite와 운영 Postgres 양쪽에서 마이그레이션 경로를 확인한다(현재 별도 마이그레이션 도구 없이 `Base.metadata.create_all`만 사용 — 스키마 변경 시 기존 운영 데이터 처리 방안이 follow-up으로 필요).
- **관리자 인증 변경 시**: `admins.csv`에 비밀번호가 평문으로 저장되는 한계(파일 유출 시 전 계정 노출, 브루트포스 방어 없음)를 인지한다. 공개 저장소에 절대 커밋하지 않도록 `.gitignore` 확인 필수, 운영 서버의 파일 접근 권한도 최소화할 것.
- **명단 변경 로직(`sync_students`/`create_student`/`update_student`) 변경 시**: `schedule_runs` 자동 폐기(`delete(ScheduleRun)`) 호출이 누락되지 않았는지 확인한다. 누락되면 오래된 생성 결과가 최신인 것처럼 남아있게 된다.
- **`schedule_generation_readiness()` 변경 시**: 5.5(spec.md)의 생성 전제조건 문구와 `main.py`의 에러 메시지 구성을 함께 갱신한다.
- **`student_access_status()`/입력기간 관련 함수 변경 시**: 이 값을 참조하는 지점이 여러 곳(`current_student_id`의 423 게이트, 로그인 라우트, 관리자 대리수정의 409 게이트)이라 하나만 고치고 나머지를 누락하기 쉽다. 세 지점 모두 재확인할 것. 시각 비교는 항상 UTC로 정규화한 뒤 비교하는지도 확인(`Asia/Seoul` 변환은 입력·표시 시점에만).
- **`ScheduleAudit`/`schedule_audits` 관련 변경 시**: `save_student_schedule()`이 `actor_type`/`actor_id`를 누락 없이 넘기는지 확인 — 관리자 대리수정 경로(`api_admin_update_student_schedule`)에서 `actor_type="admin"`을 빼먹으면 감사 로그로 누가 수정했는지 구분할 수 없게 된다.

---

## 10. 미확정(follow-up) 항목

`docs/spec.md` 9번과 동일한 범위. 아래는 아키텍처 관점에서 특히 재설계가 필요한 부분만 정리한다.

- **승인 워크플로우 도입 시**: `schedule_runs`를 "기준/확정"으로 분리하거나 별도 `work_orders` 테이블이 다시 필요해짐 — v2 spec의 데이터 모델 설계를 재검토 대상으로 참고.
- **LLM/공휴일 API 재도입 시**: 현재 `app/utils` 계층이 없으므로(zip 구조에는 별도 utils 모듈 없음) 외부 API 호출을 어느 모듈에 둘지 새로 설계해야 함.
- **다중 관리자/역할 세분화 시**: 현재 `require_admin`은 세션의 `admin: true` 불리언 하나로만 판단 — 역할별 권한 분리 로직이 없음.
- **DB 마이그레이션 도구**: 현재 Alembic 등 마이그레이션 도구 미도입. 스키마가 잦아지면 도입 검토 필요.
