# v2.6.1 생성 설정 검증 — 2026-10-04

배포하지 않고 로컬 소스만 검증했다. 실제 Firebase 쓰기·카카오톡 전송 없음.

## 통과

- Python 22건: `test_generation_preferences`, `test_message_quality`, `test_ai_model_config`, `test_gemini_model`.
- 5개 문체 모두 단건/일괄 프롬프트에 문체·개별 지침·상세 분량·과제 프리셋 전달.
- 자동 문체 해요체 보존, 문체 분석 오류 명시, 사용자 지정 분량 범위·기본값 처리.
- JS VM: 실제 `saveAiStyle` 실행, 가짜 DB에 문체·개별 지침·길이·목표 글자 수 저장. 79/801/123.5/NaN 목표 거부, 잘못된 입력 시 로컬·DB 저장 없음.
- JS VM: 실제 `_genCtx` 실행, 다과목 배열/객체형 추가 프리셋 합집합·중복 제거, 제외 교재의 프리셋 제외, 수행도 항목과 생성 요청 모두 포함.
- 변경 JS 두 파일 구문 검사 통과.

## 별도 실패

기존 `test_ai_engine` 3건은 Responses API 엔드포인트/응답/JSON 스키마를 기대한다. 현재 구현 및 HEAD는 Chat Completions를 사용한다. 응답 fixture 형태 차이로 `KeyError: choices` 2건, 미구현 `BATCH_RESPONSE_SCHEMA` 참조로 `AttributeError` 1건. 이 테스트를 삭제하거나 성공하도록 약화하지 않았다. Responses 마이그레이션 여부는 이번 생성 설정 수정 범위와 별도다.

## 미검증

실제 모델 호출을 준비했으나 `code/agent_config.json`(Claude), `code/dist/agent_config.json`(OpenAI) 모두 선택 엔진 API 키가 저장되어 있지 않아 호출 전 중단. 실제 분량 준수율·문체 차이·지침 및 프리셋 의미 보존은 아직 검증하지 못했다. 키/설정 내용은 로그에 출력하지 않았다.

실제 브라우저 화면 렌더링·실 Firebase 왕복·재빌드 실행 파일은 미검증. 현재 통과 결과는 프롬프트/설정/페이로드 계약 검증이며 실제 생성 품질 통과 판정이 아니다.

다음 실콜: 가상 학생으로 짧게/보통/자세히/직접 분량, 해요체 개별 지침, 따뜻·상세형, 일괄 생성, 입력 부족 사례를 비교. 실제 날짜·준비물·교재 미지참·채점 미실시 보존 및 환각 여부 확인 후 배포 판단.
