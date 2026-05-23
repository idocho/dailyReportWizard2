# DailyReportWizard — 요구사항 명세서

**Crafted by IDO(idocho@kakao.com) · Powered by Claude AI**  
**문서 버전**: 3.0 · **앱 버전**: v2.0.0 · **최종 수정**: 2026-05-23

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
| `firebase.py` | Firebase REST CRUD, obs 로드 | 노드 추가 시 |
| `ai_engine.py` | AI 생성, obs 프롬프트 주입, 멀티 엔진(Groq/Claude/GPT) | 엔진 추가·프롬프트 튜닝 시 |
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
- **담당 반만 표시**: `instructor_assignments` 기반 화이트리스트 필터 (없으면 전체)
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
④ obs/ 로드     → obs_data 채움 (v2.0 신규)
⑤ session/class_data/ 로드 → progress_data (없으면 lastSent/ 폴백)
```

**가져오기 고정 정책** (v0.9.3~, 다이얼로그 폐지)

| 데이터 | 정책 |
|--------|------|
| 과제수행도 | 항상 웹 데이터로 교체 |
| 진도/과제 | 항상 웹 데이터로 교체 |
| 특이사항 | 로컬 값 있으면 보호, 비어있을 때만 채움 |

> 특이사항 로컬 보호 이유: PC 직접 편집·AI 생성 내용이 재가져오기 시 덮어씌워지는 위험 방지.

한글 강사명: `urllib.parse.quote(node, safe='/')` 자동 처리

### 2.8 전송 로직

- **전송 대상**: `STATUS_READY` 학생만, `_my_classes()` 화이트리스트 적용
- **부담임 반 제외**: `assignments[cls].role == "부담임"` → 전송 제외. 폴백: `config/sheets/.../is_sub: true`
- `pyautogui` 미설치 시: `AUTOMATION=False`, 전송 버튼 비활성화
- 전송 완료 후: `student_data`, `note_data`, `force_data` 초기화 / `progress_data` 유지 / Firebase `lastSent/` push

### 2.9 설정 창

| 섹션 | 내용 |
|------|------|
| 기본 매크로 설정 | 카카오톡 전송 딜레이(초), 톡방 접두사 |
| Firebase 연결 | DB URL, DB 경로, ⚡ 연결 테스트 |
| 내 강사 계정 | 이름 입력 → 조회/신규등록, 🔄 학급명단 동기화 |
| AI 엔진 설정 | 엔진 종류 선택(groq/openai/claude) + API Key + 👁 토글 |
| 학급·학생·교재·프리셋 | 웹 PWA 전담 안내 |

**AI 엔진 설정 저장 키**

| 키 | 내용 |
|----|------|
| `ai_engine_type` | `"groq"` \| `"openai"` \| `"claude"` |
| `ai_api_key` | 통합 API Key |
| `groq_api_key` | groq 선택 시 병행 저장 (하위 호환 폴백) |

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
def _my_classes(self, sheet) -> list[tuple[str, dict]]:
    # assignments 있음 → 해당 sheet의 담당 반만 (부담임 포함)
    # assignments 없음 → 해당 sheet 전체 (show_all)
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
| `claude` | `claude-3-5-sonnet-20241022` | 문장력·감성 우선 |
| `openai` | `gpt-4o-mini` | 범용 |

**API Key 로드 순서**: `ai_api_key` → (groq 선택 시) `groq_api_key` 폴백

### 3.2 단건 생성 (`gen_single`)

- 컨텍스트: 학생명, 교재별 수행도·진도·과제, 기존 특이사항, 오늘 obs 태그
- `max_tokens=400`
- 완료 후 쿨다운 틱 시작 (`AI_COOLDOWN = 30`초)

### 3.3 일괄 생성 (`gen_all`)

- 현재 시트의 `STATUS_READY` 학생 전원 단일 API 호출
- 부담임 반 자동 제외
- 배치 프롬프트: 학생 데이터 JSON 배열 → JSON 배열 응답 (`max_tokens=4096`)
- 응답 파싱: `json.loads()` 전 ` ```json ``` ` 펜스 제거

### 3.4 obs 태그 → 프롬프트 변환 (`_build_obs_context`)

| obs 필드 | 변환 방식 |
|----------|-----------|
| `condition` | `_CONDITION_TEXT` 매핑 → 자연어 1줄 |
| `understand` | `_UNDERSTAND_TEXT` 매핑 |
| `understand_sub[]` | `_UNDERSTAND_SUB_TEXT` 매핑, 복수 가능 |
| `engage[]` | `_ENGAGE_TEXT` 매핑, 콤마 연결 |
| `caution[]` | 직접 언급 금지. "집중도 낮은 편이었음 (참고용)" 완곡 표현 |
| `extra[]` | `_EXTRA_TEXT` 매핑 — 자율학습/재시험 문장 후반 반드시 포함 |

### 3.5 생성 지침 (`_base_conditions`)

1. 톤: 학부모가 읽기 편한 다정한 문체 (~했어요, ~했습니다)
2. 금지: '어머님/학부모님' 호칭, 기계적 시스템 로그 표현, 미입력 교재 언급
3. obs 태그 반영: 기본 태그는 첫 부분에, 이벤트 태그(자율/재시험)는 후반부 필수 포함
4. 주의 태그: 완곡 표현만 ("조금 피곤해 보였지만 이내 집중하여~")
5. 출력: 순수 텍스트만 (JSON·마크다운·따옴표 금지)

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

### 4.4 수업 기록 탭 — 입력 항목

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
긍정: 📣 발표 / 🙋 질문 / 🤝 도움 / 📖 예습
```

**주의 관찰** `caution` (멀티 선택):
```
💤 졸음 / 📵 폰사용 / 🗣 잡담 / 😤 태도불량
```
> caution 태그는 Firebase에 저장되나 **학부모 리포트에 직접 노출 금지**. AI가 완곡 표현으로만 활용.

**특수 이벤트** `extra` (멀티 선택):
```
📚 자율학습 / 📝 주간Test / 🔄 재시험
```

#### 메모 (선택)

텍스트 자유 입력. 기억에 남는 순간·특이사항 기록.

### 4.5 성적 입력 탭

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

### 4.6 신호등 판정 (`dotClass`)

| 색상 | 조건 |
|------|------|
| `'g'` 초록 | 수행도 입력 + 진도/과제 하나 이상 |
| `'y'` 노랑 | 수행도 입력 + 진도/과제 없음 |
| `'e'` 회색 | 수행도 미입력 |

> 웹 신호등은 `force_ready` 미반영 (PC 전용 기능)

### 4.7 설정 화면 (아코디언)

| # | 섹션 ID | 내용 |
|---|---------|------|
| 1 | `sa-fb` | 클라우드 연결 — Firebase URL·경로, 학생 명단 불러오기 |
| 2 | `sa-acct` | 내 계정 — 강사 이름 조회·신규등록. 미로그인 시 자동 펼침 |
| 3 | `sa-preset` | 내 프리셋 — ✏️ 인플레이스 편집, 추가/삭제 |
| 4 | `sa-asgn` | 내 담당 수업 — 반+교재+역할(담임/부담임) 추가/삭제 |
| 5 | `sa-cls` | 학급 & 학생 관리 — 2단계 드릴다운 |
| 6 | `sa-admin` | 강사 관리 — 관리자 전용 (`adminOn=true` 시만 렌더링) |
| 7 | `sa-reset` | 초기화 — 4단계 (Lv1·Lv2는 assignments 범위 내만) |

**아코디언 상태 지속 (`openSaIds: Set`)**
- `_saToggle(id)` / `_saOpen(id)` 로 id 추가/삭제
- `renderMain()` 후 `renderSettings()`가 `openSaIds.has(id)` 기반으로 `open` 클래스 주입
- 기본값: `new Set(['sa-fb'])`

**관리자 모드**: `prompt()` → SHA-256 해시 → `ADMIN_HASH` 비교. 세션 변수 `adminOn`.

### 4.8 쓰기 권한 가드

| 함수 | 가드 조건 |
|------|-----------|
| `onPB()` (수행도 클릭) | `{sheet, cls, tb}` ∈ `instructor.assignments` |
| `saveProg()` (진도/과제) | `{sheet, cls, tb}` ∈ `instructor.assignments` |
| `saveNote()` (특이사항) | `{sheet, cls}` ∈ `instructor.assignments` |

- 미로그인(`instructor === null`) 시: 모든 쓰기 차단
- 가드 불통과 시: Firebase PATCH 미호출 (무시, toast 없음)

### 4.9 localStorage 키

| 키 | 내용 |
|----|------|
| `drw_fb_url` | Firebase DB URL |
| `drw_fb_path` | Firebase 경로 |
| `drw_input` | 수행도·특이사항 로컬 캐시 |
| `drw_prog` | 진도/과제 로컬 캐시 |
| `drw_obs` | 수업 관찰 태그 로컬 캐시 |
| `drw_instr` | 현재 강사 정보 |
| `drw_cfg` | config 로컬 캐시 |

### 4.10 UI 구현 규칙

**학급·교재 칩 (`buildClsAccordion`)**
- DOM ID 미사용 → `data-sh`, `data-cls`, `data-chip-type` 어트리뷰트로 식별
  (한글 클래스명 정규화 시 동일 길이 이름 간 ID 충돌 방지)
- `refreshTbChips` / `refreshStuChips`: `querySelector('[data-chip-type="..."]')` 방식

**`ensPath(sh, cls)`**
- 기존 클래스 객체라도 `students` / `textbooks` 배열 각각 존재 여부 별도 검사 후 초기화
- 구버전 Firebase 데이터 호환 보장

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
        assignments:
          - { sheet: "M", cls: "3MGM", tb: "3-1 우공비", role: "담임" }
          - { sheet: "T", cls: "3TGM", tb: "3-1 우공비", role: "부담임" }
        presets: ["과제 완벽 수행 ✅", ...]
    sheets/
      M/
        classes/
          3MGM/
            students: [{name: "김상덕"}, ...]
            textbooks: ["3-1 우공비", "3-1 라이트쎈"]
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

> `phone` 태그 폐기. caution은 직접 언급 금지 원칙에서 **태그별 차등 전달**로 변경.
> `late`는 사실 관계 전달이 가능하며 훈육 메시지로 긍정적으로 활용한다.

**FR-RESET 요구사항**

| ID | 요구사항 |
|----|---------|
| FR-RESET-01 | Lv1·Lv2는 실행 강사의 `assignments` 범위 내 키만 삭제 |
| FR-RESET-02 | Firebase 쓰기는 개별 키 null PATCH 방식만 (노드 전체 PUT 금지) |
| FR-RESET-03 | `assignments` 비어있는 강사 Lv1·Lv2 실행 시 Firebase 쓰기 차단, 로컬만 초기화. toast 안내 |

**`_myResetKeys()` 헬퍼**
```javascript
// assignments 기반 삭제 대상 키 생성
// inputKeys: "sheet|cls|name|tb" + "sheet|cls|name|__note__"
// progressKeys: "sheet|cls|tb"
```

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
| AI 쿨다운 | 30초 | `AI_COOLDOWN` 상수 |
| Groq 모델 | `llama-3.1-8b-instant` | ai_engine.py 하드코딩 |
| Claude 모델 | `claude-3-5-sonnet-20241022` | ai_engine.py 하드코딩 |
| OpenAI 모델 | `gpt-4o-mini` | ai_engine.py 하드코딩 |

---

## 9. 안정성 구현 노트

**PC 앱**
- `_pull_mobile_data`: Firebase config 로드 후 UI 갱신(`_switch_sheet`)은 messagebox 이후 동기 호출. `after()` 예약 금지 — 이벤트 루프 재진입으로 인한 TclError 유발
- `_populate_student_list`: `sl_inner` 자식 파괴 전 `status_w` 해당 sheet 항목 일괄 삭제 (stale Canvas ref 방지)
- `_update_dot`: TclError 방어 처리 필수

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

## 11. 스코프 제외

| 항목 | 사유 |
|------|------|
| 로컬 전용 시나리오 | 폐기, Firebase 필수 |
| 모바일 AI 특이사항 생성 | PC 전용 확정 |
| 웹 카카오톡 전송 | PC 앱 전용 확정 |
| 모바일 앱 설치형 | APK 전환 계획 없음 |
| PDF 출력 | Analyzer 단계에서 검토 |
