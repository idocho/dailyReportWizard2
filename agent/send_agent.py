"""
send_agent.py — CampusManager 전송 에이전트 (로컬·관리자 도메인). PLATFORM_ARCHITECTURE §3·§4.
sendJobs/{campus} 큐를 폴링 → KakaoTalk 발송 → 상태 회신. UI 없음.

발송 자체는 KakaoTalk PC 자동화(ClassManager kakao_send.py 재사용 예정)가 필요해 로컬 전용.
이 파일은 큐 처리·상태 갱신 골격 + 발송 어댑터(dry-run 기본). 실 카톡 연동은 send_one()에 연결.

실행:
  python send_agent.py --once            # 1회 처리(기본 dry-run)
  python send_agent.py --loop --interval 10
  python send_agent.py --once --real     # 실제 카톡 발송(KakaoTalk 필요, kakao 어댑터 연결 시)
설정: agent/config.json (config.example.json 참고)
"""
import argparse
import json
import time
import urllib.request
import urllib.parse
from pathlib import Path

CFG_PATH = Path(__file__).resolve().parent / "config.json"


def load_cfg():
    if not CFG_PATH.exists():
        raise SystemExit("config.json 없음 — config.example.json 복사 후 작성하세요.")
    return json.loads(CFG_PATH.read_text(encoding="utf-8"))


# ── Firebase Auth (선택: agent 계정 로그인 → idToken) ────────────────
def agent_token(cfg):
    """agent 계정 자격이 있으면 idToken 반환(룰 배포 후 필요). 없으면 None(전환 전 오픈 DB)."""
    email = cfg.get("agentEmail"); pw = cfg.get("agentPassword"); key = cfg.get("apiKey")
    if not (email and pw and key):
        return None
    url = f"https://identitytoolkit.googleapis.com/v1/accounts:signInWithPassword?key={key}"
    body = json.dumps({"email": email, "password": pw, "returnSecureToken": True}).encode()
    req = urllib.request.Request(url, data=body, headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=15) as r:
        return json.loads(r.read())["idToken"]


# ── REST 헬퍼 ────────────────────────────────────────────────────────
def _url(cfg, node, token):
    base = cfg["dbUrl"].rstrip("/")
    u = f"{base}/{node}.json"
    return u + ("?auth=" + urllib.parse.quote(token) if token else "")


def fb_get(cfg, node, token):
    with urllib.request.urlopen(_url(cfg, node, token), timeout=20) as r:
        return json.loads(r.read())


def fb_patch(cfg, node, data, token):
    req = urllib.request.Request(_url(cfg, node, token),
                                 data=json.dumps(data, ensure_ascii=False).encode("utf-8"),
                                 method="PATCH", headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=20) as r:
        return json.loads(r.read())


# ── 발송 어댑터 ──────────────────────────────────────────────────────
def send_one(cfg, room, body, real):
    """한 채팅방에 발송. dry-run이면 로그만. real이면 KakaoTalk 자동화 연결 지점."""
    if not real:
        print(f"  [dry-run] room='{room}' body='{body[:30]}...'")
        return True
    # 실 발송: ClassManager kakao_send.py 의 send_messages 로직을 여기 연결.
    #   from kakao_send import open_room, paste_send  (포팅 필요)
    raise NotImplementedError("실 카톡 발송은 kakao_send 어댑터 연결 필요(이 환경 미지원).")


# ── 큐 처리 ──────────────────────────────────────────────────────────
def process_once(cfg, real=False):
    token = agent_token(cfg)
    campus = cfg["campus"]
    prefix = cfg.get("roomPrefix", "")
    jobs = fb_get(cfg, f"sendJobs/{campus}", token) or {}
    pending = {jid: j for jid, j in jobs.items() if isinstance(j, dict) and j.get("status") == "queued"}
    if not pending:
        print("처리할 작업 없음.")
        return 0
    done = 0
    for jid, job in pending.items():
        rcpts = job.get("recipients", [])
        print(f"작업 {jid}: {job.get('cls')} {len(rcpts)}명 발송 시작")
        fb_patch(cfg, f"sendJobs/{campus}/{jid}", {"status": "sending"}, token)
        for i, rc in enumerate(rcpts):
            room = (prefix + (rc.get("name") or "")).strip()
            body = render(job.get("body", ""), rc.get("name"), job.get("cls"))
            ok = send_one(cfg, room, body, real)
            rc["status"] = "완료" if ok else "실패"
            fb_patch(cfg, f"sendJobs/{campus}/{jid}/recipients/{i}", {"status": rc["status"]}, token)
        fb_patch(cfg, f"sendJobs/{campus}/{jid}", {"status": "done"}, token)
        done += 1
        print(f"작업 {jid}: 완료")
    return done


def render(tmpl, name, cls):
    return (tmpl or "").replace("{이름}", name or "").replace("{반}", cls or "")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--once", action="store_true")
    ap.add_argument("--loop", action="store_true")
    ap.add_argument("--interval", type=int, default=10)
    ap.add_argument("--real", action="store_true", help="실제 카톡 발송(KakaoTalk 필요)")
    args = ap.parse_args()
    cfg = load_cfg()
    if args.loop:
        print(f"에이전트 시작 — campus={cfg['campus']} interval={args.interval}s real={args.real}")
        while True:
            try:
                process_once(cfg, args.real)
            except Exception as e:
                print("ERROR:", e)
            time.sleep(args.interval)
    else:
        process_once(cfg, args.real)


if __name__ == "__main__":
    main()
