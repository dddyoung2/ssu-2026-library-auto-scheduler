# Components

> 프로젝트의 폴더 구조, 파일별 책임, 의존(import) 관계를 정리한 문서.
> 코드가 추가/변경될 때마다 이 문서도 함께 갱신할 것 (CONTRIBUTING.md 문서 규칙 참고).

**현재 상태:** 저장소는 아직 스캐폴딩 단계로, `src/` 하위 폴더에는 실제 코드 파일이 없고 `.gitkeep`만 존재한다. 아래 1번은 각 폴더가 앞으로 담당할 역할(설계 의도)을, 2번은 현재 실제로 존재하는 파일의 목록을 정리한다. 실제 모듈이 추가되면 2~4번 항목을 해당 파일 기준으로 다시 채운다.

---

## 1. 폴더별 역할

| 폴더 | 역할 |
|---|---|
| `src/pages/` | Streamlit 화면(페이지) 계층. 학생/관리자 화면, 입력 폼, 조회 화면 등 사용자와 직접 상호작용하는 UI 코드가 위치한다. |
| `src/core/` | 스케줄링/업무 로직 계층. 희망 근로표 취합, OR-Tools 기반 근무표 자동 생성, 공휴일 반영, 수정 요청 처리 등 도메인 규칙을 담당한다. `pages`와 `db` 사이의 비즈니스 로직을 캡슐화한다. |
| `src/db/` | Supabase 접근 계층. 테이블 CRUD, 인증, 파일(엑셀) 업로드/다운로드 등 외부 저장소와의 입출력을 담당한다. |
| `src/utils/` | 여러 계층에서 공통으로 쓰는 유틸리티(날짜/시간 변환, 검증, 상수, 공공데이터포털 API 호출 등). 특정 도메인 로직을 포함하지 않는다. |
| `tests/` | `src/` 각 계층에 대응하는 자동화 테스트. PR 전 `python -m pytest`로 실행한다. |
| `data/exports/` | 관리자가 다운로드하는 확정 근로표 엑셀 등 산출물 저장 위치. 개인정보 포함 가능성이 있어 `.gitignore`로 관리되며 `.gitkeep`만 커밋된다. |
| `docs/` | 프로젝트 문서 (`spec.md`: 기능 명세, `architecture.md`: 아키텍처, `components.md`: 본 문서, `team-tasks.md`: 팀 역할/작업 분담). |
| `.github/` | GitHub 저장소 설정. `pull_request_template.md`(PR 템플릿), `workflows/ci.yml`(CI 자동화)를 포함한다. |

---

## 2. 파일별 책임

현재 저장소에 실제로 존재하는 파일 기준:

| 파일 | 책임 |
|---|---|
| `src/core/.gitkeep`, `src/db/.gitkeep`, `src/pages/.gitkeep`, `src/utils/.gitkeep` | 빈 폴더를 git이 추적하도록 하는 placeholder. 실제 모듈 파일이 추가되면 삭제 대상. |
| `tests/.gitkeep` | 위와 동일. 첫 테스트 파일 추가 시 삭제. |
| `data/exports/.gitkeep` | 위와 동일. 산출물이 생겨도 실제 파일은 `.gitignore`로 제외되므로 유지될 수 있음. |
| `requirements.txt` | 프로젝트 의존성 목록 (현재 비어 있음 — Streamlit/Supabase/OR-Tools/OpenAI SDK 등 추가 필요). |
| `.env.example` | 필요한 환경 변수 양식 (현재 비어 있음 — README 기준 `API_KEY`, `DB_URL` 등 채워야 함). |
| `.github/workflows/ci.yml` | CI 파이프라인 정의 (현재 비어 있음). |
| `.github/pull_request_template.md` | PR 작성 시 기본 템플릿. |
| `README.md` | 프로젝트 개요, 기능 요약, 기술 스택, 설치/실행 방법. |
| `CONTRIBUTING.md` | 브랜치/커밋/PR 규칙. |
| `AGENTS.md` / `CLAUDE.md` | AI 에이전트(Codex / Claude Code) 작업 규칙. |
| `CHANGELOG.md` | 버전별 변경 이력. |

> `src/` 실제 모듈이 추가되면, 이 표를 "파일 경로 → 담당 기능(예: `src/core/schedule_generator.py` → OR-Tools 기반 분기 근로표 생성)" 형태로 갱신한다.

---

## 3. import 관계

현재 실행 코드가 없어 실제 import 그래프는 존재하지 않는다. 대신 계층 간 의존 방향을 다음과 같이 규정한다 (향후 코드 작성 시 준수):

```
src/pages   (Streamlit UI)
    │  imports
    ▼
src/core    (스케줄링/업무 로직)
    │  imports
    ▼
src/db, src/utils  (DB 접근 / 공통 유틸)
```

- **허용:** `pages → core`, `core → db`, `core → utils`, `pages → utils`
- **금지(역방향 import 금지):** `db → core`, `db → pages`, `core → pages`, `utils → core/db/pages`
  - 하위 계층(`db`, `utils`)이 상위 계층(`core`, `pages`)을 알아서는 안 된다. 필요한 데이터는 함수 인자/반환값으로 주고받는다.
- `tests/`는 계층 구분 없이 `src/` 전체를 import할 수 있다 (단, 테스트 대상 계층에 대응하는 하위 폴더 구조 — 예: `tests/core/`, `tests/db/` — 를 권장).

> 실제 모듈이 추가되면 이 섹션에 실제 import 트리(예: `src/pages/admin_schedule.py → src/core/schedule_generator.py → src/db/supabase_client.py`)를 구체적으로 기록한다.

---

## 4. 수정 시 함께 확인해야 하는 파일

| 수정 대상 | 함께 확인할 파일 |
|---|---|
| `src/` 최상위 폴더 구조 변경 (폴더 추가/삭제) | `README.md`(프로젝트 구조), 본 문서(`docs/components.md`) |
| `src/core/*` (스케줄링 로직) | `docs/spec.md`(기능 명세와 일치 여부), `tests/`(대응 테스트), README 핵심 기능 표 |
| `src/db/*` (Supabase 접근) | `.env.example`(필요 환경 변수 반영), `requirements.txt`(Supabase client 등 의존성), `docs/architecture.md` |
| `src/pages/*` (Streamlit 화면) | `src/core/*`(호출하는 로직 인터페이스), README 실행 방법(`Usage`) |
| `src/utils/*` (공통 유틸) | 이를 참조하는 `core`/`db`/`pages` 전체 — 시그니처 변경 시 호출부 일괄 확인 |
| `requirements.txt` | `.github/workflows/ci.yml`(CI 의존성 설치 단계), README 설치 방법 |
| `.env.example` | `src/db/*`(실제 사용하는 환경 변수명과 일치하는지), 보안 규칙(실값 커밋 금지) |
| `docs/spec.md` | `docs/components.md`, README 핵심 기능 표 — 기능 추가/변경 시 3곳 동기화 |
| `docs/team-tasks.md` | `AGENTS.md`/`CLAUDE.md`의 역할 번호 매핑 — 역할 변경 시 함께 갱신 |
