# DailyReportWizard — 요구사항 명세서

**Crafted by IDO(idocho@kakao.com) · Powered by Claude AI**  
**문서 버전**: 8.89 · **앱 버전**: v2.5.0(정식·전면도입) · **최종 수정**: 2026-06-26

> Firebase 스키마 전체 명세: [DB_SCHEMA.md](DB_SCHEMA.md) (구 ClassManager에서 이관)

---

## 변경 이력

| 문서 버전 | 날짜 | 주요 변경 |
|-----------|------|-----------|
| 8.89 | 2026-06-26 | **결석 전용 버튼 독립 (프리셋 비종속)**. 결석 하드 차단이 '결석' 프리셋 존재에 의존 → 강사가 프리셋에서 빼면 무력화되던 문제. 결석을 과제 행 맨 앞 **전용 버튼**(빨강 테마 `.tg-absent`, 항상 노출)으로 분리. 클릭=`onAssignTag` 재사용(저장은 `assign_tags['결석']` 유지 → AI·리포트 호환), 선택 시 `si-absent` 하드 차단 그대로. 추가 프리셋(`apBtns`) 렌더에서 '결석' 제외(중복 방지). 웹 v318·CSS v20260640. |
| 8.88 | 2026-06-26 | **관리 메뉴를 관리자 모드 종속으로 (강사 모드 시 숨김)**. `_isMgr()`(신원)만으로 사이드바 '관리'(학생 명단·강사 계정)를 노출해 매니저가 **강사 모드인데도 관리 메뉴가 보이던** 문제. 모드 메타포 일치 위해 `_isMgr()&&adminOn`으로 게이트 — 강사 모드=관리 메뉴 숨김, 관리자 모드=노출. 운영자(super)는 adminOn 고정이라 항상 노출. renderStudents·renderAccounts 가드도 `_isMgr()&&adminOn`(강사 모드 전환 시 해당 탭이면 입력으로 복귀). 웹 v317. |
| 8.87 | 2026-06-26 | **초기화 버튼 먹통 수정 + 결석 하드 차단**. ① **초기화 오작동**: 설정 초기화 탭이 탭(`stg-pane`)으로 렌더되는데 `_resetToggle`이 죽은 구 아코디언(`#sa-reset .sa-body`)을 갱신 → 카드 선택·실행버튼 활성화가 **전 역할에서 먹통**이었음(데이터 토글은 됐으나 화면 미반영). `_resetToggle`을 `.stg-pane[data-stg="reset"] .stg-card-b` 우선 갱신으로 교정. 추가로 일반(강사 단위) 초기화 항목은 `instructor.assignments` 기준이라 담당수업 없는 **운영자(super)에겐 no-op** → 담당수업 0이면 일반 항목 미노출(운영자는 전체 항목만). ② **결석 하드 차단**: 학생 과제 행에서 `결석` 프리셋 선택 시 그 학생 카드의 나머지 입력 버튼(수행도·컨디션·이해도·참여·주의·시험) 전부 **비활성**(`pointer-events:none`+흐림), 메모·결석 버튼만 허용 — 결석 학생에 다른 항목 실수 입력 방지. `si-absent` 카드 클래스(renderInput 초기 + onAssignTag 토글 동기화), CSS `.si-card.si-absent`. 웹 v315·CSS v20260639. |
| 8.86 | 2026-06-26 | **CM 웹앱 은퇴 — 통폐합 완료(P4-A)**. 기능 패리티 확인 후 CampusManager 웹앱 폐지: ① **계정 관리**(발급·활성/비활성·역할변경·리셋·삭제, 운영자 크로스캠퍼스) DRW `renderAccounts`로 동등 ② **학생 명단**(반/학생 CRUD·M/T·무소속·이름변경 migrate) DRW `renderStudents`로 동등 ③ **일괄전송 캠퍼스 전체** = 매니저가 관리자 모드 시 `activeAsgns` 전 학급 확장으로 달성(P3 사실상 해소) — 무소속 학생 공지는 불요로 확정. CM 단독 기능 0. **조치**: (1단계) `CampusManager/firebase.json` catch-all 302 리다이렉트 배포 → (2단계, 사용자 요청) **`gritptmanager` 호스팅 사이트 영구 삭제**(`firebase hosting:sites:delete`, 서브도메인 해제·비가역). 현재 `gritptmanager.web.app`=**404**, 프로젝트 hosting 사이트는 `dailyreportwizard` 단독. CM 소스는 git 보존(repo의 firebase.json은 삭제된 site 참조하는 사문 — repo 동결). DB/Auth/Functions는 DRW와 동일 프로젝트 공유라 **미접촉**(hosting만). 통합 에이전트는 이미 단일화(8.70). **남은 정리**: 없음(통폐합 종결). |
| 8.85 | 2026-06-26 | **캠퍼스 목록 데이터화 — 추가 시 코드 변경 불요(취약점 개선)**. 로그인 캠퍼스 드롭다운이 DRW·CM index.html에 하드코딩(`<option value="dongsuwon">`)돼 캠퍼스 추가마다 코드 수정·재배포 필요했음. ① **공개읽기 `campuses` 노드** 신설(룰): `campuses/{slug}={name,order?,active?}`, `.read:true`(로그인 *전* 표시라 무인증 필요·캠퍼스명은 비민감), 쓰기는 admin/super만. ② **DRW 로그인 게이트**가 무인증 REST로 `campuses.json` 로드해 드롭다운 동적 생성(active≠false, order 정렬), 실패 시 기본 옵션 폴백(로그인 불능 방지). ③ 시드 `campuses/dongsuwon={name:"동수원",order:1}`. **검증**: 무인증 campuses 읽힘·acl/campus는 여전히 401(과개방 없음)·게이트 정상 렌더. 이후 캠퍼스 추가 = **DB 항목 1개**(운영자가 콘솔/CLI) + 운영 셋업(계정·명단·에이전트·카톡방). 룰은 `$campus` 와일드카드라 변경 불요. CM 드롭다운은 미변경(통폐합 대상). **남은 코드 약점**: 없음(드롭다운 해소). |
| 8.84 | 2026-06-26 | **운영자(super) 로그인 버그 수정 + 운영자 관리자모드 고정**. ① **버그**: 역할체계 instructor<manager<admin<super 중 `super`가 DRW 로그인 게이트 allowRoles(`['instructor','manager','admin']`)에 누락 → `auth.js`가 super 계정 로그인 거부(통폐합 P1/8.81부터). allowRoles에 `'super'` 추가(index.html). ② **운영자=관리자모드 고정**: admin/super는 담당수업 없는 순수 운영 계정 → 강사 모드 무의미. `_isTopAdmin()`(app-core) 신설, `init()`에서 운영자면 `adminOn=true` 기본, 사이드바 강사⇄관리자 토글은 **manager 전용**(`_isMgr()&&!_isTopAdmin()`)으로 운영자에겐 미노출(아바타 앰버+"전체 수업(관리자)" 라벨로 표시). 설정 시스템탭 안내문도 분기(운영자="항상 관리자 모드"). 웹 v314. CM 미변경(요청). |
| 8.83 | 2026-06-26 | **관리자 모드 = 공유 암호 → 매니저 신원 토글 (사이드바 강사⇄관리자 스위치)**. 기존 `adminOn`은 공유 SHA-256 암호(`config/admin_hash`·`ADMIN_HASH` 폴백)로 강사 누구나 셀프 승격 가능 — 클라 전용 latch라 보안벽 아니고 귀속추적 흐림. 신원 단일축으로 전환: ① **사이드바 모드 스위치**(`renderSb`, 신원블록 아래) — `_isMgr()`(매니저/운영자)에게만 세그먼트 토글 `👤 강사 | 🛠 관리자`, `setAdminMode(on)`(app-core)이 **암호 없이** `adminOn` 플립. **기본 강사 모드**(adminOn=false)로 로그인 → 담당수업 있는 매니저도 본인 반만 보다가 1클릭 전환. 관리자 모드 시 아바타·라벨·힌트 **앰버**(권한상승 신호). 일반 강사는 토글 미노출. ② **암호 경로 폐기**: `toggleAdmin`·`changeAdminPw`·`hashPw`·`ADMIN_HASH`·`config/admin_hash` 전부 제거. 설정 시스템탭의 관리자 토글/암호변경 버튼 제거(사이드바 안내문 대체), 죽은 `SA_FOOT` 삭제. ③ adminOn 게이트 기능(전체수업 접근·휴지통·시험 전체삭제·과목/교재 마스터·dev 도구)은 **불변** — 진입만 신원 기반으로. md-sw CSS. 웹 v313·CSS v20260638. **효과**: 명단 권한 A안과 동일 철학(공유암호→신원), 보안·감사 개선, 관리자 UX 향상(로그인 1회·새로고침 무관 아닌 세션 토글). |
| 8.82 | 2026-06-25 | **통폐합 P2(학생 명단 탭) + 명단 편집 권한 매니저 신원 전용 + 클로드 일괄 파싱**. ① **학생 명단 탭**: CM 2-pane roster UI를 DRW 사이드바 「🏫 학생 명단」(`_isMgr`)으로 실이식 — `renderStudents` 자체완결 모듈(`_rs` state, `fbGet`으로 `students`/`classes` 직접 로드), M/T 그룹 토글·반 리스트(카운트 배지)·⚠무소속·학생 테이블(출결번호/이름/반)·편집/반에서빼기(✕)/영구삭제·반 추가/이름변경/삭제. 반 이름변경=`_rsMigrate`(classes·students·session/class_data·scores·강사배정 일괄 이동, CM `migrateClassKey` 포팅). 삭제 안전(반소속=무소속 이동, 무소속만 영구삭제). `_rsSyncConfig`로 인메모리 `config._classStudents`·사이드바 일관성. 스키마 공유(`students/{key}={name,class}`·`classes/{id}={group,courses}` courses 보존). rs-* CSS. ② **설정 명단 정리**: 설정→학급·학생 패널은 **과정/교재 바인딩 전용**, 학생 칩 조회만(클릭편집·+추가 제거). 고아 함수 6개(addStuModal/editStu/saveStu/rmStu/_allStudentKeys/_clsOptions) 삭제. ③ **명단 편집 권한 = acl 매니저 신원 전용**(A안): `_rosterAdmin()`을 `adminOn‖_isMgr`→**`_isMgr`만**으로. 공유 관리자 암호(adminOn)로는 학급·학생 편집 불가(명단 소유권 분리 복원). adminOn은 전체수업접근+과목/교재/과정 관리 유지. ④ **[에이전트] 클로드 일괄 생성 JSON 파싱 견고화**: `generate_batch`가 ```펜스만 제거→`[`~`]` 배열만 추출(서두/후미 산문 무시)+파싱실패 명확한 에러, max_tokens 4096→8192(360*N+600). `build_batch_prompt` 순수JSON 지시 강화. 웹 v311·CSS v20260637. **남은 통폐합**: 일괄공지 매니저 전캠퍼스(P3 계획없음)·CM 은퇴(P4 미정). |
| 8.81 | 2026-06-25 | **세션 유지 선택제 + CM→DRW 통폐합 Phase 1(강사 계정 관리)**. ① **세션**: Firebase 기본 무기한 로그인 → `auth.loginByName(...,remember)`가 미체크 시 `browserSessionPersistence`(브라우저 닫으면 만료→재로그인), 체크 시 `browserLocalPersistence`+아이디 prefill 저장(`drw_login`). 비번은 브라우저 비밀번호관리자 위임. 로그인 게이트에 "로그인 유지" 체크박스. auth.js import `?v=3`. ② **통폐합 P1**: CM 강사 계정 관리를 DRW로. index.html이 acl `role`·`campus`·`uid`를 `drw_instr`에 주입 → `_isMgr()`(manager/admin/super)로 사이드바 "👥 강사 계정"·메인 분기. `auth.js`에 `callFn`(getFunctions/httpsCallable, asia-northeast3)+`window.__drwCallFn`. `app-settings.renderAccounts`(발급=createInstructor·비활성/역할=acl REST PUT·리셋/삭제=Functions, 매니저=자기캠퍼스 강사·운영자=전체). CSP에 cloudfunctions·run.app. 웹 v301. **남은 통폐합**: 학생 명단 CRUD(P2)·일괄공지 매니저 전캠퍼스 범위(P3)·CM 은퇴 리다이렉트(P4). |
| 8.80 | 2026-06-25 | **DRW 일괄공지 ↔ CM 일괄전송 UX 통일 (베스트-오브-보스, 목업 승인)**. 기능 동일(범주만 다름: DRW=본인 담당 반 / CM=캠퍼스 전 반)인데 UX 갈라진 부채 해소. 통합 사양: 디렉토리 트리(반 3-state 체크박스 indeterminate·접기·기본 전체선택→예외 해제·전체선택/해제·촘촘 행) + 작성(템플릿·**변수 삽입버튼** {이름}/{반}/{날짜}·이미지 첨부+이미지먼저 체크박스·미리보기) + 독립 **전송 모니터**. **DRW**(app-report.js): 반 체크박스 tristate(`_bulkSyncCls` data-clsbox, 개별토글 시 트리 미재렌더로 동기화)·renderBulk 진입 시 기본 전체선택·전체선택/전체해제 버튼·`.rp-stu` 행 8→5px(웹 v297·CSS v20260630). **CM**(app.js): 작성부 변수 삽입버튼 추가(캐시 v22). 두 화면 조작감 일치(코드는 repo 분리라 사양만 동기화). |
| 8.79 | 2026-06-25 | **자가 계정생성 차단 — 발급을 Cloud Function으로 일원화**. 온보딩 점검: DRW는 자가가입 없음(로그인만, 위저드 폐지)이나, CM `provision.createInstructor`가 **공개 `accounts:signUp`** REST를 써서 apiKey만으로 누구나 자가 계정생성 가능(합성이메일 선점·정크 위험)이 구멍이었음. `functions/index.js`에 `createInstructor`(onCall, `admin.auth().createUser`+acl, 권한검증: admin=전캠퍼스·강사/관리자, manager=자기캠퍼스·강사만, 합성이메일 동일규칙) 추가. CM `app.js` 계정발급을 `A.callFn('createInstructor')`로 전환(provision.createInstructor는 dead, CM 캐시 v19). 함수 4개 배포(서울). **남은 콘솔 작업**: Authentication→설정→사용자 작업→**"가입 사용 설정" 해제**(자가가입 차단) — 이후엔 인증된 관리자(함수)만 계정 생성. (migrate_instructors.py는 signUp 의존이라 차단 후 미동작 — 1회성이라 무방) |
| 8.78 | 2026-06-25 | **DRW에서 강사 관리 일괄 제거 (이중 관리 방지, 웹 v296)**. 강사 생성·전환·삭제·신규등록을 CampusManager 전담으로 일원화 → DRW `app-settings.js`서 제거: 설정 탭 `강사(instr)` 탭·pane·`_valid`/adminOn 게이트 항목, dead였던 `instrMgmt` 아코디언 const, `loadInstrsSection`·`createI`·`switchInstr`·`rmInstr`·`closeIM`(iModal), 그리고 수동 계정 조회/등록 `lookupInstr`·`_registerInstr`(로그인 게이트가 신원 주입하므로 불요, 이름만으로 신원 전환되던 우회 소지도 제거). 프리셋 헬퍼(`_HARDCODED_PRESETS`·`_defaultPresets`)는 초기화서도 쓰여 보존. 강사 본인 프로필(담당수업·문구·AI문체) 자가편집은 유지. config/instructors는 로그인 강사가 설정 저장 시 lazy 생성. |
| 8.77 | 2026-06-25 | **CM 강사 비번 리셋·삭제 활성화 — Cloud Functions 백엔드**. 브라우저는 남의 Auth 비번변경·계정삭제 불가(Admin 필요) → CM 웹 버튼이 `disabled`였음. 기존 작성돼 있던 `functions/index.js`(onCall: `resetInstructorPassword`·`deleteInstructor`·`clearMustChangePw`, requireAdmin로 admin/super+동일캠퍼스 검증, 서울 리전) 배포 연결. `firebase.json`에 `functions.source` 추가. CM `auth.js`에 `callFn`(getFunctions/httpsCallable, asia-northeast3), `app.js` 계정행 버튼 활성화(isTop=운영자 한정, reset=genPw 임시비번 토스트·삭제=확인 후 호출), CSP connect-src에 `*.cloudfunctions.net`·`*.run.app` 추가, 캐시 v17. **전제: Blaze 요금제**(사용 무료 한도, 카드 등록). 배포: DRW repo서 `firebase deploy --only functions` + CM hosting 재배포. |
| 8.76 | 2026-06-25 | **백업/복원 서비스 계정 인증 전환 (잠금 후 백업 복구)**. DB 잠금 후 `backup_db.py`(루트 GET)·`restore_db.py`(PUT)가 무인증이라 **401로 깨짐**(시크릿 미설정). 루트 read/write는 룰상 사용자 토큰 불가 → **서비스 계정(Admin, 룰 우회)** 필요. 공용 모듈 `scripts/_fb_auth.py` 신설: `auth_param(cfg)` = ① `sa-key.json`(또는 `config.service_account_path`)+`google-auth`로 OAuth2 `access_token` ② 레거시 시크릿 `auth=` 폴백 ③ 없으면 에러. backup=루트 전체(`/`) 스냅샷(campus·acl·sendJobs 등, `backup_path`로 변경 가능), restore=루트 기준(firebase_path 접두사 제거 — 루트 백업 정합). `sa-key.json`·`*serviceAccount*.json` gitignore. **운영**: 콘솔서 서비스계정 키 발급→`code/scripts/sa-key.json` 배치 + `pip install google-auth` 하면 일일 백업 재가동, 이후 레거시 시크릿 비활성화 가능. |
| 8.75 | 2026-06-25 | **에이전트 버전 0.92** — `AGENT_VERSION`·산출물명(`DRW-AI-Agent-0.92.exe`)·웹 `AGENT_DL`·guide·CM agent README 동기화(웹 JS v295). 릴리스 에셋 교체(0.91 삭제, DL 200). 직전 엔진별 키 분리 저장 포함. |
| 8.74 | 2026-06-25 | **에이전트 AI 엔진별 키 분리 저장**. 기존: 설정창이 선택 엔진 키 1개만 `fields`에 담아 저장 → `write_agent_config`가 파일 전체 교체라 **다른 엔진 키·smartWait 유실**(엔진 전환 시 재입력). 수정: `agent_gui` 설정창에 엔진 드롭다운 `<<ComboboxSelected>>` 바인딩(`_on_eng_change`) — 입력칸 키를 이전 엔진에 보관하고 새 엔진 저장 키 로드. `_eng_keys`에 gemini/claude/openai 키 전부 보유, `_save_setup`이 기존 config(`self.cfg`, smartWait 등) 보존하며 엔진별 키 전부 기록(빈 값 제거). 활성 엔진 키는 `_call_ai_hub`가 `cfg[ai_engine_type]_api_key`로 선택(불변). 라운드트립 검증(3엔진 키+smartWait 보존). exe 재빌드·재업로드. |
| 8.73 | 2026-06-25 | **v2.5.0 전면 도입 — 구버전 접근 경로 전부 제거**. 보안 잠금 후 구버전(v2.0.5~v2.4.0)은 무인증·`drw2_cbt` 경로라 잠긴 DB 접근 불가(죽은 화면) → 접근 차단. `firebase.json`: ignore에 v2.2.2/v2.2.3/v2.3.0/v2.4.0 추가(호스팅서 제거, 파일 87→23), redirect 전부 `/v2.5.0/`로 변경 + v2.2.2~v2.4.0·**루트 `/`** 추가(11개 경로 302). `versions.json` v2.5.0 단일(정식). 검증: `/`·`/v2.4.0/`·구버전 deep path 전부 302→`/v2.5.0/`, `/v2.5.0/` 200. **잔여 보안 권고**: 레거시 DB 시크릿(`?auth=secret`은 룰 우회) Firebase 콘솔서 비활성화 — 단 `backup_db.py`/`restore_db.py`가 시크릿 의존이라 서비스계정 토큰 전환 후 봉인. AI 실명 가명화·미성년 동의도 잔여. |
| 8.72 | 2026-06-25 | **🔒 보안 룰 cutover 실행 — DB 잠금 라이브(최대 위협 해소)**. v2.5 이래 개방돼 있던 DB를 Firebase Auth+acl 룰로 잠금. `firebase.json`에 `database.rules`=`database.rules.v2.json` 연결 → `firebase deploy --only database`. **검증**: 무인증 루트 read **200→401 "Permission denied"**(acl 포함 차단), 라이브 에이전트 **"로그인 OK 보안 토큰 사용"** + **AI 생성·카톡 전송 E2E 성공**(genJobs/sendJobs 쓰기 규칙 라이브 검증) 확인. 웹 v294 동반 배포(401 재시도 훅). 롤백 자산 `database.rules.open.json` 보유(30초 복구). ⚠️ **운영 주의**: 기존 강사 6명 에이전트는 **신규 exe 업데이트 + 웹 비번 입력 전까지 잠금 후 동작 불가**(다음 접속 시 무장 필요) — 현재 단독 테스트라 수용. 매니저 캠퍼스 일괄공지(root sendJobs)·CM 웹도 manager/admin 토큰으로 동작. |
| 8.71 | 2026-06-25 | **보안 룰 cutover 준비 — 에이전트 인증·룰 보완·웹 토큰재시도 (배포 전 단계, 라이브 룰 미반영)**. 최대 위협=DB 전면 개방(무인증 read 200 검증) 닫기 위한 선결 작업. ① **에이전트 로그인**: `agent_auth.py`(웹 synth_email·auth.js 파이썬 포팅 — `synth_email`/`sign_in`/`refresh`/`TokenManager`, JS와 바이트동일 검증). 설정창에 "웹 로그인 비밀번호" 입력(선택) → DPAPI 암호화(`secret_codec` SENSITIVE_KEYS에 `login_password` 추가) → 강사 본인 계정으로 idToken 발급, `process_once`/`write_heartbeat`에 토큰 전달. **무중단 안전장치**: 비번 미설정·로그인 실패 시 `token()`→None→무인증 폴백(룰 미배포 동안 기존 에이전트 무중단). ② **룰 보완**: `database.rules.v2.json` campus 하위에 `genJobs`/`sendJobs`/`agents` 쓰기 규칙 누락분 추가(강사=본인 키 소유권 검증, manager=캠퍼스, admin=전역). 미보완 시 잠금 후 리포트 생성·전송·하트비트 전멸이라 필수. `_lookup_role`이 uid 있으면 `acl/{uid}` 직접 조회(룰 호환). ③ **웹 토큰만료 재시도**: `app-core` fb헬퍼가 401/403 시 `window.__getFreshToken__`(index.html, getIdToken 재발급)으로 1회 재시도(웹 v294). ④ 에이전트 재빌드(`agent_auth` 번들)·재업로드. **미실행(최종 go 대기)**: 라이브 룰 배포·웹 v294 배포 — 검증 후 수동. |
| 8.70 | 2026-06-25 | **에이전트 단일화 — DRW + CampusManager 공용**. CM 전용 에이전트(`CampusManager/agent/`의 send_agent·agent_gui·kakao_send 복붙본, DRW 대비 stale)를 폐지하고 **DRW AI Agent 하나로 통합**. `agent_worker`: ① `process_sendjobs` 일반화(`base`/`claim_id` 파라미터, 수신자 `msg` 없으면 `job.body`를 `{이름}/{반}/{날짜}` 치환 `render`로 생성) ② `process_campus_sendjobs`(루트 `sendJobs/{campus}` 큐) ③ `_lookup_role`(acl에서 campus+instructorId 매칭 역할 조회, 프로세스 캐시) ④ `process_once`가 역할 `manager/admin/super`면 캠퍼스 일괄공지 큐도 처리(일반 강사는 미폴링·비노출 — 공지 가능자는 전 톡방 입장 매니저 소수). 다중 매니저 경쟁은 status 필터(1차)+sender 선점 사전/사후 확인(2차, best-effort, 캠퍼스당 1대 권장). GUI 변경 없음(역할 자동감지). CM 잡 구조(`{cls,body,recipients:[{nameKey,name}],image?,imageFirst?}`) 호환 검증(모킹 dry: room=prefix+name·msg=body render·선점 양보). 단일 exe 재빌드·재업로드. CM repo: 중복 .py 4개 git rm, README 통합 안내로 교체. |
| 8.69 | 2026-06-25 | **호스팅 배포(v2.5.0 v293) + CSP Auth 차단 버그 수정**. 배포 직전 발견: v2.5.0 로그인 게이트가 Firebase SDK를 `gstatic.com`에서 import + Auth가 `identitytoolkit`/`securetoken.googleapis.com` 호출하나 `firebase.json` CSP `script-src`에 gstatic 없고 `connect-src`에 auth 엔드포인트 없음 → **배포판 로그인 전면 차단**(localhost는 CSP 미적용이라 미검출). 수정: `script-src`에 `https://www.gstatic.com`, `connect-src`에 `https://*.googleapis.com` 추가. `firebase deploy --only hosting`(87파일). 라이브 검증: 포털·v2.5.0·guide·v2.4.0 전부 200, CSP 헤더에 gstatic·googleapis 반영, 배포 JS v293. 에이전트 릴리스(`DRW-AI-Agent-0.91.exe`) 동반 공개. |
| 8.68 | 2026-06-25 | **에이전트 리네이밍·버전 갱신 — DRW AI Agent v0.91**. AI 생성을 담당하는 'AI 에이전트' 성격 반영해 명칭 변경(`DRW Agent`→`DRW AI Agent`), 버전 0.9→0.91. 동기화: `agent_gui` 창/헤더 제목·`AGENT_VERSION`, `build-agent.ps1` 산출물명(`DRW-AI-Agent-0.91.exe`), 웹 `AGENT_DL`·에이전트 안내 모달, `guide.html` 다운로드 버튼(웹 JS v293). 릴리스 `agent` 에셋 교체(구 `DRW-Agent-0.9.exe` 삭제 → `DRW-AI-Agent-0.91.exe`). 기능 변경 없음(명칭·버전만). |
| 8.67 | 2026-06-24 | **과제 커스텀 프리셋(`assign_tags`) AI 프롬프트 반영**. 강사 등록 자유문구(교재 미지참·오답풀이 안 함·채점 미실시 등)가 `tags.assign_tags`로 저장되고 genJob 페이로드까지 전달되나 `ai_engine._build_tags_context`가 키를 소비하지 않아 **프롬프트에서 누락**되던 버그. condition 다음에 `- 과제 관련 특이사항: ...`(자유텍스트 그대로) 추가. 과제 고정등급(assign_grade)은 기존대로 items.value로 전달. 에이전트 재빌드·재업로드. |
| 8.66 | 2026-06-24 | **① 데일리 리포트 다반 일괄 전송 (v2.5.0 JS v292·CSS v20260629)**. 전송이 활성반 단독 → `전송` 모달이 **검토중(발송문 작성) 학생을 여러 반에 걸쳐 한 번에** 표시(`openReportSend`가 `_myClassList` 순회, 활성반 우선). 반 헤더 체크(`_sendClsToggle`)로 반 단위 토글·학생별 제외. `doReportSend`가 선택분을 **반별로 묶어 sendJob 다건 적재**(반별 history·취소·모니터 단위 유지) — A안(다반 선택)+B안(기존 큐 순차처리) 결합. 에이전트 불변(반별 잡 그대로). **② 카톡 전송 인터벌 단축**(`kakao_send.send_messages`): 학생 간 고정지연 — 말미 sleep 0.3→0.1, 방닫기 esc 0.2→0.12, 매건 재포커스 0.3→0.2(학생당 ~0.4s↓, room_opened 게이트가 정확성 보호). 에이전트 재빌드·재업로드. **③ guide.html 전면 갱신** — v2.4 잔재(설정 위저드·PC 전송 클라이언트·drw2_cbt 수동입력·데이터 가져오기·groq·수동 명단갱신) 제거, 현 구조 반영(로그인 게이트·강사 에이전트 설치/트레이/자동시작·5탭 사이드바·리포트·전송 트리·일괄공지 다반·시험 결과 태그·AI설정 문체·로그인 시 자동 최신로드). |
| 8.65 | 2026-06-24 | **리포트·일괄 디렉토리 트리 통합 + AI 503 재시도 (v2.5.0 JS v291·CSS v20260628)**. ① 레일을 **반→학생 디렉토리 트리**로(`_railTreeHtml` 리포트·일괄 공통) — 오늘 수업 반 펼침·그외 접힘, **당일 전체 학생 한눈에**, 트리서 직접 반·학생 선택(사이드바 의존 제거). 리포트=학생 단일선택 편집(활성반 `_rpActiveCls` 분리, 생성·전송·발송제외 모두 활성반 스코프). ② **일괄공지 다반 선택** — 트리 체크박스(반단위/학생단위, 여러 반 가로질러), 리포트와 동일 4열 GUI, bulkSend가 반 혼합 수신자 1잡 발송(cls="일괄 N반", history 미기록). ③ 시험 태그 복수선택(8509ddc). ④ **AI 503/429/5xx 백오프 재시도**(`_call_ai_hub` 1·2·4초 4회) — Gemini 무료티어 과부하 해소. 에이전트 재빌드. |  2026-06-24 | **에이전트 실발송 토글 제거(운영 항상 real)** — dry/real UI 체크박스가 수동실행 기본 dry라 '미발송인데 웹엔 완료' footgun → 제거. 운영은 **항상 실 발송**, 테스트는 **`--dry` CLI 플래그**로만(상태창에 🧪DRY 표시). `--auto`/자동시작은 그대로 real. **트레이 빌드 보강**: `pystray._win32`(동적 import) 정적분석 누락 → `--collect-all pystray`로 백엔드 확실 번들 + `_init_tray` 예외 가드(트레이 실패해도 일반 창 구동). exe 재빌드·재업로드. **트레이 frozen 미동작 수정(8.65)**: 배포 exe에서 트레이 안 되고 닫으면 종료되던 문제 — 원인 ① 빌드가 pystray 없는 다른 파이썬(pwsh CLI) 사용해 **pystray 미번들**(ModuleNotFoundError로 `_HAS_TRAY=False`) ② import 실패 시 `except as e`의 `e`가 블록 종료 후 삭제되는데 로그줄에서 참조 → **NameError 앱 크래시**. 해결: 빌드 `python -m PyInstaller`+`--collect-submodules pystray`+pystray._win32 hidden-import(pwsh python에 pystray 설치), `_e` 참조 제거. 재빌드 20MB(pystray 포함)·재업로드. frozen서 `tray init OK` 확인. ‖ **(직전) 시스템 트레이 최소화** — `pystray`(+PIL) 도입. 창 닫기(X)·최소화(iconic) → 트레이로 숨김(`_hide_to_tray`/`_on_unmap`), 워커는 백그라운드 계속. 트레이 메뉴 열기(더블클릭 기본)·종료, 아이콘 런타임 생성(인디고 사각+점). `--auto`(자동시작) 시 트레이로 조용히 가동. pystray 미설치 환경은 `_HAS_TRAY=False`로 일반 창 폴백. 빌드: `build-agent.ps1`에 `pystray`·`pystray._win32` hidden-import + 사전설치 추가, exe 재빌드(13MB)·릴리스 재업로드(동일 URL). |  **① 에이전트 v0.9 명명** — exe `DRW-Agent-0.9.exe`(릴리스 에셋·AGENT_DL 갱신, 웹 v289 재배포), agent_gui 창/헤더 제목 영문화(`DRW Agent`·`Setup`, 입력 라벨 한글 유지), `AGENT_VERSION` 상수. **② v2.4→v2.5 데이터 마이그레이션(클론 이후 델타)** — drw2_cbt(안정·실작업) → campus/dongsuwon(개발) 멀티패스 PATCH로 244경로 이관: obs 117(06-22·23)·history 62·신규학생 2(3008·99501)·input `__note__` 52(추가34+충돌18 v2.4우선)·session/class_data 11(진도/과제 충돌 v2.4우선). scores 동일(불요), classes 교수부↔교수진은 미변경(사용자 결정), config/instructors 범위 외. 양 트리 백업 `migration/`(gitignore·PII). 이관 후 v2.4-only 잔여 0 검증. ⚠️ 두 트리는 여전히 분기 — 이번은 일회성 캐치업, 이후 실작업은 한 트리로 단일화 필요. |
| 8.62 | 2026-06-24 | **v2.4.0 안정판 / v2.5.0 개발버전 명명 + 호스팅 배포(실사용 테스트)**. `firebase.json` ignore서 `v2.5.0/**` 제거(공개), `versions.json` v2.4.0→`안정판`(beta=🟢안정 섹션) + v2.5.0→`개발`(dev=🧪개발본 섹션) 추가, `build-portal.ps1`로 포털 재생성, `firebase deploy --only hosting`(87파일). 라이브 확인: 포털·`/v2.5.0/`·`/v2.4.0/` 전부 HTTP 200. **주의(미해결)**: ① 보안 룰 전환(cutover)은 별도 — 현재 DB 룰 개방 상태 유지(v2.5.0 로그인 게이트는 UX, 룰 미강제). ② 데이터 경로 분기 — v2.4.0(구 `drw2_cbt`) vs v2.5.0(로그인→`campus/dongsuwon`) 트리 별개라 두 버전 간 데이터 비동기(검증은 v2.5.0 단독 사용 권장). ③ 강사 에이전트는 campus=dongsuwon·이름=로그인명 일치 필요. |
| 8.61 | 2026-06-24 | **신규 obs 태그 — 시험 결과(`exam`) 단일선택 축 (v2.5.0 캐시 v288 · 에이전트 재배포)**. 마이닝 도출: 강사가 시험 후 '잘봤다/실수 많다'류 피드백을 자주 작성 → 흩어진 caution 태그 대신 **단일선택 시험결과 축** 신설(condition/understand 패턴). 레벨: 🏆우수/👍양호/⚠️실수실점/🧩심화아쉬움/📉아쉬움. 동기화: `app-core.js` TAGS.exam + `onTagExam`, `app-input.js` '시험' 행, `app-report.js` `_obsTagLabels`(우수·양호=pos/그외=warn), `ai_engine.py` `_EXAM_TEXT`(레벨별 AI 지침: 직접적이되 비공격적 — 칭찬/완곡 코칭/기본기칭찬+심화/격려)+`_build_tags_context` 반영(시험 결과를 메시지 핵심으로). 시험 본 날만 선택(미선택 시 미반영). 실 Claude 5레벨 생성 검증. 에이전트 exe 재빌드(13MB)·릴리스 재업로드. (constants.py TAGS는 PC앱 제거로 잉여 — 미동기화) |
| 8.60 | 2026-06-24 | **에이전트 frozen exe 치명 버그 수정(exe 재배포)**. 슬림화(67→20MB) 검증 중 발견: PyInstaller onefile에서 `__file__`이 임시추출폴더(`_MEI…`, 종료 시 삭제)라 ① **agent_config.json이 매 실행 휘발**(재설정 반복) ② 자동시작 .bat가 임시 .py 경로 참조(무효)·GUI exe와 불일치. 수정: `agent_worker._BASE_DIR`=frozen이면 `sys.executable` 부모(exe 옆)로 config 영속, `register_autostart`=frozen이면 `start "" exe --auto`, `agent_gui` `--auto` 인자 → 설정 존재 시 실 발송 모드 자동 가동(턴키 자동시작). **검증**: 제외 모듈(cv2/numpy/pandas) 차단 상태서 에이전트 전체 import + 핵심 함수(build_prompt·SmartWait·send_messages·decode_image 등) 정상(런타임 불사용 확정), 재빌드 exe 기동 무크래시. 릴리스 `agent` 에셋 교체(동일 URL). |
| 8.59 | 2026-06-24 | **에이전트 exe 빌드·배포 + 다운로드 안내 (v2.5.0 캐시 v287)**. `scripts/build-agent.ps1`로 `agent_gui.py` 단일 exe(`DRW-Agent.exe`, **20MB**, 동적 import kakao_send·secret_codec·ai_engine·ai_style·constants·agent_worker hidden-import 보강) PyInstaller 빌드. **용량 최적화**: 에이전트는 키 입력·클립보드만 사용(이미지 인식·스크린샷 미사용)인데 pyautogui→pyscreeze가 cv2(opencv)·numpy·pandas를 끌어와 67MB로 비대 → `--exclude-module cv2 numpy pandas scipy matplotlib IPython pytest`로 **67MB→20MB**(PIL·pyscreeze는 pyautogui import 안정성 위해 유지). **배포**: GitHub Release 태그 `agent`(PUBLIC 레포 → 무인증 다운로드, HTTP 200 확인) 에셋으로 업로드(git 미커밋, dist/ gitignore). **다운로드 경로**: `https://github.com/idocho/dailyReportWizard2/releases/download/agent/DRW-Agent.exe` — 에이전트 미감지 안내 모달(`_agentGuide`)에 `⬇ 에이전트 다운로드` 버튼(`AGENT_DL`)+SmartScreen 안내 추가. 재빌드 시 `gh release upload agent DRW-Agent.exe --clobber`로 동일 URL 유지. |
| 8.58 | 2026-06-24 | **에이전트 미실행 감지 + 설치 안내 (v2.5.0 캐시 v286)**. AI 생성·카톡 전송은 로컬 에이전트가 처리하는데 에이전트 미실행 시 작업이 큐에 무한 대기하던 문제. **하트비트**: 에이전트(`agent_gui._worker`)가 `write_heartbeat`로 `campus/{campus}/agents/{instructorId}={ts(ms),real}`를 ~15s마다 기록. **웹**(`app-report.js`): `_agentAlive()`(하트비트 90s 이내 확인) 게이트를 AI 생성(`genReportOne`/`genReportAll`)·전송(`openReportSend`)·일괄(`bulkSend`) 진입에 추가 — 미감지 시 `_agentGuide` 모달(에이전트 실행/설치 가이드 링크 `guide.html` + '그래도 대기열 추가' 우회). 신규 DB 경로 `campus/{campus}/agents/{id}`(에이전트 소유). |
| 8.57 | 2026-06-24 | **리포트·전송 화면 리디자인 (v2.5.0 JS v284·CSS v20260627)**. 승인 목업 반영. ① **4열 카드 패널화**(레일·편집·미리보기·전송모니터 각 둥근 카드). ② **라이트 테마 색 전면 교정** — 다크 잔재(저대비 연두/앰버 텍스트, `rgba(255,255,255,.05)` 보더) → 의미별 정상 대비(긍정 `#047857`/주의 `#B45309`/중립 `#4338CA`). 뱃지·pill·태그·제외칩·경고 모두. ③ **학생 레일 아바타**(이니셜) + 선택 강조. ④ **편집**: 아바타 헤더 + 진도/과제/수행도 **메트릭 칩** + 관찰 태그 pill + 강사메모 앰버 콜아웃 + 넓은 textarea + primary 생성. ⑤ **미리보기 카톡 말풍선**(좌상단 꼬리). ⑥ **전송 모니터 다크 패널화** — 작업 열(밝음)과 명확히 구분되는 어두운 상태보드, `● 실시간` 펄스 + 작업 카드 + **진행 프로그레스 바**. `_ini`(아바타), 작업카드 마크업(rp-job-top/rp-bar2/rp-job-sub) 신설. |
| 8.56 | 2026-06-24 | **입력↔리포트 탭 분리 + 전송상태 팝오버 (v2.5.0 JS v279·CSS v20260625)**. 입력(교재별 grain)과 전송/리포트(학생별 grain)의 UX 일관성 문제로 통합 「수업」 탭(Form A 스테이지 토글)을 **분리**: 사이드바 nav를 `✏️ 수업 입력`(`goNav('input')`) / `📤 리포트·전송`(`goNav('report')`) 2개 독립 항목으로. `_stageBar` 토글 호출 제거(input·report 양쪽 — 함수는 잔존하나 미사용). **전송상태**: 리포트 3열 레일 하단(부적절 위치)에서 **상단 전송 버튼 옆 팝오버**로 이동 — `전송상태` 버튼 + 진행/대기 건수 pill(닫혀도 표시), 클릭 시 `.rp-stat-pop` 드롭다운에 작업 목록·정리(`toggleRpStatus`, `loadReportJobs`가 `#rp-jobs`+pill 갱신). 레일은 학생 전환 전용으로 정리. |
| 8.55 | 2026-06-24 | **문체 설명·예시 문구 복원 (v2.5.0 캐시 v271)**. 웹 설정 「문체」 탭이 라벨 드롭다운만 있고 각 문체의 **설명(guidance)·예시 문구**가 없던 문제(ai_style.py STYLE_PRESETS 내용이 JS 미반영, RP_STYLES는 라벨뿐). `app-report.js`에 `RP_STYLE_INFO`(STYLE_PRESETS의 desc+예시 미러) 추가, `app-settings.js` 문체 드롭다운 아래 안내 박스(`#aiStyleInfo`)에 선택 문체의 설명+예시 렌더(`_aiStyleInfoHtml`/`renderAiStyleInfo`, select onchange 갱신). auto는 '본인 노트 학습' 안내. CSS `.ai-style-info`/`.asi-*` 추가. |
| 8.54 | 2026-06-24 | **카톡 전송 속도 — 학습값 영속(진짜 적응형) develop**. 기존: `SmartWait`(AIMD+EMA 자동 가감속)이 매 sendJob마다 시드 0.5에서 재학습 → 잡 간 학습 소실(docstring '학습값 영속' 의도 미구현). 수정(`agent_worker._send_real`): 잡 종료 시 학습된 `sw.wait`를 ① **cfg 인메모리**(세션 내 다음 잡 warm-start) ② **디스크**(`_persist_smartwait` → `agent_config.json.smartWait`, 재시작 후 warm-start) 양쪽 영속. `_persist_smartwait`는 raw JSON의 `smartWait`(평문·비민감)만 갱신 — 암호화 키 필드(`*_api_key`, DPAPI) 미열람·미변경. 완료·타임아웃 무관하게 그 시점 운영점 보존. 수동 속도 옵션(PC 고정 프리셋 0.3~2.0s)은 폐기 유지 — 자동 적응이 대체(턴키 UX). 격리 테스트: 영속·warm-start·키필드 보존 확인. |
| 8.53 | 2026-06-24 | **history 누적 웹 이관 — 8.52 미해결 해소 (v2.5.0 캐시 v270)**. PC `_push_history`(전송 확정 시 `history/{nameKey}/{date}={note,instructor}` 기록) 동작을 웹+에이전트 경로로 이관. **웹**(`doReportSend`): sendJob 각 수신자에 `note`(발송 특이사항=`_curDraft`) 동봉 + 잡에 `date`(todayKey)·`instructor` 추가. **에이전트**(`process_sendjobs.on_item`): 카톡 전송 **성공한 수신자만** `campus/{campus}/history/{nameKey}/{date}={note,instructor}` PATCH 누적 — **real 발송 한정**(dry 제외)·**`date` 있는 리포트 잡만**(bulk 공지 제외). 실패분은 미기록(PC가 실패 학생 제외하던 동작 계승). Analyzer가 obs/·scores/와 nameKey+date로 조인하는 원료 복구. PC의 `__note__` 소거(import 브리지 anti-staleness)는 모바일 가져오기 폐기로 불요(웹 `__draft__`는 todayKey date-gating 자연 만료). 격리 테스트: real 리포트→3명 history 기록·스키마 일치, dry·bulk→미기록 확인. |
| 8.52 | 2026-06-24 | **PC 네이티브 앱 제거 — 빌드 단순화 (브랜치 endgame)**. 카톡 전송용으로 존재하던 PC 풀 클라이언트가 웹(v2.5.0)+강사 에이전트(생성·전송)로 완전 대체되어 기능 잉여화 → 코드 제거. **삭제(7파일)**: `app.py`(2630줄 fat client)·`main.py`(진입점)·`pc_auth.py`(PC 로그인)·`message.py`(PC 메시지 빌더)·`kakao_image.py`(에이전트는 자체 `decode_image` 보유)·`firebase.py`·`storage.py`·`errors.py`(셋은 PC앱/`AiEngine` 클래스 전용이라 동반 잉여화). **`ai_engine.py` 슬림화**: PC 전용 `AiEngine` 클래스(~360줄, tkinter 결합)·`_merge_student_tags`·firebase/storage/errors import 제거. **잔존 = 에이전트·마이닝 공용**: 프롬프트 조립(`build_single_prompt`/`build_batch_prompt`)·`_call_ai_hub`·`_base_conditions`·`_build_tags_context`·`_*_TEXT` 테이블. **빌드**: PC `DailyReportWizard.spec`(gitignore·로컬) 폐기 → `scripts/build-agent.ps1` 신설(추적, `agent_gui.py` 단일 exe = `DRW-Agent.exe`). 검증: 에이전트 스택(agent_worker·agent_gui·ai_engine·kakao_send·secret_codec) + 마이닝(`ai_engine._*_TEXT`) import 무결. ⚠️ 미해결: `history/` 누적(_push_history)은 PC앱 동작이었음 — 웹+에이전트 경로의 history 기록 구현 여부 별도 점검 필요(Analyzer 조인 원료). |
| 8.51 | 2026-06-24 | **AI 생성 메시지 퀄리티 개선 — 컨디션 프롬프트 재작성 (`ai_engine.py`)**. 실 Claude(sonnet-4-6) 키로 컨디션 5단계 × 복합태그 6종 × 문체 3종 다회 시뮬레이션 후 도출. **문제**: ① `_CONDITION_TEXT["normal"]="무난하게 수업에 참여함"` → AI가 그대로 앵무새, 학부모에 밋밋·부정 인상("오늘은 무난하게…"). ② 모든 메시지가 `- 수업 컨디션:` 문구로 **시작·도배**(컨디션이 헤드라인 독점, 단조). **수정**: ① `_CONDITION_TEXT` 전면 재작성 — '무난' 제거(정상=「평소와 같이 안정적으로 집중」), good·normal엔 "굳이 언급 말 것" 메타지시 동봉, low·bad는 완곡·격려 어조. ② `_base_conditions()`에 지침 11~13 추가 — **컨디션은 보조맥락(메시지는 학습 내용·성취로 시작), good·normal은 미언급 허용, '무난·그냥·특별한 것 없이' 등 금지어, 건설적·앞을 향한 마무리**. 적용 범위: `build_single_prompt`/`build_batch_prompt`가 `_build_tags_context`+system(`_base_conditions`) 사용 → **에이전트 단건·일괄 생성 전 경로 자동 전파**(웹 생성 라인). A/B 검증: 정상 컨디션 "무난" 100% 제거·학습 리드 전환, caution(졸음·잡담) 완곡화·메모 보존·하이라이트 우선 모두 유지 확인. (PC `gen_all`은 system="" 라 미적용이나 PC 라인 폐기 예정) |
| 8.50 | 2026-06-24 | **다기기 진도/과제 동기화 수정 (v2.5.0 캐시 v269)** — 진도/과제(반 공통, `session/class_data`)의 로드 병합이 `if(!progressData[k])`(**로컬 우선**, 빈 키만 채움)이라, 한 기기에 캐시된 뒤 다른 기기서 변경하면 갱신 안 되던 staleness. **태블릿 입력 → PC 발송** 주 워크플로가 정확히 이 경로에 물림. `Object.assign(progressData, sessD.class_data)`로 **Firebase 정본 우선** 전환(`app-scores.js` init·`app-settings.js` 명단 새로고침 2곳). 메모(`__note__`)·발송문(`__draft__`)·과제수행도·관찰태그는 **기존부터 Firebase 우선**이라 일관성 확보. 트레이드오프: 오프라인서 쓴(미반영) 로컬 진도값은 재로드 시 손실 가능하나 진도는 반 공통·재입력 용이, 쓰기는 즉시 `fbPatch`라 온라인 시 무손실 |
| 8.49 | 2026-06-24 | **웹 통합 — PC 기능 마이그레이션 누락분 3종 이식 (v2.5.0 캐시 v268, 브랜치 endgame)**. PC→웹 기능 감사로 확인된 미이식 기능 보완. ① **진도/과제 발송 제외 토글**(PC `_toggle_exclude_prog` 이식) — 리포트 탭 발송 제외 바: 담당 과목별 `✓/✕` 토글로 이번 발송에서 진도/과제 제외(세션 메모리 `_excludeProg` set, key=`classId\|subject`). `_rpData`서 제외 과목의 progress/homework를 빈값 처리 → **메시지·AI 생성 동시 제외**(수행도·관찰태그·메모는 유지). 진도/과제가 입력된 과목만 토글 노출. ② **일괄 공지 저장 템플릿 CRUD**(PC `_bulk_add/del/load_tmpl` 이식) — 기존 단일 textarea(세션 휘발)에 저장 템플릿 추가: `config/instructors/{id}/bulkTemplates[]`(`{name,body}`)에 영속, 드롭다운 불러오기 + 💾저장(이름 중복 시 덮어쓰기) + 🗑삭제. 로그인 init서 `config.instructors[id].bulkTemplates` 하이드레이트. ③ **전송 취소**(PC `_cancel_send`/`_bulk_cancel` 이식) — 웹→에이전트 비동기 큐의 중단 경로: 작업 패널 `취소` 버튼 — 대기(queued) 건은 `sendJobs/{id}` 삭제(에이전트 미실행), 진행(sending) 건은 `cancel:true` 패치 → 에이전트 `process_sendjobs`가 건별 폴링(`should_cancel`)으로 **진행 중 학생까지 발송 후 나머지 중단**, 상태 `canceled`(미발송분 `대기` 유지). `kakao_send.send_messages`에 `should_cancel` 훅(매 건 직전 검사). + 완료·취소·오류 건 **수동 일괄 정리** 링크. 에이전트 격리 테스트: 정상=done(전건 발송), 취소=canceled(0발송·미발송 보호) 확인 |
| 8.48 | 2026-06-21 | **v2.5.0 — 로그인 전환(Firebase Auth + 캠퍼스 경로)** (브랜치 endgame). 설계: `AUTH_DESIGN.md`·`PLATFORM_ARCHITECTURE.md`. ① **강사 로그인**: 캠퍼스 선택+한글 이름+비번 → 합성 이메일(`n{hex}@{campus}.drw.local`, `synth_email`)로 Firebase Auth 로그인 → `acl/{uid}`(campus·role·instructorId·active) 검증. 비번은 Firebase 해시 보관, 관리자 발급+첫 로그인 변경강제(mustChangePw). ② **웹 DRW v2.5.0**(v2.4.0 클론·신규 라인): index.html 로그인 게이트(성공 후 앱 로드), 온보딩 위저드·설정 「🔥연결」 탭·강사 자가등록 **제거**, fbE가 idToken 사용, 로그아웃. ③ **PC앱**: 시작 시 로그인 게이트(refresh_token 세션복원), `pc_auth.py`(REST signIn/refresh/updatePassword), firebase.py `_id_token` 우선, 설정 「연결/강사계정」 탭·설치 위저드 제거, 50분 토큰갱신, 로그아웃 추가. refresh_token DPAPI 암호화·idToken 메모리만. ④ **캠퍼스 경로 분리**: `campus/{campus}/...`(drw2_cbt→campus/dongsuwon 복사, 구 클라 보존). ⑤ **관리자**: CampusManager 독립 repo(계정·명단·전송)+전송 에이전트. ⑥ 강사 7명 일괄 계정 생성. **미배포·미전환**(F 룰배포·cutover 대기) |
| 8.47 | 2026-06-21 | **공식배포 前 보안 강화 (CBT 막바지·브랜치 endgame)** — ① **[PC] API 키·DB 시크릿 로컬 암호화** — `code/secret_codec.py` 신설(순수 `ctypes` DPAPI, pywin32 의존 0). `config.json`의 `groq/openai/claude/gemini_api_key`·`firebase_secret`을 `CryptProtectData`로 암호화(`dpapi:` 프리픽스+base64). **현재 Windows 사용자+머신 바인딩** — 파일만 복사해선 복호 불가(평문키 디스크 노출·과금탈취 차단). `storage.py` `save_config`은 암호화 복사본만 기록(메모리 cfg는 평문 유지 → 앱 코드 무수정), `load_config`은 복호 후 평문 반환 + 레거시 평문 config 자동 재저장 마이그레이션. **하위호환**: `unprotect`는 `dpapi:` 없으면 그대로 반환(평문·비-Windows 개발환경 100% 동작). `backup_db.py`·`restore_db.py`도 `secret_codec.unprotect`로 시크릿 복호(룰 전환 후 백업 유지). ② **[웹] 보안 응답 헤더** — `firebase.json`에 CSP(`default-src 'self'`; script/style `'unsafe-inline'`(인라인 핸들러 호환); connect-src firebaseio·firebasedatabase) + `X-Content-Type-Options:nosniff`·`X-Frame-Options:DENY`·`Referrer-Policy`·`Permissions-Policy`. ③ **[운영] 룰 전환 원샷 스크립트** `scripts/deploy-rules.ps1` — 백업→[무장확인 게이트]→schema_version=14→firebase.json database 배선(멱등)→`firebase deploy --only database`→무인증차단/유인증통과 검증을 순서·`-DryRun` 지원으로 자동화(`SECURITY_RULES_PLAN.md` 런북 실행체). **라이브 룰 배포 자체는 클라 무장 후 수동 트리거**(미무장 시 전 클라 차단) |
| 8.46 | 2026-06-16 | **설정 UI 정리 (PC·웹)** — ① **[PC] 설정창 폭 확대·잘림 수정**: 고정 560→660 + `resizable(True,True)`·`minsize(600,560)`(가로 조절 가능). `_wrap_to_width`를 본문 공용으로 끌어올려 안내문·엔진 설명·미리보기·힌트가 창 폭에 맞춰 자동 줄바꿈(고정 wraplength 잘림 해소). ② **[PC] 개별 지침 직관화**: 라벨 `개별 지침`→`✏️ 나만의 프롬프트`(인디고), 빈칸 placeholder 예시("항상 존댓말 / 끝에 응원 한마디 / 줄임말 금지", 저장 시 예시문은 빈값 처리), 동작 설명 힌트("AI에게 그대로 전달돼 매 생성마다 반영"). ③ **[웹] 시스템 탭 분리**: 모든 설정 탭 하단에 항상 노출되던 「초기 설정 위저드 다시 실행 / 관리자 모드 / 크레딧」(`stg-foot`)을 독립 「⚙️ 시스템」 탭으로 이동 — `_pane('system',SA_FOOT)`, `.stg-foot` 구분선 제거, 캐시버스트 `?v=202606161700`. 실캡처·프리뷰 검증(탭 전환·footer 단일 노출·관리자 ON 시 5탭) |
| 8.45 | 2026-06-16 | **[웹] GUI 정리 — 온보딩 풀스크린·설정 좌측 탭·사이드바 튜닝(§4.2·4.8·4.8-C)** — ① **온보딩 풀스크린**: 위저드 중 `#wr.wz-mode`로 사이드바 숨김(`renderMain` 토글)+본문 전체폭. 위저드 헤더에 설치·운용 **가이드 링크**(`.wz-guide`) 추가. ② **설정 좌측 탭**: 단일 롱 스크롤 아코디언 → 4탭(`.stg-rail`: 👤계정·수업/🔥연결/💬문구·데이터/👑관리자) + `setStg` CSS show/hide(아코디언·async 보존), `@600px` 가로 탭 반응형. 기존 `sa` 섹션 재사용. ③ **사이드바 튜닝**: `--sw` 212→192px. 캐시버스트 `?v=202606161200`(app.css·app-core·app-settings). 프리뷰 검증(온보딩 사이드바 none·가이드 노출·탭 전환·모바일 가로전환·콘솔 무에러) |
| 8.44 | 2026-06-16 | **[PC] 설정창 좌측 탭 사이드바 재구성(§2.9)** — AI 기능 추가로 설정창이 단일 롱 스크롤로 비대해져 정리. 좌측 탭 레일(132px) + 탭별 스크롤 콘텐츠 + 하단 고정 푸터(저장/취소)로 분리. 탭: **🤖 AI 생성(기본·전면)** / 🔥 연결 / 👤 강사 계정 / ⚙ 일반(전송속도·접두사). 기존 위젯 빌드 코드는 유지하고 섹션별 부모를 `inner = tab_*`로 재지정, 섹션 구분선 제거. 창 520×720→560×680. exe 재빌드 |
| 8.43 | 2026-06-15 | **[릴리즈] v2.4.0 베타 승격** — PC앱 AI 개선 일괄(문체 반영·개별 지침·설정 GUI·에러 사용자화·기본엔진 Gemini·이름 주어 제거·출결번호 픽스, v8.37~8.42) 테스트 완료 후 v2.4.0 릴리즈. lockstep: 웹 라인 `code/public/v2.3.0`→`v2.4.0` 동결 클론(웹 코드 미변경, 인라인 APP_VERSION만 갱신), `APP_VERSION` v2.4.0, versions.json v2.4.0 베타·최신/v2.3.0 이전 강등, 포털 index.html 재생성, firebase redirect 최신 타겟 v2.4.0. Mac 환경이라 포털 생성은 build-portal.ps1 동등 로직 수동 실행. **exe 빌드·firebase deploy는 Windows에서 별도 수행 필요** |
| 8.42 | 2026-06-15 | **[v2.3.0] 생성 메시지 이름 주어 중복 제거** — 메시지 위 ‘오늘의 OOO는?’ 고정 헤더에 이름이 이미 있는데 본문이 ‘OOO는/OOO 학생은/OO이는’로 시작해 중복. 종전 규칙이 "기본 원칙/예외 외"로 약해 일부 엔진이 무시. **하드 금지로 강화**: `_base_conditions` 규칙1·일괄 `[문체 기준]` 모두 이름 주어 절대 금지+이름 없이 시작 명시, 단건 `[학생 이름]`은 "식별용 참고, 본문 주어 금지"로 라벨 변경. exe 재빌드 |
| 8.41 | 2026-06-15 | **[v2.3.0] AI 엔진 기본값 groq→gemini 통일** — `DEFAULT_CONFIG.ai_engine_type`가 `groq`였고 런타임 fallback(`ai_engine.py` 쿨다운·엔진설정·일괄, `app.py` 버튼초기화)도 `'groq'`이라, 키 미설정/신규 config에서 무료·비추천 Groq가 기본으로 잡히던 불일치. UI·위저드는 이미 `gemini` 기본(`AI_ENGINE_ORDER` 선두) → 전 지점 `gemini`로 통일. exe 재빌드 |
| 8.40 | 2026-06-15 | **[v2.3.0] 에러 메시지 사용자화 — `errors.py` 신설(§9)** — payload 크기 초과 등 기술 에러를 비개발자도 알아들을 한국어 안내로 변환(`humanize_error`). HTTP 코드 맵+timeout/네트워크/파싱/내용필터, **응답 본문 용량초과 키워드 우선 감지(400→413 승격)**. 끝에 `(참고: HTTP 413)` 식별코드만 잔존. `ai_engine`(단건·일괄 except 블록을 humanize로 일원화, 기존 `HTTP {code}: {reason}`·`str(e)` 노출 제거)·`app.py`(가져오기/연결/계정/명단 실패) 적용. exe 재빌드 |
| 8.39 | 2026-06-15 | **[v2.3.0] AI 설정 GUI 개선 + 강사 개별 지침** — ① 엔진 콤보 아래 무료/유료 배지+한 줄 설명(`_ENG_INFO`/`_render_eng_info`). ② 문체 콤보 아래 미리보기(프리셋=지침+예시, auto=`ai_style.profile_summary` 분석 요약+예시, 백그라운드 fetch). ③ **개별 지침** 자유 텍스트박스 신설 — config `ai_custom_prompt`, 문체와 직교(무엇을 챙길지), 단건은 system(`_system_conditions`)·일괄은 `[학생데이터]` 앞에 `[강사 개별 지침]` 블록 주입(§3.5 우선순위: 안전·사실 규칙이 항상 우선, 가드레일 문구는 프롬프트 내부에만·UI 미노출). `ai_style.profile_summary` 추가. exe 재빌드 |
| 8.38 | 2026-06-15 | **[v2.3.0] 단건 AI 생성 출결번호 노출 버그픽스** — `gen_single`의 `name` 인자가 nameKey(출결번호)인데 `build_single_prompt`가 이를 `[학생 이름]`에 그대로 넣어, 일부 엔진이 학생 이름 자리에 출결번호를 출력. **픽스**: `gen_single`에서 `all_students[nameKey].name`을 조회해 `display_name`으로 분리 전달(데이터·태그 조회는 nameKey 유지). `build_single_prompt(display_name=...)` 파라미터 신설(미지정 시 name 폴백). 일괄(`gen_all`)은 본래 display_name 사용이라 영향 없음 |
| 8.37 | 2026-06-15 | **[v2.3.0] AI 메시지 문체(말투) 반영 — `ai_style.py` 신설(§3.6)** — 강사가 직접 수정·전송한 최종 특이사항(`history/`)의 말투·분량을 AI 생성에 반영. 실DB 289건(강사 5명) 문체 분석으로 4개 대표 유형 도출(따뜻·상세/정돈·균형/정보·코칭/간결·요점). 설정 `ai_style_mode`: **`auto`(기본)** = 로그인 강사 본인 history 노트를 통계 분석(길이·이모지·느낌표·해요체·개조식)해 문체 지침 자동 생성 + 본인 노트 2개 few-shot, 또는 4프리셋 수동 선택(override). 주입: 단건은 `_DEFAULT_STYLE_BLOCK` 자리, 일괄은 `[문체 기준]` 다음에 `AiEngine._style_block()` 삽입(지침+예시). 예시 블록에 '이름·점수 베끼지 말 것' 경고. 세션 캐시 `{mode}|{instructor}`(history fetch 1회·읽기 전용, 표본 40건), 설정 저장 시 `invalidate_style_cache()`. 설정창 AI 섹션에 "메시지 문체" 콤보박스 추가. 신규 `code/ai_style.py`, `ai_engine.py`/`app.py` 연동, exe 재빌드 |
| 8.36 | 2026-06-15 | **[PC] 이미지 전송 후 잔류 톡방 일괄 정리** — 정책 8.8(이미지 방은 업로드 취소 위험에 건별 미닫음)로 누적되던 채팅방을 **전체 전송 완료 후 일괄 닫기**. `kakao_image.close_rooms(rooms)` 신설(CM `kakao_send.close_rooms` 미러): ① 카카오톡 프로세스 소속 창만(타 앱 동명 제목 오폐쇄 차단) ② 제목 전방일치(`room_opened` 포함비교보다 엄격 — 파괴 동작이라) → `WM_CLOSE` PostMessage(X클릭 경로: 업로드 진행 중이면 카톡이 확인 팝업으로 보류, 자동 조작 안 함=업로드 보호). `_do_send`·`_do_bulk_send`가 이미지 방·오류 중단 방을 `lingering`에 모아 종료 후 `_cleanup_rooms()`(2초 유예 후 호출, 상태바에 "🧹 N개 정리 · M개 유지" 표기). 비치명·비 Windows no-op |
| 8.35 | 2026-06-14 | **[v2.3.0] 위저드 교재 입력 datalist + 교재명 통일 마이그레이션** — ① 최초 설정 위저드 교재 입력(`#wzTb`)이 평문이라 기존 교재 재선택 불가→중복·오타 파편화. 설정 경로와 동일하게 `config.textbooks ∪ 모든 반 courses` 소스 datalist 연결(자동완성). ② DB 파편화 교재명 통일(활성 course + obs): `Signature100+`·`시그니처 100+`→`SIGNATURE 100+`, `유형해결의 법칙`→`유형해결의법칙`, `쏀`→`쎈` 등. 18 course rename + 84 obs 이동(충돌 0), `config/textbooks` 레지스트리 정리. 백업 `migration_backup_textbooks_20260614.json`(gitignore). **앱 버전 라벨**: v2.3.0 베타 승격·v2.2.3 이전 강등(versions.json) |
| 8.34 | 2026-06-14 | **[v2.3.0] obs 신규 태그 `writeup_weak`(✍️ 서술 미흡) 추가** — 노트 마이닝(`scripts/mine_note_tags.py`) 첫 검토에서 강사 교차 반복 발굴된 후보. caution 분류(학부모 완곡 전달). 기존 highlight:process_good(풀이과정 우수)의 부정 축으로, 서술형·논술형 풀이과정 작성 미흡을 기록. 3곳 동기화: 웹 `app-core.js` TAGS.caution(입력 UI)·PC `constants.py` TAGS(표시 LUT)·`ai_engine.py` _CAUTION_TEXT("서술형·논술형 풀이 과정 작성이 미흡하여 연습이 필요함"). 더미 생성기·캐시버스트(`app-core.js?v=202606141600`) 갱신, exe 재빌드 |
| 8.33 | 2026-06-14 | **[v2.3.0] PC obs 태그 표시 줄바꿈(flow-wrap)** — 학생 카드 obs 요약(`_render_obs_tags`)이 단일 `pack(side='left')`로만 깔려 태그가 많으면 오른쪽으로 넘쳐 잘림. 박스 실폭(`holder.winfo_width`) 기준 `tkinter.font.measure`로 누적 폭 계산해 넘치면 새 줄 생성하는 flow-wrap으로 교체. `<Configure>` 바인딩으로 창 리사이즈 시 자동 재배치(폭 불변 시 무시해 재귀 차단). 검증: 폭 260→4줄/420→3줄/640→2줄, 15태그 전부 표시 |
| 8.32 | 2026-06-14 | **[v2.3.0] PC obs 태그 표시 신키 누락 픽스** — v8.30 재구조화가 웹 `app-core.js` TAGS·PC `ai_engine.py` 문구만 갱신하고 PC `constants.py` TAGS(읽기 전용 표시용 키→라벨 LUT, `_obs_tag_segments`)는 누락 → PC 학생 카드 obs 요약 줄에서 신키 4종(deep_try 심화도전·process_good 풀이과정우수·slow 풀이느림·calc_miss 계산실수)이 `if k in lut` 필터에 걸려 표시 안 됨. **픽스**: `constants.py` TAGS에 신키 4종 추가 + 폐기 9종은 과거 날짜 데이터 표시 호환 위해 legacy로 유지(웹 입력 UI 미노출과 무관하게 옛 기록 라벨 해석 보장). PC는 obs 쓰기 없음(표시 전용)이라 legacy 키 잔존이 입력 UI에 영향 없음. exe 재빌드 |
| 8.31 | 2026-06-14 | **[v2.3.0] 버전 통합 갱신** — obs 태그 재구조화(8.30) 작업을 정식 라인으로 승격. PC·웹 버전 v2.3.0 통합. ① 웹 개발 라인 디렉터리 `code/public/v2.2.4/` → `v2.3.0/` rename(`index.html` `APP_VERSION`·캐시버스트 `app-core/app-input ?v=202606141400`) ② PC `constants.py` `APP_VERSION` v2.2.3→**v2.3.0**(exe `DailyReportWizard_v2.3.0.exe` 재빌드) ③ `versions.json` 최신 개발본 v2.3.0(desc obs 태그)·포털(`code/public/index.html`) 재생성 ④ `firebase.json` redirect는 dead 버전→안정판(v2.2.3) 유지(v2.3.0 정식 안정판 승격은 deploy 시점). **잔여(배포 시 수동)**: firebase deploy·gh release(exe·zip)·v2.2.3 동결 처리는 미실행 |
| 8.30 | 2026-06-12 | **[v2.2.4·브랜치 feature/obs-tag-restructure] obs 태그 재구조화** — 실데이터 1,019세션·노트 267건 분석 기반. ① **폐기 9종**(UI만, 데이터 보존): understand_sub:confused(8건)·engage:present(6)/help(7)/preview(2)/error_fix(3)·caution:attitude(4)·extra:weekly_test(0)/retest(1)·highlight:perfect(3)/improved(1) ② **신설 4종**: engage:deep_try 🧗심화도전(노트 94건)·highlight:process_good 📝풀이과정우수(55)·caution:slow ⏳풀이느림(37)·calc_miss ➗계산실수(11) — slow·calc_miss는 관찰용(Analyzer 패널티 미반영) ③ **UI 행 재편**: 이해도+하이라이트 / 참여·풀이(engage+understand_sub+extra 통합) / 주의 ④ **기본 과제 프리셋** `DEFAULT_ASSIGN_PRESETS`(결석·보강등원·채점미실시·오답풀이안함·교재미지참 — 자작 프리셋 상위 빈도 정식화) ⑤ PC `ai_engine.py` 신설 4종 문구 추가(폐기 키 매핑은 과거 데이터 호환 유지) ⑥ 더미 생성기 신태그 전환. **알려진 기존 이슈(별도)**: 같은 필드 태그 연타 시 PATCH 도착 순서 역전으로 마지막 토글 유실 가능(간격 클릭은 정상) |
| 8.29 | 2026-06-12 | **[v2.2.4] 관리자 암호 회전 가능화** — `toggleAdmin` 검증을 `config/admin_hash`(DB) 우선·코드 상수(`ADMIN_HASH`) 폴백으로 변경. 관리자 모드 on 상태에서 「🔑 관리자 암호 변경」(8자 이상, 2회 확인) → SHA-256 해시를 `config/admin_hash`에 저장 — 전 버전·전 기기 즉시 적용, 재배포 불요. **[정리]** 구 firebase init 잔재 삭제(`code/firebase.json`·`code/.firebaserc` — 오발 deploy 시 ignore/redirect 없이 공개되는 위험 사본, `code/.gitignore`, 구 스키마 `gen_dummy.js`), AI 도구 로컬 설정 gitignore 추가 |
| 8.28 | 2026-06-12 | **[v2.2.4] 몽키 테스트 검증 + 픽스 2건** — 격리 dbPath(mtest1) 시드 후 브라우저 자동 조작으로 사용자 시나리오 11종 + 무작위 30액션 검증(JS 에러 0). 픽스: ① 회차 "1회" 입력 시 카드 "1회회" 중복 표기 — 저장 시 회차 정규화(meta.round도 "1") + 잔존 데이터 표시 방어(trailing 회 제거) ② 점수 전부 빈칸이면 만점 음수/0 저장되던 검증 우회 — `만점≥1` 강제. 관찰(수정 안 함): 학년→반별 유형 격하 시 타 반 점수가 새 weekly 노드에 잔류(유실 아님·보존 우선), 격하 시 만점 자동 변경이 기존 점수와 충돌하면 검증이 차단(만점 수동 재조정으로 해결) |
| 8.27 | 2026-06-12 | **[v2.2.4] 학생 추가 CM 일원화** — 웹 인라인 학생 추가(addStuInline) 제거. 종전 웹 추가는 `nameKey=이름(+숫자)`로 생성해 스키마 정본(nameKey=출결번호, v2.1)을 위반 — Analyzer 종단 비교·CM CSV와 이질. 「+ 추가」 칩 → 「＋ CM에서 추가」 안내(클릭 시 toast). 명단 CRUD는 CM 단일 소유(v8.13) 원칙 완성. 학생 삭제(rmStu)·조회는 웹 관리자 유지. **실DB 이름 키 4명 마이그레이션 완료(2026-06-12)** — 권서림→6247·박소이→5015·박현서→62484·윤서빈→32621. students/obs/input/history 동반 이동(scores 해당 없음), 백업→신규 기록→검증→구 키 삭제 절차, 로컬 백업 보관(migration_backup_namekeys_20260612.json, gitignore) |
| 8.26 | 2026-06-12 | **v2.2.4 개발 라인 신설 (릴리즈 절차)** — v2.2.3 동결(8.18~8.25 성적 입력 개편 포함, 안정판 승격), `code/public/v2.2.4/` 복제 생성(new-version 절차 수동 재현 — pwsh 부재). versions.json: v2.2.4 개발중(exe 미제공)/v2.2.3 베타·안정판/v2.2.2 이전. firebase.json 구버전 redirect 목적지 /v2.2.3/ 갱신(v2.2.2는 스키마 호환이라 호스팅 유지). 포털 재생성. 이후 웹 수정은 v2.2.4/에만 |
| 8.25 | 2026-06-12 | **관리자 모드 = 전체 수업 바운더리** — 별도 admin 계정 대신 기존 adminOn 확장(감사 추적 보존: 본인 계정 + admin 게이트). ① `activeAsgns()` 신설: 일반=내 assignments, adminOn=전체 `classes/{cid}/courses` 합성(내 담당 우선, 합성분 `admin:true`·「관리」 배지, 보관 과목 제외). `curAsgn()` 중앙 접근자 — curAI 범위 초과 가드(admin 해제 시) ② 사이드바 라벨 「전체 수업 (관리자)」, selA/selGroup/devPushDummy/입력·성적 탭 전부 activeAsgns 기준 ③ 권한 통과: `_canWrite`·`_canInputWeekly`(보관 차단은 유지)·`_canInputAchievement`(담임 제한 해제)에 adminOn 우회 ④ toggleAdmin이 renderSb 동반 갱신. 새로고침 시 해제(세션 한정)·암호 게이트 종전 유지 |
| 8.24 | 2026-06-12 | **시험 삭제 방어·복원 장치** — 학년 공유 시험을 담임 한 명이 통째 삭제 가능하던 위험 차단. ① 삭제 전 `scores/trash/{ts}_{key}` 전체 스냅샷(원경로·사유·삭제자·시각), 백업 실패 시 삭제 중단 ② 학년 시험 비관리자 삭제 = 내 반 점수만 비우기(타 반 보존), 전체 삭제는 adminOn 전용 ③ 관리자 휴지통 UI — 성적 탭 하단 🗑 토글, 복원/영구 삭제. DB_SCHEMA v1.6(`scores/trash/` 신설, 비파괴 — schema_version 불변) |
| 8.23 | 2026-06-12 | **학년 시험 testKey에서 날짜 제외** — 학년 `유형[|회차]` / 반별 `날짜|유형[|회차]` 유지. 같은 실전모의고사를 다른 날 응시(또는 강사가 기본 오늘 날짜 방치)해도 학년 코호트가 갈라지지 않음. 날짜는 meta 대표값(마지막 저장). 회차 키 정규화("1회"→"1", 표시 원형). confirm 문구 식별자 단위별 표기. 구키(날짜 포함) 학년 기록은 수정·저장 시 자동 이동 |
| 8.22 | 2026-06-12 | **학년 시험 카드 "반 평균" 분리 버그 픽스** — 학년 공유 노드의 students 맵(과정 전체)을 그대로 평균 내 반 평균=학년 평균으로 표시되던 문제. 카드 통계(반 평균·n/N명 입력)는 현재 반 명단(nameKey) 필터로 산출, 🎓 학년 집계만 과정 전체 코호트. 편집 화면 초기 통계도 동일 필터(첫 입력 시 기준 점프 해소) |
| 8.21 | 2026-06-12 | **학년 집계 원점수 표기** — 🎓 학년 집계 줄을 백분율 환산(8.19) 대신 원점수 그대로(평균/최고/최저 X점) 노출. `_scoreStatLine` 재사용, `_pctStatLine`·`_achievementAggregate` 제거 |
| 8.20 | 2026-06-12 | **기출모의고사 단위 정정: 과정(학년) → 반별** — `ACHIEVEMENT_TYPES`=[성취도평가, 반배치고사, 실전모의고사] 3종으로 축소. 과정 단위 = 같은 curriculum 수강생 전체 코호트(예: 중3-1 전체). 기존 `scores/achievement/`에 저장된 기출모의고사 잔존 기록은 표시·삭제 정상(kind 기준), 수정·저장 시 weekly로 자동 이동(8.19 경계 이동 로직) |
| 8.19 | 2026-06-12 | **[웹] 성적 입력 무결성 일괄 + 유형별 기본 만점** ① **KMA 제외** — `SCORE_TYPES` 7종(8.18의 KMA 추가 철회. 기존 KMA 기록은 직접입력 폴백으로 표시·수정 가능) ② **유형별 기본 만점** `SCORE_TYPE_MAX`(성취도평가·반배치고사 150, 그 외 100) — 유형 선택 시 만점 자동 세팅, 직접입력은 제외 ③ **[Critical] 학년 공유 노드 점수 유실 해소** — 저장을 렌더된 학생만 갱신하는 머지로 전환(타 반·전출생 보존), 제자리 수정은 meta/·students/ 서브경로 PATCH(동시 입력 안전) ④ testKey 항상 재계산+소독(`_scoreKeySafe`), 날짜·유형·회차 변경 시 키 이동(경계 이동 포함, 고스트 해소), 무음 덮어쓰기 confirm ⑤ 점수 0~만점 검증, 만점 변경 시 input `max`·표기 동기화(+헤더 "만점" 라벨 파괴 버그 픽스) ⑥ 삭제 kind 기준 판정 + 학년 공유 삭제 경고 ⑦ 학년 집계 백분율 변환 정정(원점수→%), 목록 meta.date 정렬, 캐시 무효화 시 스테일 클리어(null/undefined 구분), dead code(`_pushScore`/`_deleteScore`/`getScorePath`) 제거 **[CM]** `scores/achievement` 발송 지원 — 현재 반 학생 응시 시험만 「학년·{curriculumKey}」 그룹으로 드롭다운 합류(통계는 학년 코호트) **[Analyzer]** 구형 평면 레코드 폴백, pct 0~100 클램프, 단독 응시 백분위 100→50 중립 |
| 8.18 | 2026-06-12 | **[웹] 시험 유형 목록 timer 동기화** `SCORE_TYPES` 6종→8종: **확인학습·KMA 추가**, 순서를 timer 프로젝트 시험 프리셋과 일치(주간Test·확인학습·실전모의고사·기출모의고사·성취도평가·반배치고사·KMA·직접입력 — 실전↔기출 순서 교체). `직접입력` 말미 유지(`slice(0,-1)` 커스텀 판별 로직 의존). 기존 저장 데이터 영향 없음(추가만, 명칭 변경 없음). `ACHIEVEMENT_TYPES`(학년단위 4종) 불변 — 확인학습·KMA는 반별(weekly) 경로로 저장 |
| 8.17 | 2026-06-11 | **[웹] 보관 과목 원클릭 복원 + 교재 표시 정렬** ① 학급 관리 과목 칩에 **보관 행** 신설 — 보관 과목 있을 때만 「▸ 보관 N」 토글(기본 접힘) 표시, 펼치면 빗금·흐림 칩 + **↩ 복원** 버튼. `restoreCourse()`: 확인 → `archived:null` PATCH(기존 obs/scores/history 그대로 연결, 로컬 롤백+toast) — 종전 "같은 과정·교재 재입력" 복원 방식의 사용성 개선(재입력 복원도 그대로 동작). 담당 배정은 보관 시 제거되므로 복원 후 「수업 추가」에서 재배정. 권한은 과목 등록과 동일(강사 가능). 펼침 상태는 세션 보존 — 보관 행(`archOpen{classId}`)과 **학급 아코디언(`clsAccOpen{classId}`)** 모두, 보관/복원의 renderMain 재빌드마다 접히지 않음. **보관(×) 직후엔 보관 행 자동 펼침**(방금 보관한 과목 위치 피드백). 마크업은 `_courseChipsBlockHtml()` 단일 헬퍼로 통합(아코디언·드릴인·refresh 3곳 발산 방지) ② **교재 표시 정렬** — 과목 칩(과정→교재명)·담당 수업 목록(설정/위저드)·수업 입력 과목 알약·**사이드바 내 담당 수업** 모두 학급→과정→교재명 ko 오름차순. **[PC]** `_my_classes` 반 이름 오름차순(좌측 패널·전송·상태바 순회 일관) + 학생 상세/메시지 미리보기 교재 카드 `sorted(subjects)`. `_sortedAsgns()` 원본 인덱스 보존으로 removeA/selA 인덱스 핸들러 무영향(저장 순서 불변, 표시만 정렬) ③ **표시 동일 중복 가드** — 칩 표시가 curriculum·textbook 필드 기반이라 구형 키(교재명만)와 신형 복합 키가 똑같이 보이는 중복 등록 가능했음(3MSM 유형해결의법칙 실사례 → DB 정리 완료). `_findCourseTwin()`: 과목 추가(인라인·위저드) 시 정규화된 과정·교재 필드 일치 키 탐색 — 활성 쌍둥이=중복 차단, 보관 쌍둥이=**새 키 생성 대신 그 키 복원**. 잔존 구형 키 8개는 쌍둥이 없음(개편 시 자연 소멸) |
| 8.16 | 2026-06-11 | **Security Rules 전환 사전 배선 (#15 — 룰 미배포, 운영 무영향)** ① **4클라 DB Secret(`?auth=`) 옵션 지원** — 웹 `fbE()`(+설정·위저드 「DB 시크릿」 입력란, `drw_db_secret`), PC `firebase.py _fb_url`(+`config.json firebase_secret`, constants 기본키), CM `_fb_url`(+설정 탭 「Firebase Secret」, `dbSecret`), Analyzer `fbE()`(+설정 패널, `drw_fb_secret`, 「DRW 설정 가져오기」가 시크릿도 복사). **시크릿 미설정 시 종전과 100% 동일(no-op)**. 백업/복원 스크립트(backup_db.py·restore_db.py)도 동일 지원 — 룰 배포 후 안전망 유지. ② **schema_version 게이트** — DB `{path}/schema_version`(정수, 스키마 v1.4=14)이 클라 `SCHEMA_MAX` 초과 시 차단(웹=차단 화면, PC·CM=에러 후 종료, Analyzer=경고만/read-only). 노드 부재·읽기 실패=통과(전환 전 호환·가용성 우선). ③ `database.rules.json` deny-by-default 초안(의도적으로 firebase.json 미연결 — 오발 배포 방지) + 전환 런북 `documents/SECURITY_RULES_PLAN.md`(클라 먼저 무장→노드 생성→룰 배포→검증→롤백 절차) |
| 8.15 | 2026-06-11 | **신뢰성/정합 일괄** ① **[웹] obs 동시쓰기 race 완화(C3)** — `pushObs(…,field)`가 날짜 객체 통째가 아니라 변경된 필드만 `obs/{nk}/{subj}/{date}` 키 단위 PATCH. 두 강사 동시 입력 시 서로 다른 태그 필드 충돌·유실 방지. ② **[웹·PC] 동명이인 오발송 가드(B4)** — 전송 직전 표시이름 중복 검사, 겹치는 이름 전원 자동 제외+안내(같은 '오직 {이름}' 방으로 합쳐져 타 학부모 발송되던 위험). DRW `_dedup_same_name`(데일리·발송 탭), CM `_send` 동일. ③ **[운영] 백업 월간 영구 스냅샷** — 매월 1일 백업은 30일 경과해도 보존(반 소속 등 장기 이력 소급 조회). ④ **잔재 정리(C4)** — DB `lastSent` 노드 삭제, 본문 lastSent 잔재·assignments 형식 정정(DRW_REQ §5, DB_SCHEMA v1.4 객체배열). Analyzer v0.3(nameKey-first 종단 비교)은 별도 repo |
| 8.14 | 2026-06-11 | **교재 명단 — 전역 레지스트리 + 관리자 관리 UI** `config/textbooks/{교재명}: true` 부활(문서 v3.3 노드) — classes와 독립이라 **반 전체 삭제에도 교재명 자동완성 보존**(학기 개편 대비). ① 과목 등록(addCourseInline/wzAddCourse) 시 `_registerTbName()` 자동 등록(공백 정규화·idempotent), ② 자동완성 datalist = 레지스트리 ∪ 현존 courses, **ko 오름차순 정렬**, ③ 관리자 설정 「📚 교재 명단」 섹션 — 목록(오름차순)+직접 추가+✕ 제거(자동완성 후보에서만 제외, 과목·기록 무영향), admin 가드. 기존 DB 과목(보관 포함)에서 15개 시드 완료 — 철자 변형 중복(SIGNATURE 100+/Signature100+/시그니처 100+ 등)은 관리자 UI로 정리 가능 |
| 8.13 | 2026-06-11 | **명단 권한 분리 — 학급·학생 CRUD 관리자 전용 (웹)** 관리자 시나리오 정리에 따라: 강사는 학급·학생 정보를 조회만, 추가/삭제는 관리자(`adminOn`)만. ① 학생 칩 ×(rmStu)·「+ 추가」(addStuInline)·「학급 삭제」(rmCls) UI를 admin 조건부 렌더, ② 함수 자체에 admin 가드 이중화(toast 안내), ③ **dev 도구(🔧 날짜 변경·🎲 더미) admin 게이트(A4)** — 일반 강사 오조작에 의한 운영 obs 오염 차단. 과목(교재) 등록·보관은 수업 소관이라 강사 유지. 역할 정리: 웹 일반=수업 운영(입력·성적·과목·본인 배정), 웹 관리자=교무 정정(오늘 입력/진도 정리·강사 관리·dev 도구), CM=명단 단일 소유(반·학생 CRUD·CSV·개편·일괄 발송). 이 분리는 C1 Security Rules 화이트리스트의 기준이 됨 |
| 8.12 | 2026-06-11 | **Analyzer 스탯 원료 불가침 원칙 — 관리자 초기화 파괴 동작 제거** 학기 개편(학급 삭제 후 재편성) 대비 점검에서 발견: ① 관리자 「전체 입력 삭제」가 `fbPut('obs',null)`로 **관찰 누적 전체를 파괴**(레이더/월간 리포트 원료 소멸) → 「전체 오늘 입력 삭제」로 재정의: input/ 전체 + obs는 **오늘 날짜키만** 전 학생·전 과목 정리, 누적 보존. ② 「명단 & 설정 삭제」의 `fbPut('students',null)` 제거 → 「강사 & 설정 삭제」로 재정의(명단은 CM 소관, 이력의 이름 해석 원료 보존). 불변식 확립: **obs/scores/history/students = Analyzer 원료, 웹·PC 어디서도 일괄 삭제 경로 없음.** 학급 삭제 개편 시에도 학생 grain 이력 전체 보존(반 이력 추적은 불요 결정 — 종단 비교는 nameKey 기준). 구형 과목 키 표시 문제는 known issue(개편 시 자연 해소) |
| 8.11 | 2026-06-11 | **전송 속도 「스마트」 모드 (기본값)** — 시스템 응답성을 실측해 자동 가감속. 신호 = 검증 게이트 자체("Enter→방 열림" 실측 t_open + 1차 재시도 여부). AIMD: 1차 실패 → wait ×1.6 즉시 감속 / 빠른 통과(≤0.2s) 연속 2회 → -0.15s 가속 / 지연 EMA>0.8s → 선제 +0.1s. 범위 [0.25, 1.2]s, 학습값 `smart_wait` config 영속(다음 실행 이어받음, 전송 종료 시 저장). 시뮬레이션 검증: 빠른 시스템 4명 내 하한 수렴, 실패 2회 시 0.64s 감속, 회복 8명 내 재수렴. 수동 고속/보통/안정은 고정 오버라이드로 유지. 게이트가 바닥을 받쳐 오발송 불가 — 적응은 1차 통과율만 조절 |
| 8.10 | 2026-06-11 | **전송 속도 프리셋 (설정 UI)** "대기 시간(초)" 숫자 입력 제거 → **고속/보통(권장)/안정** 3단 라디오. `send_speed` ∈ fast(0.3s)/normal(0.5s)/stable(1.0s) → `_send_wait()`가 1차 시도 마진으로 변환(검증 게이트가 실패를 흡수하므로 프리셋은 첫 시도 템포만 결정, 재시도는 항상 느린 프로파일). 저장 시 구 `wait_time` 키 제거. 안정=저사양/카톡 응답 지연 환경용 |
| 8.9 | 2026-06-11 | **이미지 클립보드 DIB 캐시 — 텍스트→이미지 간 지연 제거** 학생마다 PowerShell+.NET 기동(실측 ~2s)으로 이미지를 클립보드에 올리던 것이 체감 지연 원인. 1회 BMP 변환 후 DIB 바이트 캐시(mtime 검증) + ctypes `SetClipboardData(CF_DIB)` 직접 세팅 — **반복 복사 실측 2.07s → 1ms**. 전송 루프 시작 전 `prefetch_image()` 선행 변환으로 첫 학생도 무지연. 실패 시 기존 PowerShell SetImage 폴백. CM 동일 미러 |
| 8.8 | 2026-06-11 | **이미지 방 미닫음 정책** — 이미지 확인 후에도 업로드는 백그라운드 진행되므로 즉시 esc 시 카톡 "전송 중인 파일" 확인 팝업에 흐름이 막히고(확인 시 업로드 취소 위험) 8.7의 탈출 루프가 역효과. 정책 변경: **이미지를 보낸 방은 닫지 않고 유지**(업로드 자체 완료, 다음 학생은 메인 창 재포커스→검색으로 진행 — 방 창은 누적되나 무해), 텍스트만 보낸 방만 esc 탈출 루프 적용. CM 동일 미러 |
| 8.7 | 2026-06-11 | **이미지 전송 팝업 인지 + 방 탈출 보장** 이미지 붙여넣기 확인 팝업의 등장이 간헐적으로 지연되면 고정 대기 후 Enter가 헛발사 → 팝업 잔존 → 마지막 esc가 팝업에 먹혀 **방 탈출 실패, 다음 학생들 입력이 같은 방에 쏟아지던 문제**. `_send_image` 이벤트 기반 재구성 — ① 붙여넣기 후 팝업 등장 대기(전면이 방 제목을 벗어나는지 폴링, 최대 8s), 미등장 시 Enter 미발사+실패 처리(스트레이 입력 방지), ② 확인 Enter 후 팝업 닫힘 검증(최대 8s), 미종료 시 esc 취소+실패, ③ 전송 종료 시 **전면이 방을 벗어날 때까지 esc 반복(최대 4회)** — 한 방 갇힘 원천 차단. 실패 경로에 전면 창 제목 진단 로그. 비 Windows 는 레거시 고정 대기 유지. CM 동일 미러. 주의: 본문 전송 후 이미지 실패 시 학생은 실패 집계되나 본문은 이미 발송됨(재전송 시 본문 중복 가능) |
| 8.6 | 2026-06-11 | **카톡 전송 — 키워드 정합 + 속도 최적화** ① 실측 진단(send_debug.log)으로 본문 미발사 원인 확정: 방 이름 규칙은 "오직 XXX"(공백 1개)인데 `room_prefix` 설정이 strip 저장("오직")되며 검색어가 "오직XXX"로 생성. `get_room`이 prefix-이름 공백 1개를 보장하도록 정규화(설정 공백 유무 무관), 발송 탭의 직접 이어붙이기도 `get_room` 단일 경로로 통일. ② `room_opened` 검증은 **포함 비교(공백 무시)** — "오직 XXX"는 검색 키워드일 뿐 창 제목엔 친구명 등 혼재(실측). 메인 창·타 학생 방은 차단 유지. ③ **속도 최적화** — 검증 게이트 전제로 고정 마진 축소: 빠른 1차 시도(키 간격 ~0.15s·검색 로딩 max(0.3,wait)·Enter 후 0.1s+폴링 0.1s 간격) → 실패 시에만 느린 프로파일 재시도, 본문 전송 0.35s→0.35s, 학생 간 간격 0.8→0.3s, `focus_kakao` 빠른 경로(이미 전면이면 즉시 통과). 학생당 체감 ~3.4s→~1.6s. CM `kakao_send.py` 동일 미러 |
| 8.5 | 2026-06-11 | **카톡 순차 전송 검증 게이트 — 연쇄 오류(단일 방 연속 전송·미전송) 차단** 검색→Enter 후 방이 실제 열렸는지 확인 없이 본문을 붙여넣던 것이 원인: 타이밍 한 번 밀리면 본문이 검색창/이전 방으로 발사돼 연쇄. `_kakao_send_one` 재구성 — ① `copy_text_verified()`: 클립보드 반영 폴링 확인(이전 내용 붙여넣기 레이스 차단), ② `room_opened()`: 전면 창 제목=방 이름 폴링 검증(그룹방 인원수 표기 허용) — **미확인 시 본문 미발사**, ③ 실패 시 검색 정리+메인 재포커스 후 대기 늘려 1회 재시도, 그래도 실패면 예외 → 해당 학생만 실패 집계(연쇄 차단, 오방 전송도 차단). 본문 클립보드도 검증. ClassManager `kakao_send.py` 동일 미러. 헬퍼: `kakao_image.foreground_title/room_opened/copy_text_verified` |
| 8.4 | 2026-06-11 | **카카오톡 창 자동 포커스 — 간헐 전송 오류 근본 대응** 기존 "전송 시작 후 3초 내 카톡 창 직접 클릭" 의존이 간헐 오류 최다 원인(실패 시 키 입력이 엉뚱한 창으로). `kakao_image.focus_kakao()` 신설 — Win32 EnumWindows로 카톡 메인 창(제목 '카카오톡'/'KakaoTalk', class `EVA_Window_Dblclk` 우선) 탐지, **트레이 상태(invisible)도 SW_RESTORE 복원**, ALT 탭 후 SetForegroundWindow + 전면 검증. `_do_send`/`_do_bulk_send`: 3초 카운트다운 → 1초 취소 여유+자동 포커스(실패 시 키 입력 없이 안전 중단, 데이터 유지), **매 학생 전 재포커스**(전송 중 사용자 개입 복구, 소실 시 해당 지점 중단+안내). 버튼/다이얼로그 문구에서 수동 클릭 지시 제거. ClassManager `kakao_send.py`에도 동일 구현(매 건 재포커스, done_cb는 실제 성공 건수). 실기 검증: 트레이 숨김 카톡 복원·전면화 성공 |
| 8.3 | 2026-06-11 | **메시지 발송 기본 빌트인 템플릿** `storage.DEFAULT_TEMPLATES` 5종(일반 공지·휴원/일정 변경·시험 안내·결석 보강 안내·교재 준비 안내, 변수 {이름}{반}{날짜}) — `templates.json` 없거나 비어 있을 때만 시드, 사용자 수정·삭제분은 재주입 안 함. CM도 동일 정책으로 6종(공통 5 + 성적 통보 score형) — `ClassManager/template_engine.DEFAULT_TEMPLATES` |
| 8.2 | 2026-06-11 | **신뢰성 일괄 수정 (v2.2.3 개발 라인)** ① **[웹] 주간성적 입력 차단 해제** — `_canInputWeekly`가 `course.instructor` 필드로 판정했으나 과목 등록이 이 필드를 저장한 적 없어(실DB 36과목 전부 미보유) 반별 시험 저장이 전원 차단되던 버그. 담당 수업 배정(assignments) 기준으로 교체(`_canInputAchievement`와 동일 모델). ② **[웹] write 실패 표면화** — 핵심 입력 3종(과제수행도/메모·진도/과제·관찰태그)의 무음 실패(`setSync` no-op)와 설정·성적·초기화의 `.catch(()=>{})` 21곳을 `fbFail(label)` toast로 일괄 교체. 로컬 저장은 유지되므로 재시도 안내. ③ **[PC] 전송 시 특이사항 유실 가드** — `_push_history`의 history 기록+`__note__` 소거를 루트 단일 multi-path PATCH로 원자화(실패 시 둘 다 미적용 → note 보존, 경고 팝업). `_do_send` 카톡 예외 학생을 sent에서 제외하고 실패 명단 표시, 실패 존재 시 로컬 초기화 보류(재전송 가능). ④ [CM] 성적통지 nameKey/meta 버그 수정은 ClassManager repo(template_engine v2.0 스키마 대응 + 회귀 테스트 3종) 참조 |
| 8.1 | 2026-06-11 | **운영: DB 일일 백업 체계 (A1)** `code/scripts/backup_db.py`(루트 전체 스냅샷 → `scripts/backup/drw2_*.json`, 30일 보존, git 제외) + `restore_db.py`(노드/전체 복원, dry-run 기본, 복원 전 현재 상태 자동 저장) + `register_backup_task.ps1`(작업 스케줄러 매일 14:00, 미실행 시 보충). Security Rules 도입 전 데이터 유실 대비 안전망. 호스팅은 하위호환 버전(v2.2.2)만 공개 — 구버전 ignore+redirect(`firebase.json`), 개발 라인 v2.2.3 신설 |
| 8.0 | 2026-06-10 | **과목 소프트 삭제(archived) + classes 전체 PUT 제거 (v2.2.2)** ① 웹 `rmCourse`가 하드 삭제(`fbPut null`) 대신 **`classes/{classId}/courses/{subject}/archived: true` 마킹** — obs/scores/history/session 기록을 DB에 보존하면서 표시·입력·전송에서만 제외(웹 `activeCourses()`, PC `firebase.active_courses()` 공통 필터). 같은 과정·교재 재추가 시 `archived:null` PATCH로 **복원**(기존 기록 그대로 연결, `addCourseInline`/`wzAddCourse` 중복 검사도 archived 구분). Analyzer는 course 노드가 보존되므로 보관 과목의 과거 기록 조인 가능. 관리자 과목 목록은 보관 과목을 「보관」 배지로 표시. `_canInputWeekly`·`_syncAssignments`·PC 가져오기 방어필터 모두 활성 과목 기준. 실패 시 무음이던 `rmCourse` DB 쓰기에 toast+로컬 롤백 추가. ② **`pushCfg()`(classes 노드 전체 PUT) 제거** — stale 로컬 config를 가진 다른 기기가 삭제된 과목을 통째 부활시키던 버그 원인(3MAXIMO 사례). `rmCls`는 해당 학급 노드만 타겟 `fbPut null`로 전환, 죽은 코드 `addCls`/`addCourse`(prompt형) 삭제. 기존 3MAXIMO 잔존 과목 2건(공통수학1 시험직전R·대수 RPM)은 DB에서 archived 마킹 완료 |
| 7.9 | 2026-06-08 | **특이사항 전송 시 소거 — 당일 소비 모델 (v2.2.0)** `input/{nameKey}/__note__`(특이사항)가 날짜 무관 단일 필드라 전송 후에도 영속 → 다음 가져오기 시 옛 메모가 잔류하던 문제. 전송 확정 시점(`_push_history`)에 ① 메시지 최종 note → `history/`(기존), ② **원본 입력 note `input/{nameKey}/__note__` → null 소거**(신규, 단일 원자적 multi-path PATCH). 특이사항이 obs(날짜별)처럼 "당일 소비"로 동작 → 다음날/가져오기 fresh. PC의 input/ 쓰기는 전송된 학생 `__note__` 소거만 허용(CLAUDE.md 규칙 반영) |
| 7.8 | 2026-06-08 | **진도/과제 메시지 제외 토글 + 버그픽스 (v2.2.0)** ① 데일리 탭 중앙 패널 "오늘 수업(반 공통)" 과목별 **`✕ 메시지서 제외`** 토글 — 전날 잔류 진도/과제 등 불필요 데이터를 담임이 이번 전송 메시지서 제외(메모리 `exclude_prog`, DB·readiness 무관, 전송/가져오기 시 리셋). `_class_info_for()` 공통 헬퍼로 preview·전송 일관. 부담임은 토글 미표시. ② **빈 웹 note 미반영 버그** — `_import_mobile_data` `if final` 가드 제거, `__note__` 빈값도 항상 덮어씀(기존 기록 잔류 방지). ③ **AI 일괄생성 진행 팝업 잔류 버그** — OK 모달 → 자동 소멸 modeless Toplevel, 완료/에러 시 `_close_prog()`. ④ **삭제된 과목 진도/과제 고아 read 버그** — 웹 `rmCourse`가 `classes/courses`만 지우고 `session/class_data/{classId\|subject}`는 잔류시켜 PC가 계속 read하던 문제. (a) PC 가져오기 시 **현존 `courses`에 없는 pkey 무시**(방어 필터), (b) 웹 과목 삭제 시 `session/class_data` 동반 null PATCH(예방), (c) 기존 고아 11건 1회 청소 |
| 7.7 | 2026-06-08 | **메시지 발송 탭 신설 — ClassManager 발송 기능 이식 (v2.2.0)** 메인 UI를 `ttk.Notebook` 2탭 구조로 전환(헤더/크레딧은 상단 고정). ① **탭1 「📋 데일리 리포트」** = 기존 시트바+3패널+상태바+푸터 워크플로우 그대로(빌더 4개에 `parent` 인자 추가, 동작·레이아웃 무변경). ② **탭2 「✉ 메시지 발송」** 신설(§2.13) — **담당 학생 전체**(`_my_classes('M')+_my_classes('T')`, 부담임🔒 반 제외, nameKey 중복 제거)를 반별 체크박스로 제공, `{이름}{반}{날짜}` 변수 템플릿(`templates.json` 로컬 영속)·미리보기·**이미지 첨부**(본문↔이미지 순서 토글) 후 카톡 일괄 전송. 데일리 전용 부수효과(`history/` 기록·전송 후 초기화)는 **호출 안 함** — 일반 공지/안내 발송 전용. ③ 카톡 키 시퀀스를 `_kakao_send_one(m, wait, warm)` 공용 헬퍼로 추출 — `_do_send`(데일리)·`_do_bulk_send`(발송 탭) 공유, 이미지 송신(`copy_image_to_clipboard`+붙여넣기, `img_wait=max(wait,1.0)`) 일원화. 신규 모듈 `kakao_image.py`, `message.render/build_bulk_ctx/bulk_variables`, `storage.load_templates/save_templates`. ④ **⚙ 설정 버튼을 노트북 탭 행 우측으로 이동** — 기존 데일리 탭 시트바에서 분리, 두 탭이 공유하는 전역 설정(Firebase·강사·AI키·room_prefix·wait_time)이라 탭과 동일 행(노트북 탭 스트립) 우측에 `place(in_=nb, relx=1.0, anchor='ne')` 오버레이로 배치. M/T·📥 가져오기·🗑 초기화는 데일리 워크플로우 컨트롤이라 탭 내 유지 |
| 7.6 | 2026-06-06 | **DB 재구조화 — Analyzer 정합 + 전송 코멘트 누적 (v2.1.2)** ① `history/{nameKey}/{YYYY-MM-DD}={note,instructor}` 신규 — PC가 **전송 확정 시점(카톡 루프 이전, 전송 성패 무관)**에 단일 원자적 multi-path PATCH로 기록(학생 grain, todayKey). 카톡 전송 중 abort/크래시에도 이력 보존. AI 월간 리포트 반복 회피·맥락 소스. ② `lastSent/` 폐기(빈 껍데기), 가져오기 폴백 제거. ③ `input/.assign` 죽은 필드 + 레거시 `onPB` 제거 — 과제수행도는 `obs/assign_grade` 단일 소스. ④ 로컬 캐시 간소화 — `class_data`(진도/과제)만 디스크 영속, student/note/force는 메모리만(죽은 I/O 제거). ⑤ Firebase 스키마 섹션 실구조로 정정(누적 obs/scores/history vs 휘발 input/session, 날짜포맷 이원화 명시). ⑥ PC 쓰기 규칙 개정 — `history/` 허용. ⑦ DB 마이그레이션(`scripts/migrate_v2_1_2.py`): 구 과목별 note→`__note__` 통합, 죽은 assign 제거, lastSent 삭제 |
| 7.5 | 2026-06-06 | **PC 학생별 선택 관찰 태그 표시 (v2.1.2)** — 웹에서 선택한 오늘 `obs/` 태그를 PC 중앙 패널 교재별 수행도 도트 줄 아래 **한 줄 압축**으로 읽기 전용 표시. 순서 컨디션→이해도(+세부)→참여→기타→하이라이트→주의, 하이라이트=초록·주의=빨강 강조, 빈 경우 생략. `_obs_tag_segments()`/`_render_obs_tags()` 신설. 기존 `tag_data`(obs 로드) 재사용 — AI 생성에만 쓰이던 데이터를 화면에도 노출 |
| 7.4 | 2026-06-06 | **특이사항 학생별 단일 필드로 정리 (v2.1.1)** — 과목별로 흩어져 입력·저장되던 특이사항을 학생 종속 단일 필드로 환원. 웹 쓰기/읽기 모두 `input/{nameKey}/__note__`(`{note}`) 사용, 과목 화면 어디서 입력해도 동일 값 공유. 과제수행도(`assign`)만 과목별 유지. PC `_import_mobile_data`는 `__note__`만 `note_data[(classId,nameKey)]`로 적재하고 실 과목 루프에서 note 제외(기존 last-non-empty-subject 덮어쓰기 모호성 제거). 구 과목별 note 데이터는 웹·PC 양쪽 fallback으로 1건 보존(마이그레이션). 초기화 시 `__note__` 학생당 1회 null PATCH 추가 |
| 7.3 | 2026-06-04 | **카톡 순차 전송 첫 학생 오작동 수정** — 3초 카운트다운 종료 직후 첫 학생 전송 시 카톡 창 포커스/검색창 안정화 전에 `ctrl+f`·붙여넣기가 발사돼 첫 명만 오작동(검색 실패·엉뚱한 입력)하던 레이스 수정. `_do_send` 루프 첫 반복(`i==0`)에 워밍업 지연 `warm=0.6s` 추가 — `room` 클립보드 복사 후 `warm`초 대기, 첫 `ctrl+f` 후 `0.2+warm`초 대기로 창 포커스 정착 보장. 2번째 학생부터는 `warm=0`(기존 타이밍 유지). `wait_time` 설정과 독립 |
| 7.2 | 2026-06-03 | **룩앤필 리뉴얼 — 미니멀·프로 디자인 시스템 (웹+PC)** — 통일된 디자인 토큰 도입: 중성 표면 3단(`--bg`/`--panel`/`--panel-2`), 잉크 위계(`--text`/`--sub`/`--gray`), 라인 2단, 절제된 인디고 액센트(`--indigo` #4F46E5 / `--indigo-ink` #4338CA), 반경 3단, 그림자 3단. **웹**: `app.css` `:root` 토큰 교체로 전 화면 일괄 리스킨(JS 무변경, 클래스명 유지) + 사이드바(다크 #0E1016·라운드 nav·계정 카드)·카드(부드러운 그림자)·버튼·입력(포커스 링)·관찰 태그칩(`.tg-radio`/`.tg-check` 통일, 색상 의미 보존)·학생 슬림카드·설정 아코디언(아이콘 타일)·성적 카드 폴리시. **PC**: `constants.py` 팔레트 교체 + `app.py` 하드코딩 hex 스윕(표면·시맨틱 톤 정렬). 시안은 분리 사이트 `code/public/redesign/`에서 선검증. 액센트는 인디고 유지 |
| 7.1 | 2026-06-03 | **PC 클라이언트 최초 설치 위저드(온보딩) 신설** — 기존 단일 안내 messagebox(`_prompt_first_run`)를 3단계 순차 위저드로 교체(§2.9-B). **팝업 아닌 메인 창 오버레이** 방식 — 정상 UI 빌드를 `_build_main_ui`로 분리하고 최초 실행 시 메인 창에 위저드 오버레이(`_wz_root`)만 띄움 → 완료 시 오버레이 destroy + 정상 3-패널 빌드(웹 위저드와 동일한 단일 창 레이아웃 분기). 단계: ①🔥Firebase 연결(+⚡테스트) ②🔑강사 계정(조회/등록+동기화) ③🤖AI 엔진+API키(건너뛰기 가능) → 🎉완료(요약+웹 명단 안내). 웹 위저드(§4.8-C)와 동일 컨셉, **학생 명단·수업 배정 단계는 웹 전용이라 제외**하고 **AI 엔진 키 단계 추가**(PC 전용). **엔진별 키 발급 가이드 인라인화** — AI키 단계서 엔진 선택 시 발급처/단계/키형식/주의를 위저드 안에 직접 표시(`_WZ_GUIDE`, guide.html 4부 발췌, `webbrowser.open` 링크), "가이드 참고"로 떠넘기지 않음. 스텝 인디케이터는 `tk.Canvas` 원+연결선 직접 드로잉(`_wz_draw_steps`). 단계 가드(0:URL·경로, 1:instructor_id). 신규 함수 `_run_setup_wizard`/`_wz_*` 일괄(`app.py`), 기존 `make_scroll_frame`·팔레트·폰트 재사용 |
| 7.0 | 2026-06-03 | **초기 설정 위저드(온보딩) 신설** (웹 PWA) — 강사 미설정 신규 사용자의 빈 화면+단일 버튼을 4단계 순차 가이드로 대체. `init()` `!instructor` 시 `wizardActive=true`로 위저드 발동, `renderMain()` 최상단 분기로 위저드 활성 중 탭 이탈 차단. 단계: ①🔥 Firebase 연결(`saveFb`) ②🔑 계정(`lookupInstr`) ③👥 명단(`loadCfg`) ④📚 담당 수업(`addA`). 입력 DOM ID를 기존 설정 화면과 동일하게 두어 기존 핸들러 무수정 재사용. **교재 미등록 케이스 처리(핵심)** — 수업 배정 단계서 선택 반에 등록된 과목 없으면 인라인 과목(교재) 등록 폼(`wzGs`/`wzTb` → `wzAddCourse()`, `subject="{과정} {교재}"`, `addCourseInline` 미러) 노출 후 즉시 배정 가능. 반(classId) 생성은 위저드 범위 외(기존 학급 관리). 단계 가드(0:Firebase 미저장, 1:강사 미등록 차단), 완료 요약 체크리스트(`wzFinish`), "나중에 할게요" 이탈(`wzSkip`→설정). 상태 변수 `wizardActive`/`wzStep`/`wzCls`(`app-core.js`), `renderWizard`/`_wzPane`/`wzNext`/`wzBack`/`wzSkip`/`wzFinish`/`wzSetCls`/`wzAddCourse`(`app-settings.js`), CSS `.wz-*`/`.stp*`(`app.css`). index.html 캐시버전 `202606031200` 갱신 |
| 1.0 | 2026-05-19 | v0.9.0 통합 명세 작성 |
| 1.1 | 2026-05-19 | v0.9.1 버그픽스 반영 |
| 1.2 | 2026-05-19 | v0.9.2 담당 반 필터링·쓰기 권한 가드 |
| 1.3 | 2026-05-20 | v0.9.3 가져오기 정책 고정 / v0.9.4 웹 초기화 보안 |
| 2.0 | 2026-05-21 | DRW 2.0 — 입력 데이터 다각화, DailyReportAnalyzer 연계 목적 |
| 3.0 | 2026-05-23 | DRW_REQUIREMENTS + DRW2_REQUIREMENTS 통합. 모듈 구조 반영. 멀티 AI 엔진 반영. 구버전 잔재 정리 |
| 3.1 | 2026-05-24 | 버그 수정 반영 (extra_notes NameError / _do_send 스레드 안전성 / _fetch_class_data 경로 / nickname_suffix / 연결 테스트). _open_progress_window dead code 제거 |
| 3.2 | 2026-05-24 | AI 생성 품질 개선 (few-shot 예시·system prompt 분리·temperature 0.75·caution 완곡화·highlight 태그 신설). obs→tag 변수명 정리. preset "추가 자율학습 실시" 제거 |
| 3.3 | 2026-05-24 | 교재 레지스트리(`cfg.textbooks`) 신설. 진도 cascade 피커·과제 피커 UX 구현. CURRICULUM 상수·GRADE_SEM_LIST 추가. 학년학기 표시 형식 통일(중3-1 스타일). stripIdx() 단원 번호 제거. 설정 입력창 Enter 키 지원. 교재 chip 학년학기 배지 표시 |
| 3.4 | 2026-05-24 | 교재 매트릭스 구조 변경. `cfg.textbooks={name:true}` (이름 레지스트리, grade_sem 분리). `cfg.sheets[sh].classes[cls].tb_grade={교재명:grade_sem}` per-class 구조 신설. 학급 교재 추가 시 레지스트리에 없으면 즉시 등록. 교재관리 메뉴에서 학년정보 제거 |
| 3.5 | 2026-05-24 | PC 앱 grade_sem 전파. `build_message(tb_grade=)` 파라미터 추가 — 멀티교재 시 `[중1-1 최상위수학]` 레이블. `_render_student` LabelFrame/진도섹션 grade_sem 표시. `build_single_prompt`/`gen_single`/`gen_all` tb_grade 전달 — AI 프롬프트에 과정명 포함 |
| 3.6 | 2026-05-24 | CURRICULUM 상수 단원명 정비. 수식(`y=ax²`, `0/0`, `1cm³` 등) 제거. 영어 괄호(`(Permutation)`, `(SSS, SAS, ASA)`, `(라디안)` 등) 제거. 교육학적 군더더기("의 도입", "알아보기") 제거. 과도하게 긴 설명구 단축. 비문 교정("자료을"→"자료를"). 단원명 전체 비문 없는 간결한 한국어로 통일 |
| 3.7 | 2026-05-24 | 웹 과제 입력/선택 시 확대 방지. `hw-num`, `hw-free` font-size를 16px로 지정하고, 터치 컨트롤에 `touch-action: manipulation` 적용. 과제수행도(`.px`)와 과제 타입(`.hw-tb`) 버튼은 색상만 전환하고 크기는 고정 |
| 3.8 | 2026-05-24 | 교재 매트릭스 저장 보강. 설정의 교재 목록은 전역 `config/textbooks`에 저장하고 모든 학년학기/학급 교재 추가에서 동일 목록을 읽음. 학년학기 값은 학급별 `tb_grade`에만 저장 |
| 3.9 | 2026-05-24 | 웹 설정 학급 관리에서 `M`/`T` 기본 시트 보장. Firebase/로컬 config에 한쪽 시트가 누락되어도 `_ensureConfigShape()`로 `M`, `T`를 복원하고 전체 학급 탐색에 항상 표시 |
| 4.0 | 2026-05-24 | PC 데이터 가져오기 정책 변경. 웹에서 직접 수정한 메모(`__note__`)가 PC에 즉시 반영되도록 메모/특이사항도 항상 웹 데이터로 교체 |
| 4.1 | 2026-05-24 | 단건 AI 생성 전 현재 특이사항 `Text` 위젯 값을 `note_data`에 즉시 동기화. FocusOut 전 작성한 메모도 프롬프트 `[기존 특이사항 참고]`에 반영 |
| 4.2 | 2026-05-24 | AI 프롬프트에서 직접 작성 메모 중요도 상향. `[기존 특이사항 참고]`를 `[직접 작성 메모 — 반드시 반영]`으로 변경하고 작성 지침/일괄 JSON 필드에 반드시 포함 규칙 추가 |
| 4.3 | 2026-05-24 | AI 프롬프트에서 기타(`extra`) 태그 중요도 상향. 자율학습·주간Test·재시험은 다른 수업 묘사와 섞지 않고 별도 문장으로 강조하도록 지침 추가 |
| 4.4 | 2026-05-24 | 웹 커리큘럼 데이터 외부화. `app.js` 하드코딩 `CURRICULUM` 제거, `code/public/data/math-curriculum-2022.json`을 `fetch()`로 로드 후 앱 내부 `{grade_sem:[{main,subs}]}` 형태로 정규화 |
| 4.5 | 2026-05-24 | 커리큘럼 목차 미표시 버그픽스. fetch() → file:// 환경 CORS 차단 문제. `data/curriculum.js`(`const CURRICULUM_RAW=...`) 분리 후 `<script src>` 로드로 전환. app.js fetch 의존성 제거. file:// · HTTP 서버 · GitHub Pages 모든 환경 동작 |
| 4.6 | 2026-05-24 | `curriculum.js` 단원명 순번 및 수식 제거. `"Ⅰ. 실수와 그 연산"` → `"실수와 그 연산"`, `×`/`÷` → 한국어 서술, `y=ax^2` → `"기본형 이차함수의 그래프 성질"` 등. `stripIdx()`는 기존 저장값 호환용으로 유지 |
| 4.7 | 2026-05-24 | 학급 삭제 시 담당 수업 cascade 삭제. `rmCls()`에서 `instructor.assignments` 중 해당 `sheet|cls` 항목 자동 제거 및 Firebase 동기화 |
| 4.8 | 2026-05-24 | 교재·강사 목록 가나다순 정렬. 교재 삭제 시 assignments cascade 정리. `_my_classes()` 버그픽스 — instructor_id 설정 + assignments=[] 시 전체 반 노출 오류. `_sync_shared_sheets_from_firebase()` 전면 개선 — 시작 시 `config/` 전체 읽어 sheets + instructor assignments 동시 동기화. `_fetch_class_data` save_config·_switch_sheet 누락 수정. `_pull_mobile_data` session 폴백 버그픽스 — `session` 노드 자체 없을 때만 `lastSent` 폴백. 노드 존재 + `class_data` 비어있으면(의도적 초기화) 폴백 없이 빈 데이터 처리 |
| 4.9 | 2026-05-24 | 진도 저장값 소단원만 저장. `pgBuild()` — 소단원 선택 시 `소단원`만, 단원 전체 선택 시 `대단원`만 저장 (기존 `"대단원 › 소단원"` 복합 저장 폐기) |
| 5.0 | 2026-05-25 | 웹 성적 입력 탭 구현. `scores/` Firebase 노드 쓰기. 시험 유형 6종(주간Test·기출모의고사·실전모의고사·성취도평가·반배치고사·직접입력), 회차·날짜·만점·메모·반 전체 일괄 입력, 백분율·반평균·최고·최저 실시간 산출. `goNav('scores')`, `scoreData`, `SCORE_TYPES`, `_renderScoreList/Edit`, `_saveScore`, `_deleteScore` 신설 |
| 5.1 | 2026-05-25 | 가져오기 알고리즘 간소화. `_pull_mobile_data()` 시작 시 `student_data`, `note_data`, `progress_data`, `force_data` 전부 clear 후 Firebase 데이터만 채움. 로컬 잔류 데이터 병합 로직 제거 |
| 5.2 | 2026-05-25 | 관찰 태그 대폭 개편. ① 과제 고정 등급 3→5단계(`done/most/half/little/none`). ② 컨디션 4→5단계(PES 화살표 스타일, `low` 추가). ③ 이해도 3→5단계(`top/good/normal_u/confused/hard`). ④ 하이라이트 단일→복수선택 전환(배열 저장). ⑤ 버튼 UX: 택1=pill(tg-radio), 복수=dashed square(tg-check). ⑥ 기본 프리셋 11→7개로 정리(`오답 풀이 안함` 추가). ⑦ PC 앱 A안: `obs/assign_grade` → `student_data` 매핑(`ASSIGN_GRADE_LABELS`). ⑧ `ai_engine.py` condition/understand/highlight 키 현행화 |
| 5.3 | 2026-05-25 | PC 앱 과제 데이터 통합 고도화. ① `ASSIGN_GRADE_LABELS` 전문 라벨 확정(`과제 완료/대부분 수행/절반 수행/일부 수행/미수행`). ② `app.py` obs 매핑에 `assign_tags` 복수 추가 — `assign_grade` 라벨 + 다중 선택 태그를 `" / "` 구분자로 결합(`"대부분 수행 / 교재 미지참 / 오답 풀이 안함"` 형태). ③ Firebase `assign_tags` 배열·딕셔너리 이중 구조 모두 대응(배열이면 직접 사용, dict이면 키 정렬 후 값 추출) |
| 5.5 | 2026-05-25 | 초기화 기능 수정. ① `tags` 초기화 obs 키 수정(`sheet\|cls\|name` → `sheet\|cls\|name\|tb`) — 구버전 키로 인해 tagData 조회 실패, 아무것도 삭제 안 되던 버그. ② 초기화 항목 재정의: "수행도 & 특이사항"을 "수행도 & 관찰 태그"(obs 전체)와 "특이사항 메모"(inputData notes만)로 분리 — v2.0에서 수행도가 obs/에 저장되므로 기존 `input` 초기화로 수행도 삭제 불가였던 혼동 해소. ③ `input` 초기화는 `__note__` 키만 삭제하도록 축소. ④ 관리자 `all-input` 초기화에 `obs/` 노드 삭제 추가(`tagData={}`, `fbPut('obs',null)`) |
| 6.0 | 2026-05-27 | **DB 구조 전면 재설계** — 반 중심 → 학생 중심. 변수명 일괄 변경 (`sheet`→`group`, `cls`→`classId`, `tb`→`subject`, `cfg`→`config`, `okey` 제거 등). Firebase 경로 전면 변경. scores 노드 weekly/achievement 분리. 교재 등록 권한 강사로 명확화. 성적 입력 권한 분리 (반별=담당강사, 학년단위=담임). |
| 6.1 | 2026-05-28 | **nameKey = 출결번호** — 이름 기반 키 + 동명이인 suffix 로직 폐기. 출결번호(불변 고유번호)를 Firebase 학생 키로 사용. ClassManager에서 발부 및 CSV 관리. |
| 6.4 | 2026-05-29 | **전체 AI 생성 버그픽스** — `gen_all`이 `system=_base_conditions()` 전달 시 규칙 #10("JSON 금지")이 배치 JSON 응답 요구와 충돌 → 파싱 실패. 배치 호출은 `system=""` 로 변경 (`build_batch_prompt` 자체에 지침 내장) |
| 6.5 | 2026-05-30 | **무료 AI 엔진 Gemini 탑재** — `_call_ai_hub`에 `gemini` 분기 추가(`gemini-2.5-flash`, 무료 티어, 월 제한 없음·일당 RPD만). key=URL 쿼리파람, `system_instruction` 사용, **`thinkingConfig.thinkingBudget=0` 필수**(미설정 시 출력 잘림). 모델 `GEMINI_MODEL` 상수화. `AI_FREE_ENGINES=('groq','gemini')` 신설 — 쿨다운 무료군 판정 일원화(3곳: `_check_cooldown`/`_start_cooldown_tick`/app.py 버튼 초기화). 설정 combobox에 `gemini` 추가, `gemini_api_key` 저장키 추가. 배치 `max_tokens` 4096→8192 상향(학생당 ~68토큰 실측, 40명 잘림 없음 검증) |
| 6.9 | 2026-05-30 | **학생 명단 이름순 렌더링 (PC 클라이언트)** — 모든 학생 명단(좌측 목록·전송 대상 다이얼로그·상태바·◀▶ 이동)을 이름 가나다 오름차순 표시. 기존엔 Firebase REST가 반환하는 nameKey(출결번호) 사전순. **최소 변경**: `_sync_shared_sheets_from_firebase`의 `all_students` 할당 1곳에서 `dict(sorted(...))` 정렬 → 5개 빌더 루프·네비게이션·다이얼로그가 모두 순서 상속, 개별 정렬 불필요(빌더 불일치 버그 원천 차단). **키 불변(표시 순서만)**, None-safe(`name` 폴백 `''`) + 동명이인 `nameKey` tiebreak. 반 정렬은 미적용. **웹도 동일 적용** — `app-core.js`에 공유 헬퍼 `sortStu(arr)`(가나다 `localeCompare(_,'ko')` + nameKey tiebreak) 신설, `_classStudents` 빌드 2곳(`app-settings.js`·`app-scores.js`) + 학생 추가 push 1곳(`app-settings.js`)에서 호출 → 웹 입력·성적·설정 명단 전부 이름순 |
| 6.8 | 2026-05-30 | **카톡 전송 개선 (PC 클라이언트)** — ① **대상자 개별 제외**: 🚀 전송 시 기존 `askyesno` 텍스트 확인 → `_open_send_dialog()` 체크박스 모달로 교체. 준비 완료 학생 전체 기본 체크, 체크 해제 = 이번 전송만 제외(상태 미변경), [전체 선택]/[전체 해제] 버튼, 선택 0명 차단. ② **순차 전송 취소**: `self._send_cancel`(`threading.Event`) 신설. 전송 시작 후 `send_btn` → "⏹ 전송 취소" 토글(`_set_send_btn_cancel`/`_cancel_send`). 3초 카운트다운(0.1s×30)·전송 루프 매 학생 진입 시 검사 → 현재 학생 완료 후 중단. 취소 시 전송된 N명만 발송하고 **로컬 초기화 생략**(미전송분 유지), 완료 시에만 기존 초기화+`lastSent/` push. §2.8 갱신. ③ 웹 변경분 델타 가져오기 — 차기 과제로 보류 |
| 6.7 | 2026-05-30 | **과정명 중복 표시 버그픽스 (PC 클라이언트)** — subject 키가 신 포맷(`{과정} {교재}`, 예 `중3-1 라이트쎈`)인 과목에서 PC 화면·카톡 메시지·AI 프롬프트가 과정명을 한 번 더 prepend해 `중3-1 중3-1 라이트쎈`으로 중복되던 문제. 원인: subject 키 포맷이 구(키=교재명, curriculum 별도)·신(키=`과정 교재` 조합) 두 가지 공존(`app-settings.js`). `constants.grade_label(grade_sem, subject)` 헬퍼 신설 — 키가 이미 `"{과정} "`로 시작하면 과정명 prepend 생략. `app.py`(진도/과목 라벨 2곳)·`message.py`(`tb_label`)·`ai_engine.py`(단건 프롬프트·배치 student·progress 3곳) 총 6곳을 헬퍼로 일원화. 구 포맷 과목은 기존과 동일 표시 |
| 6.6 | 2026-05-30 | **엔진별 API Key 격리 버그픽스** — `ai_api_key` 공유 폴백이 엔진 전환 시 타 엔진 키를 노출·저장하던 문제. `_get_engine_settings`/`_key_for_engine`/`_save_all` 모두 엔진별 슬롯(`{engine}_api_key`) 전용으로 변경, `ai_api_key` read/write 제거(deprecated). **설정 엔진 목록 순서 재조정**: `gemini → claude → openai → groq`(무료·추천 우선). **가이드 문서**(`public/guide.html`) AI 키 발급 가이드를 설치 가이드 내 "4부 · AI 엔진 키 발급"으로 편입(별도 최상위 탭 제거), 엔진별 서브탭으로 발급 가이드 + 앱 등록 절차 + 비교표 제공. **엔진 표시 명칭 공식 영문 통일**(웹 가이드 + PC 클라이언트 공통): `AI_ENGINE_LABELS = {gemini:'Gemini', claude:'Claude', openai:'GPT (OpenAI)', groq:'Groq'}`, `AI_ENGINE_ORDER`로 표시 순서 관리. PC 설정 드롭다운은 표시명을 보이고 내부 id로 매핑(저장값·API 분기·키 슬롯은 기존 소문자 id 유지). 일괄생성 확인창·키 미입력 경고도 표시명 사용. **엔진별 쿨다운 분리** — `AI_COOLDOWNS={groq:30, gemini:7}`(그 외 PAID 3초)로 전환, 기존 `AI_FREE_ENGINES` 일괄 30초 판정 폐기(Gemini free RPM~10 → 7초로 완화, 3곳 동일 적용). Firebase Hosting 배포 |
| 6.3 | 2026-05-29 | **부담임 필터링 버그픽스** — `_is_sub_teacher()` 가 `cls` 키만 검사해 `classId` 키 assignment에서 role 못 읽던 문제. `a.get('cls') or a.get('classId','')` 로 수정 — 카톡 전송·AI 일괄생성 대상에서 부담임 반 올바르게 제외 |
| 6.2 | 2026-05-28 | **소형 화면 차단 기준 완화 후 임시 비활성** — 기준 11인치급(1024px) → 9인치급(840px, `max-width:1023px`→`839px`, 1024×9/11≈838→840) 계산. 이후 **전면 개방**: 차단 미디어쿼리 주석 처리(`@media(max-width:839px)`)로 모든 해상도 접근 허용. 복구 시 839px 기준 재적용. index.html 안내 문구·헤더 주석 동기화. 추가로 `#scr-mask` div 자체 주석 처리(`file://` 크롬 css 캐시로 css 주석만으론 미반영되던 문제 회피). 빈 화면 원인 추적용 임시 JS 에러 표시기(`window.onerror`/`unhandledrejection` → 화면 빨간 박스) 삽입 — 해결 후 제거 예정 |
| 5.9 | 2026-05-25 | Claude 프롬프트 캐싱 적용. `Anthropic-Beta: prompt-caching-2024-07-31` 헤더 추가. system 필드를 배열+`cache_control: ephemeral` 구조로 변경 — 전체 AI생성 시 학생 수만큼 반복 호출되는 `_base_conditions()` 캐시 히트로 input 토큰 ~90% 절감 |
| 5.8 | 2026-05-25 | AI 엔진별 API Key 독립 저장. `groq_api_key` / `openai_api_key` / `claude_api_key` 분리. 설정창 엔진 전환 시 해당 엔진 저장 키 자동 로드. `_get_engine_settings` 엔진별 키 우선 조회 → `ai_api_key` 폴백 |
| 5.7 | 2026-05-25 | AI 생성 지침 8번 추가 — 과제 반복 금지. 진도·과제 정보는 메시지 별도 항목으로 전달되므로 특이사항에서 재낭독 금지 |
| 5.6 | 2026-05-25 | ai_engine.py 개선. ① `_merge_student_tags()` 신설 — v5.4 교재별 obs 키(`sheet\|cls\|name\|tb`) 대응, 복수 교재 태그 병합(단일 필드 first-wins, 배열 필드 union). ② `gen_single`/`gen_all` obs 키 3분할→4분할 수정 (태그 미전달 버그 수정). ③ `_base_conditions()` 중복 제거 — 프롬프트 텍스트에서 제거, system 파라미터로만 전달. ④ `build_batch_prompt` 진도/과제 포함 — `gen_all` targets에 `progress` 필드 추가, 단건 프롬프트와 동일 수준 컨텍스트 제공. ⑤ Groq 모델 문서 정정 `llama-3.1-8b-instant` → `qwen/qwen3-32b` |
| 5.4 | 2026-05-25 | obs 데이터 교재별 분리. ① `tagData` 키 구조 변경: `sheet\|cls\|name` → `sheet\|cls\|name\|tb` — 같은 학생의 교재별 독립된 obs 저장. ② Firebase 경로 동일 변경(`obs/{sheet}\|{cls}\|{name}\|{tb}/{date}`). ③ `getTags(sheet,cls,name,tb)`, `pushObs(sheet,cls,name,tb)`, `onTagCondition/Understand/Multi/onAssignGrade/onAssignTag` 전부 `tb` 파라미터 추가. ④ Python `app.py` obs 키 파싱 3분할→4분할(`_sh,_cls,_name,_tb`), `textbooks` 루프 제거(키에서 직접 추출). ⑤ `onTagCondition` UI 갱신 스코프를 `[data-g="condition"]` 로 한정. ⑥ CSS: `.tg-radio.sel-c`에 기본 background(`var(--indigo)`) 추가(understand 선택 시각 보장). ⑦ highlight `sel-m` 색 `#B45309`→`#CA8A04`(caution 앰버와 차별화, 골드) |

---

## 1. 프로젝트 개요

### 1.1 목적

수학학원 교사(IDO 및 부담임)가 매일 학생·학부모에게 데일리 리포트를 카카오톡으로 전송하는 과정을 자동화한다.  
v2.0부터는 DailyReportAnalyzer가 월간 학부모 리포트를 생성할 수 있도록 수업 관찰 데이터를 추가 수집한다.

### 1.2 구성 파일

#### PC 앱 (Python / tkinter)

| 파일 | 역할 | 주요 수정 시점 |
|------|------|--------------|
| `main.py` | 진입점, 아이콘, 에러 로그 | 거의 수정 없음 |
| `constants.py` | 전역 상수, 색상, 폰트, TAGS, DEFAULT_CONFIG | 태그·상수 추가 시 |
| `storage.py` | 경로, config, cache I/O | 저장 구조 변경 시 |
| `firebase.py` | Firebase REST CRUD, 태그 로드(`fetch_tags`) | 노드 추가 시 |
| `ai_engine.py` | AI 생성, 태그 프롬프트 주입, 멀티 엔진(Groq/Gemini/Claude/GPT) | 엔진 추가·프롬프트 튜닝 시 |
| `message.py` | 카카오톡 메시지 조립 | 포맷 변경 시 |
| `app.py` | UI 전체 (App 클래스) | UI 수정 시 |
| `drw_icon.ico` | PC 앱 아이콘 — 256×256 레이어 필수 | — |

**빌드**: `pyinstaller --onefile --noconsole --name "DailyReportWizard" --add-data "drw_icon.ico;." main.py`

#### 웹 PWA

| 파일 | 역할 | 런타임 |
|------|------|--------|
| `index.html` | 강사 태블릿 입력 화면 — 단일 HTML | 브라우저 |

### 1.3 역할 분리

```
웹 PWA (index.html)                    PC 앱 (모듈 구조)
─────────────────────────────          ──────────────────────────────
강사 등록 및 담당 수업 배정            Firebase에서 데이터 취합 (📥)
교재 등록/관리 (curriculum 지정)       학생별 데이터 열람
반 공통 진도/과제 입력                 특이사항 직접 편집
학생별 입력:                           AI 특이사항 초안 생성
  - 과제수행도 (assign_grade)          (Groq / Gemini / Claude / GPT 선택)
  - 수업 관찰 태그 (obs/)              카카오톡 메시지 전송 (담임)
  - 성적 입력 (scores/)
프리셋 관리
```

**권한 원칙 (v6.0)**
- 학생 등록/삭제/반 배정: ClassManager 관리자 전용
- 교재(subject) 등록: 강사 (담임/부담임 모두 가능)
- 반별 주간 시험 성적 입력: 해당 subject의 `instructor`만
- 학년단위 시험 성적 입력: 담임만
- KakaoTalk 데일리 리포트 발송: 담임 (PC 앱)

※ **로컬 전용 시나리오 폐기** — Firebase 연결 필수  
※ **PC 앱 쓰기 제한**: Firebase 쓰기는 `history/` 기록 + 전송 학생 `input/{nameKey}/__note__` 소거 + 강사 신규 등록만 허용 (v2.1.2~)  
※ **진도/과제 입력**: 웹 전용 (v3.0 이후 PC 직접 입력 UI 제거)

### 1.4 연계 프로젝트

```
DailyReportWizard 2.0  →  Firebase 저장
                                 ↓
DailyReportAnalyzer    ←  데이터 읽기 → 월간 리포트 생성
```

DRW 2.0이 저장하는 수업 관찰 데이터(`obs/`)와 성적 데이터(`scores/`)는 DailyReportAnalyzer의 입력 원천이 된다.

### 1.5 운용 시나리오

```
[수업 중/후] 강사별 웹 입력
  1. 웹 접속 → 강사 이름 입력 → 조회 (또는 신규 등록)
  2. 담당 수업 탭 선택 (반 · 교재)
  3. 반 공통: 진도/과제 입력
  4. 학생별: 수행도 프리셋 클릭 + 수업 관찰 태그 선택 + 메모

[수업 후] PC 취합 및 전송 (담임 IDO)
  1. 📥 데이터 가져오기 → Firebase 전체 로드
  2. 학생별 데이터 중앙 패널에서 열람
  3. 필요 시 특이사항 직접 수정 or ✨ AI생성 / ✨ 전체 AI생성
  4. 필요 시 ⚡ 강제 완료로 특수 상황 학생 전송 대상 포함
  5. 우측 패널 메시지 확인 → 카카오톡 전송
```

---

## 2. PC 앱 — app.py (App 클래스)

> ⚠️ **[폐기됨 · 문서 8.52, 2026-06-24]** PC 풀 클라이언트(`app.py`/`main.py`/`firebase.py`/`storage.py`/`errors.py`/`message.py`/`kakao_image.py`)는 웹(v2.5.0)+강사 에이전트 통합으로 **코드 제거**되었다. 아래 §2~§3 서술은 역사적 기록(필요 시 git 이력 복원). 현행 생성·전송은 §(에이전트)·`agent_worker.py`/`ai_engine.py`(프롬프트·`_call_ai_hub` 모듈 함수만 잔존)·`kakao_send.py` 참조. AI 생성 품질 지침은 §3의 `_base_conditions`/`_*_TEXT`(잔존)와 8.51 변경 이력 참조.

### 2.1 레이아웃

```
┌─────────────────────────────────────────────────────────────────┐
│  헤더: 로고 · 버전 · 날짜                   [pyautogui 경고]     │  ← 상단 고정
│  크레딧 바: Crafted by IDO …              AI-Assisted ✦         │
├─────────────────────────────────────────────────────────────────┤
│  노트북 탭: [📋 데일리 리포트] [✉ 메시지 발송]        [⚙ 설정] │  ← 탭 행 우측 오버레이·전역
├─────────────────────────────────────────────────────────────────┤
│  ▼ 탭1 「데일리 리포트」 — 기존 워크플로우 (동작 무변경)         │
│  탭바: [M반] [T반]                    [📥 데이터 가져오기] [🗑]  │
│ ┌────────────┬──────────────────────────┬─────────────────────┐ │
│ │  좌 패널   │  중앙 패널               │  우 패널            │ │
│ │  학생 목록 │  진도/과제 요약 (반 공통) │  메시지 미리보기    │ │
│ │  (신호등)  │  교재별 수행도·특이사항   │  글자 수            │ │
│ │  ▾/▸ 접기 │  ⚡강제완료 ✨AI생성      │                     │ │
│ ├────────────┴──────────────────────────┴─────────────────────┤ │
│ │  상태바: 완료 N · 진행중 N · 미입력 N (hover 툴팁)          │ │
│ │                          [✨ 전체 AI생성] [🚀 전송 (N명)]   │ │
│ └─────────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────────┘

  ▼ 탭2 「메시지 발송」 — §2.13
 ┌──────────────┬──────────────────────────────────────────────┐
 │  담당 학생   │  메시지 템플릿 [+추가][삭제]                 │
 │  전체 (M+T)  │  ┌ 템플릿 편집 (Text) ─────────────────────┐ │
 │  반별 그룹   │  변수: {이름} {반} {날짜}                   │
 │  ☑ 체크박스  │  미리보기 (첫 선택 학생)                     │
 │  반 선택/    │  📎 이미지 첨부 [✕]      [☐ 이미지 먼저]    │
 │  전체선택    │  🚀 카카오톡 창 활성화 후 전송 / ⏹ 취소      │
 │  N명 선택    │  상태: 전송 중... / ✅ 완료                   │
 └──────────────┴──────────────────────────────────────────────┘
```

**창 크기**: 기본 1100×780, 최소 920×680  
**아이콘**: `drw_icon.ico` — `resource_path()`로 탐색 (frozen 시 `_MEIPASS`, 개발 시 소스 디렉토리). Pillow 설치 시 `wm_iconphoto(256×256)` 병행 적용

### 2.2 신호등 (STATUS)

| 상태 | 색상 | 조건 |
|------|------|------|
| `STATUS_READY` | ● 초록 | (모든 교재 수행도 입력 AND 진도/과제 하나 이상) OR `force_data=True` |
| `STATUS_PARTIAL` | ◐ 노랑 | 수행도 일부 입력 / 수행도 완료이나 진도·과제 전무 |
| `STATUS_EMPTY` | ○ 회색 | 수행도 전혀 미입력 |

> **force_ready**: 입력 여부 무관하게 STATUS_READY로 강제 승격. `daily_cache.json` 저장, 전송 완료 후 초기화.

### 2.3 좌 패널 — 학생 목록

- **M반 / T반 탭 전환**
- **담당 반만 표시**: `instructor_assignments` 기반 화이트리스트 필터. `instructor_id` 미설정 시 전체 표시, 설정 후 담당 없으면 빈 목록
- **학급 접기/펼치기**: ▾/▸ 토글 버튼. `cls_fold_state` 딕셔너리로 상태 유지. 기본: 전체 접힘
- **부담임 반**: `🔒 학급명` 표시, 흐린 색상
- **이전/다음 이동**: `_student_list_flat()` 도 `_my_classes()` 기반

### 2.4 중앙 패널 — 열람 + 편집

**구성 요소 (위→아래)**

1. **진도/과제 요약** — `session/class_data`에서 로드. 입력값 있는 교재만 표시
2. **교재별 과제수행도** — `input/`에서 로드. ●/○ 도트 + 수행도 텍스트 (읽기 전용)
   - **선택된 관찰 태그 표시 (v2.1.2, 읽기 전용)** — 도트 줄 아래, 오늘(`today_key`) `obs/` 태그를 **한 줄 압축**으로 표시. 표시 순서: 컨디션 → 이해도(+세부) → 참여 → 기타 → 하이라이트 → 주의. 구분자 `·`. **하이라이트=초록·주의=빨강** 강조, 나머지 기본색. 태그 없으면 줄 자체 생략. 입력은 웹 전용이라 PC는 표시만. `App._obs_tag_segments()` / `_render_obs_tags()`
3. **⚡ 강제 완료 버튼**
   - OFF: 회색 `"⚡ 강제 완료"`
   - ON: 초록 `"⚡ 강제 완료 (ON) — 클릭하여 해제"`
   - 부담임 반: `state='disabled'`
4. **특이사항** — `tk.Text` 위젯
   - 담임 반: 직접 편집 가능. `FocusOut` 시 `note_data` 자동 저장
   - 부담임 반: `state='disabled'` (읽기 전용)
   - Windows 이모지: `Segoe UI Emoji` 폰트 + surrogate pair 정규화
5. **✨ AI생성 버튼**
   - 부담임 반: `state='disabled'` (`"✨ AI생성 (부담임)"`)
   - 쿨다운 중: `"⏳ Ns"` 카운트다운

### 2.5 우 패널 — 메시지 미리보기

읽기 전용. 학생 선택 시 실시간 렌더링.

```
[데일리 리포트] M/D (요일)
-------------------------
▶ 오늘의 진도
▶ 오늘의 과제
▶ 과제 수행도
▶ 오늘의 {이름}는?
```

### 2.6 상태바

- **집계 범위**: `_my_classes(sheet)` 기반 — 담당 반만
- **표시**: `완료 N명   진행중 N명   미입력 N명`
- **hover 툴팁**: 이름 목록 (`완료: 김철수, 이영희 / 진행중: 박민준`)
- 우측 범례: `● 완료   ◐ 진행중   ○ 미입력`

### 2.7 데이터 가져오기 (📥)

순서:
```
① 로컬 초기화  → student_data, note_data, progress_data, force_data 전부 clear
② config/ 로드  → sheets, presets 갱신
③ config/instructors/{id} 로드 → 강사별 assignments 우선 적용
④ input/ 로드   → student_data, note_data 채움
⑤ obs/ 로드     → tag_data 채움 (v2.0 신규)
⑥ session/class_data/ 로드 → progress_data (lastSent 폴백은 v2.1.2 폐기 — 노드 없으면 빈 데이터)
```

**가져오기 고정 정책** (v5.1~)

- 가져오기 시작 시 로컬 데이터 전체 초기화 → Firebase 데이터만 채움
- 로컬 잔류 데이터 병합 없음

| 데이터 | 정책 |
|--------|------|
| 과제수행도 | 로컬 초기화 후 웹 데이터로 채움 |
| 진도/과제 | 로컬 초기화 후 웹 데이터로 채움 |
| 메모/특이사항 | 로컬 초기화 후 웹 데이터로 채움 |
| 강제완료 | 로컬 초기화 (웹에 없으므로 빈 상태) |

한글 강사명: `urllib.parse.quote(node, safe='/')` 자동 처리

### 2.8 전송 로직

- **학생 표시 순서**: 모든 학생 명단(좌측 목록·전송 대상 다이얼로그·상태바·◀▶ 이동) **이름 가나다 오름차순**. `_sync_shared_sheets_from_firebase`에서 `all_students` dict 로드 시 1회 정렬(`key=(name 폴백'', nameKey)`) → 모든 `.items()` 순회가 상속, 빌더별 개별 정렬 불필요. **키(nameKey=출결번호)는 불변**, 표시 순서만 변경. None-safe + 동명이인 `nameKey` tiebreak. 웹 명단(입력·성적·설정)도 공유 헬퍼 `sortStu()`로 동일 이름순 적용
- **전송 대상**: `STATUS_READY` 학생만, `_my_classes()` 화이트리스트 적용
- **부담임 반 제외**: `assignments[cls].role == "부담임"` → 전송 제외. 폴백: `config/sheets/.../is_sub: true`
- **대상자 선택 (개별 제외)**: 🚀 전송 클릭 시 `_open_send_dialog()` 체크박스 모달. 준비 완료 학생 전체 기본 체크, 체크 해제 = **이번 전송만 제외**(상태 미변경, 다음 전송엔 재포함). [전체 선택]/[전체 해제] 버튼. 선택 0명 시 전송 차단
- **첫 학생 워밍업**: 카운트다운 종료 직후 첫 학생(`i==0`)은 `warm=0.6s` 지연 추가(`room` 복사 후 + 첫 `ctrl+f` 후) — 카톡 창 포커스/검색 정착 전 발사로 인한 첫 명 오작동 방지. 2번째부터 `warm=0`
- **순차 전송 취소**: 전송 시작 후 `send_btn` → "⏹ 전송 취소" 토글. `self._send_cancel`(`threading.Event`) set → 3초 카운트다운 및 루프 매 학생 진입 시 검사, **현재 학생 완료 후 중단**. 취소 시 전송된 N명만 발송, **로컬 데이터 초기화 안 함**(미전송분 유지). 완료 시에만 기존 초기화 (history 기록은 전송 확정 시점에 선행)
- `pyautogui` 미설치 시: `AUTOMATION=False`, 전송 버튼 비활성화
- 전송 **완료** 후: `student_data`, `note_data`, `force_data` 초기화 / `progress_data` 유지 (`history/` 기록·`__note__` 소거는 전송 확정 시점 단일 multi-path PATCH로 선행)
- **스레드 안전**: `_do_send`는 별도 스레드 실행. UI 업데이트 전체를 `root.after(0, ...)` 로 메인 스레드에 위임

### 2.9 설정 창

**좌측 탭 사이드바 구조** — 창 좌측 탭 레일(`rail`, 폭 132) + 우측 탭별 스크롤 콘텐츠(`make_scroll_frame`를 holder 프레임으로 감싸 `_show_tab`으로 show/hide) + 하단 고정 푸터(저장/취소, 탭 무관 항상 노출). 기본 탭 = **AI 생성**(전면·핵심 기능). 각 섹션은 `inner = tab_*` 재지정으로 해당 탭에 빌드.

| 탭 | 내용 |
|----|------|
| 🤖 AI 생성 (기본·전면) | 엔진 선택(+무료/유료 배지·한 줄 설명) + API Key + 👁 + **메시지 문체**(선택 시 미리보기) + **개별 지침** 텍스트박스 (§3.6) |
| 🔥 연결 | Firebase DB URL, DB 경로, ⚡ 연결 테스트 (`config` 노드 조회 + null 여부 검증) |
| 👤 강사 계정 | 이름 입력 → 조회/신규등록, 🔄 학급명단 동기화 |
| ⚙ 일반 | 카카오톡 전송 속도(스마트/고속/보통/안정), 톡방 접두사 |
| (웹 전담) | 학급·학생·교재·프리셋은 웹 PWA에서 관리 |

**AI 엔진 설정 저장 키**

| 키 | 내용 |
|----|------|
| `ai_engine_type` | `"groq"` \| `"gemini"` \| `"openai"` \| `"claude"` |
| `ai_api_key` | 마지막 저장 Key (폴백용) |
| `groq_api_key` | Groq 전용 Key |
| `gemini_api_key` | Gemini 전용 Key |
| `openai_api_key` | OpenAI 전용 Key |
| `claude_api_key` | Claude 전용 Key |
| `ai_style_mode` | 메시지 문체(§3.6). `"auto"`(기본·내 말투 자동) \| `"warm_detail"` \| `"balanced"` \| `"info_coach"` \| `"concise"` |
| `ai_custom_prompt` | 강사 개별 지침(§3.6) 자유 텍스트. 빈 문자열이면 미적용 |

**학급명단 동기화 (`_fetch_class_data`)**

`config/instructors/{id}/assignments` 노드 조회 (list). 반드시 강사 계정 조회 완료 후 실행.

### 2.9-B 최초 설치 위저드 (온보딩)

**목적**: 최초 실행(Firebase 미설정) 시 단일 안내 messagebox("설정 열기")를 3단계 순차 위저드로 대체. 웹 PWA 위저드(§4.8-C)와 동일 컨셉, PC 전용 항목 반영.

**발동·컨테이너**: `__init__`에서 `firebase_url`/`firebase_path` 미설정 시 정상 3-패널 UI를 빌드하지 않고 `_run_setup_wizard()` 호출. **팝업(Toplevel) 아님** — 메인 창 전체를 덮는 오버레이 `tk.Frame`(`self._wz_root`, `place(relwidth=1,relheight=1)`)에 가운데 정렬 카드(560px)로 렌더. 완료/이탈 시 `_wz_exit()`가 오버레이를 destroy → 그 아래 정상 레이아웃 노출. 정상 UI 빌드는 `_build_main_ui()`로 분리(`_main_built` 플래그) — 최초 실행은 위저드 종료 후 빌드, 일반 실행은 즉시 빌드.

**3단계** (`_WZ_STEPS`):

| 단계 | 아이콘 | 내용 | 호출 함수 (기존 재사용) |
|------|--------|------|------------------------|
| 0 연결 | 🔥 | Firebase URL·경로 + ⚡연결 테스트 | `firebase_get(tmp,"config")` |
| 1 계정 | 🔑 | 강사 이름 조회/신규등록 + 담당 동기화 | `firebase_get`/`firebase_put`, `_sync_shared_sheets_from_firebase` |
| 2 AI키 | 🤖 | 엔진 드롭다운 + API키 (**건너뛰기 가능**) | `save_config` (커밋 시) |
| 완료 | 🎉 | 실데이터 요약 + "웹서 명단 구성 후 📥가져오기" 안내 | `_wz_commit` |

> 웹 위저드와 차이: **학생 명단·수업 배정 단계 없음**(웹 전용) → 완료 화면서 안내. **AI 엔진+API키 단계 추가**(PC 전용).

**엔진별 키 발급 가이드 (`_WZ_GUIDE`)**: AI키 단계에서 선택한 엔진에 따라 발급 절차를 **인라인 상세 표시**(guide.html 4부 발췌). 엔진 변경(`_wz_on_engine`) 시 즉시 갱신 + 해당 엔진 저장 키 자동 로드.

| 엔진 | 무료/유료 | 발급처 | 키 형식 |
|------|-----------|--------|---------|
| Gemini | 무료 | aistudio.google.com/apikey | `AIza...`/`AQ.Ab8...` (limit:0 → 새 프로젝트 재발급) |
| Claude | 유료 | console.anthropic.com | `sk-ant-...` (Billing 충전 $5, 1회 표시) |
| GPT (OpenAI) | 유료 | platform.openai.com/api-keys | `sk-...` (Billing 충전, 1회 표시) |
| Groq | 무료 | console.groq.com/keys | `gsk_...` |

각 가이드 박스: 무료/유료 배지 · 🔗발급처 링크(`webbrowser.open`) · 번호 단계 · 키 형식 · ⚠️주의. (설치·운용 가이드 링크로 떠넘기지 않고 위저드 내 직접 안내)

**단계 가드** (`_wz_next`): 0=URL·경로 미입력 차단, 1=`instructor_id` 미설정 차단.

**스텝 인디케이터**: `tk.Canvas`에 원 3개 + 연결선 직접 드로잉(`_wz_draw_steps`) — 완료=초록 ✓, 현재=인디고, 대기=회색.

**이탈/커밋** (모두 `_wz_exit()` 경유 — 오버레이 destroy 후 `_main_built` 미빌드면 `_build_main_ui`, 빌드돼 있으면 `_populate_student_list`/`_refresh_student_view` 갱신):
- "나중에"(`_wz_close`): 입력분 `save_config` 후 종료. 미설정 시 다음 실행 재발동.
- "건너뛰기"(AI 단계, `_wz_skip_ai`): 키 비우고 완료 단계로.
- "✅ 설정 완료"(`_wz_commit`): `ai_engine_type`+`{engine}_api_key`+`firebase_url/path` 저장 → `_wz_exit` → Firebase 설정 시 `_sync_shared_sheets_from_firebase`.

**구현**: `app.py` `_run_setup_wizard`/`_wz_render`/`_wz_draw_steps`/`_wz_pane_*`/`_wz_build_guide`/`_wz_build_footer`/`_wz_next`/`_wz_back`/`_wz_skip_ai`/`_wz_close`/`_wz_commit`/`_wz_exit`/`_wz_lookup_instr`/`_wz_test_conn`/`_wz_on_engine`, 정상 UI 분리 `_build_main_ui`. 메인 창 한 곳에서 위저드↔정상 레이아웃 전환.

### 2.10 데이터 지속성

| 데이터 | 저장 위치 | 초기화 시점 |
|--------|-----------|-------------|
| 진도/과제 (`progress_data`) | `daily_cache.json` | 가져오기 시 초기화 후 재채움 / 수동 초기화 |
| 과제수행도 (`student_data`) | 메모리 | 가져오기 시 초기화 후 재채움 / 전송 완료 후 |
| 특이사항 (`note_data`) | 메모리 | 가져오기 시 초기화 후 재채움 / 전송 완료 후 |
| 강제완료 (`force_data`) | `daily_cache.json` | 가져오기 시 초기화 / 전송 완료 후 자동 |
| 학생 명단·설정 | `config.json` | 변경 즉시 |
| 강사 배정 | `config.json` | 가져오기 시 덮어쓰기 |

### 2.11 플랫폼 지원

| 항목 | Windows | macOS |
|------|---------|-------|
| UI | ✅ | ✅ |
| 폰트 | 맑은 고딕 | Apple SD Gothic Neo |
| 이모지 입력 | Segoe UI Emoji + surrogate pair | TkDefaultFont |
| 단축키 | Ctrl | Command |
| 카카오톡 전송 | ✅ | ❌ (AUTOMATION=False) |

### 2.12 담당 반 필터링 (`_my_classes`)

**핵심 원칙**: `instructor_assignments` 설정 시 모든 연산 범위를 담당 반으로 한정. 담당 외 반은 어떤 연산에도 관여하지 않는다.

```python
def _my_classes(self, sheet) -> list:
    # assignments 있음 → 해당 sheet의 담당 반만 (부담임 포함)
    # instructor_id 미설정 + assignments 없음 → 전체 표시 (show_all, 초기 셋업용)
    # instructor_id 설정 + assignments 없음 → 빈 목록 (담당 없음으로 간주)
    # _populate_student_list·_refresh_status_dots·_student_list_flat 등 모든 필터링 경유
```

**적용 함수 목록**

| 함수 | 역할 |
|------|------|
| `_refresh_statusbar()` | 상태바 카운트 |
| `_student_list_flat()` | ◀/▶ 이동 대상 |
| `_populate_student_list()` | 좌 패널 렌더링 |
| `_collect_ready()` | 전송 대상 수집 |
| `_send()` → `all_names` | 전송 확인 팝업 제외 목록 |
| `_open_send_dialog()` | 대상자 체크박스 선택(개별 제외) 모달 |
| `_set_send_btn_cancel()` / `_cancel_send()` | 전송 중 취소 버튼 토글·취소 요청 |
| `_gen_ai_note_all()` | 전체 AI생성 대상 |

**부담임 반 추가 제한**

| 대상 | 제한 |
|------|------|
| 특이사항 `tk.Text` | `state='disabled'` |
| ⚡ 강제 완료 버튼 | `state='disabled'` |
| ✨ AI생성 버튼 | `state='disabled'` |
| 전송 대상 | 제외 |
| 전체 AI생성 대상 | 제외 |

### 2.13 메시지 발송 탭 (ClassManager 발송 기능 이식)

데일리 리포트와 **별개**로, 담당 학생 학부모에게 임의 메시지(공지·안내·일정 등)를 템플릿 기반으로 일괄 전송하는 탭. 데일리 리포트 워크플로우(진도/과제/특이사항/`history` 누적)와 완전히 독립적이며, **전송 후 데이터 초기화·`history/` 기록을 하지 않는다**(공지성 발송이라 이력 누적 대상 아님).

**대상 — 담당 학생 전체 (`_my_students_all()`)**
- `_my_classes('M') + _my_classes('T')` 의 모든 반 학생을 합집합으로 수집 (그룹 무관 통합 발송)
- **부담임(🔒) 반 제외** (`_is_sub_teacher`) — 데일리 전송 정책과 일관
- `nameKey` 기준 중복 제거, 표시 순서는 `all_students`(이름 오름차순) 상속
- 좌 패널에서 **반별로 그룹핑**한 체크박스로 표시 — `반 선택`(반 단위 일괄 체크)·`전체선택`/`전체해제`·`N명 선택` 카운터·`↺` 새로고침. Firebase 동기화(`_sync_shared_sheets_from_firebase`)·데이터 가져오기 시 자동 갱신

**템플릿 (`{변수}` 치환)**
- 변수: `{이름}` `{반}` `{날짜}`(M/D) — `message.render()` + `message.build_bulk_ctx()`. 성적 변수는 범위 외(웹 입력·읽기 전용)
- `templates.json`(런타임 폴더)에 `[{name, body}, …]` 로컬 영속 — `storage.load_templates/save_templates`. 편집 시 즉시 저장(`<KeyRelease>`)
- 미리보기 = 첫 번째 선택 학생 기준 실시간 렌더

**이미지 첨부 (선택)**
- `📎 이미지 첨부` → 파일 선택, `✕`로 제거. `이미지 먼저` 체크박스로 본문↔이미지 전송 순서 토글(기본: 본문→이미지)
- 1회성 첨부(템플릿에 미저장), 선택된 모든 수신자에게 동일 적용
- 클립보드 복사 = `kakao_image.copy_image_to_clipboard` (Windows: PowerShell `Clipboard.SetImage` `-STA`, 추가 pip 의존성 없음 / macOS: `osascript`)

**전송 (`_bulk_send` → `_do_bulk_send`)**
- 방 검색어 = `{room_prefix}{이름}` (`get_room`과 동일 규칙, 설정 공유)
- 본문·이미지 누락 검증 → 대상·이미지 정보 확인 팝업 → 3초 카운트다운(취소 가능) → 순차 전송
- 키 시퀀스는 데일리와 **공용 헬퍼 `_kakao_send_one(m, wait, warm)`** 사용 (첫 학생 `warm=0.6s` 워밍업 동일). 이미지 송신은 `img_wait=max(wait_time,1.0)`로 붙여넣기 미리보기 팝업 대기
- 전송 중 버튼 → `⏹ 전송 취소`(`_bulk_cancel`, 현재 학생 완료 후 중단). 데일리 푸터 버튼/상태와 **독립**(`bulk_send_btn`/`bulk_status`)

**탭 도입 구조 변경**
- `_build_main_ui`가 헤더 빌드 후 `ttk.Notebook` 생성, 탭1에 기존 빌더(`_build_sheet_bar/_build_panels/_build_statusbar/_build_footer`)를 `parent=tab` 으로 호출 — **네 빌더에 `parent=None` 기본 인자만 추가**하고 내부 동작·`side`/`pack` 순서는 그대로 유지(시각·동작 회귀 없음)

---

## 3. PC 앱 — ai_engine.py (AI 생성 엔진)

### 3.1 멀티 엔진 구조

설정 창에서 엔진을 선택하면 `_call_ai_hub()`가 해당 엔진 규격으로 API를 호출한다.

| 엔진 | 모델 | 용도 |
|------|------|------|
| `groq` | `qwen/qwen3-32b` | 무료, 속도 최적화 |
| `gemini` | `gemini-2.5-flash` | 무료, 월 제한 없음(일당 RPD만) |
| `claude` | `claude-sonnet-4-6` | 문장력·감성 우선 |
| `openai` | `gpt-4o-mini` | 범용 |

**Gemini 규격 특이사항**:
- key는 헤더가 아닌 URL 쿼리파람(`?key=`)으로 전달
- endpoint: `…/v1beta/models/{GEMINI_MODEL}:generateContent`
- body: `contents[].parts[].text` + `system_instruction.parts[].text`
- **`thinkingConfig.thinkingBudget=0` 필수** — 2.5-flash는 thinking 모델이라 미설정 시 출력 토큰이 thinking에 소모돼 응답 잘림
- 응답 파싱: `candidates[0].content.parts[0].text` (후보 없으면 safety filter로 간주, 예외)
- 모델은 `constants.GEMINI_MODEL` 상수로 분리 (교체 시 한 줄)

**API Key 저장/로드**: 엔진별 고유 슬롯(`{engine}_api_key`)에만 저장·조회한다. 공유 `ai_api_key` 폴백은 **제거**(엔진 전환 시 타 엔진 키가 노출·오염되던 버그 수정). 엔진을 바꾸면 그 엔진에 저장된 키만 자동 로드되며, 키가 없으면 빈칸이다. `ai_api_key`는 deprecated(미사용).

### 3.2 단건 생성 (`gen_single`)

- 컨텍스트: 학생명, 교재별 수행도·진도·과제, 직접 작성 메모, 오늘 태그
- AI 호출 직전 현재 특이사항 `Text` 위젯 값을 `note_data`에 저장한 뒤 프롬프트를 생성한다. 따라서 FocusOut 전 작성한 메모도 `[직접 작성 메모 — 반드시 반영]`에 반영된다.
- **표시 이름 분리**: `gen_single`의 `name` 인자는 nameKey(출결번호)다. 데이터·태그 조회는 nameKey로 하되, 프롬프트 `[학생 이름]`에는 `all_students[nameKey].name`을 조회해 `display_name`으로 전달한다. (미전달 시 nameKey가 그대로 새어 일부 엔진이 출결번호를 이름으로 출력하던 버그 수정). 일괄(`gen_all`)은 처음부터 display_name 사용.
- 직접 작성 메모는 참고 자료가 아니라 교사가 직접 입력한 핵심 전달 사항으로 취급하며, 최종 문장에 자연스럽게 포함해야 한다.
- `max_tokens=400`, `temperature=0.75` (자연스러운 문체)
- system prompt: `_base_conditions()` 전달 (Claude: system 필드, Groq/OpenAI: system role 메시지, Gemini: `system_instruction`)
- **문체 블록 주입**: 프롬프트의 `[문체 참고 예시]` 위치에 `AiEngine._style_block()` 결과(§3.6)를 삽입. 비면 기본 예시 3종 fallback(`_DEFAULT_STYLE_BLOCK`)
- 완료 후 쿨다운 틱 시작

### 3.3 일괄 생성 (`gen_all`)

- 현재 시트의 `STATUS_READY` 학생 전원 단일 API 호출
- 부담임 반 자동 제외
- 배치 프롬프트: 학생 데이터 JSON 배열 → JSON 배열 응답 (`max_tokens=8192`, `temperature=0.5`)
  - 학생당 출력 ~68토큰 실측 → 8192는 ~100명까지 여유. (4096→8192 상향: 메모/하이라이트 포함 시 마진 확보)
- system prompt: `_base_conditions()` 전달 (JSON 안정성 위해 temperature 0.5 유지)
- **문체 블록 주입**: `[문체 기준]` 다음에 `_style_block()` 결과(§3.6) 삽입. 비면 "기본 분량은 2~3문장 100자 내외." 사용
- 응답 파싱: `json.loads()` 전 ` ```json ``` ` 펜스 제거

### 3.4 태그 → 프롬프트 변환 (`_build_tags_context`)

| 태그 필드 | 변환 방식 |
|----------|-----------|
| `highlight` | `_HIGHLIGHT_TEXT` 매핑 → 블록 최상단에 "⭐ 오늘의 하이라이트"로 삽입 |
| `condition` | `_CONDITION_TEXT` 매핑 → 자연어 1줄 |
| `understand` | `_UNDERSTAND_TEXT` 매핑 |
| `understand_sub[]` | `_UNDERSTAND_SUB_TEXT` 매핑, 복수 가능 |
| `engage[]` | `_ENGAGE_TEXT` 매핑, 콤마 연결 |
| `caution[]` | '졸음·잡담·태도불량' 직접 단어 사용 금지. 완곡 표현으로만 활용 |
| `extra[]` | `_EXTRA_TEXT` 매핑 — 자율학습/주간Test/재시험은 별도 전달 이벤트로 취급하고 독립 문장으로 강조 |

> **주의**: `caution`과 `extra`는 독립 블록. caution 없이 extra만 있어도 정상 처리됨.

### 3.5 생성 지침 (`_base_conditions`)

1. 문체: ~했습니다 체 통일. **학생 이름을 주어로 쓰지 않음**(‘OOO는/OOO 학생은/OO이는’ 금지) — 메시지 위 ‘오늘의 OOO는?’ 헤더에 이름이 이미 있어 중복. 이름 없이 수업 내용·행동으로 바로 시작. 단건 `[학생 이름]`은 식별용 참고로만 제공
2. 금지: '어머님/학부모님' 호칭, 시스템 표현, 할루시네이션
3. 태그 반영: 명시된 항목만. 미명시 이벤트 임의 추가 금지
4. 주의 태그: '졸음·잡담·태도불량' 직접 단어 절대 금지. '오늘은 조금 피곤해 보이는 날이었습니다' 수준 완곡 표현
5. 기타 이벤트: 자율학습·주간Test·재시험은 다른 수업 묘사와 섞지 않고 별도 문장으로 명확히 전달
6. 하이라이트: ⭐ 항목 있으면 가장 인상적으로 표현
7. 결석: 데이터 없으면 안부 인사 + 다음 수업 기약 코멘트
8. 과제 반복 금지: 진도·과제(페이지·번호)는 메시지 별도 항목으로 전달되므로 특이사항에서 그대로 읽어주는 문장 금지
9. 출력: 순수 텍스트 (JSON·마크다운 금지). 2~3문장, 100자 내외

> **강사 개별 지침과 우선순위**: `ai_custom_prompt`(§3.6)가 있으면 단건은 system(`_system_conditions` = `_base_conditions()` + 개별 지침), 일괄은 `[학생데이터]` 앞에 `[강사 개별 지침]` 블록으로 주입. 블록 머리말에 "위의 작성 지침과 사실·안전 규칙을 위반하지 않는 선에서 반영"을 명시 → 자유 입력이 호칭 금지·할루시네이션 금지·과제 반복 금지 등 안전 규칙을 덮어쓰지 못한다. **이 가드레일 문구는 프롬프트 내부에만 존재하고 설정 UI에는 노출하지 않는다.**

**few-shot 예시** (단건 프롬프트에 포함, 문체·어조 참고용)
> "오늘 이차함수 단원에서 막혔던 개념을 반복 설명 후 이해했습니다. 틀린 문항을 스스로 재풀이하며 오답을 정리하는 모습이 인상적이었습니다."

> 위 기본 예시는 `ai_style_mode`가 미설정이거나 auto 모드에서 분석할 본인 노트가 없을 때만 쓰인다. 그 외에는 §3.6 문체 블록이 이 자리를 대체한다.

### 3.6 메시지 문체 (ai_style.py)

강사가 직접 수정·전송한 최종 특이사항(`history/`)의 말투·분량을 AI 생성에 반영한다. 설정 `ai_style_mode`로 모드를 고른다.

**모드**

| 모드 id | 라벨 | 동작 |
|---------|------|------|
| `auto` (기본) | ✍️ 내 말투 자동 | 로그인 강사(`instructor_id`) 본인이 전송한 노트를 history에서 추출해 통계 분석 → 문체 지침 자동 생성 + 본인 노트 2개를 few-shot 예시로 사용 |
| `warm_detail` | 📖 따뜻·상세형 | 4문장+, 공감·노력 서술, 😊 이모지 |
| `balanced` | 📋 정돈·균형형 | 3~4문장, 담백·명료, 이모지 없음 |
| `info_coach` | 🎯 정보·코칭형 | 일정·시험·코칭 구체 명시, 운영 안내 빠짐없이 |
| `concise` | ⚡ 간결·요점형 | 2~3문장, 점수·사실 위주 개조식 |

> 4개 프리셋은 실DB `history/` 289건(강사 5명, 2026-06) 문체 분석으로 도출. 프리셋 예시는 학생 실명 없는 실노트를 익명화해 하드코딩(`STYLE_PRESETS`).

**auto 분석** (`analyze_notes`/`build_guidance`)
- 통계: 평균 길이, 이모지율, 느낌표율, 해요체율, 개조식율
- 길이→분량 지침(110자 미만 간결 / 200자 미만 정돈 / 이상 상세), 이모지율≥0.4→이모지 사용 지침, 해요율≥0.35→부드러운 어조, 느낌표율≥0.3→느낌표 허용, 개조식율≥0.4→줄바꿈 요약
- 예시(`pick_examples`): 실명 흔적 적은 노트 중 중앙값 길이 근처 2개

**주입/캐시** (`AiEngine._style_block`)
- `resolve_style(mode, provider)` → (지침, 예시) → `style_prompt_block()`로 `[문체 지침]`+`[문체 참고 예시]` 텍스트화
- 예시 블록에 "말투·길이만 참고, 예시의 이름·점수·사실은 가져오지 말 것" 경고 명시(실명·사실 베끼기 방지)
- 세션 캐시 키 `{mode}|{instructor}` — auto 모드 history fetch는 1회만, 설정 저장 시 `invalidate_style_cache()`로 무효화
- auto 모드는 history 읽기만 함(쓰기 없음). 표본 상한 40건(최신순)

**강사 개별 지침** (`ai_custom_prompt`)
- 문체와 직교(어떻게=문체 / 무엇을=개별 지침). 문체 모드와 무관하게 항상 적용
- `AiEngine._custom_block()`이 `[강사 개별 지침 …]` 블록 생성, 빈 값이면 미주입. 우선순위는 §3.5 참조(안전 규칙 우선)
- 저장은 config(강사 PC/계정별) → 자연히 강사별 개인화

**설정 UI** (app.py `_open_settings` AI 섹션)
- 엔진 콤보 아래 `_ENG_INFO`로 무료/유료 배지(● 색상)+한 줄 설명 갱신(`_render_eng_info`). `AI_ENGINE_LABELS`는 웹/가이드 공유라 라벨 자체는 변경하지 않음
- 문체 콤보 아래 미리보기 Label(`_render_style_preview`): 프리셋=지침+예시, auto=`profile_summary`(평균 길이·어조·이모지 여부)+예시 1개. auto는 history fetch라 백그라운드 스레드로 "분석 중…"→결과 갱신
- 개별 지침 `tk.Text`(3줄). 저장 시 `ai_custom_prompt`에 기록, 가드레일 문구는 UI 미노출

---

## 4. 웹 PWA — index.html

### 4.1 디자인 목표

- **기기**: 9인치급 이상 태블릿 가로모드 / PC (권장 11인치 1024×768)
- **밀도**: 12명 이내 한 반이 스크롤 없이 한 화면에 표시 (행 높이 ≤ 54px)
- **입력 방식**: 버튼 선택 중심, 텍스트 최소화
- **소형 화면 차단**: **현재 임시 비활성(전면 개방)**. 차단 미디어쿼리(`@media(max-width:839px){#scr-mask{display:flex}}`) 주석 처리 — 모든 해상도 접근 허용. 복구 시 9인치급 기준 = 11인치 앵커 1024px × 9/11 ≈ 838 → 840px(`max-width:839px`)

### 4.2 레이아웃

```
┌─────────────────────────────────────────────────────┐
│ 헤더: 날짜 · [M반][T반] · [3MGM·우공비][3MGM·라이트쎈] │
├─────────────────────────────────────────────────────┤
│ 진도/과제 바 (반 공통, 고정)                          │
├─────────────────────────────────────────────────────┤
│ 컬럼 헤더: 학생 | 과제수행도 | 수업태도 | 이해도 |     │
│            참여관찰 | 메모                            │
├──────┬──────────────────────────────────────────────┤
│ (좌) │ 행 기반 입력 테이블 — 학생 1명 = 1행          │
│ 학생 │                                              │
│ 목록 │ [📝 수업 기록 탭] [📊 성적 입력 탭]           │
├──────┴──────────────────────────────────────────────┤
│ 상태바: ● 완료 N명  ◐ 진행 N명  ○ 미입력 N명        │
└─────────────────────────────────────────────────────┘
```

### 4.3 탭 구조

| 탭 | 내용 | 입력 주기 |
|---|---|---|
| 📝 수업 기록 | 과제수행도 + 수업 관찰 태그 (condition/understand/engage/caution) | 매 수업 |
| 📊 성적 입력 | 시험 유형별 점수 일괄 입력 | 주 1회 |

**수업 탭 버튼 표시 형식**: `반명 학년학기 교재명`  
예) `중1A 중1-1 최상위수학` — 학년학기는 `cfg.sheets[sh].classes[cls].tb_grade[tb]`에서 조회하여 교재명 앞에 표시.  
상단 타이틀도 동일 형식: `중1A · 중1-1 최상위수학`

### 4.4 진도 피커 (반 공통)

학급-교재 조합에 학년학기(`cfg.sheets[sh].classes[cls].tb_grade[tb]`)가 등록된 경우 cascade dropdown, 미등록 시 텍스트 직접 입력으로 fallback.

**Cascade 흐름**:
1. 대단원 선택 (`CURRICULUM[gradeSem]` 기반 옵션)
2. 소단원 선택 (대단원 선택 후 동적 로드) 또는 "단원 전체"
3. ✏️ 직접 입력 선택 시 자유형식 텍스트 입력

**저장값 형식**: 소단원 선택 시 `"소수와 합성수"` (소단원만), 단원 전체 선택 시 `"소인수분해"` (대단원만), 직접 입력 시 자유 텍스트.  
`stripIdx()` 적용 — `"Ⅰ. 소인수분해"` → `"소인수분해"`, `"1. 덧셈과 뺄셈"` → `"덧셈과 뺄셈"`

**커리큘럼 로드**: `index.html`에서 `<script src="data/curriculum.js">` 로 `CURRICULUM_RAW` 전역 상수 로드 → `loadCurriculum()`(동기)이 `_normalizeCurriculum(CURRICULUM_RAW)`으로 변환  
범위: 초3-1 ~ 초6-2, 중1-1 ~ 중3-2, 공통수학1/2, 대수, 미적분I, 확통  
커리큘럼 수정 시 `code/public/data/curriculum.js`만 편집

**GRADE_SEM_LIST**: `{val, label}` 배열. label = val과 동일한 단축 형식 (`중3-1`, `대수`, `확통`).

### 4.4-B 과제 피커 (반 공통)

3종 타입 토글 버튼 + 숫자 입력:

| 타입 | 형식 | 저장 예시 |
|------|------|-----------|
| p. 페이지 | 시작~끝 | `p.45~p.52` |
| # 번호 | 시작~끝 | `#1~#30` |
| 자유 | 직접 입력 | `단원 마무리 전체` |

시작 번호 생략 가능: `~p.52` (끝 페이지만)  
미리보기 배지: 입력값 있을 때만 표시.  
과제 숫자 입력칸과 자유 입력칸은 iOS/Safari 자동 확대 방지를 위해 `font-size:16px` 이상을 유지한다.  
과제 타입 버튼과 과제수행도 버튼은 선택 상태에서 배경/테두리/글자색만 변경하며 크기·scale 전환은 하지 않는다.  
`_parseHwStr(s)` — 기존 저장값 파싱하여 피커 초기 상태 복원.

### 4.5 수업 기록 탭 — 입력 항목

#### 과제 수행도 (단일 선택)

```
── 성실 계열 ──────  ── 부분 계열 ──────  ── 미수행 계열 ────  ── 특수 ───
✅ 완벽 수행         △ 거의 완료           ✗ 미수행              결석
👍 수행 양호         ◑ 과반 수행           교재 없음
📝 채점전 완료       ▽ 일부만 수행         검사 불가
                                           검사 거부
```

#### 수업 관찰 태그 (constants.py TAGS 정의)

**수업 태도** `condition` (단일 선택):
```
💡 번뜩임 / 👍 잘함 / 😐 보통 / 😴 힘듦
```

**이해도** `understand` (단일 선택) + `understand_sub` (멀티):
```
단일: 🟢 빠름 / 🟡 보통 / 🔴 느림
멀티: 💪 혼자해결 / 🔁 오답재풀이 / 😵 개념혼동
```

**참여 관찰** `engage` (멀티 선택):
```
긍정: 📣 발표 / 🙋 질문 / 🤝 도움 / 📖 예습 / 💡 오류정정
```

**주의 관찰** `caution` (멀티 선택):
```
💤 졸음 / 🗣 잡담 / 😤 태도불량 / ⏰ 지각
```
> caution 태그는 Firebase에 저장되나 **학부모 리포트에 직접 노출 금지**. AI가 완곡 표현으로만 활용.

**특수 이벤트** `extra` (멀티 선택):
```
📚 자율학습 / 📝 주간Test / 🔄 재시험
```

**오늘의 하이라이트** `highlight` (단일 선택):
```
🏆 만점·완벽 / 📈 큰 향상 / ✅ 개념완전습득 / 💎 끝까지도전
```
> 선택 시 AI 프롬프트 블록 최상단에 삽입되어 메시지에서 가장 먼저 강조됨.

#### 메모 (선택)

텍스트 자유 입력. 기억에 남는 순간·특이사항 기록.

### 4.6 성적 입력 탭

**네비게이션**: 사이드바 `📊 성적 입력` → `goNav('scores')`

**시험 유형 7종** (`SCORE_TYPES`) — timer 시험 목록 동기화(v8.18), KMA 제외(v8.19)

| 유형 | 단위 | 기본 만점 | 설명 |
|------|------|----------|------|
| 주간Test | 반별 | 100 | 매주 정기 테스트 |
| 확인학습 | 반별 | 100 | 수업 내 확인학습 테스트 |
| 실전모의고사 | 과정(학년) | 100 | 실전 모의고사 |
| 기출모의고사 | 반별 | 100 | 기출문제 기반 모의고사 (v8.20: 과정→반별 정정) |
| 성취도평가 | 과정(학년) | 150 | 단원별 성취도 평가 |
| 반배치고사 | 과정(학년) | 150 | 반 편성/재배치 시험 |
| 직접입력 | 반별 | (유지) | 사용자 정의 시험명 — 만점 자동 세팅 제외 |

과정(학년) 단위 = `ACHIEVEMENT_TYPES`, 같은 curriculum 수강생 전체가 한 코호트(예: 중3-1 과목 수강생 전체). 단위 선택 메뉴는 의도적으로 없음 — 유형이 단위를 자동 결정.

유형 선택 시 `SCORE_TYPE_MAX` 기준으로 만점 입력란 자동 세팅(`_onScoreTypeChange`), 이후 수동 수정 가능. 만점 변경은 각 점수 input의 `max` 속성·`/만점` 표기·통계에 즉시 반영.

**저장 무결성 (v8.19)**
- **렌더된 학생만 갱신**: 저장 시 화면에 렌더된(현재 반) 학생만 갱신/삭제. 학년 공유 노드(`scores/achievement/`)의 타 반 학생·전출생 점수는 보존(머지) — 통째 교체로 인한 타 반 점수 유실 해소
- **제자리 수정은 서브경로 PATCH**: `…/{testKey}/meta`·`…/{testKey}/students`(렌더 키만) — 타 담임 동시 입력과 충돌 없음
- **testKey 항상 재계산**: 반별 `날짜|유형[|회차]` / **학년 `유형[|회차]`(날짜 제외, v8.23)** — 반·학생별 시행일이 달라도(강사가 기본 오늘 날짜를 그대로 둬도) 같은 학년 시험으로 묶임, 날짜는 meta에만(마지막 저장 대표값). 회차는 키 식별 시 정규화(`"1회"→"1"`, 표시 원형). 조각은 Firebase 금지문자(`. # $ [ ] /`)·구분자(`|`) 치환(`_scoreKeySafe`, 표시값은 meta 원형). 식별자 변경 시 새 키로 이동(구 위치 삭제), weekly↔achievement 경계 이동 포함 — 고스트 중복 해소
- **무음 덮어쓰기 방지**: 신규 작성·키 이동 대상에 기존 기록 존재 시 병합 여부 confirm
- **점수 범위 검증**: 0~만점 벗어나면 저장 차단(toast)
- **삭제는 kind 기준**: 목록의 소속 컬렉션(weekly/achievement)으로 경로 판정(type 문자열 추정 폐기)
- **삭제 방어/복원 (v8.24)**: ① 모든 시험 삭제는 `scores/trash/`에 전체 노드 스냅샷 후 진행 — **백업 실패 시 삭제 중단** ② 학년 공유 시험의 비관리자(담임) "삭제" = **내 반 점수만 비우기**(타 반 보존, 마지막 반이면 빈 노드 정리). **시험 전체 삭제는 관리자(adminOn) 전용** ③ 관리자 휴지통 UI(성적 탭 하단): 복원(원경로 PATCH)·영구 삭제. 휴지통 자동 정리 없음(수동)
- 목록 정렬: `meta.date` 최신순(키는 보조)

**입력 필드**

| 필드 | 타입 | 기본값 | 설명 |
|------|------|--------|------|
| 시험 유형 | select | 주간Test | `SCORE_TYPES` 선택 또는 직접입력 |
| 회차 | text | 1 | 자유 텍스트 (1, 2, "5월" 등) |
| 날짜 | date | 오늘 | YYYY-MM-DD |
| 만점 | number | 100 | 점수 백분율 기준 |
| 메모 | text | - | 시험 범위·특이사항 |
| 학생별 점수 | number | - | 반 전체 일괄 입력 |

**자동 산출 (실시간)**
- 학생별 백분율 = 점수 / 만점 × 100
- 반 평균·최고점·최저점·입력 인원 수

**입력 플로우**:  
`+ 새 시험 추가` → 시험 정보 설정 → 학생별 점수 입력 → 저장 → 목록 뷰  
기존 시험: `수정` 버튼 → 동일 폼 (testKey 유지하여 덮어쓰기) / `삭제` 버튼

### 4.7 신호등 판정 (`dotClass`)

| 색상 | 조건 |
|------|------|
| `'g'` 초록 | 수행도 입력 + 진도/과제 하나 이상 |
| `'y'` 노랑 | 수행도 입력 + 진도/과제 없음 |
| `'e'` 회색 | 수행도 미입력 |

> 웹 신호등은 `force_ready` 미반영 (PC 전용 기능)

### 4.8 설정 화면 (좌측 탭 + 아코디언)

**좌측 탭 레일 구조** (v2.4.0~) — 잡다해진 단일 롱 스크롤을 4탭으로 분리. `.stg`(flex) = `.stg-rail`(좌측 탭, 124px) + `.stg-panes`(우측). 탭 전환은 재렌더 없이 `setStg(t)`가 `.stg-tab`/`.stg-pane`의 `on` 클래스만 토글(전 패널 렌더 후 CSS show/hide → 아코디언 상태·async 로드 보존). 상태 `stgTab`(기본 `account`). `@max-width:600px`에서 레일이 가로 스크롤 탭으로 전환. 각 탭 내부는 기존 `sa` 아코디언 섹션 그대로 재사용.

| 탭 (`data-stg`) | 포함 섹션 |
|------|------|
| 👤 계정·수업 (account, 기본) | `sa-acct`(내 계정) · `sa-asgn`(내 담당 수업) · `sa-cls`(학급 & 학생 관리) |
| 🔥 연결 (conn) | `sa-fb`(Firebase URL·경로·시크릿, 명단 불러오기) |
| 💬 문구·데이터 (data) | `sa-preset`(자주 쓰는 문구) · `sa-reset`(초기화) |
| 👑 관리자 (admin, `adminOn`만) | `sa-tbmgmt`(과목 목록) · `sa-tblist`(교재 명단) · `sa-admin`(강사 관리) |

`.stg-foot`(탭 무관 하단 고정): 위저드 다시 실행 · 관리자 모드 토글 · 관리자 암호 변경 · 크레딧. 개별 `sa` 섹션 정의는 종전과 동일.

**설정 입력창 Enter 키 지원**  
모든 설정 텍스트 입력창(Firebase URL·경로, 계정 이름, 새 문구, 강사 등록, 교재명)에서 Enter 키 입력 시 해당 버튼 동작 실행.

**아코디언 상태 지속 (`openSaIds: Set`)**
- `_saToggle(id)` / `_saOpen(id)` 로 id 추가/삭제
- `renderMain()` 후 `renderSettings()`가 `openSaIds.has(id)` 기반으로 `open` 클래스 주입
- 기본값: `new Set(['sa-fb'])`

**관리자 모드**: `prompt()` → SHA-256 해시 → `ADMIN_HASH` 비교. 세션 변수 `adminOn`.

### 4.8-B 교재 레지스트리 (`cfg.textbooks`)

**매트릭스 구조** (v3.8~): 교재명 목록은 전역 레지스트리이며 모든 학년학기에서 같은 전체 목록을 읽는다. grade_sem은 교재 자체가 아닌 **학급-교재 조합**에 종속.  
→ "최상위수학"은 `config/textbooks`에 한 번만 등록하고, 중1A반에선 `중1-1`, 중2B반에선 `중2-1`로 동시 사용 가능.

```
cfg.textbooks = { "최상위수학": true, "우공비": true }   // 이름 레지스트리만
cfg.sheets.M.classes.중1A.textbooks = ["최상위수학", "우공비"]
cfg.sheets.M.classes.중1A.tb_grade  = { "최상위수학": "중1-1", "우공비": "중3-1" }
```

**grade_sem 조회**: `cfg.sheets[sh].classes[cls].tb_grade[tb]`  
**`cfg.textbooks` 값**: `true` (존재 여부만 — grade_sem 저장 안 함)

**관리 흐름**:
1. 관리자 `sa-tbmgmt`: `[교재명] [+ 등록]` — `config/textbooks` 이름 레지스트리에만 추가 (학년정보 없음)
2. 학급 교재 추가(`addTbInline`): `[학년학기 ▼] [교재 ▼]` 선택. 교재 드롭다운은 선택한 학년학기에 종속되지 않고 `config/textbooks` 전체 목록을 표시  
   - 드롭다운에 없으면 "✏️ 직접 입력..." → 텍스트 입력 → 글로벌 레지스트리에도 자동 등록
   - 저장: `textbooks[]` push + `tb_grade[name] = gs`
3. 교재 chip: `중1-1 최상위수학 ×` (학년학기 badge 왼쪽)

**GRADE_SEM_LIST 단축 표시**:
- 중·초: `중3-1`, `초4-2` 형식
- 고등: `공통수학1`, `대수`, `미적분I`, `확통`

### 4.8-C 초기 설정 위저드 (온보딩)

**목적**: 강사 미설정 신규 사용자를 빈 화면 + 단일 버튼으로 방치하던 기존 동작을, 4단계 순차 가이드로 대체. 설정 항목을 순서대로 따라 입력하게 유도.

**발동 조건**: `init()`에서 `!instructor` 일 때 `wizardActive=true; wzStep=0` 설정 후 `renderMain()`. (기존 "⚙️ 설정으로 이동" 빈 화면 폐기)

**렌더 분기**: `renderMain()` 최상단에서 `if(wizardActive){renderWizard(mc);return;}` — 위저드 활성 중에는 사이드바 탭(`goNav`)을 눌러도 탭 콘텐츠 대신 위저드가 계속 렌더됨(이탈 차단). 종료는 "나중에 할게요"(skip) 또는 "시작하기"(finish)로만.

**풀스크린 (v2.4.0~)**: 온보딩 중엔 사이드바가 의미 없으므로 `renderMain()`이 `#wr`에 `wz-mode` 클래스를 토글(`wr.classList.toggle('wz-mode',wizardActive)`). CSS `#wr.wz-mode .sidebar{display:none}` + `.main{margin-left:0}` → 위저드가 전체폭 사용. 위저드 헤더(`.wz-head`)에 **설치·운용 가이드 링크**(`.wz-guide` → `./guide.html`) 노출(온보딩 단계에서도 가이드 접근 가능).

**상태 변수** (`app-core.js`):
- `wizardActive` (bool) — 위저드 활성
- `wzStep` (0~4) — 0:Firebase 1:계정 2:명단 3:수업 4:완료
- `wzCls` — 수업 단계에서 선택된 반(classId)

**4단계 구성** (`WZ_STEPS`):

| 단계 | 아이콘 | 내용 | 호출 함수 (기존 재사용) | 입력 DOM ID |
|------|--------|------|------------------------|-------------|
| 0 연결 | 🔥 | Firebase URL·경로 저장 | `saveFb()` | `#sUrl` `#sPth` |
| 1 계정 | 🔑 | 강사 이름 조회/신규등록 | `lookupInstr()` | `#acctName` |
| 2 명단 | 👥 | 학생 명단 불러오기 | `loadCfg()` | – |
| 3 수업 | 📚 | 담당 수업 배정 (+교재 등록) | `addA()` / `wzAddCourse()` | `#aCls` `#aTb` `#aRole` `#wzGs` `#wzTb` |

> 입력 DOM ID를 기존 설정 화면과 동일하게 두어 `saveFb`/`lookupInstr`/`addA` 등 기존 핸들러를 수정 없이 재사용. 이들이 끝에 호출하는 `renderMain()`은 `wizardActive` 덕분에 위저드를 재렌더하므로 단계 상태가 보존됨.

**교재 미등록 케이스 (핵심)**: 수업 단계에서 선택한 반(`wzCls`)에 등록된 과목(`config.classes[wzCls].courses`)이 없으면:
- "⚠️ 이 반에 등록된 교재 없음" 표시 + "수업 추가" 버튼 비활성
- 인라인 **과목(교재) 등록 폼** 노출: `[과정 ▼ (GRADE_SEM_LIST)] [교재명] [✓]` → `wzAddCourse()`
- `wzAddCourse()`: `subject = "{과정} {교재}"` 조합으로 `config.classes[wzCls].courses[subject]={textbook,curriculum}` 추가 + `saveLocal()` + `renderMain()`, 이후 `fbPatch('classes/{wzCls}/courses/{subject}')` (실패 무시·toast). `addCourseInline` 로직 미러
- 등록 즉시 과목 셀렉트(`#aTb`) 채워지고 "수업 추가" 활성
- **반(classId) 자체는 위저드에서 생성하지 않음** — 반 없으면 "이전 단계에서 학생 명단을 먼저 불러오세요" 안내. 반 생성은 기존 학급 관리 화면에서.

**단계 가드** (`wzNext()`):
- 0단계: `!dbUrl || !dbPath` → toast 차단
- 1단계: `!instructor` → toast 차단

**완료(4단계)**: 실데이터 기반 요약 체크리스트(Firebase 연결/강사명/학급·학생 수/담당 수업 수) → "🚀 시작하기"(`wzFinish()`: `wizardActive=false; activeTab='input'`).

**이탈**: "나중에 할게요"(`wzSkip()`: `wizardActive=false; activeTab='setting'`) → 기존 아코디언 설정 화면으로. 강사 미설정 상태면 다음 새로고침 시 위저드 재발동.

**스텝 인디케이터**: 상단 진행바 — 완료=초록 ✓, 현재=인디고(글로우), 대기=회색. CSS `.wz-*` / `.stp*` (`app.css`).

### 4.9 쓰기 권한 가드

| 함수 | 가드 조건 |
|------|-----------|
| `onPB()` (수행도 클릭) | `{sheet, cls, tb}` ∈ `instructor.assignments` |
| `pushProgress()` (진도/과제) | `{sheet, cls, tb}` ∈ `instructor.assignments` |
| `saveNote()` (특이사항) | `{sheet, cls}` ∈ `instructor.assignments` |

- 미로그인(`instructor === null`) 시: 모든 쓰기 차단
- 가드 불통과 시: Firebase PATCH 미호출 (무시, toast 없음)

### 4.10 localStorage 키

| 키 | 내용 |
|----|------|
| `drw_fb_url` | Firebase DB URL |
| `drw_fb_path` | Firebase 경로 |
| `drw_input` | 수행도·특이사항 로컬 캐시 |
| `drw_prog` | 진도/과제 로컬 캐시 |
| `drw_tags` | 수업 관찰 태그 로컬 캐시 (v3.2: drw_obs → drw_tags 변경) |
| `drw_instr` | 현재 강사 정보 |
| `drw_cfg` | config 로컬 캐시 |

### 4.11 UI 구현 규칙

**학급·교재 칩 (`buildClsAccordion`)**
- DOM ID 미사용 → `data-sh`, `data-cls`, `data-chip-type` 어트리뷰트로 식별
  (한글 클래스명 정규화 시 동일 길이 이름 간 ID 충돌 방지)
- `refreshTbChips` / `refreshStuChips`: `querySelector('[data-chip-type="..."]')` 방식

**`ensPath(sh, cls)`**
- 기존 클래스 객체라도 `students` / `textbooks` 배열 각각 존재 여부 별도 검사 후 초기화
- 구버전 Firebase 데이터 호환 보장

**`_ensureConfigShape()`**
- `cfg.sheets.M`, `cfg.sheets.T`는 항상 `{classes:{}}` 형태로 존재해야 한다.
- Firebase나 localStorage의 config에 한쪽 시트가 누락되어도 로드/저장/설정 렌더링 전에 자동 복원한다.

**`esc(s)` 유틸**
- HTML 이스케이프: `&`, `<`, `>`, `"`, `'` (`&#39;`) 전체 처리

---

## 5. Firebase 데이터 구조

```
{firebase_path}/

  config/
    instructors/
      {name}/
        name: "IDO"
        assignments:           ← list (웹에서 배정)
          - { classId: "3MGM", subject: "중3-1 SIGNATURE 100+", group: "M", role: "담임" }   ← 실제 저장 형식
          - { classId: "3TGM", subject: "중3-1 SIGNATURE 100+", group: "T", role: "부담임" } (구형 sheet/cls/tb 키는 PC 폴백만)
        presets: ["과제 완벽 수행 ✅", ...]
    textbooks/                 ← 전역 교재 이름 레지스트리 (관리자 전용, v3.3~)
      최상위수학: true
      우공비:     true
      ※ 값은 항상 true. grade_sem은 학급별 tb_grade에 저장
    sheets/
      M/
        classes/
          3MGM/
            students: [{name: "김상덕"}, ...]
            textbooks: ["우공비", "라이트쎈"]
            tb_grade: { "우공비": "중3-1", "라이트쎈": "중3-1" }  ← v3.4 신규
            is_sub: false   ← 구버전 폴백 (assignments.role 우선)
      T/ ...

  classes/                  ← 웹·CM 쓰기 / 전 클라이언트 읽기 (v2.0 정본 — config/sheets 아님)
    {classId}/
      group: "M"|"T"
      courses/
        {subject}/           ← subject = "{과정} {교재}" 조합 키
          textbook:   "SIGNATURE 100+"
          curriculum: "중3-1"
          archived:   true   ← v8.0 소프트 삭제. true면 보관 과목 — 표시·입력·전송 제외,
                               obs/scores/history/session 기록은 보존. 같은 키 재추가 시 필드 제거(복원).
                               쓰기는 항상 과목 노드 단위 PATCH (classes 전체 PUT 금지 — 부활 버그)

  input/                    ← 웹 쓰기 / PC·Analyzer 읽기  (당일, 휘발)
    {nameKey}/
      __note__:  { note: "..." }     ← 당일 특이사항. **학생별 단일(과목 무관, v2.1.1+)**
    (※ v2.1.1 이전 과목별 {subject}.note·.assign 은 폐기 — 마이그레이션으로 __note__ 통합)

  obs/                      ← 웹 쓰기 / PC·Analyzer 읽기  ★date별 누적
    {nameKey}/{subject}/{YYYY-MM-DD}:
        assign_grade:   "done"|"most"|"half"|"little"|"none"   ← **과제수행도 단일 소스**
        assign_tags:    [추가 프리셋…]
        condition:      "great"|"good"|"normal"|"low"|"bad"
        understand:     "top"|"good"|"normal_u"|"confused"|"hard"
        understand_sub: ["self_solve","retry","confused"]
        engage:         ["present","question","help","preview","error_fix"]
        caution:        ["sleepy","chat","attitude","late"]
        extra:          ["self_study","weekly_test","retest"]
        highlight:      ["perfect","improved","mastered","effort"]

  session/                  ← 웹 쓰기 / PC 읽기  (당일, 휘발)
    date: "M/D (요일)"      ← 표시용 포맷 (todayKey YYYY-MM-DD 아님 — 주의)
    class_data/
      {classId}|{subject}: { progress, homework }

  scores/                   ← 웹 쓰기 / Analyzer 읽기  ★누적
    achievement/{curriculumKey}/{testKey}: { meta:{type,date,max_score,memo,round?}, students:{nameKey:점수} }
    weekly/{classId}/{subject}/{testKey}:   { meta, students }
      testKey = "{YYYY-MM-DD}|{type}[|{round}]"

  history/                  ← PC 쓰기(전송 시 동기) / Analyzer 읽기  ★v2.1.2 신규 누적
    {nameKey}/{YYYY-MM-DD}: { note: "전송된 최종 특이사항", instructor: "{id}" }

  schema_version: 14        ← 정수, DB_SCHEMA 버전×10 (v1.4=14). Security Rules 전환 창에 생성(v8.16).
                              클라 SCHEMA_MAX 초과 시: 웹·PC·CM 차단, Analyzer 경고. 부재 시 통과.

  (lastSent/ — v2.1.2 폐기)
```

**접근 인증 (v8.16, Security Rules 전환 대비)**: 모든 클라이언트 REST 요청은 시크릿 설정 시
`?auth={DB Secret}`을 부가(레거시 admin 토큰 — 룰 우회). 미설정 시 무인증(전환 전 동작).
저장 위치 — 웹 `drw_db_secret`(localStorage) / PC `config.json firebase_secret`(v8.47부터 DPAPI 암호화) /
CM `settings.json dbSecret` / Analyzer `drw_fb_secret`(localStorage).
룰·전환 절차는 `documents/SECURITY_RULES_PLAN.md`, 룰 본문은 `database.rules.json`(미배포 초안),
전환 실행은 `scripts/deploy-rules.ps1`(클라 무장 후 수동).
⚠️ 웹·CM·Analyzer 시크릿은 여전히 평문 저장 — DB Secret은 룰 우회 admin 토큰이라
단말 1대만 새도 전체 DB 노출. 근본 차단은 2차 Firebase Auth(경로별 룰)로만 가능(CBT 종료 후).

**누적 vs 휘발**: 누적 = `obs/`·`scores/`·`history/` (Analyzer 소스, 날짜키 YYYY-MM-DD). 휘발(당일 덮어쓰기) = `input/`·`session/`.
**날짜 포맷**: 누적 노드·testKey = `YYYY-MM-DD`(todayKey). session.date = `M/D(요일)`(표시용).
**TAGS key는 불변** — Firebase 저장값. label만 수정 가능.  
**assignments 구조**: list (Firebase 저장 기준). `_fetch_class_data`에서 `config/instructors/{id}/assignments` 경로로 조회.

**부담임 판단 우선순위**
```
1순위: instructor_assignments[cls].role === "부담임"
2순위 (폴백): config/sheets/.../is_sub === true
```

---

## 6. 관찰 태그 정의 (constants.py TAGS)

5개 축(스파이더 차트) 원천 데이터:

| 축 | 원천 | 산출 방식 |
|---|---|---|
| ① 수업 태도 | `condition` | 긍정(great+good) 비율 |
| ② 참여도 | `engage` (발표+질문+오류정정) | 발생 횟수 / 수업수 |
| ③ 과제 성실도 | `assign` (input/) | 성실 계열 횟수 / 수업수 |
| ④ 이해도 | `understand` + `understand_sub` | 빠름 비율 + 긍정 태그 빈도 |
| ⑤ 성취도 | `scores/` | 최근 시험 학급 내 백분율 |

---

## 7. 초기화 정책

### PC 초기화

**원칙**: 로컬 캐시 범위 내에서만 동작. Firebase 직접 삭제 없음.

| 동작 | 로컬 범위 | Firebase |
|------|-----------|----------|
| 현재 반 초기화 | 해당 반 student + note | 없음 |
| 전체 초기화 | `_my_classes()` 범위 전체 | 없음 |
| 전송 후 자동 | student + note + force | 없음 |

### 웹 초기화 (4단계)

| 레벨 | 로컬 범위 | Firebase 범위 | 권한 |
|------|-----------|---------------|------|
| Lv1 | inputData — assignments 해당 키만 | input/ — 해당 키 null PATCH | 일반 강사 |
| Lv2 | inputData + progressData — assignments 해당 키만 | input/ + session/ — 해당 키 null PATCH | 일반 강사 |
| Lv3 | inputData + progressData 전체 | input/ + session/ + 전 강사 assignments 초기화 | **관리자** |
| Lv4 | 전체 | config/ + input/ + session/ 전체 | **관리자** |

**caution 태그 학부모 전달 정책**

| key | label | 전달 방식 |
|---|---|---|
| `late` | ⏰ 지각 | **직접 언급** — 시간 엄수 습관을 권유하는 수준으로 전달 |
| `sleepy` | 💤 졸음 | **완곡** — 컨디션 관리 필요성 암시 |
| `chat` | 🗣 잡담 | **완곡** — 집중력 유지 필요성 암시 |
| `attitude` | 😤 태도불량 | **완곡** — 수업 참여 자세에 대한 대화 필요성 암시 |

**FR-RESET 요구사항**

| ID | 요구사항 |
|----|---------|
| FR-RESET-01 | Lv1·Lv2는 실행 강사의 `assignments` 범위 내 키만 삭제 |
| FR-RESET-02 | Firebase 쓰기는 개별 키 null PATCH 방식만 (노드 전체 PUT 금지) |
| FR-RESET-03 | `assignments` 비어있는 강사 Lv1·Lv2 실행 시 Firebase 쓰기 차단, 로컬만 초기화. toast 안내 |

---

## 8. 버전 관리 및 고정값

### 8.1 버전 관리 정책

| 파일 | 상수명 | 선언 위치 |
|------|--------|----------|
| `constants.py` | `APP_VERSION` | 최상단 |
| `index.html` | `const APP_VERSION` | `<script>` 최상단 |

**하드코딩 금지** — 버전 문자열은 각 파일 내 단일 상수로 관리.

### 8.2 DEFAULT_CONFIG 키 (constants.py)

| 키 | 기본값 | 비고 |
|----|--------|------|
| `wait_time` | `0.5` | 카카오톡 전송 딜레이 (초) |
| `room_prefix` | `"오직 "` | 톡방 접두사 |
| `firebase_url` | `""` | |
| `firebase_path` | `""` | |
| `ai_engine_type` | `"gemini"` | 멀티 엔진 선택 (무료·추천 기본값, `AI_ENGINE_ORDER` 선두) |
| `ai_api_key` | `""` | 통합 API Key |
| `instructor_id` | `""` | |

### 8.3 고정 상수

| 항목 | 값 | 위치 |
|------|-----|------|
| AI 쿨다운 (Groq) | 30초 | `AI_COOLDOWN_GROQ` |
| AI 쿨다운 (Gemini) | 7초 | `AI_COOLDOWN_GEMINI` (free RPM~10) |
| AI 쿨다운 (유료) | 3초 | `AI_COOLDOWN_PAID` |
| 엔진별 쿨다운 맵 | `{groq:30, gemini:7}`, 그 외 PAID | `AI_COOLDOWNS` |
| Groq 모델 | `qwen/qwen3-32b` | ai_engine.py |
| Gemini 모델 | `gemini-2.5-flash` | `GEMINI_MODEL` (constants.py) |
| Claude 모델 | `claude-sonnet-4-6` | ai_engine.py |
| OpenAI 모델 | `gpt-4o-mini` | ai_engine.py |

---

## 9. 안정성 구현 노트

**PC 앱**
- `_pull_mobile_data`: Firebase config 로드 후 UI 갱신(`_switch_sheet`)은 messagebox 이후 동기 호출. `after()` 예약 금지 — 이벤트 루프 재진입으로 인한 TclError 유발
- `_populate_student_list`: `sl_inner` 자식 파괴 전 `status_w` 해당 sheet 항목 일괄 삭제 (stale Canvas ref 방지)
- `_update_dot`: TclError 방어 처리 필수
- `_do_send`: 별도 스레드 실행. 루프 내 상태 업데이트는 `root.after(0, lambda ...)`, 완료 후 처리는 `root.after(0, _on_done)` 으로 메인 스레드에 위임 (tkinter 스레드 안전 원칙)
- `_build_tags_context`: `caution`과 `extra`는 독립 블록. caution 없이 extra만 존재해도 정상 처리 (변수 스코프 분리). `highlight` 있으면 lines 최상단에 삽입
- `nickname_suffix`: 한 글자 이름 방어 — `full_name[1:] or full_name`
- **에러 메시지 사용자화 (`errors.py` `humanize_error(exc, context)`)**: 기술적 예외를 비개발자용 한국어 안내로 변환. HTTP 상태코드 맵(`_HTTP_MSG`: 400/401/403/404/413/429/5xx)+timeout/URLError(네트워크)/JSONDecodeError(파싱)/Gemini 빈응답(내용 필터). **용량 초과 우선 감지**: 응답 본문에 `payload size`·`too large`·`exceeds the limit` 등이 있으면 상태코드와 무관하게 413("한 번에 보낸 내용이 너무 많습니다. 학생 수를 줄여 나눠서 생성") 안내(일부 API는 400으로 반환). 끝에 `(참고: HTTP 413)` 식 식별 코드만 남겨 문의 시 추적 가능. 적용처: `ai_engine`(단건·일괄 생성), `app.py`(데이터 가져오기·Firebase 연결 테스트·강사 계정 처리·명단 가져오기)

**웹 PWA**
- 아코디언 상태는 `openSaIds: Set`로 DOM 재생성 후에도 복원
- `esc(s)`: onclick 어트리뷰트 내 작은따옴표 충돌 방지 필수

---

## 10. 미완료 (T.B.D.)

| 항목 | 비고 |
|------|------|
| 최종 메시지 직접 수정 | 미리보기 패널 편집 가능화. AI생성 후 편집 시 재생성 경고 필요 |
| PC 강사 배정 UI | 현재 웹에서만 가능 |
| Firebase Security Rules | **현재 무인증 공개 — 공식배포 前 룰 배포 필수**(`scripts/deploy-rules.ps1`). 2차 Firebase Auth(경로별 권한·클라 admin 게이트 대체)는 CBT 종료 후 |
| API Key 보안 저장 | **[PC] v8.47 DPAPI 암호화 완료**(`secret_codec.py`). 웹/CM/Analyzer DB 시크릿은 평문(localStorage·json) — 2차 Auth로 해소 |
| 웹/PC IP 보호 | 웹 JS 평문 노출(난독화 미적용)·PC exe 디컴파일 가능. 핵심 프롬프트(`ai_engine.py`) 서버화는 미적용 |
| PII 파기 정책 | obs/scores/history 소프트삭제만(무한 누적). 보존기간·파기 절차 미정 |

## 11. 스코프 제외

| 항목 | 사유 |
|------|------|
| 로컬 전용 시나리오 | 폐기, Firebase 필수 |
| 모바일 AI 특이사항 생성 | PC 전용 확정 |
| 웹 카카오톡 전송 | PC 앱 전용 확정 |
| 모바일 앱 설치형 | APK 전환 계획 없음 |
| PDF 출력 | Analyzer 단계에서 검토 |
| 학생 등록/삭제/반 배정 | ClassManager 관리자 전용 |

---

## 12. v6.0 Firebase 경로 변환 (구 → 신)

> 상세 스키마: [ClassManager/documents/DB_SCHEMA.md](../../ClassManager/documents/DB_SCHEMA.md)

### 12.1 핵심 경로 변환

| 구 경로 | 신 경로 |
|---------|---------|
| `config/sheets/{group}/classes/{classId}/students` | `students/?orderBy="class"&equalTo="{classId}"` |
| `obs/{group}\|{classId}\|{nameKey}\|{subject}/{date}` | `obs/{nameKey}/{subject}/{date}` |
| `input/{group}\|{classId}\|{nameKey}\|{subject}` | `input/{nameKey}/{subject}` |
| `scores/{group}\|{classId}/{testKey}/students/{name}` | `scores/weekly/{classId}/{subject}/{testKey}/students/{nameKey}` |
| `config/sheets/{g}/classes/{cls}/tb_grade/{tb}` | `classes/{classId}/courses/{subject}/curriculum` |

### 12.2 성적 노드 분리

| 시험 유형 | 신 경로 | 입력 권한 |
|----------|---------|----------|
| 주간Test, 확인학습, 기출모의고사, 직접입력 | `scores/weekly/{classId}/{subject}/{testKey}/` | 해당 subject instructor |
| 성취도평가, 반배치고사, 실전모의고사 | `scores/achievement/{curriculumKey}/{testKey}/` | 담임만 |

> 단위 선택 UI는 없음 — 유형이 단위를 결정(`ACHIEVEMENT_TYPES`). 기출모의고사는 v8.20에서 과정 단위 → 반별로 정정(기존 achievement 잔존 기록은 수정·저장 시 weekly로 자동 이동).
>
> **testKey 식별 규칙(v8.23)**: 반별 = `날짜|유형[|회차]`, 학년 = `유형[|회차]`(날짜 제외 — 시행일이 반·학생별로 달라도 같은 시험으로 합산, 날짜는 meta 대표값). 같은 과정에서 같은 유형 시험을 회차 없이 반복하면 충돌 confirm이 뜨므로 학년 시험은 **회차 입력 권장**. 날짜 포함 구키로 저장된 기존 학년 기록은 수정·저장 시 새 키로 자동 이동.

`curriculumKey`: curriculum 키의 `.`을 `_`로 치환 (Firebase 키 제약)  
예) `middle_school.grade_3.semester_1` → `middle_school_grade_3_semester_1`

### 12.3 변수명 변환

| 구 변수명 | 신 변수명 |
|----------|----------|
| `sheet` / `sh` / `curSheet` | `group` / `activeGroup` |
| `cls` / `src_cls` / `dst_cls` | `classId` / `sourceClassId` / `targetClassId` |
| `tb` | `subject` |
| `cfg` | `config` |
| `okey` | 제거 (복합키 불필요) |
| `fbUrl` / `fbPath` | `dbUrl` / `dbPath` |
| `curNav` | `activeTab` |
| `sts` | `students` |
| PC 직접 진도/과제 입력 UI | v3.0에서 웹 전용으로 전환, PC UI 제거 완료 |
| `name` (이름 기반 nameKey) | `nameKey` = 출결번호 (불변 고유번호, ClassManager 발부) |
