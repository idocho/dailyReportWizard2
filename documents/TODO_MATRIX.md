# DRW 생태계 TODO 매트릭스

_최종 갱신: 2026-06-22 · 3-repo (dailyReportWizard2 / CampusManager / dailyReportAnalyzer)_

## 트리거(시점) 범례
| 표시 | 의미 |
|---|---|
| 🟢 NOW | 지금 가능 — 블로커 없음 |
| 🔵 CUTOVER | **개발 완료 후** 보안 컷오버 묶음(클론 DB) |
| 🔴 BLOCKED | 외부 조건 대기 |
| ⚪ LATER | CBT 종료 후 (구조 부채·보류) |

영역: 웹=DRW 웹 / PC=DRW PC앱 / CM=CampusManager / AGENT=전송 에이전트 / ANL=Analyzer / DB=공통·인프라 / DOC=문서

---

## 📊 repo × 시점 매트릭스

| 영역 | 🟢 NOW | 🔵 CUTOVER (개발완료 후) | 🔴 BLOCKED | ⚪ LATER (CBT후) |
|---|---|---|---|---|
| **DRW 웹** | — | 설정 dbUrl·apiKey 교체 · Auth 강제 | — | 전역상태 store 캡슐화 |
| **DRW PC** | v2.5.0 exe 재빌드·배포 | constants.py dbUrl·apiKey 교체 | — | app.py 분할(2478 LOC) |
| **CampusManager** | CSV import · 템플릿 DB관리 | firebase-config 교체 | Cloud Functions(비번리셋·삭제)=Blaze | app.py 분할(1421) · 테스트 복구 |
| **전송 에이전트** | exe 패키징+자동시작 · 자동정리(done) | agent 계정+자격 암호화 · config dbUrl 교체 | — | — |
| **Analyzer** | — | 로그인 전환(read Auth) | — | 차트 테마 파라미터화 · 레이더/태그 감사 |
| **공통·DB** | — | **클론 DB 생성·룰 배포·Auth강제·마이그레이션·기존DB 폐기** | reorganize_semester(엑셀 대기) | REST 5중 통합 · 구형 과목키 |
| **문서** | REQUIREMENTS v2.5 이력 · guide URL 제거 | — | — | — |

주기(공통): 일일 DB 백업 · 노트→태그 마이닝

---

## 상세 (시점별 풀이)

## 🟢 NOW — 지금 가능
| 작업 | 영역 | 비고 |
|---|---|---|
| DRW_REQUIREMENTS v2.5 변경이력 갱신 | DOC | 코드 수정 시 문서 동기화 규칙 |
| 에이전트 자동 정리(오래된 done 삭제) | AGENT | 선택 기능 — 현재는 수동 "완료 정리" |
| guide.html 실DB URL/경로 복사버튼 제거(#11) | DOC/DB | 비공개 전달로 전환 |
| 에이전트 exe 패키징(CampusAgent.exe)+로그인 자동시작 | AGENT | PyInstaller, 작업 스케줄러 |
| PC앱 v2.5.0 exe 재빌드+배포 | PC | 로그인 전환 반영본 |
| CSV import | CM | 명단 대량 입력 |
| 전송 템플릿 DB 관리 | CM | 현재 코드 상수 TPL |

## 🔵 CUTOVER — 개발 완료 후 (보안 묶음, 한 번에)
| 작업 | 영역 | 비고 |
|---|---|---|
| 새 클론 DB 생성 | DB | 새 프로젝트 vs 새 인스턴스 — 결정 필요 |
| Security Rules 배포(deny-by-default + acl 화이트리스트) | DB | `database.rules` 초안 존재, firebase.json 미연결 |
| Firebase Auth 강제 | DB | 로그인은 이미 구현됨(웹·PC·CM) |
| 설정 교체(dbUrl·apiKey) | 웹·PC·CM·AGENT | firebase-config.js·constants.py·config.json |
| CBT 테스터·실데이터 마이그레이션 | DB | acl/Auth + obs/scores/history/students |
| agent 계정(acl role:agent)+자격 DPAPI 암호화 | AGENT | 룰 적용 후 |
| Analyzer 로그인 전환 | ANL | read-only Auth |
| 기존 오픈 DB 잠정 폐기 | DB | **컷오버 최종 단계** |

## 🔴 BLOCKED — 외부 조건 대기
| 작업 | 영역 | 대기 조건 |
|---|---|---|
| Cloud Functions 배포(비번 리셋/계정 삭제) | CM/DB | Firebase **Blaze 요금제** |
| reorganize_semester.py 부트스트랩(#13) | DB | **새학기 정의표 엑셀** 입수 |

## ⚪ LATER — CBT 종료 후 (구조 부채·보류)
| 작업 | 영역 | 비고 |
|---|---|---|
| app.py 갓클래스 분할 | PC/CM | DRW 2478 / CM 1421 LOC |
| Firebase REST 5중 복제 통합 | 전역 | 설정키 발산 중 |
| 웹 전역 가변상태 → store 캡슐화 | 웹 | |
| CM 테스트 ImportError 복구 | CM | |
| Analyzer 차트 다크/라이트 테마 파라미터화 | ANL | 4쌍 복붙 |
| 레이더 formula 감사 + 태그 3중 정의 부채 | ANL | [[analyzer-stat-audit]] |
| 구형 과목 키 8개 | DB | 개편 시 자연 소멸 |

## 🔁 주기 작업
| 작업 | 영역 | 비고 |
|---|---|---|
| 강사 노트→태그 마이닝 | 도구 | [[note-tag-mining]] build/ingest 주기 실행 |
| 일일 DB 백업(매월1일 영구) | DB | scripts/backup_db.py — 룰 전 유일 안전망 |

---

## ✅ 이번 세션(2026-06) 완료 — 참고
인증 로그인(웹·PC·CM) · 역할 3단(admin/manager/instructor) · DPAPI 키 암호화 · 평문키 제거 ·
캠퍼스 경로 분리 · CampusManager(계정·명단·전송) · 반 삭제/이름변경(cascade) · 통합 앱 아이콘 ·
전송 이미지 첨부+실시간 상태 · 에이전트(이미지·per-recipient·SSE·GUI 오버레이·SmartWait) ·
대기작업 취소+완료 일괄정리 · 전송 탭 3칼럼 레이아웃 · **실 카톡 발송 검증 완료**
