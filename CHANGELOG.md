# Changelog

## [0.2.0] - 2026-08-12
### 변경
- 프로젝트 방향 전환(v3): Streamlit + Supabase(BaaS) + OR-Tools + OpenAI 계획을 폐기하고, 검증된 FastAPI + SQLite 프로토타입 기반으로 전환. 범위를 전체 시간표 생성 → 데스크 시간표 생성 → 엑셀 다운로드까지로 축소하고, 확정/배포·주간요청·수정요청·이의제기·LLM·대시보드·공휴일 API 연동은 follow-up으로 이동
- 1~3지망 처리 방식을 스왑 휴리스틱(1순위 전량 배정 후 부족분만 2·3순위와 교환)으로 확정
- DB를 Supabase PostgreSQL(순수 DB 호스팅, Auth/RLS 미사용)로, 배포를 Render.com(서비스명 `lissurary`)으로 확정. Streamlit Community Cloud는 사용하지 않음
- 다중 관리자 계정(`admins.csv`/Render Secret File), 학생 개별 등록/수정, 전체 시간표 생성 전 "전원 최종제출+유형지정" readiness 체크 등 v4.6 기준 스펙 반영
- 프로젝트명을 Library Auto Scheduler에서 **Lissurary**로 변경
- `docs/spec.md`, `docs/architecture.md`, `docs/components.md`, `README.md`를 위 방향 전환 기준으로 전면 재작성
- 폴더 구조를 Streamlit 대상 `src/{core,db,pages,utils}`에서 FastAPI 대상 `app/{main,config,database,admin_auth,demo_scheduler,validators,exports,templates,static}`으로 전환

### 추가
- `docs/team-tasks.md` 작성: 역할 번호(0=프론트엔드/알고리즘, 1=백엔드/AI) ↔ 담당자 매핑, 역할별 작업 범위, 현재 phase 요약
- 검증된 FastAPI 프로토타입(v4.6/`lissurary_deploy`) 코드를 `app/`에 실제 이식 — `src/{core,db,pages,utils}` 빈 스캐폴딩 제거
- `supabase/migrations/`에 `app/database.py` 모델과 1:1 대응하는 선택적 DDL 추가
- **학생 시간표 입력기간(시작~마감) 관리** 기능(v4.7): 입력기간 밖이거나 관리자가 수동 잠그면 학생 로그인·수정이 423으로 차단됨
- **관리자의 학생별 시간표 열람/대리수정** 기능(v4.7): 입력기간이 잠긴 상태에서만 관리자가 개별 학생 시간표를 직접 수정 가능(충돌 방지), 모든 수정은 `schedule_audits`에 감사 기록
- Render `render.yaml`을 결제 없는 기능 검증을 위해 `plan: free`로 임시 설정(실사용 전 `starter`로 복귀 예정)

### 수정
- 문서(`README.md`, `docs/spec.md`, `docs/architecture.md`, `docs/components.md`)가 v4.7 기능(입력기간 관리, 대리수정, 신규 테이블 2종)을 반영하지 못하고 있던 것을 발견해 전면 재동기화
- 관리자 학생 목록에서 '시간표 보기'/'수정 저장' 두 열만 오른쪽에 고정되도록 `app/static/style.css` 패치(v4.7.1, 기능 변경 없음)

## [0.1.0] - 2026-08-09
### 추가
- 초기 레포지토리 구조 설정
- 초기 디렉터리 및 파일 생성
- 초기 문서 파일 내용 기재