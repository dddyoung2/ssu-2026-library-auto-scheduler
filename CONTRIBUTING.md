# CONTRIBUTING
> Commit·PR·Branch 규칙. 모든 기여자 공통 해당 사항.

## 작업 원칙
**중요 규칙:**
1. `main`에 직접 commit/push 금지
2. 한 작업 = 한 브랜치 = 한 PR
3. 항상 최신 `main`에서 새 브랜치 생성
4. 본인 브랜치만 push
5. 시크릿 파일, 개인정보, 대용량 모델 파일 commit 금지
6. PR 전 테스트 결과 확인

## Branch & Commit Message 네이밍
**Branch 권장 형식:** `<type>/<short-description>`
**Commit Message 권장 형식:** 
`<type>(<scope>): <summary>`
`<body>`

**Type - 종류**
- `feat`: 신규 기능
- `fix`: 버그 수정
- `refactor`: 리팩토링
- `docs`: 문서
- `test`: 테스트
- `chore`: 빌드·설정·의존성

**Scope - 영역**
작업한 기능(영역)명을 적습니다.

**Summary - 요약**
- 한글, 영어 상관없음
- 50자 이내

**Body - 본문(선택)**
- "왜" 변경했는지에 대해 서술
- 한 줄 띄우고 작성
- 줄당 72자 이내

Branch Naming 예시: 
- `feat/admin-login`
- `fix/user-login`
- `docs/readme-v1-2`

Commit Message 예시:
- `feat(auth): 로그인 화면 추가`
- `fix(scheduler): 배정 오류 수정`
- `docs(readme): 실행 방법 갱신`
- `test(scheduler): 결과 집계 테스트 추가`

## Git 작업 흐름
**작업 시작:** `git switch main` → `git pull` → `git switch -c <type>/<short-description>`

**PR 전 점검:** `git status` → `git diff` → `python -m pytest`

## Pull Request 규칙
### 템플릿
- 기본적으로 .github/pull_request_template.md를 템플릿으로 준수하고, 이하 템플릿은 예시용으로 참고하기 바람.
``` markdown
# Pull Request Name
## 변경 요약
*무엇을 했는가*

## 왜 필요한가
*spec참조*

## 테스트 결과
- [ ] *테스트1*
- [ ] *테스트2*
- [ ] *테스트3*

## 체크리스트
- [ ] 시크릿이 커밋에 포함되지 않았는지
- [ ] `main` 브랜치가 아닌 별도 브랜치를 사용하는지

## Follow-UP
- *이어서 할 것*
```

### PR 크기
- 300줄 이하 권장
- 너무 큰 변경은 PR 쪼개기 권장
- 엔진 관련은 더 작게

### 리뷰어가 볼 점
- 깃허브 레포지토리 관리자 승인 필수
- 변경 요청을 받을 시 추가 commit 필요 (강제로 push 금지)

## 테스트 규칙
- 자동화 가능한 테스트는 PR 전 실행한다.
- 실행하지 못한 테스트는 PR에 이유를 기록한다.

## 보안 규칙
다음 항목은 commit하지 않는다.
- `.env`
- API key
- access token
- Supabase 서비스 키
- 개인정보 포함 데이터

## 문서 규칙
- 프로그래밍을 하면서 같이 바뀌는 실수를 방지하고자 완료한 작업을 체크하는 행동을 제외하고는 문서와 코드를 동시에 바꾸지 말고, 문서만 따로 할 것.

## 빠른 참조
|작업명|명령어|
|---|---|
|레포지토리 생성|`git clone <repo-URL>`|
|최근 작업 불러오기|`git pull origin main`|
|branch 생성 및 이동|`git branch -c <type>/<short-description>`|
|작업 단위 깃허브에 업로드|`git push -u origin <branch-name>`|
|local branch delete|`git branch -d <branch-name>`|