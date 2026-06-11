# Firebase Security Rules 전환 계획 (#15)

**작성**: 2026-06-11 · **상태**: 준비 완료(코드/룰 사전 배선됨) — **전환 창 대기**

## 배경
- RTDB `dailyreportwizard-default-rtdb` 전체가 무인증 공개(read/write) — CRITICAL
- 무중단 전환 불가: 룰 배포 순간 시크릿 없는 클라이언트는 전부 차단됨
- 사전 작업(운영 무영향, 완료): 4클라 + 백업/복원 스크립트에 `?auth=` 옵션 지원 주입.
  시크릿 미설정 시 기존과 100% 동일 동작(no-op)

## 2단 전략
| 단계 | 시점 | 내용 |
|------|------|------|
| 1차 | 전환 창(반나절) | DB Secret을 4클라에 설정 + deny-by-default 룰 배포 → 공개 노출 봉인. 시크릿은 레거시 admin 토큰이라 룰 우회 |
| 2차 | CBT 종료 후 | Firebase Auth 승격(강사 신원 로그인, ADMIN_HASH 클라 게이트 대체) + 경로별 화이트리스트 룰 |

## 클라이언트별 시크릿 설정 위치
| 클라이언트 | 설정 키 | 입력 방법 |
|-----------|---------|----------|
| 웹 DRW (v2.2.3) | `drw_db_secret` (localStorage) | 설정 → Firebase 연결 → "DB 시크릿" 입력란 (태블릿마다 1회) |
| PC DRW | `config.json` → `firebase_secret` | 설정 다이얼로그 또는 config.json 직접 편집 |
| ClassManager | `config.json` → `dbSecret` | 설정 다이얼로그 또는 config.json 직접 편집 |
| Analyzer | `fbSecret` (localStorage, 연결 폼) | 접속 폼 "DB 시크릿" 입력란 |
| backup_db.py / restore_db.py | PC DRW `config.json` 재사용 | firebase_secret 자동 인식 |

시크릿 발급: Firebase 콘솔 → 프로젝트 설정 → 서비스 계정 → **데이터베이스 보안 비밀**(legacy token).
전달: 비공개 채널만(카톡 메모 ✕ 권장, 직접 입력). guide.html에 절대 게재 금지(#11 A2 연계).

## 전환 창 절차 (순서 엄수)
1. **백업 1회**: `python code/scripts/backup_db.py` 성공 확인
2. Firebase 콘솔에서 DB Secret 확보
3. **클라이언트 먼저 무장**(룰 배포 전 — 이 순서면 다운타임 0에 수렴):
   - PC DRW·CM의 config.json에 시크릿 추가, 앱 재시작 후 데이터 로드 확인
   - 운영 태블릿 웹앱 설정에 시크릿 입력, 새로고침 후 로드 확인
   - Analyzer 접속 폼에 시크릿 입력 확인
4. `schema_version` 노드 생성: `drw2_cbt/schema_version = 14` (DB_SCHEMA v1.4 ↔ 정수 14)
   ```
   curl -X PUT "https://dailyreportwizard-default-rtdb.firebaseio.com/drw2_cbt/schema_version.json?auth=SECRET" -d "14"
   ```
5. **룰 배포**: firebase.json에 `"database": { "rules": "database.rules.json" }` 추가 후
   `firebase deploy --only database`
6. **검증**:
   - 무인증 차단: `curl https://dailyreportwizard-default-rtdb.firebaseio.com/drw2_cbt/students.json` → `Permission denied` 확인
   - 유인증 통과: 같은 URL `?auth=SECRET` → 데이터 반환 확인
   - 웹 입력→전송, CM 명단 조회, Analyzer 리포트, backup_db.py 각 1회 스모크
7. exe 재빌드 불필요(이미 시크릿 지원 빌드라면). 미지원 구 exe 사용 중이면 교체 먼저

## 롤백
콘솔(Realtime Database → 규칙)에서 `.read/.write: true`로 임시 복원 → 원인 해결 후 재배포.
firebase.json의 database 항목 제거하면 이후 `firebase deploy`가 룰을 건드리지 않음.

## schema_version 정책
- 노드: `{dbPath}/schema_version` = 정수(스키마 v1.4 → `14`)
- 클라 기동 시 1회 읽어 `지원 최대치 < 노드값`이면 경고/차단("앱 업데이트 필요")
- 노드 부재 = 통과(전환 전 DB 호환). 읽기 실패(네트워크) = 통과(가용성 우선)
- 스키마 호환 깨지는 변경 시: DB_SCHEMA.md 버전업 + 노드값 증가 + 클라 상수 동반 갱신

## 주의
- `database.rules.json`은 전환 창 전까지 firebase.json에 연결하지 않는다
  (`firebase deploy` 오발 배포 → 전 클라 차단 사고 방지)
- 웹은 시크릿을 localStorage에 보관 — 공개 JS에 하드코딩 금지
- 2차(Firebase Auth) 화이트리스트 스케치는 database.rules.json 주석 참조
