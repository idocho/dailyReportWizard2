# 역량 레이더 5축 공식 (요약)

`scripts/compute_radar.js` 가 구현하는 축 계산. **정본은 `../dailyReportAnalyzer/analyzer.html` 의 `computeWindowData`** — 이 문서·스크립트는 그 미러다. 정본이 바뀌면 둘 다 갱신.
기준: ANALYZER_REQUIREMENTS 문서 v2.9 (2026-06-14).

| 축 | 원천 | 산출 요지 |
|----|------|----------|
| ① 학습태도 | obs.condition − caution | condition 가중평균(great95~bad25) − (late·sleepy·chat·attitude 패널티). **condition 결측 시 중립 65**. slow·calc_miss·writeup_weak 무패널티 |
| ② 수업참여 | obs.engage | **결측=중립 50 baseline** + 태그보너스(question·deep_try·present·help, 최대 +50). 희소 positive-only 축이라 결측을 미참여로 처벌 안 함 |
| ③ 자기주도 | obs.assign_grade + 보조 | 과제평균×0.85 + autoBehavior(self_study·retry·legacy, cap15). **과제평균 = 전 과목-세션 평균**(`__hwAll`, 다과목 최악값 병합 금지) |
| ④ 이해응용 | obs.understand + 보조 | understand 가중평균(top95~hard28) + 보너스(self_solve·retry·mastered·process_good, cap15) − writeup_weak 감점(cap8). 결측 65 |
| ⑤ 성취성장 | scores/weekly·achievement | 0.6×백분위 + 0.4×원점수% + highlight보너스(perfect·improved·effort). **성적 결측 시 중립 50**. 단독응시 백분위 50 |

핵심 원칙(차트 "그럴듯"): 모든 축은 **결측=중립**으로 통일(태도65·참여50·성취50·이해65) — 결측이 dent를 만들지 않게. 약점은 earned 저점, 결측은 중립 → 시각적으로 구분됨.

폐기 태그(present·help·preview·error_fix·perfect·improved·attitude 등)도 공식·카운터에 유지 — 옛 데이터 호환(신규 데이터선 0 기여).
