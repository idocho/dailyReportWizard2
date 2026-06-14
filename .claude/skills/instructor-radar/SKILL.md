---
name: instructor-radar
description: 강사(또는 전체) 담당 학생들의 역량 레이더(스파이더) 차트를 실저장 Firebase 데이터로 생성해 한 차트에 겹쳐(오버랩) 인터랙티브하게 보여준다. DailyReportAnalyzer의 5축 공식(학습태도·수업참여·자기주도·이해응용·성취성장)을 그대로 적용. "OO 강사 학생들 레이더/스파이더 차트 그려줘", "담당 학생 역량 비교 차트", "학생들 5축 오버랩 차트", "강사별 학생 차트" 등 강사·학생 단위 역량 레이더/스파이더 차트를 요청하면 반드시 이 스킬을 사용. obs 태그·성적 기반 학생 역량 시각화 전반에 적용.
---

# 강사별 학생 역량 레이더

특정 강사(또는 전체)가 담당한 학생들의 **역량 5축**을 실저장 데이터로 계산해, 한 스파이더 차트에 모든 학생을 **겹쳐(오버랩)** 그리고 평균을 강조한다. 범례 클릭으로 학생을 켜고/끄고, 호버로 한 명만 강조해 "누가 누군지" 구분한다.

5축: **학습태도 · 수업참여 · 자기주도 · 이해응용 · 성취성장** (각 0~100).

## 왜 이렇게 하나

- 레이더는 학생 간 강·약점 패턴을 한눈에 비교하는 데 강력하지만, 22명을 겹치면 스파게티가 된다 → **토글 + 호버 강조**로 읽힌다.
- 축 공식은 Analyzer 정본(`computeWindowData`)과 동일해야 리포트 화면과 수치가 일치한다. 그래서 자체 계산하지 않고 **미러 스크립트**(`scripts/compute_radar.js`)를 쓴다.

## 절차

### 1. 데이터 계산
`scripts/compute_radar.js` 실행 — Firebase에서 obs·scores·history·students 취합 후 5축 계산, JSON 출력.

```
node .claude/skills/instructor-radar/scripts/compute_radar.js "조이도"
node .claude/skills/instructor-radar/scripts/compute_radar.js --all
```

- 첫 인자 = 강사명(history의 instructor 필드로 학생 식별). `--all` = obs 있는 전체.
- 자격은 `code/dist/config.json`(firebase_url·path)에서 자동 해석. 읽기 secret 불요.
- stdout = `[{nameKey,name,N,attitude,engage,autonomy,understand,achievement,tests}, ...]` (세션수 N 내림차순).
- stderr 에 `[radar] … N명 계산` 진단. JSON만 파싱할 것.

출력을 파싱해 위젯용 배열로 변환: 각 학생을 `["이름", 학습태도, 수업참여, 자기주도, 이해응용, 성취성장]` 형태로.

### 2. 차트 렌더
`references/widget_template.html` 을 읽어 두 placeholder를 치환 후 `show_widget` 으로 렌더:

- `__DATA__` → 위 학생 배열의 JS 리터럴 (예: `[["김승헌",52,84,79,86,50],["이은호",66,80,77,80,50], ...]`)
- `__TITLE__` → 차트 제목 (예: `조이도 담당 22명`)

템플릿은 Chart.js 레이더 + 토글/호버/평균선이 이미 구성돼 있다. 코드를 새로 쓰지 말고 템플릿을 재사용한다(일관성·검증된 동작).

### 3. 해석 (응답 텍스트로)
차트는 위젯이 보여주므로 **중복 서술 금지**. 대신 응답 텍스트로 데이터 특징을 짚어준다:
- 평탄한 축이 있으면 원인(예: 성취성장 전원 50 = 성적 미연동 = 결측 중립).
- 눈에 띄는 저점이 **earned(실제 약점)** 인지 **결측 중립**인지 구분.
- 필요하면 특정 학생 1~2명 원본 태그 카운트로 드릴다운 제안.

## 결측=중립 원칙 (중요)

축은 모두 결측을 **중립**으로 처리한다(태도65·참여50·성취50·이해65). 그래서 "데이터 없음"이 레이더에 dent(찌그러짐)를 만들지 않고, 진짜 약점(earned 저점)과 시각적으로 구분된다. 평탄/중립 축이 보이면 결함이 아니라 **그 데이터가 없다는 정직한 신호** — 사용자에게 그렇게 설명한다.

## 공식 동기화 주의

`scripts/compute_radar.js` 의 축 계산은 `../dailyReportAnalyzer/analyzer.html` 의 `computeWindowData` 미러다(현재 ANALYZER 문서 v2.9 기준). **Analyzer 공식이 바뀌면 스크립트도 갱신**할 것. 축 정의 요약은 `references/radar_formulas.md` 참조. (태그는 웹 app-core.js·PC constants.py·Analyzer·이 스크립트 4곳에 정의되는 동기화 부채가 있음.)
