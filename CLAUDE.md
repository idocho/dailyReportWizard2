# DailyReportWizard2 — Claude 작업 지침

## 필수 규칙

### 요구사항 문서 동기화
**코드 수정 시 반드시 `documents/DRW_REQUIREMENTS.md`도 함께 업데이트.**

- 기능 추가/변경/삭제 → 해당 섹션 수정
- Firebase 구조 변경 → 섹션 5 업데이트
- 버그 픽스라도 동작 스펙이 바뀌면 반영
- 문서 버전(`문서 버전: X.X`) 및 변경 이력 테이블 항목 추가

### 프로젝트 파일 위치
| 항목 | 경로 |
|------|------|
| 웹 PWA JS | `code/public/js/app.js` |
| 웹 PWA CSS | `code/public/css/app.css` |
| 웹 PWA HTML | `code/public/index.html` |
| 요구사항 문서 | `documents/DRW_REQUIREMENTS.md` |
| Analyzer 요구사항 | `documents/ANALYZER_REQUIREMENTS.md` |
| 커리큘럼 원본 JSON | `src/math-curriculum-2022.json` |

## 아키텍처 핵심 원칙

- `grade_sem` → 교재(`cfg.textbooks[tbName]`) 종속. 학급 종속 아님
- `pkey` 형식: `{sheet}|{cls}|{tb}` (예: `M|중1A|최상위수학`)
- Firebase 쓰기: 웹 전용. PC 앱은 `lastSent/` + 강사 등록만 허용
- 관리자 기능: `adminOn === true` 시만 렌더링

## 커뮤니케이션
- **caveman ultra 모드 기본 적용** — 세션 시작 즉시 `/caveman ultra` 활성화. "stop caveman" / "normal mode" 명령 전까지 유지.
