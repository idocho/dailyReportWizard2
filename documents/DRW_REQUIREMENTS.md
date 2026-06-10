# DailyReportWizard — 요구사항 명세서

**Crafted by IDO(idocho@kakao.com) · Powered by Claude AI**  
**문서 버전**: 8.10 · **앱 버전**: v2.2.3(개발)/v2.2.2(안정) · **최종 수정**: 2026-06-11

> Firebase 스키마 전체 명세: [ClassManager/documents/DB_SCHEMA.md](../../ClassManager/documents/DB_SCHEMA.md)

---

## 변경 이력

| 문서 버전 | 날짜 | 주요 변경 |
|-----------|------|-----------|
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
※ **PC 앱 쓰기 제한**: Firebase 쓰기는 `lastSent/` 기록 + 강사 신규 등록만 허용  
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
⑥ session/class_data/ 로드 → progress_data (없으면 lastSent/ 폴백)
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
- **순차 전송 취소**: 전송 시작 후 `send_btn` → "⏹ 전송 취소" 토글. `self._send_cancel`(`threading.Event`) set → 3초 카운트다운 및 루프 매 학생 진입 시 검사, **현재 학생 완료 후 중단**. 취소 시 전송된 N명만 발송, **로컬 데이터 초기화 안 함**(미전송분 유지). 완료 시에만 기존 초기화 + `lastSent/` push
- `pyautogui` 미설치 시: `AUTOMATION=False`, 전송 버튼 비활성화
- 전송 **완료** 후: `student_data`, `note_data`, `force_data` 초기화 / `progress_data` 유지 / Firebase `lastSent/` push
- **스레드 안전**: `_do_send`는 별도 스레드 실행. UI 업데이트 전체를 `root.after(0, ...)` 로 메인 스레드에 위임

### 2.9 설정 창

| 섹션 | 내용 |
|------|------|
| 기본 매크로 설정 | 카카오톡 전송 딜레이(초), 톡방 접두사 |
| Firebase 연결 | DB URL, DB 경로, ⚡ 연결 테스트 (`config` 노드 조회 + null 여부 검증) |
| 내 강사 계정 | 이름 입력 → 조회/신규등록, 🔄 학급명단 동기화 |
| AI 엔진 설정 | 엔진 종류 선택(표시명 Gemini/Claude/GPT (OpenAI)/Groq, 내부 id gemini/claude/openai/groq) + API Key + 👁 토글 |
| 학급·학생·교재·프리셋 | 웹 PWA 전담 안내 |

**AI 엔진 설정 저장 키**

| 키 | 내용 |
|----|------|
| `ai_engine_type` | `"groq"` \| `"gemini"` \| `"openai"` \| `"claude"` |
| `ai_api_key` | 마지막 저장 Key (폴백용) |
| `groq_api_key` | Groq 전용 Key |
| `gemini_api_key` | Gemini 전용 Key |
| `openai_api_key` | OpenAI 전용 Key |
| `claude_api_key` | Claude 전용 Key |

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
- 직접 작성 메모는 참고 자료가 아니라 교사가 직접 입력한 핵심 전달 사항으로 취급하며, 최종 문장에 자연스럽게 포함해야 한다.
- `max_tokens=400`, `temperature=0.75` (자연스러운 문체)
- system prompt: `_base_conditions()` 전달 (Claude: system 필드, Groq/OpenAI: system role 메시지, Gemini: `system_instruction`)
- 완료 후 쿨다운 틱 시작

### 3.3 일괄 생성 (`gen_all`)

- 현재 시트의 `STATUS_READY` 학생 전원 단일 API 호출
- 부담임 반 자동 제외
- 배치 프롬프트: 학생 데이터 JSON 배열 → JSON 배열 응답 (`max_tokens=8192`, `temperature=0.5`)
  - 학생당 출력 ~68토큰 실측 → 8192는 ~100명까지 여유. (4096→8192 상향: 메모/하이라이트 포함 시 마진 확보)
- system prompt: `_base_conditions()` 전달 (JSON 안정성 위해 temperature 0.5 유지)
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

1. 문체: ~했습니다 체 통일. 학생 이름 **또는** 수업 내용으로 자연스럽게 시작 (이름 고정 패턴 금지)
2. 금지: '어머님/학부모님' 호칭, 시스템 표현, 할루시네이션
3. 태그 반영: 명시된 항목만. 미명시 이벤트 임의 추가 금지
4. 주의 태그: '졸음·잡담·태도불량' 직접 단어 절대 금지. '오늘은 조금 피곤해 보이는 날이었습니다' 수준 완곡 표현
5. 기타 이벤트: 자율학습·주간Test·재시험은 다른 수업 묘사와 섞지 않고 별도 문장으로 명확히 전달
6. 하이라이트: ⭐ 항목 있으면 가장 인상적으로 표현
7. 결석: 데이터 없으면 안부 인사 + 다음 수업 기약 코멘트
8. 과제 반복 금지: 진도·과제(페이지·번호)는 메시지 별도 항목으로 전달되므로 특이사항에서 그대로 읽어주는 문장 금지
9. 출력: 순수 텍스트 (JSON·마크다운 금지). 2~3문장, 100자 내외

**few-shot 예시** (단건 프롬프트에 포함, 문체·어조 참고용)
> "오늘 이차함수 단원에서 막혔던 개념을 반복 설명 후 이해했습니다. 틀린 문항을 스스로 재풀이하며 오답을 정리하는 모습이 인상적이었습니다."

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

**시험 유형 6종** (`SCORE_TYPES`)

| 유형 | 설명 |
|------|------|
| 주간Test | 매주 정기 테스트 |
| 기출모의고사 | 기출문제 기반 모의고사 |
| 실전모의고사 | 실전 모의고사 |
| 성취도평가 | 단원별 성취도 평가 |
| 반배치고사 | 반 편성/재배치 시험 |
| 직접입력 | 사용자 정의 시험명 |

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

### 4.8 설정 화면 (아코디언)

| # | 섹션 ID | 내용 |
|---|---------|------|
| 1 | `sa-fb` | 클라우드 연결 — Firebase URL·경로, 학생 명단 불러오기 |
| 2 | `sa-acct` | 내 계정 — 강사 이름 조회·신규등록. 미로그인 시 자동 펼침 |
| 3 | `sa-preset` | 내 프리셋 — ✏️ 인플레이스 편집, 추가/삭제 |
| 4 | `sa-asgn` | 내 담당 수업 — 반+교재+역할(담임/부담임) 추가/삭제 |
| 5 | `sa-cls` | 학급 & 학생 관리 — 2단계 드릴다운 |
| 6 | `sa-tbmgmt` | 교재 목록 관리 — **관리자 전용**. 전역 교재 레지스트리 (`cfg.textbooks`) 등록/삭제 |
| 7 | `sa-admin` | 강사 관리 — 관리자 전용 (`adminOn=true` 시만 렌더링) |
| 8 | `sa-reset` | 초기화 — 4단계 (Lv1·Lv2는 assignments 범위 내만) |

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
          - { sheet: "M", cls: "3MGM", tb: "3-1 우공비", role: "담임" }
          - { sheet: "T", cls: "3TGM", tb: "3-1 우공비", role: "부담임" }
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

  (lastSent/ — v2.1.2 폐기)
```

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
| `ai_engine_type` | `"groq"` | 멀티 엔진 선택 |
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

**웹 PWA**
- 아코디언 상태는 `openSaIds: Set`로 DOM 재생성 후에도 복원
- `esc(s)`: onclick 어트리뷰트 내 작은따옴표 충돌 방지 필수

---

## 10. 미완료 (T.B.D.)

| 항목 | 비고 |
|------|------|
| 최종 메시지 직접 수정 | 미리보기 패널 편집 가능화. AI생성 후 편집 시 재생성 경고 필요 |
| PC 강사 배정 UI | 현재 웹에서만 가능 |
| Firebase Security Rules | 현재 기본 설정. 최종 단계에서 강화 예정 |
| API Key 보안 저장 | config.json 평문 저장 중. macOS Keychain / 암호화 미적용 |

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
| 주간Test, 직접입력 | `scores/weekly/{classId}/{subject}/{testKey}/` | 해당 subject instructor |
| 성취도평가, 기출모의고사, 실전모의고사, 반배치고사 | `scores/achievement/{curriculumKey}/{testKey}/` | 담임만 |

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
