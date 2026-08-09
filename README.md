# ssu-2026-library-auto-scheduler
도서관 교내 근로를 디지털틱하게 빠르고, 간편하게

---

## 📌 개요

- **프로젝트명:** Library Auto Scheduler
- **참여 대회/목적:** 숭실대 AI 업무 혁신 챌린지 (2026)
- **핵심 기능 요약:** 도서관 근로장학생 근로표 작성 업무를, LLM과 최적화 알고리즘(OR-Tools)으로 자동화하는 스케줄링 시스템

---

## 🧩 핵심 기능

| 기능명 | 설명 |
|---|---|
| 근로생 – 분기 단위 희망 근로표 입력 | 강의시간·개인불가·1~3지망을 드롭다운 폼으로 구조화하여 입력 (자유 서술 없음) |
| 근로생 – 주간 특별 스케줄 입력 | 고정 포맷(추가/제외, 일자, 시간, 사유)으로 입력. 시험기간 등 특별 추가근무 신청도 이 기능으로 처리 |
| 근로생 – 생성된 근로표 확인 | 로그인 계정 기준 본인 근로 시간대만 자동 필터링되어 표시 |
| 관리자 – 근로 기간 대상 명단 업로드 | 학기+방학 근로 대상자 명단 업로드·저장 (데이터 파이프라인 시작점) |
| 관리자 – 단위 근로표 생성 및 확인 | 조건 충족 근로표 자동 생성, 수동 수정/확정/배포 |
| 관리자 – 주간 데스크 근로표 생성 및 확인 | 분기 근로표 + 주간 특이사항 기반 데스크표 생성·배포 |
| 근로생 – 근로표 수정 요청 (1회) | 배포된 확정 근로표에 대해 1회 한정 수정 요청 제출 |
| 관리자 – 근로일정(영업시간/공휴일) 설정 | 총 근로일, 학기중/방학중 근로일 설정. 공휴일 불러오기: 설정된 근로기간(학기+방학) 중 선택한 분기(학기 또는 방학) 범위만 공공데이터포털 특일정보 API로 조회해 자동 반영 (수기 추가/수정도 병행 가능) → 학생 입력 폼·근로표 생성 로직에 자동 반영되어 해당 일정 제한 |
| 관리자 – 단위 스케줄표 제출 확인 | 근로생별 제출 여부 확인 + 스케줄표 미리보기 |
| 관리자 – 주간 스케줄 수정 요청 확인 | 추가/제외 요청 확인, 사유 검토 후 승인·거절 |
| 관리자 – 근로표 엑셀 다운로드 | 확정된 분기/주간 근로표를 엑셀 파일로 다운로드 |

---

## 🏗️ 시스템 아키텍처

*(계획서에서 작성한 데이터 흐름도/구조도를 그대로 재사용. 프론트엔드-백엔드-AI모델-DB 흐름을 이미지로 첨부)*

<!-- 아키텍처 다이어그램 이미지 삽입 -->

---

## 🛠️ 기술 스택

**Frontend**
- Streamlit

**Backend**
- Supabase, Google OR-Tools

**AI / 모델**
- OpenAI LLM API

**Database / Infra**
- Supabase

** Deployment **
- Streamlit Community Cloud

---

## 📂 프로젝트 구조
```
project/
├── src/            # 소스 코드
├── models/         # AI 모델 관련
├── tests/           # 데이터셋
├── docs/           # 문서
└── README.md
```
---

## ⚙️ 설치 방법 (Installation)

### 저장소 클론

``` bash
git clone https://github.com/dddyoung2/ssu-2026-library-auto-scheduler.git

cd {repo}
```
### 가상 환경(venv)
#### Install
``` bash
py -3.12 -m venv .venv
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

## ▶️ 실행 방법 (Usage)

```bash
python src/app.py
```
또는 [Link]()이용

---

## 🔑 환경 변수 설정

`.env.example` 파일을 참고하여 `.env` 파일을 생성하세요.

```env
API_KEY=your_api_key_here
DB_URL=your_db_url_here
```

---

## 📊 성능 / 벤치마크

*(계획서의 "정량적 목표" 대신, 실제 측정된 결과 수치로 대체)*

| 지표 | 결과 |
|---|---|
| 관리자 수기 작성 소요 시간 | None |
| 프로그램 자동 생성 소요 시간 | None |
| 정확도 | None |
| 완전도 | None |
| 응답 속도 | None |

---

## 👥 팀 (Contributors)

| 이름 | 역할 | GitHub |
|---|---|---|
| 송민호 | 프론트엔드 및 규칙 알고리즘 설계 | [![Github](https://img.shields.io/badge/minhosong-181717?style=flat&logo=github&logoColor=white)](https://github.com/minhosong-mse) |
| 김도영 | DB 설계 및 AI 엔지니어링 | [![Github](https://img.shields.io/badge/dddyoung2-181717?style=flat&logo=github&logoColor=white)](https://github.com/dddyoung2) |
