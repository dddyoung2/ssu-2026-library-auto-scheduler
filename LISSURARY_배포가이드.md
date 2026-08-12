# LISSURARY 상시 배포 가이드

이 패키지는 Render 서비스 이름을 `lissurary`로 설정한 배포 준비 버전입니다. Render가 해당 이름을 허용하면 기본 주소는 `https://lissurary.onrender.com` 형태가 됩니다. 이름 충돌 시 Render가 다른 서브도메인을 부여할 수 있습니다.

## 권장 운영 구조

- GitHub: 소스코드(Private 저장소 권장)
- Render Starter: FastAPI 웹서비스, 상시 실행
- Supabase PostgreSQL: 학생/시간표/배정 결과 영구 저장
- Render Secret File `admins.csv`: 관리자 계정

## 1. GitHub에 업로드

압축을 풀고 새 Private repository에 프로젝트 파일을 업로드합니다. `.gitignore`에 `data/admins.csv`가 포함되어 있으므로 실제 관리자 비밀번호 파일은 GitHub에 올리지 않습니다.

## 2. Supabase 데이터베이스 만들기

1. Supabase에서 새 프로젝트 생성
2. 프로젝트 상단 `Connect` 클릭
3. Render에서 사용할 경우 `Session pooler` 연결 문자열(포트 5432)을 권장
4. 연결 문자열을 복사

예시 형태:

```text
postgres://postgres.PROJECT_REF:DB_PASSWORD@aws-REGION.pooler.supabase.com:5432/postgres
```

Render의 `DATABASE_URL` 값에 그대로 입력합니다. 앱이 시작될 때 필요한 테이블을 자동 생성합니다.

## 3. Render에 배포

1. Render 로그인
2. `New` → `Blueprint`
3. GitHub의 프로젝트 저장소 연결
4. 루트의 `render.yaml` 선택
5. `DATABASE_URL`에 Supabase 연결 문자열 입력
6. 배포

`render.yaml`은 다음을 미리 설정합니다.

- 서비스명: `lissurary`
- 리전: Singapore
- Web Service: Starter
- HTTPS 쿠키 사용
- `/health` 헬스체크

Starter는 무료 인스턴스처럼 유휴 시 자동으로 꺼지지 않는 상시 실행용 설정입니다.

## 4. 관리자 계정 등록

Render 서비스 → `Environment` → `Secret Files` → `Add Secret File`

Filename:

```text
admins.csv
```

Contents 예시:

```csv
user_id,password,active
library_manager,원하는비밀번호1,1
scheduler_admin,원하는비밀번호2,1
```

Render에서는 이 파일이 `/etc/secrets/admins.csv`로 제공되며 앱이 이 파일을 읽습니다. 관리자 계정을 변경할 때는 Render의 Secret File 내용을 수정하고 저장하면 됩니다.

## 5. 학생 등록

최초 DB에는 학생이 0명입니다. 관리자 로그인 후 학생관리 화면에서:

- 학생 1명 직접 추가 또는
- CSV 명단 업로드

를 사용합니다. 등록되지 않은 학생은 로그인할 수 없습니다.

학생 CSV 형식:

```csv
name,student_no,work_type,active
김학생,20260001,A,1
이학생,20260002,B,1
박학생,20260003,,1
```

## 6. 배포 후 확인

1. `/health` 접속 확인
2. 관리자 로그인
3. 학생 1명 테스트 등록
4. 학생 로그인 및 임시저장/최종제출
5. 서버 재배포 후에도 학생 데이터가 남는지 확인
6. 더미 40명으로 제출 및 자동배정 테스트

## Supabase 요금제 주의

Supabase Free 프로젝트는 장기간 DB 활동이 없으면 일시정지될 수 있습니다. 학기 중 지속적으로 사용하는 수준이라면 먼저 Free로 검증할 수 있지만, 아무 때나 즉시 접속되어야 하는 완전한 상시 운영이 필요하면 운영 전에 Supabase 유료 플랜을 고려하십시오.

## 관리자 파일 주의

`data/admins.csv`는 로컬 테스트용입니다. 실제 운영용 관리자 계정은 GitHub에 커밋하지 말고 Render Secret File로 관리하는 것을 권장합니다.
