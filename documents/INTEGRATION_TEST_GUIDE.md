# DRW 웹↔에이전트 통합 테스트 가이드 (상세)

_2026-06-23 · 웹 리포트 탭(v2.5.0) ↔ 강사 PC 에이전트(agent_gui)_

## 0. 구조 한눈에
```
[강사 웹 v2.5.0]  ──genJobs──▶  [Firebase 큐]  ──▶  [본인 PC 에이전트]
  리포트 탭                campus/{c}/genJobs        agent_gui (개인키·카톡 로컬)
  생성·검토·전송요청       campus/{c}/sendJobs        생성(ai_engine)·발송(kakao_send)
        ◀── draft·상태 회신 ────────────────────────────┘
```
- **불변식 ①**: 웹 로그인 이름 == 에이전트 `instructorId` (큐 경로 키)
- **불변식 ②**: 웹 캠퍼스(acl.campus) == 에이전트 `campus`
- 키·카톡은 **에이전트(이 PC)만**. 웹·Firebase엔 키 없음.

## 1. 준비물
| 항목 | 비고 |
|---|---|
| 에이전트 PC | Windows + KakaoTalk **로그인** 상태 |
| Python 패키지 | `pip install pyautogui pyperclip` |
| 강사 계정 | 담당 수업·학생 있는 본인 계정 (또는 아래 §2 테스트 반) |
| 개인 AI 키 | Gemini / Claude / GPT 중 본인 것 |

## 2. 안전 샌드박스 (실 학부모 차단) — 권장
CampusManager에서:
1. **테스트 반** 생성 (예: `ZZ테스트`)
2. **테스트 학생** 추가 — 이름 = **본인이 통제하는 카톡방 제목**(접두사 포함 일치). 예: 방 "오직 테스트" → 학생 이름 "테스트", 접두사 "오직 "
3. 본인 강사 계정에 이 반 **담당 배정**
→ 모든 전송이 본인 방으로만. 실 학부모 위험 0.

## 3. 에이전트 실행 (GUI)
```powershell
cd D:\WorkSpace\Development\dailyReportWizard2\code
python agent_gui.py
```
**최초 1회 설정 폼:**
- 캠퍼스 id: `dongsuwon`
- 본인 이름: **웹 로그인명과 정확히 동일**
- AI 엔진: 드롭다운(Gemini/Claude/GPT)
- 개인 API 키 / 카톡 방 접두사(예: `오직 `)
- ☑ Windows 시작 시 자동 실행 → **[저장하고 시작]** (키 DPAPI 암호화)

이후 **상태창**: 🟢 작동중 · ☐실발송 토글 · [시작]/[중지] · [설정].

## 4. 단계별 테스트

### Phase A — dry (플러밍·UI, 무비용·무발송)
1. 상태창: **실발송 체크 해제** → [시작]
2. 웹 로그인 → **📨 리포트 전송** 탭 → 좌측 반/과목 선택
3. 학생 **생성** 클릭 → textarea에 `[dry] …` 표시
4. **전송 대상 선택** → 전송 시작 → "완료"(카톡 미발송)

**기대 결과**
- 학생 목록·신호등 점·메모/검토중 배지 표시
- 생성 왕복 정상, 톤 버튼(따뜻/간결/구체) 동작
- 전송 대상 모달: 미생성 제외·동명이인 ⚠ 자동 제외
- 전송 상태: 대기 → 전송 중 N/M → 완료 (라이브)

### Phase B — 실 AI 생성 (카톡 안전)
1. 상태창: **실발송 체크** → [시작]
2. 웹: 생성/일괄/톤 → **본인 키로 진짜 AI 문구**
   > ★ **전송만 안 누르면 카톡 절대 안 감** (sendJob은 "전송" 클릭 시 생성)

**기대 결과**
- 문구에 **수행도·진도·과제·관찰태그·직접메모** 반영 (PC앱 동일 품질)
- 톤별 어조 차이(따뜻/간결/구체)
- 생성 시 에이전트 상태창 "마지막 활동" 갱신

### Phase C — 실 카톡 발송 (통제 방으로만)
1. 테스트 학생(통제 방) 생성·검토
2. 전송 대상 선택(그 학생만) → 전송 시작
3. **에이전트 오버레이 "전송 중 N/M · 만지지 마세요"** 표시 → **입력 금지**
4. 본인 카톡방 도착 확인 + 웹 상태 "완료"

**기대 결과**
- 오버레이가 카톡 포커스 안 뺏음(자동화 정상)
- 방 도착 + `history/{nameKey}/{날짜}` 기록
- 동명이인은 "제외(동명이인)" 처리

## 5. 검증 체크리스트
| # | 항목 | A | B | C |
|---|---|:-:|:-:|:-:|
| 1 | 리포트 탭 렌더·담당 반/학생 | ☐ | | |
| 2 | 신호등·배지(메모/검토중) | ☐ | | |
| 3 | 생성(개별/일괄) → draft | ☐ | ☐ | |
| 4 | 톤 따뜻/간결/구체 | | ☐ | |
| 5 | 수행도·진도·과제·태그·메모 반영 | | ☐ | |
| 6 | 전송 대상: 미생성·동명이인 제외 | ☐ | | ☐ |
| 7 | 전송 상태 라이브 | ☐ | | ☐ |
| 8 | 오버레이 "만지지마" | | | ☐ |
| 9 | 본인 방 도착 + history | | | ☐ |

## 6. 트러블슈팅
| 증상 | 원인 / 조치 |
|---|---|
| 담당 수업 안 보임 | 설정→담당 추가 / `config/instructors/{이름}` 확인 |
| 생성 눌러도 무반응 | **웹 로그인명 ≠ 에이전트 instructorId** (큐 경로 불일치) |
| "생성 시간초과 — 에이전트 확인" | 에이전트 미실행 / 개인키 오류 / 쿼터 → 에이전트 상태창·콘솔 |
| 문구 품질 낮음 | 입력 탭에서 진도·과제수행도·메모 입력됐는지 확인 |
| "채팅방 열기 실패" | `roomPrefix`+이름 ≠ 실제 방 제목(공백 무시됨) |
| 엉뚱한 창에 입력 | 발송 중 마우스/키보드 건드림 → 손 떼고 재시도 |

## 7. 디버깅 — 큐 직접 보기
```powershell
$env:PYTHONIOENCODING='utf-8'
python -c "import json,urllib.request as u,urllib.parse as p; DB='https://dailyreportwizard-default-rtdb.firebaseio.com'; g=lambda n:json.loads(u.urlopen(DB+'/'+p.quote(n,safe='/')+'.json').read() or b'null'); I='홍길동'; print('GEN',json.dumps(g('campus/dongsuwon/genJobs/'+I),ensure_ascii=False)[:400]); print('SEND',json.dumps(g('campus/dongsuwon/sendJobs/'+I),ensure_ascii=False)[:400])"
#  I = 본인 이름. status·draft·items.value(수행도)·recipients 확인
```

## 8. 안전 수칙
- **dongsuwon = 실 캠퍼스.** Phase C 전 실 학부모 발송 금지 — 테스트 반(통제 방)만
- 발송은 본인 PC 앞에서, 발송 중 입력 금지
- Phase A/B의 genJobs는 무해(초안만) — 카톡은 "전송" 클릭 시에만
- 개인 키는 본인 PC(DPAPI)만 — 공유 금지

## 부록. 개발자 격리 검증 (참고)
실 계정 없이 파이프라인만 확인할 때: 격리 캠퍼스 `zz_test`에 시드 후, 웹 로그인 게이트를
localStorage 주입으로 우회 + dry 에이전트(`process_*`) 구동. (이 방식으로 전 사이클 검증 완료:
탭 렌더→생성→draft→톤→전송→완료, 수행도=완료·태그 분리 확인.)
```python
# 시드 예 (campus/zz_test): config/instructors·classes·students·session·input·obs
# obs/{nk}/{과목}/{오늘} = {assign_grade:'done', assign_tags:[...]}
```
