# DailyReportWizard — 요구사항 명세서

**Crafted by IDO(idocho@kakao.com) · Powered by Claude AI**  
**문서 버전**: 4.9 · **앱 버전**: v2.0.0 · **최종 수정**: 2026-05-24

---

## 변경 이력

| 문서 버전 | 날짜 | 주요 변경 |
|-----------|------|-----------|
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
| `ai_engine.py` | AI 생성, 태그 프롬프트 주입, 멀티 엔진(Groq/Claude/GPT) | 엔진 추가·프롬프트 튜닝 시 |
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
반 공통 진도/과제 입력                 학생별 데이터 열람
학생별 입력:                           특이사항 직접 편집
  - 과제수행도                         AI 특이사항 초안 생성
  - 수업 관찰 태그 (v2.0 신규)         (Groq / Claude / GPT 선택)
학급·학생·교재·프리셋 관리             카카오톡 메시지 전송
```

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
│  헤더: 로고 · 버전 · 날짜                   [pyautogui 경고]     │
│  크레딧 바                                                        │
├─────────────────────────────────────────────────────────────────┤
│  탭바: [M반] [T반]              [📥 데이터 가져오기] [⚙ 설정]   │
├──────────────┬──────────────────────────┬───────────────────────┤
│  좌 패널     │  중앙 패널               │  우 패널              │
│  학생 목록   │  진도/과제 요약 (반 공통) │  메시지 미리보기      │
│  (신호등)    │  교재별 수행도 표시       │  글자 수              │
│  ▾/▸ 접기   │  ⚡ 강제 완료 버튼        │                       │
│              │  특이사항 (편집 가능)     │                       │
│              │  ✨ AI생성 버튼           │                       │
├──────────────┴──────────────────────────┴───────────────────────┤
│  상태바: 완료 N명   진행중 N명   미입력 N명  (hover → 이름 툴팁) │
│                                [✨ 전체 AI생성] [🚀 전송 (N명)]  │
└─────────────────────────────────────────────────────────────────┘
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
① config/ 로드  → sheets, presets 갱신
② config/instructors/{id} 로드 → 강사별 assignments 우선 적용
③ input/ 로드   → student_data, note_data 채움
④ obs/ 로드     → tag_data 채움 (v2.0 신규)
⑤ session/class_data/ 로드 → progress_data (없으면 lastSent/ 폴백)
```

**가져오기 고정 정책** (v0.9.3~, 다이얼로그 폐지)

| 데이터 | 정책 |
|--------|------|
| 과제수행도 | 항상 웹 데이터로 교체 |
| 진도/과제 | 항상 웹 데이터로 교체 |
| 메모/특이사항 | 항상 웹 데이터로 교체 |

> 웹 입력 화면에서 직접 수정한 메모가 PC 앱에 즉시 반영되는 것을 우선한다. PC에서 AI 생성/직접 편집한 특이사항은 다음 가져오기 시 웹 메모 값으로 교체될 수 있다.

한글 강사명: `urllib.parse.quote(node, safe='/')` 자동 처리

### 2.8 전송 로직

- **전송 대상**: `STATUS_READY` 학생만, `_my_classes()` 화이트리스트 적용
- **부담임 반 제외**: `assignments[cls].role == "부담임"` → 전송 제외. 폴백: `config/sheets/.../is_sub: true`
- `pyautogui` 미설치 시: `AUTOMATION=False`, 전송 버튼 비활성화
- 전송 완료 후: `student_data`, `note_data`, `force_data` 초기화 / `progress_data` 유지 / Firebase `lastSent/` push
- **스레드 안전**: `_do_send`는 별도 스레드 실행. UI 업데이트 전체를 `root.after(0, ...)` 로 메인 스레드에 위임

### 2.9 설정 창

| 섹션 | 내용 |
|------|------|
| 기본 매크로 설정 | 카카오톡 전송 딜레이(초), 톡방 접두사 |
| Firebase 연결 | DB URL, DB 경로, ⚡ 연결 테스트 (`config` 노드 조회 + null 여부 검증) |
| 내 강사 계정 | 이름 입력 → 조회/신규등록, 🔄 학급명단 동기화 |
| AI 엔진 설정 | 엔진 종류 선택(groq/openai/claude) + API Key + 👁 토글 |
| 학급·학생·교재·프리셋 | 웹 PWA 전담 안내 |

**AI 엔진 설정 저장 키**

| 키 | 내용 |
|----|------|
| `ai_engine_type` | `"groq"` \| `"openai"` \| `"claude"` |
| `ai_api_key` | 통합 API Key |
| `groq_api_key` | groq 선택 시 병행 저장 (하위 호환 폴백) |

**학급명단 동기화 (`_fetch_class_data`)**

`config/instructors/{id}/assignments` 노드 조회 (list). 반드시 강사 계정 조회 완료 후 실행.

### 2.10 데이터 지속성

| 데이터 | 저장 위치 | 초기화 시점 |
|--------|-----------|-------------|
| 진도/과제 (`progress_data`) | `daily_cache.json` | 수동 초기화 또는 확인 후 |
| 과제수행도 (`student_data`) | 메모리 | 전송 완료 후 자동 |
| 특이사항 (`note_data`) | 메모리 | 전송 완료 후 자동 |
| 강제완료 (`force_data`) | `daily_cache.json` | 전송 완료 후 자동 |
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
| `_gen_ai_note_all()` | 전체 AI생성 대상 |

**부담임 반 추가 제한**

| 대상 | 제한 |
|------|------|
| 특이사항 `tk.Text` | `state='disabled'` |
| ⚡ 강제 완료 버튼 | `state='disabled'` |
| ✨ AI생성 버튼 | `state='disabled'` |
| 전송 대상 | 제외 |
| 전체 AI생성 대상 | 제외 |

---

## 3. PC 앱 — ai_engine.py (AI 생성 엔진)

### 3.1 멀티 엔진 구조

설정 창에서 엔진을 선택하면 `_call_ai_hub()`가 해당 엔진 규격으로 API를 호출한다.

| 엔진 | 모델 | 용도 |
|------|------|------|
| `groq` | `llama-3.1-8b-instant` | 무료, 속도 최적화 |
| `claude` | `claude-sonnet-4-6` | 문장력·감성 우선 |
| `openai` | `gpt-4o-mini` | 범용 |

**API Key 로드 순서**: `ai_api_key` → (groq 선택 시) `groq_api_key` 폴백

### 3.2 단건 생성 (`gen_single`)

- 컨텍스트: 학생명, 교재별 수행도·진도·과제, 직접 작성 메모, 오늘 태그
- AI 호출 직전 현재 특이사항 `Text` 위젯 값을 `note_data`에 저장한 뒤 프롬프트를 생성한다. 따라서 FocusOut 전 작성한 메모도 `[직접 작성 메모 — 반드시 반영]`에 반영된다.
- 직접 작성 메모는 참고 자료가 아니라 교사가 직접 입력한 핵심 전달 사항으로 취급하며, 최종 문장에 자연스럽게 포함해야 한다.
- `max_tokens=400`, `temperature=0.75` (자연스러운 문체)
- system prompt: `_base_conditions()` 전달 (Claude: system 필드, Groq/OpenAI: system role 메시지)
- 완료 후 쿨다운 틱 시작

### 3.3 일괄 생성 (`gen_all`)

- 현재 시트의 `STATUS_READY` 학생 전원 단일 API 호출
- 부담임 반 자동 제외
- 배치 프롬프트: 학생 데이터 JSON 배열 → JSON 배열 응답 (`max_tokens=4096`, `temperature=0.5`)
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
8. 출력: 순수 텍스트 (JSON·마크다운 금지). 2~3문장, 100자 내외

**few-shot 예시** (단건 프롬프트에 포함, 문체·어조 참고용)
> "오늘 이차함수 단원에서 막혔던 개념을 반복 설명 후 이해했습니다. 틀린 문항을 스스로 재풀이하며 오답을 정리하는 모습이 인상적이었습니다."

---

## 4. 웹 PWA — index.html

### 4.1 디자인 목표

- **기기**: 11인치 태블릿 가로모드 (1024×768) 전용
- **밀도**: 12명 이내 한 반이 스크롤 없이 한 화면에 표시 (행 높이 ≤ 54px)
- **입력 방식**: 버튼 선택 중심, 텍스트 최소화
- **소형 화면 차단**: 1024px 미만 전체 오버레이 마스킹

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

**시험 유형 (기본 5종)**

| 유형 | 회차 |
|---|---|
| 주간 Test | O (1회차, 2회차...) |
| 성취도 평가 | X (단원명으로 구분) |
| 반배치고사 | X (시기로 구분) |
| 실전 모의고사 | O |
| 기출 모의고사 | O |

**입력 플로우**:  
시험 유형 선택 → 회차/식별자 선택 → 만점 설정 → 학급 전체 점수 입력 → 분포/석차 자동 산출 → 저장

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

  input/                    ← 웹 쓰기 / PC 읽기
    {sheet}|{cls}|{name}|{tb}:      { assign: "과제 수행 양호 👍" }
    {sheet}|{cls}|{name}|__note__:  { note: "수업 태도 양호" }

  obs/                      ← 웹 쓰기 / PC 읽기 (v2.0 신규)
    {sheet}|{cls}|{name}/
      {YYYY-MM-DD}:
        condition:      "great" | "good" | "normal" | "bad"
        understand:     "fast" | "normal_u" | "slow"
        understand_sub: ["self_solve", "retry", "confused"]
        engage:         ["present", "question", "help", "preview", "error_fix"]
        caution:        ["sleepy", "chat", "attitude", "late"]
        extra:          ["self_study", "weekly_test", "retest"]
        highlight:      "perfect" | "improved" | "mastered" | "effort"  ← v3.2 신규

  session/                  ← 웹 쓰기 / PC 읽기
    class_data/
      {sheet}|{cls}|{tb}: { progress: "3단원 2차시", homework: "p.45~48" }

  scores/                   ← 웹 쓰기 / Analyzer 읽기 (v2.0 신규)
    {sheet}|{cls}/
      {exam_type}|{round}|{YYYY-MM-DD}:
        meta: { type, round, date, perfect }
        {학생명}: 85
        {학생명}: 72

  lastSent/                 ← PC 쓰기
    date: "5/19 (화)"
    class_data/
      {sheet}|{cls}|{tb}: { progress, homework }
```

**obs 키 규칙**: `obs/{sheet}|{cls}|{name}/{YYYY-MM-DD}`  
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
| AI 쿨다운 (유료) | 3초 | `AI_COOLDOWN_PAID` |
| Groq 모델 | `llama-3.1-8b-instant` | ai_engine.py |
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
| PC 직접 진도/과제 입력 UI | v3.0에서 웹 전용으로 전환, PC UI 제거 완료 |
