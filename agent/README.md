# agent/ — CampusManager 전송 에이전트 (로컬)

`sendJobs/{campus}` 큐를 폴링해 KakaoTalk으로 발송하고 상태를 회신하는 **UI 없는 로컬 프로그램**.
관리자 도메인(일괄 전송) 전용 — 강사 일일 전송과 분리(PLATFORM_ARCHITECTURE §3).

## 흐름
```
CampusManager(웹) → sendJobs/{campus}/{jobId} (queued)
   → [에이전트] queued 발견 → sending → 각 수신자 발송 → recipients[].status=완료 → job status=done
   → 웹이 상태 표시
```

## 실행
```
cp config.example.json config.json   # 값 채우기
python send_agent.py --once          # 1회(기본 dry-run, 카톡 미발송·로그만)
python send_agent.py --loop --interval 10
python send_agent.py --once --real   # 실제 카톡 발송(KakaoTalk PC 필요)
```
Windows 작업 스케줄러로 상시 1대 가동(캠퍼스당) 권장.

## 검증 현황
- ✅ 큐 폴링·{이름}/{반} 치환·방이름(roomPrefix+이름)·상태 회신·멱등 — 라이브 검증 완료(dry-run).
- ⏳ **실 카톡 발송**: `send_one(real=True)` 가 NotImplemented — ClassManager `kakao_send.py`
  의 send 로직을 어댑터로 연결해야 함(KakaoTalk PC 환경 필요, 본 개발 환경 미지원).

## 설정·보안
- `config.json` 은 git 제외. 룰 배포(F) 후 `agentEmail/agentPassword/apiKey` 채우면
  agent 계정(acl role:agent)으로 인증(idToken). 그 전엔 비워둠(오픈 DB).
- agent 자격은 추후 DPAPI 암호화 권장(`code/secret_codec.py` 패턴).

## 남은 작업
- kakao 발송 어댑터 연결(ClassManager kakao_send 포팅) + 이미지 첨부
- agent 계정 발급(acl role:agent) + 자격 암호화
