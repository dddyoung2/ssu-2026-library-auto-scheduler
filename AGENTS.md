# Agent Guide

이 파일은 Codex 전용이다. Codex는 세션 시작 시 이 파일을 자동으로 읽는다.

## Project Context
이 프로젝트가 무엇을 해결하는지, 주요 사용자는 누구인지 요약한다.

## Required Reading
1. README.md
2. docs/spec.md, 있을 때 관련 섹션
3. docs/architecture.md, 구조 변경 시
4. docs/team-tasks.md

## Role Assignment
docs/team-tasks.md에 기록된 역할 번호를 확인하고, 존재한다면 현재 작업자가 담당하는 역할(예: 0=프론트엔드/알고리즘, 1=백엔드/AI)에 맞춰 작업 범위를 제한한다.

## Do Not
- .env, secrets, API key를 커밋하지 않는다.
- main 브랜치에 직접 push하지 않는다.
- 사용자 승인 없이 merge하지 않는다.

## Work Start Procedure
1. 현재 브랜치와 git status를 확인한다.
2. 현재 브랜치가 main이면, 이번 작업과 관련된 새 브랜치를 생성하고 그 브랜치로 이동한다. 브랜치 이름은 CONTRIBUTING.md의 브랜치 네이밍 규칙을 준수한다.
3. Required Reading 문서를 읽는다.
4. docs/team-tasks.md에서 자신의 역할을 확인한다.
5. 작업 범위와 제외 범위를 확인한다.

## Work Completion Procedure
1. 변경 요약을 작성한다.
2. 테스트 실행 결과를 기록한다.
3. 남은 리스크를 기록한다.
4. commit 메시지와 PR 작성은 CONTRIBUTING.md의 규칙을 준수한다.
5. commit/push/PR 전 사용자 확인을 받는다.

## Report Format
- Summary
- Changed Files
- Test Results
- Risks / Blocked