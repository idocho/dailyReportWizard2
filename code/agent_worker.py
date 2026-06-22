"""
agent_worker.py — 강사 본인 PC 에이전트의 AI 생성 워커.

genJobs 큐를 읽어 본인 **개인 API 키(로컬 DPAPI)** 로 `ai_engine` 을 재사용해
특이사항을 생성하고 draft 를 회신한다. 키는 이 PC를 떠나지 않는다(웹·서버 미전송).
프롬프트 조립은 PC앱과 동일한 `ai_engine.build_single_prompt` 를 그대로 써서 품질 동일.

데이터 흐름(시퀀스 ②~⑤):
  웹 → genJobs/{campus}/{instructorId}/{id}  (학생 맥락 JSON, status=queued)
  → [이 워커] 로컬 키로 생성 → {draft, status:done} 회신 → 웹이 검토

전송(kakao_send)·트레이/오버레이/셋업 마법사는 별도 모듈. 여기는 생성만.
"""
import argparse
import json
import threading
import time
import urllib.request
import urllib.parse
from pathlib import Path

from ai_engine import build_single_prompt, _call_ai_hub, _base_conditions

CFG_PATH = Path(__file__).resolve().parent / "agent_config.json"


# ── genJobs payload → build_single_prompt 입력 재구성 ─────────────────
def _reconstruct(job):
    """웹이 보낸 context JSON 을 PC앱과 동일한 dict 구조로 복원.

    job = {
      nameKey, cls, displayName, sheet?,
      items: [{subject, value, progress?, homework?, gradeLabel?}],
      tags: {..._build_tags_context 입력 형태...}, note, styleBlock?
    }
    """
    cls = job["cls"]
    nk = job["nameKey"]
    display = job.get("displayName") or nk
    textbooks, student_data, progress_data, tb_grade = [], {}, {}, {}
    for it in job.get("items", []):
        sub = it.get("subject")
        if not sub:
            continue
        textbooks.append(sub)
        student_data[(cls, nk, sub)] = {"value": it.get("value", "")}
        progress_data[(cls, sub)] = {"progress": it.get("progress", ""),
                                     "homework": it.get("homework", "")}
        if it.get("gradeLabel"):
            tb_grade[sub] = it["gradeLabel"]
    return {
        "sheet": job.get("sheet", ""), "cls": cls, "name": nk, "display": display,
        "textbooks": textbooks, "student_data": student_data,
        "progress_data": progress_data, "tags": job.get("tags") or {},
        "note": job.get("note", ""), "style_block": job.get("styleBlock", ""),
        "tb_grade": tb_grade,
    }


# 톤 조절 재생성 — 웹 신규 강점. 데이터(사실)는 유지하고 어조만 조정.
TONE_DIRECTIVES = {
    "warm":     "더 따뜻하고 공감 어린 어조로, 격려를 담아 다시 작성하세요.",
    "concise":  "더 간결하게 — 핵심만 한두 문장으로 다시 작성하세요.",
    "detailed": "더 구체적으로 — 관찰된 행동·수치·사례를 짚어 다시 작성하세요.",
}


def generate(cfg, job, ai_call=_call_ai_hub):
    """단건 생성 — 본인 로컬 키 사용. job['tone'](warm/concise/detailed)로 톤 재생성 지원.
    ai_call 주입 가능(테스트용 모킹)."""
    engine = cfg.get("ai_engine_type", "gemini").strip().lower()
    key = cfg.get(f"{engine}_api_key", "").strip()
    if not key:
        raise RuntimeError(f"개인 {engine} API 키 미설정 — 에이전트 설정에서 입력 필요")
    c = _reconstruct(job)
    prompt = build_single_prompt(
        c["sheet"], c["cls"], c["name"], c["textbooks"],
        c["student_data"], c["progress_data"], c["note"], c["tags"],
        tb_grade=c["tb_grade"], style_block=c["style_block"], display_name=c["display"])
    # 톤 조절: 사실은 데이터에서, 어조만 조정. 이전 작성본 참고로 연속성 유지.
    tone = (job.get("tone") or "").strip()
    if tone in TONE_DIRECTIVES:
        prompt += f"\n[톤 조절 지시 — 사실·안전 규칙 유지]\n{TONE_DIRECTIVES[tone]}\n"
        if job.get("currentDraft"):
            prompt += f"[이전 작성본(어조 참고용, 사실은 위 데이터 우선)]\n{job['currentDraft']}\n"
    return ai_call(engine, key, prompt, max_tokens=400, temperature=0.75,
                   system=_base_conditions())


# ── Firebase REST (genJobs 큐) ───────────────────────────────────────
def _url(db, node, token):
    u = f"{db.rstrip('/')}/{node}.json"
    return u + ("?auth=" + urllib.parse.quote(token) if token else "")


def _get(db, node, token):
    with urllib.request.urlopen(_url(db, node, token), timeout=20) as r:
        return json.loads(r.read())


def _patch(db, node, data, token):
    req = urllib.request.Request(_url(db, node, token),
                                 data=json.dumps(data, ensure_ascii=False).encode("utf-8"),
                                 method="PATCH", headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=20) as r:
        return json.loads(r.read())


def process_genjobs(cfg, db, instructor_id, token=None, ai_call=_call_ai_hub):
    """본인 genJobs 큐의 queued 작업을 생성 처리. 반환: 처리 건수."""
    base = f"campus/{cfg['campus']}/genJobs/{urllib.parse.quote(instructor_id)}"
    jobs = _get(db, base, token) or {}
    pending = {jid: j for jid, j in jobs.items()
               if isinstance(j, dict) and j.get("status") == "queued"}
    done = 0
    for jid, job in pending.items():
        try:
            draft = generate(cfg, job, ai_call=ai_call)
            _patch(db, f"{base}/{jid}", {"draft": draft, "status": "done"}, token)
            done += 1
        except Exception as e:
            _patch(db, f"{base}/{jid}", {"status": "error", "error": str(e)[:200]}, token)
    return done


# ── 전송 워커 (sendJobs, 본인 카톡) ──────────────────────────────────
def _send_msgs(cfg, job):
    """sendJob.recipients(검토 끝난 per-student msg) → kakao_send 입력."""
    prefix = cfg.get("roomPrefix", "")
    return [{"room": (prefix + (r.get("name") or "")).strip(), "msg": r.get("msg", "")}
            for r in job.get("recipients", [])]


def _send_real(cfg, msgs, item_cb):
    """본인 카톡 실발송 — SmartWait 적응. 완료까지 동기 대기."""
    import kakao_send
    if not getattr(kakao_send, "AUTOMATION", False):
        raise RuntimeError("pyautogui/pyperclip 미설치 또는 비-Windows — 실 발송 불가")
    sw = kakao_send.SmartWait(cfg.get("smartWait", cfg.get("waitTime", 0.5)))
    done = threading.Event()
    kakao_send.send_messages(msgs, wait_ctrl=sw, status_cb=lambda t: print("  " + t),
                             item_cb=lambda i, ok, room, err: item_cb(i, ok, err),
                             done_cb=lambda n: done.set())
    if not done.wait(timeout=25 * len(msgs) + 30):
        raise RuntimeError("발송 타임아웃 — 카톡 응답 없음")


def process_sendjobs(cfg, db, instructor_id, token=None, real=False):
    """본인 sendJobs 큐 처리 — per-recipient 라이브 상태 회신. 반환: 처리 건수."""
    base = f"campus/{cfg['campus']}/sendJobs/{urllib.parse.quote(instructor_id)}"
    jobs = _get(db, base, token) or {}
    pending = {jid: j for jid, j in jobs.items()
               if isinstance(j, dict) and j.get("status") == "queued"}
    done = 0
    for jid, job in pending.items():
        _patch(db, f"{base}/{jid}", {"status": "sending"}, token)
        msgs = _send_msgs(cfg, job)
        results = []

        def on_item(i, ok, err=None):
            results.append(ok)
            patch = {"status": "완료" if ok else "실패"}
            if err:
                patch["error"] = str(err)[:120]
            _patch(db, f"{base}/{jid}/recipients/{i}", patch, token)

        try:
            if real:
                _send_real(cfg, msgs, on_item)
            else:
                for i, m in enumerate(msgs):
                    time.sleep(0.02)
                    on_item(i, True)
            _patch(db, f"{base}/{jid}", {"status": "done", "fail": results.count(False)}, token)
            done += 1
        except Exception as e:
            _patch(db, f"{base}/{jid}", {"status": "error", "error": str(e)[:200]}, token)
    return done


# ── 오케스트레이션 ───────────────────────────────────────────────────
def process_once(cfg, db, instructor_id, token=None, real=False):
    """생성 → 전송 큐를 한 번씩 처리. dry(real=False)=AI·카톡 모킹."""
    ai = _call_ai_hub if real else (lambda e, k, p, **kw: f"[dry] {p[:0]}AI 생성 문구(테스트)")
    g = process_genjobs(cfg, db, instructor_id, token, ai_call=ai)
    s = process_sendjobs(cfg, db, instructor_id, token, real=real)
    return g, s


def _load_cfg():
    if not CFG_PATH.exists():
        raise SystemExit("agent_config.json 없음 — 셋업 마법사로 생성하세요.")
    try:
        import secret_codec
        return secret_codec.decrypt_fields(json.loads(CFG_PATH.read_text(encoding="utf-8")))
    except Exception:
        return json.loads(CFG_PATH.read_text(encoding="utf-8"))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--once", action="store_true")
    ap.add_argument("--loop", action="store_true")
    ap.add_argument("--interval", type=int, default=8)
    ap.add_argument("--real", action="store_true", help="실 AI 생성 + 실 카톡 발송")
    args = ap.parse_args()
    cfg = _load_cfg()
    db = cfg["dbUrl"]
    instr = cfg["instructorId"]
    token = cfg.get("_id_token")  # 룰 배포 후 인증
    if args.loop:
        print(f"강사 에이전트 시작 — {instr}@{cfg['campus']} real={args.real}")
        while True:
            try:
                g, s = process_once(cfg, db, instr, token, real=args.real)
                if g or s:
                    print(f"생성 {g} · 전송 {s}")
            except Exception as e:
                print("ERROR:", e)
            time.sleep(args.interval)
    else:
        g, s = process_once(cfg, db, instr, token, real=args.real)
        print(f"생성 {g} · 전송 {s}")


if __name__ == "__main__":
    main()
