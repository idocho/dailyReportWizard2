# DailyReportWizard2 코드 분석 보고서

작성일: 2026-07-01  
분석 대상: `D:\WorkSpace\Development\dailyReportWizard2`  
기준 버전: 최신 배포 버전 `code/public/v2.5.0/`

## 0. 분석 범위와 근거

본 보고서는 현재 저장소의 최신 배포 버전인 `code/public/v2.5.0/`과 이 버전의 운영에 직접 연결되는 에이전트, Firebase, 배포 스크립트 구성을 기준으로 작성했다. 구버전 디렉터리는 기능 분석 기준에서 제외하고, 배포 이력과 롤백 확인 용도로만 취급한다.

주요 확인 경로:

- 최신 웹 앱: `code/public/v2.5.0/`
- 최신 웹 인증 모듈: `code/public/v2.5.0/js/auth/`
- 강사 에이전트: `code/agent_gui.py`, `code/agent_worker.py`, `code/agent_auth.py`, `code/kakao_send.py`, `code/ai_engine.py`
- Firebase/DB: `firebase.json`, `database.rules*.json`, `documents/DB_SCHEMA.md`
- Cloud Functions: `functions/index.js`, `functions/package.json`
- 배포/빌드: `scripts/*.ps1`, `deploy.sh`, `code/*.spec`
- Git: branch `main`, remote `https://github.com/idocho/dailyReportWizard2`

## 1. 로그인 및 PT Talk 개발 소스코드 형상관리

### 1.1 로그인 관련 소스 구조

최신 배포 버전의 로그인/인증 코드는 `code/public/v2.5.0/js/auth/`에 위치한다.

- `auth.js`: 웹 로그인/인증 흐름 담당
- `firebase-config.js`: Firebase client config
- `synth_email.js`: 사용자 식별자를 Firebase Auth 이메일 형태로 변환하는 보조 모듈
- `code/agent_auth.py`: 강사 PC 에이전트의 인증 또는 권한 검증 보조 계층

별도 참고 코드로 `platform/auth/`가 존재한다. 이 폴더에는 `login.html`, `admin.html`, `auth.js`, `provision.js`, `firebase-config.example.js`가 있어 인증 UI와 계정 provisioning 흐름을 검증한 흔적이 있다. 다만 최신 배포 기준의 운영 코드는 `code/public/v2.5.0/js/auth/`로 보는 것이 맞다.

판단:

- 로그인 기능은 Firebase Auth 기반 구조다.
- 업무 권한과 강사/캠퍼스 설정은 Firebase Auth 단독이 아니라 DB 설정 노드와 함께 운용되는 구조로 보인다.
- `firebase-config.js`는 공개 가능한 client config만 포함되어야 하며, 서비스 계정 키나 비밀값이 섞이지 않도록 관리해야 한다.

### 1.2 PT Talk 관련 소스 형상

최신 배포 버전 기준으로 저장소에는 명시적 `PT Talk` 단일 폴더명은 보이지 않는다. 기능상 학부모/학생 대상 리포트 생성 및 카카오톡 전송 흐름이 PT Talk 성격의 핵심 기능으로 보인다.

관련 소스:

- 웹 입력/리포트 생성: `code/public/v2.5.0/js/app-input.js`, `app-report.js`, `app-core.js`
- 설정/관리: `code/public/v2.5.0/js/app-settings.js`
- 점수/성적: `code/public/v2.5.0/js/app-scores.js`
- 강사 에이전트 UI: `code/agent_gui.py`
- 전송 워커: `code/agent_worker.py`
- 카카오 발송: `code/kakao_send.py`
- AI 문구 생성: `code/ai_engine.py`, `code/ai_style.py`

판단:

- 최신 배포 웹 앱에서 입력 데이터와 전송 작업을 만들고, PC 에이전트가 AI 생성 및 카카오 전송을 수행하는 하이브리드 구조다.
- 소스가 웹, 에이전트, AI, 전송 모듈로 나뉘어 책임 경계가 비교적 명확하다.
- PT Talk라는 기능명을 공식 명칭으로 쓸 경우, 실제 코드명인 report/send/agent 흐름과 PT Talk 용어를 매핑한 운영 문서가 필요하다.

### 1.3 형상관리 방식

Git 저장소 상태:

- 현재 브랜치: `main`
- 원격 저장소: `https://github.com/idocho/dailyReportWizard2`
- 최신 배포 버전 디렉터리: `code/public/v2.5.0/`
- 과거 버전 디렉터리: `code/public/v2.0.5/`부터 `code/public/v2.4.0/`까지 보존
- 포털 버전 목록: `code/public/versions.json`
- 버전 포털 빌드: `scripts/build-portal.ps1`
- 신규 버전 생성: `scripts/new-version.ps1`

형상관리 특징:

- 웹 산출물은 버전 디렉터리 단위로 관리한다.
- 본 보고서 기준 최신 배포 버전은 `v2.5.0`이다.
- `v2.4.0` 이하 버전은 분석 기준에서 제외하고, 이력/비교/롤백 확인 용도로만 취급한다.
- Firebase Hosting 공개 버전은 `firebase.json`과 버전 포털/redirect 정책으로 제어한다.
- Python 에이전트는 PyInstaller spec 파일(`DRW-Agent*.spec`, `DRW-AI-Agent*.spec`)로 배포 산출물을 관리한다.

리스크:

- 운영 문서와 배포 체크리스트가 최신 배포 버전 `v2.5.0` 기준으로 완전히 동기화되어 있는지 확인이 필요하다.
- `main`에 직접 개발하는 형태로 보이며, 릴리즈/핫픽스 브랜치 정책은 코드상 명확히 드러나지 않는다.

권고:

- 최신 배포 기준을 `v2.5.0`으로 문서와 배포 체크리스트에 명확히 표기한다.
- 운영 배포 전 Git tag 또는 release branch를 사용해 Firebase 공개 버전과 소스 버전을 연결한다.
- PT Talk 기능명을 공식 명칭으로 쓸 경우, `report/send/agent` 코드 흐름과 PT Talk 용어를 매핑한 문서를 추가한다.

## 2. 회원정보, 로그, 액션 기반 DataBase 관리

### 2.1 Database 종류와 관리 위치

최신 배포 버전은 Firebase Realtime Database 중심 구조다.

관련 파일:

- DB 규칙: `database.rules.json`, `database.rules.v2.json`, `database.rules.open.json`
- DB 스키마 문서: `documents/DB_SCHEMA.md`
- Firebase 설정/호스팅/함수 배포: `firebase.json`
- DB 백업/복원: `code/scripts/backup_db.py`, `code/scripts/restore_db.py`
- Firebase 인증 보조: `code/scripts/_fb_auth.py`
- 백업 예약: `code/scripts/register_backup_task.ps1`

판단:

- 회원정보, 설정, 수업 데이터, 입력 데이터, 전송 이력은 Firebase Realtime Database에 저장되는 구조다.
- 스키마 정본을 `documents/DB_SCHEMA.md`로 별도 관리하고 있어 DB 구조 변경 시 문서화 체계가 있다.
- 운영 백업/복원 스크립트가 존재하므로 DB 운영 관리 도구는 최소한 갖춰져 있다.

### 2.2 회원정보 관리

회원정보는 Firebase Auth와 Realtime Database의 설정 노드가 함께 쓰이는 방식으로 판단된다.

관련 구성:

- Firebase Auth 로그인: `code/public/v2.5.0/js/auth/auth.js`
- synthetic email 생성: `code/public/v2.5.0/js/auth/synth_email.js`
- 계정 provision 참고 도구: `platform/auth/provision.js`
- 강사 등록/관리: `config/instructors/{id}` 구조 사용

판단:

- 로그인 계정 식별은 Firebase Auth가 담당한다.
- 실제 업무 권한, 강사 목록, 캠퍼스 설정 등은 DB의 `config` 계층에서 관리되는 것으로 보인다.
- 관리자 기능은 `adminOn === true` 조건과 DB 권한 규칙을 함께 검증해야 한다.

권고:

- Firebase Auth UID, synthetic email, instructor id, campus 권한의 매핑 규칙을 `DB_SCHEMA.md` 또는 `AUTH_DESIGN.md`에 최신 배포 기준으로 유지한다.
- 관리자 UI 숨김만으로 보안을 보장하지 말고 `database.rules.v2.json`에서 쓰기 권한이 실제로 제한되는지 정기 검증한다.

### 2.3 로그 및 이력 관리

확인되는 주요 로그/이력 계층:

- 전송 성공 이력: `campus/{campus}/history/{nameKey}/{YYYY-MM-DD}`
- 이력 값: `{note, instructor}`
- 전송 작업: 최신 웹 앱에서 sendJob 생성 후 에이전트가 처리
- 전송 성공분만 history 기록
- dry run 또는 bulk 제외 정책 존재
- 기존 `lastSent/`는 폐기

판단:

- 시스템 로그는 별도 감사 로그 DB라기보다 업무 이벤트 이력(history) 중심으로 관리된다.
- “카카오 전송 성공”이라는 액션 결과가 DB 이력으로 남는 구조라 전송 감사 가능성이 있다.
- 로그인 감사 로그, 관리자 설정 변경 로그, 데이터 수정 액션 로그가 별도 DB 노드로 표준화되어 있는지는 보강 확인이 필요하다.

권고:

- 액션 기반 관리를 강화하려면 `auditLogs/{date}/{eventId}` 형태의 표준 이벤트 로그를 별도 도입한다.
- 최소 이벤트 필드는 `actorUid`, `actorInstructorId`, `campus`, `action`, `targetPath`, `targetKey`, `beforeHash`, `afterHash`, `createdAt`, `clientVersion` 정도가 적절하다.
- 학생 개인정보 및 상담/특이사항은 원문 로그 중복 저장을 피하고, 필요한 경우 해시 또는 요약만 남긴다.

### 2.4 핵심 업무 데이터 구조

핵심 데이터 구조:

- `grade_sem`은 교재(`cfg.textbooks[tbName]`) 종속이며 학급 종속이 아니다.
- `pkey` 형식은 `{classId}|{subject}`이다.
- 진도/과제 데이터는 `session/class_data/{pkey}`에 저장된다.
- 특이사항은 학생 종속 단일 데이터이며 과목 grain이 아니다.
- 입력 특이사항은 `input/{nameKey}/__note__`, 누적 이력은 `history/`를 사용한다.
- 과제수행도는 `obs/assign_grade`가 단일 소스다.
- 로컬 캐시 `daily_cache.json`은 진도/과제만 영속하고 student/note/force는 메모리만 사용한다.

판단:

- DB grain이 비교적 명확하게 정리되어 있어 Analyzer와 전송 기능 간 조인이 가능하다.
- `history/{nameKey}/{date}` 구조는 학생 단위 장기 이력 분석에 적합하다.
- `pkey`가 문자열 결합 키이므로 classId/subject에 구분자 `|`가 들어가지 않도록 입력 검증이 필요하다.

## 3. 배포 도구 및 서버

### 3.1 웹 배포

최신 배포 웹 버전 `code/public/v2.5.0/`은 Firebase Hosting 기반으로 배포되는 정적 웹 앱이다.

관련 파일:

- `firebase.json`
- `.firebaserc`
- `deploy.sh`
- `scripts/build-portal.ps1`
- `scripts/new-version.ps1`
- `code/public/versions.json`
- `code/public/index.html`

구조:

- `code/public/` 아래 버전별 정적 웹 앱을 두며, 본 보고서 기준 최신 배포 버전은 `v2.5.0`이다.
- `versions.json`과 `build-portal.ps1`로 버전 포털을 생성한다.
- 공개 가능한 버전만 Firebase Hosting에 노출하고, 구버전은 redirect/ignore 정책으로 관리한다.
- 최신 배포 버전의 JS/CSS 변경 시 `code/public/v2.5.0/index.html`의 cache busting query(`?v=`) 갱신이 필요하다.

판단:

- 정적 웹 앱 + Firebase Hosting 구조라 서버 운영 부담이 낮다.
- 버전 디렉터리 방식은 롤백과 비교 검증에 유리하다.
- 운영 공개 버전 문서가 `v2.5.0` 기준으로 고정되어 있지 않으면 잘못된 버전이 배포될 위험이 있다.

### 3.2 서버 측 기능

서버 측 코드는 Firebase Cloud Functions 형태로 존재한다.

관련 파일:

- `functions/index.js`
- `functions/package.json`
- `functions/package-lock.json`
- `functions/README.md`

판단:

- 저장소에는 정적 호스팅 외에 Cloud Functions 서버리스 계층이 있다.
- Node.js 의존성은 `functions/package*.json`으로 관리된다.
- 별도 VM 서버가 아니라 Firebase Functions 기반 서버리스 구조로 보는 것이 타당하다.

### 3.3 강사 에이전트 배포

PC 배포 도구는 PyInstaller 기반이다.

관련 파일:

- `scripts/build-agent.ps1`
- `code/DRW-Agent.spec`
- `code/DRW-Agent-0.9.spec`
- `code/DRW-AI-Agent-0.91.spec`
- `code/DRW-AI-Agent-0.92.spec`
- `code/DRW-AI-Agent-0.93.spec`
- `code/build/`
- `code/dist/`

판단:

- 강사 PC 앱은 Python 소스를 PyInstaller로 패키징해 배포한다.
- 에이전트는 최신 웹 앱이 생성한 sendJob을 처리하고, AI 문구 생성/카카오 전송/전송 성공 이력 기록을 담당한다.
- PC 풀 클라이언트는 제거되고 웹+에이전트 통합 구조로 전환된 상태다.

권고:

- 에이전트 배포 산출물 버전과 웹 최신 배포 버전 `v2.5.0`을 함께 기록해야 장애 분석이 쉽다.
- `dist/` 산출물이 Git에 포함되어 있다면, 운영상 필요한지 확인하고 불필요하면 릴리즈 아티팩트로 분리한다.

### 3.4 DB 운영 도구

DB 운영 스크립트는 Python/PowerShell 조합이다.

관련 파일:

- `code/scripts/backup_db.py`
- `code/scripts/restore_db.py`
- `code/scripts/register_backup_task.ps1`
- `scripts/deploy-rules.ps1`
- `scripts/register-mine-task.ps1`
- `scripts/mine_note_tags.py`
- `scripts/mine_notify.ps1`

판단:

- DB 백업/복원, 보안 규칙 배포, 태그 마이닝/알림 작업까지 운영 자동화가 일부 구축되어 있다.
- `code/scripts/sa-key.json`이 존재하므로 서비스 계정 키 관리가 매우 중요하다.

권고:

- `sa-key.json`이 운영 비밀키라면 Git 추적 대상에서 제거하고 Secret Manager 또는 로컬 미추적 파일로 관리한다.
- 백업 파일 보관 위치, 보존 기간, 복원 절차를 운영 문서에 명확히 적는다.
- 보안 규칙 배포는 `scripts/deploy-rules.ps1`를 표준 경로로 정하고, 배포 전 rules dry-run 또는 emulator 검증 절차를 둔다.

## 4. 종합 평가

최신 배포 기준의 저장소는 Firebase 기반 웹 앱(`code/public/v2.5.0/`), Firebase Realtime Database, Cloud Functions, Python 기반 강사 에이전트, 카카오 전송 모듈이 결합된 구조다.

강점:

- 최신 배포 버전 `v2.5.0`을 기준으로 웹 앱 코드가 분리되어 있으며, 과거 버전 디렉터리로 릴리즈 이력과 롤백 단위를 확인할 수 있다.
- Firebase Hosting/Realtime Database/Functions 기반이라 별도 서버 운영 부담이 작다.
- DB 스키마 문서와 요구사항 문서가 존재해 변경 관리 체계가 있다.
- 에이전트, AI, 카카오 전송, 웹 입력 모듈이 분리되어 책임 경계가 보인다.
- 백업/복원/규칙 배포 스크립트가 있어 운영 자동화 기반이 있다.

주요 리스크:

- 운영 문서와 배포 체크리스트가 최신 배포 버전 `v2.5.0`을 기준으로 고정되어 있는지 확인이 필요하다.
- 인증 설정 파일과 서비스 계정 키로 보이는 파일이 저장소에 있어 비밀정보 관리 점검이 필요하다.
- 액션 로그가 업무 이력 중심이며, 관리자 변경/로그인/권한 변경 감사 로그 체계는 별도 확인 또는 보강이 필요하다.
- PT Talk라는 기능명과 실제 코드 모듈명이 직접 매핑되어 있지 않아 인수인계 문서가 부족할 수 있다.

우선 개선 순서:

1. 현재 운영/개발 기준 버전을 최신 배포 버전 `v2.5.0`으로 문서화한다.
2. `sa-key.json`, Firebase config, agent config의 비밀정보 포함 여부를 점검한다.
3. 로그인/회원/권한 매핑 문서를 `AUTH_DESIGN.md`와 `DB_SCHEMA.md` 기준으로 정리한다.
4. 관리자/강사 액션 로그 표준 노드를 설계한다.
5. 웹 최신 배포 버전 `v2.5.0`, 에이전트 버전, Firebase rules 버전을 하나의 배포 체크리스트로 묶는다.

