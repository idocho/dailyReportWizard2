---
description: 강사 노트(history/) 태그 마이닝 — build·세션내 분석·ingest 전 과정 1회 실행
---

강사 전송 노트에서 기존 obs 태그가 못 담는 반복 워딩을 발굴하는 주기 작업을 한 번에 수행한다.
LLM 분석은 **이 세션의 네가 직접** 수행한다(외부 API 호출·과금 없음, 수동 붙여넣기 없음).

인자(`$ARGUMENTS`): 비우면 마지막 실행 이후(증분), `--all` 전체, `--days N`/`--since YYYY-MM-DD` 가능.

## 순서

1. **build** — 프롬프트 생성:
   - `python scripts/mine_note_tags.py build $ARGUMENTS` 실행 (인자 없으면 그대로 `build`).
   - "분석할 노트 없음"이면 거기서 멈추고 사용자에게 알림(이번 기간 새 노트 없음).

2. **분석** — `documents/tag-mining/PROMPT.md`를 Read로 읽는다(크면 페이지로 나눠 전부 읽음).
   파일 안 [현행 태그]·[노트 모음]·출력 JSON 스키마 지침을 **그대로 따라** 분석한다:
   - 여러 학생·**여러 강사**에 걸쳐 반복되는 교육적으로 의미 있는 패턴만.
   - 단일 강사 복붙 문구·운영 공지·문체는 `ignore`. 기존 태그로 충분하면 `covered_by_existing:true`.
   - frequency는 실제 관찰 건수 근사. rationale에 어느 강사들에 걸쳤는지 명시.

3. **결과 기록** — 분석 JSON을 `documents/tag-mining/_result.json`에 Write →
   `python scripts/mine_note_tags.py ingest documents/tag-mining/_result.json` 실행 →
   임시 `_result.json` 삭제. (REPORT.md 누적·state.json 갱신은 스크립트가 처리)

4. **보고** — 사용자에게 표로 요약: 신규 후보(빈도순)·🚩승격 권고(streak≥3)·총평.

## 가드레일

- **태그를 자동으로 추가/승격하지 말 것.** 발굴·기록·보고까지만. 실제 태그 신설은 사용자가 결정한다.
  (신설 시엔 3곳 동기화: 웹 `app-core.js` TAGS·PC `constants.py` TAGS·`ai_engine.py` _*_TEXT + 캐시버스트 + exe 재빌드)
- PROMPT.md·_result.json은 학생 PII 포함 → gitignore 대상(이미 설정됨). REPORT.md·state.json만 커밋.
- 실행에 firebase url/path만 필요(읽기 secret 불요). 자격은 `code/dist/config.json`에서 자동 해석.
- 스크립트 출력이 깨지면(cp949) 무시 — 스크립트가 utf-8로 재설정함.
