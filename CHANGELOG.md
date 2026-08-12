# Changelog

## [미출시]
### 변경
- 프로젝트 방향 전환(v3): Streamlit + Supabase(BaaS) + OR-Tools + OpenAI 계획을 폐기하고, 검증된 FastAPI + SQLite 프로토타입 기반으로 전환. 범위를 전체 시간표 생성 → 데스크 시간표 생성 → 엑셀 다운로드까지로 축소하고, 확정/배포·주간요청·수정요청·이의제기·LLM·대시보드·공휴일 API 연동은 follow-up으로 이동
- 1~3지망 처리 방식을 스왑 휴리스틱(1순위 전량 배정 후 부족분만 2·3순위와 교환)으로 확정
- DB를 Supabase PostgreSQL(순수 DB 호스팅, Auth/RLS 미사용)로, 배포를 Render.com(서비스명 `lissurary`)으로 확정. Streamlit Community Cloud는 사용하지 않음
- 다중 관리자 계정(`admins.csv`/Render Secret File), 학생 개별 등록/수정, 전체 시간표 생성 전 "전원 최종제출+유형지정" readiness 체크 등 v4.6 기준 스펙 반영
- 프로젝트명을 Library Auto Scheduler에서 **Lissurary**로 변경
- `docs/spec.md`, `docs/architecture.md`, `docs/components.md`, `README.md`를 위 방향 전환 기준으로 전면 재작성
- 폴더 구조를 Streamlit 대상 `src/{core,db,pages,utils}`에서 FastAPI 대상 `app/{main,config,database,admin_auth,demo_scheduler,validators,exports,templates,static}`으로 전환 예정임을 문서에 명시(코드 이식은 별도 진행)

### 추가
- `docs/team-tasks.md` 작성: 역할 번호(0=프론트엔드/알고리즘, 1=백엔드/AI) ↔ 담당자 매핑, 역할별 작업 범위, 현재 phase 요약

## [0.1.0] - 2026-08-09
### 추가
- 초기 레포지토리 구조 설정
- 초기 디렉터리 및 파일 생성
- 초기 문서 파일 내용 기재