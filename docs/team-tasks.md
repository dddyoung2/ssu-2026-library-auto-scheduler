# Team Tasks — 역할 및 작업 분담

> 이 문서는 `CLAUDE.md`/`AGENTS.md`의 "Role Assignment" 절차가 참조하는 근거 파일이다. AI 에이전트는 세션 시작 시 이 문서에서 현재 작업자의 역할 번호를 확인하고, 그 역할의 작업 범위 밖의 파일은 건드리지 않는다.
> 작업 항목 자체의 최신 목록·상태·담당자는 **Notion "프로젝트 일정" 데이터베이스**가 원본(source of truth)이다. 이 문서는 역할 번호 ↔ 담당자 매핑과 각 역할의 작업 범위(포함/제외)만 고정 기술한다.

---

## 1. 역할 번호

| 번호 | 역할 | 담당자 | GitHub |
|---|---|---|---|
| 0 | 프론트엔드 및 규칙 알고리즘 설계 (팀장) | 송민호 | [@minhosong-mse](https://github.com/minhosong-mse) |
| 1 | DB 설계 및 AI 엔지니어링 (백엔드) | 김도영 | [@dddyoung2](https://github.com/dddyoung2) |

Notion 데이터베이스의 "역할" 속성 값(`프론트엔드`/`백엔드`/`공통`)과의 대응 관계:
- `프론트엔드` = 역할 0
- `백엔드` = 역할 1
- `공통` = 역할 구분 없이 두 사람 모두 작업 가능(계획서 작성, 아키텍처 다이어그램 등)

---

## 2. 역할별 작업 범위 (현재 phase 기준 — v3.2 `lissurary` / Render+Supabase)

### 역할 0 — 프론트엔드 (송민호)
- **포함**: `app/templates/*.html`, `app/static/*.js`/`*.css` — 로그인, 학생 스케줄 입력 그리드, 관리자 명단 관리·시간표 생성·다운로드 화면
- **제외**: `app/database.py`, `app/admin_auth.py`, `app/demo_scheduler.py`, `app/validators.py`, `app/exports.py`, DB/배포 설정
- Notion 대응 작업: `프론트엔드_01~05`

### 역할 1 — 백엔드/AI (김도영)
- **포함**: `app/database.py`(SQLAlchemy 모델·DB 접근), `app/admin_auth.py`(다중 관리자 인증), `app/demo_scheduler.py`(스왑 휴리스틱 알고리즘), `app/validators.py`, `app/exports.py`, `app/config.py`, Supabase/Render 배포 설정
- **제외**: `app/templates/*`, `app/static/*`(화면 마크업/스타일)
- Notion 대응 작업: `백엔드_01~09`

### 공통 (역할 구분 없음)
- 프로젝트 계획서, 정량 목표, 아키텍처 다이어그램, 신청서 작성(인적사항/문제정의/해결과정/개선성과/확산가능성)
- Notion 대응 작업: `공통_01~08`

---

## 3. 현재 phase 요약

프로젝트명 **Lissurary**(구 Library Auto Scheduler). 검증된 FastAPI 프로토타입(`v4_6_final`/`lissurary_deploy`)을 그대로 `app/`에 이식하는 단계이며, MVP 범위는 **전체 시간표 생성 → 데스크 시간표 생성 → 엑셀 다운로드**까지다. 확정/배포 워크플로우, 주간 추가·제외 요청, 수정요청·이의제기, LLM 연동, 상태 대시보드, 공휴일 API 연동은 이번 phase에서 제외되며 `docs/spec.md` 9번에 follow-up으로 정리되어 있다.

배포는 Render.com(FastAPI 웹서비스, 서비스명 `lissurary`) + Supabase(PostgreSQL 순수 호스팅, Auth/RLS 미사용)로 확정되었다. 상세는 `docs/architecture.md` 참고.

---

## 4. 역할 변경/재배정 시

- 담당자 변경 시 1번 표만 갱신하면 되고, `CLAUDE.md`/`AGENTS.md`의 역할 번호 정의(0/1)는 그대로 유지한다(역할 "번호"와 "사람"을 분리해 관리).
- 작업 범위(2번) 자체가 바뀌는 구조적 변경(예: 폴더 구조 개편)이 있으면 이 문서와 `docs/components.md` 4번 "수정 시 함께 확인해야 하는 파일" 표를 함께 갱신한다.
