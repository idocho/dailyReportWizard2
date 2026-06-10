# DailyReportWizard2 — Claude 작업 지침

## 필수 규칙

### 요구사항 문서 동기화
**코드 수정 시 반드시 `documents/DRW_REQUIREMENTS.md`도 함께 업데이트.**

- 기능 추가/변경/삭제 → 해당 섹션 수정
- Firebase 구조 변경 → 섹션 5 업데이트
- 버그 픽스라도 동작 스펙이 바뀌면 반영
- 문서 버전(`문서 버전: X.X`) 및 변경 이력 테이블 항목 추가

### 목업 우선 원칙
**UI/UX 변경 작업 시 반드시 목업을 먼저 구현하고 사용자 확인을 받은 후 실 코드에 반영.**

- 사용자가 "목업 먼저", "mockup first", "화면 먼저 보여줘" 등을 명시하면 **실 코드 수정 금지**
- 목업 확인 전 실 파일(`app-*.js`, `app.css`, `index.html` 등) 변경 절대 금지
- 목업 승인 후에만 실 코드 반영 진행
- 목업 방법: 별도 HTML 파일 생성 또는 preview eval로 DOM 임시 조작 (소스 파일 미변경)

### 프로젝트 파일 위치
| 항목 | 경로 |
|------|------|
| **현재 개발 라인 (웹 수정은 여기만)** | `code/public/v2.2.3/` — JS `js/app-core.js`·`app-input.js`·`app-scores.js`·`app-settings.js`, CSS `css/app.css`, HTML `index.html` |
| 동결 버전 (수정 금지) | `code/public/v2.2.2/` 이하 전 버전 — 릴리즈 시 `scripts/new-version.ps1`로 동결 복제 |
| 버전 포털 | `code/public/versions.json` → `scripts/build-portal.ps1` 로 `code/public/index.html` 생성 |
| PC 앱 | `code/app.py`, `firebase.py`, `constants.py`, `ai_engine.py` 등 |
| 요구사항 문서 | `documents/DRW_REQUIREMENTS.md` |
| Analyzer 요구사항 | `documents/ANALYZER_REQUIREMENTS.md` |
| 공유 DB 스키마 정본 | `../ClassManager/documents/DB_SCHEMA.md` |
| 커리큘럼 원본 JSON | `code/public/v2.2.3/data/math-curriculum-2022.json` (버전 디렉터리 내 — 별도 `src/` 없음) |

### 버전 정책 (2026-06-11~)
- **DB 스키마 완전 하위호환 버전만 호스팅 공개.** 구버전은 `firebase.json` ignore + `/v최신/` 302 redirect
- 웹 변경은 항상 현재 개발 라인 디렉터리에만. JS/CSS 수정 시 `index.html` 캐시버스트 `?v=` 갱신
- 릴리즈: 개발 라인 안정화 → versions.json 라벨 갱신(안정판) → 다음 개발 라인 신설(`new-version.ps1`)

## 아키텍처 핵심 원칙

- `grade_sem` → 교재(`cfg.textbooks[tbName]`) 종속. 학급 종속 아님
- `pkey` 형식: `{classId}|{subject}` (예: `중1A|수학`) — `session/class_data/{pkey}` 키. web write + PC read 모두 2-part
- Firebase 쓰기: 웹 전용. PC 앱은 **PC 소유·웹 미사용 경로만** 허용 — `history/{nameKey}/`(전송 코멘트 누적) + 강사 등록(`config/instructors/{id}` 신규). `lastSent/`는 폐기됨(v2.1.2)
- `history/{nameKey}/{YYYY-MM-DD}` = `{note, instructor}` — 전송된 최종 특이사항 누적(학생 grain, 날짜키=todayKey). Analyzer가 obs/·scores/와 nameKey+date로 조인
- 전송 확정 시점(`_push_history`) PC 동작: ① `history/`에 최종 note 기록, ② **`input/{nameKey}/__note__` 소거**(원본 draft consume) — 특이사항을 "당일 소비"로 만들어 다음 가져오기 시 옛 메모 잔류 방지. PC의 input/ 쓰기는 이 소거(전송된 학생 한정)만 허용
- 특이사항(note)은 **학생 종속 단일**(과목 grain 아님). 입력 `input/{nameKey}/__note__`, 누적 `history/`. 과제수행도는 `obs/assign_grade`가 단일 소스(`input/.assign` 폐기)
- 로컬 캐시(daily_cache.json)는 **진도/과제(class_data)만** 영속. student/note/force는 메모리만(v2.1.2)
- 관리자 기능: `adminOn === true` 시만 렌더링

## 커뮤니케이션
- **caveman ultra 모드 기본 적용** — 세션 시작 즉시 `/caveman ultra` 활성화. "stop caveman" / "normal mode" 명령 전까지 유지.
