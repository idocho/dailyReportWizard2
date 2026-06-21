# platform/ — 인증·플랫폼 재구성 작업 영역

신규 코드 격리 영역. **안정 코드(DRW·ClassManager) 미접촉** (PLATFORM_ARCHITECTURE §0).
설계: [AUTH_DESIGN.md](../documents/AUTH_DESIGN.md) · [PLATFORM_ARCHITECTURE.md](../documents/PLATFORM_ARCHITECTURE.md)

## 현재 산출물 (브랜치 endgame, 미배포)
| 파일 | 상태 |
|---|---|
| `synth_email.js` | 이름+캠퍼스 → 합성 이메일(로그인/계정생성 공용). **테스트 통과(15/15)** |
| `synth_email.test.js` | 순수 Node 테스트. `node platform/synth_email.test.js` |
| `../database.rules.v2.json` | 2차 룰 초안(auth+acl+campus). JSON 검증 완료. **미연결·미배포** |

## ⛔ 콘솔/오너 의존 블로커 (운영자만 가능 — 진행 전 필요)
로그인 UI 구현·실테스트는 아래가 선행돼야 함:
1. **Firebase Authentication 활성화** (콘솔 → Authentication → 이메일/비밀번호 사용)
2. **웹 앱 설정값 확보** (콘솔 → 프로젝트 설정 → 웹 앱): `apiKey`, `authDomain` 등
   — Firebase JS SDK / REST 로그인에 필요(apiKey 는 공개값).
3. (룰 자동검증용) **Java(JDK) 설치** — DB 에뮬레이터 구동 전제. 현재 미설치.

## 룰 테스트 계획 (에뮬레이터 가능 시 = Java 설치 후)
`@firebase/rules-unit-testing` + DB 에뮬레이터로 검증할 케이스:
- instructor: 자기 캠퍼스 read O / 타 캠퍼스 read X / input·obs·scores write O / students write X
- admin: 자기 캠퍼스 students·classes write O / 타 캠퍼스 X / acl 에 instructor 생성 O /
  **acl 에 admin·super 생성 X(권한상승 차단)** / 타 캠퍼스 acl X
- super: 전 캠퍼스 read·write O / acl 전체 O / schema_version write O
- agent: 자기 캠퍼스 sendJobs read + status write O / input·obs write X / 타 캠퍼스 X
- active:false: 모든 접근 즉시 X (토큰 유효해도)
- 비로그인(auth=null): 전부 X

## 다음 단계 (AUTH_DESIGN §8 / PLATFORM §5)
1. (블로커 해소 후) DRW web 로그인 모듈 — 캠퍼스 선택+이름+비번 → synthEmail → signInWithPassword
2. CampusManager 계정관리(발급/비활성·역할·캠퍼스) — 신규 프로젝트
3. 무중단 전환(구 OR 신 병행) → 룰 배포 → 시크릿 폐기
