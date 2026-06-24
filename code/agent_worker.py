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

from ai_engine import build_single_prompt, build_batch_prompt, _call_ai_hub, _base_conditions
from constants import grade_label
import ai_style

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


def generate(cfg, job, ai_call=_call_ai_hub, notes_provider=None):
    """단건 생성 — 본인 로컬 키 + 문체(ai_style)·개별지침 적용(PC앱 gen_single 동일).
    job['tone']로 톤 재생성. notes_provider=AUTO 말투 학습용 강사 노트 공급자."""
    engine = cfg.get("ai_engine_type", "gemini").strip().lower()
    key = cfg.get(f"{engine}_api_key", "").strip()
    if not key:
        raise RuntimeError(f"개인 {engine} API 키 미설정 — 에이전트 설정에서 입력 필요")
    c = _reconstruct(job)
    # 문체 블록: 프리셋이면 해당 지침, auto면 강사 전송노트 학습(notes_provider)
    try:
        guidance, examples = ai_style.resolve_style(job.get("styleMode") or "auto",
                                                    notes_provider or (lambda: []))
        style_block = ai_style.style_prompt_block(guidance, examples)
    except Exception:
        style_block = ""
    prompt = build_single_prompt(
        c["sheet"], c["cls"], c["name"], c["textbooks"],
        c["student_data"], c["progress_data"], c["note"], c["tags"],
        tb_grade=c["tb_grade"], style_block=style_block, display_name=c["display"])
    # 톤 조절: 사실은 데이터에서, 어조만 조정. 이전 작성본 참고로 연속성 유지.
    tone = (job.get("tone") or "").strip()
    if tone in TONE_DIRECTIVES:
        prompt += f"\n[톤 조절 지시 — 사실·안전 규칙 유지]\n{TONE_DIRECTIVES[tone]}\n"
        if job.get("currentDraft"):
            prompt += f"[이전 작성본(어조 참고용, 사실은 위 데이터 우선)]\n{job['currentDraft']}\n"
    # system = 공통 지침 + 강사 개별 지침
    system = _base_conditions()
    custom = (job.get("customPrompt") or "").strip()
    if custom:
        system += ("\n\n[강사 개별 지침 — 위 작성 지침과 사실·안전 규칙을 위반하지 않는 선에서 반영]\n" + custom)
    return ai_call(engine, key, prompt, max_tokens=400, temperature=0.75, system=system)


def generate_batch(cfg, job, ai_call=_call_ai_hub, notes_provider=None):
    """반 전체 1회 호출 생성(PC gen_all 동일) — build_batch_prompt. 반환: {nameKey: note}."""
    engine = cfg.get("ai_engine_type", "gemini").strip().lower()
    key = cfg.get(f"{engine}_api_key", "").strip()
    if not key:
        raise RuntimeError(f"개인 {engine} API 키 미설정 — 에이전트 설정에서 입력 필요")
    students = job.get("students", [])
    targets = []
    for st in students:
        cls = st.get("cls") or job.get("cls", "")
        data, progress = {}, {}
        for it in st.get("items", []):
            sub = it.get("subject");
            if not sub:
                continue
            label = grade_label(it.get("gradeLabel", ""), sub)
            if it.get("value"):
                data[label] = it["value"]
            if it.get("progress") or it.get("homework"):
                progress[label] = {"progress": it.get("progress", ""), "homework": it.get("homework", "")}
        targets.append({"sheet": "", "cls": cls, "name": st.get("displayName", ""),
                        "data": data, "progress": progress,
                        "existing": (st.get("note") or "").strip(), "tags": st.get("tags") or {}})
    if not targets:
        return {}
    try:
        guidance, examples = ai_style.resolve_style(job.get("styleMode") or "auto", notes_provider or (lambda: []))
        style_block = ai_style.style_prompt_block(guidance, examples)
    except Exception:
        style_block = ""
    custom = (job.get("customPrompt") or "").strip()
    custom_block = (f"[강사 개별 지침 — 위 작성 지침과 사실·안전 규칙을 위반하지 않는 선에서 반영]\n{custom}" if custom else "")
    prompt = build_batch_prompt(targets, style_block=style_block, custom_block=custom_block)
    raw = ai_call(engine, key, prompt, max_tokens=min(4096, 256 * len(targets) + 400),
                  temperature=0.75, system=_base_conditions())
    clean = raw.replace("```json", "").replace("```", "").strip()
    parsed = json.loads(clean)
    name_to_key = {st.get("displayName"): st.get("nameKey") for st in students}
    drafts = {}
    for item in (parsed if isinstance(parsed, list) else []):
        dn = (item.get("name") or "").strip(); note = (item.get("note") or "").strip()
        nk = name_to_key.get(dn)
        if dn and note and nk:
            drafts[nk] = note
    return drafts


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


def _fetch_instructor_notes(db, cfg, instructor_id, token):
    """history/ 에서 해당 강사가 전송한 노트 본문(최신순 일부) — AUTO 말투 학습용."""
    try:
        hist = _get(db, f"campus/{cfg['campus']}/history", token) or {}
    except Exception:
        return []
    rows = []
    for nk, days in hist.items():
        if not isinstance(days, dict):
            continue
        for d, rec in days.items():
            if isinstance(rec, dict) and (rec.get("note") or "").strip() and rec.get("instructor", "") == instructor_id:
                rows.append((d, rec["note"]))
    rows.sort(key=lambda x: x[0], reverse=True)
    return [n for _, n in rows[:40]]


def process_genjobs(cfg, db, instructor_id, token=None, ai_call=_call_ai_hub):
    """본인 genJobs 큐의 queued 작업을 생성 처리. 반환: 처리 건수."""
    base = f"campus/{cfg['campus']}/genJobs/{urllib.parse.quote(instructor_id)}"
    jobs = _get(db, base, token) or {}
    pending = {jid: j for jid, j in jobs.items()
               if isinstance(j, dict) and j.get("status") == "queued"}
    done = 0
    _notes = [None]   # AUTO 말투 학습 노트 — 1회 fetch 캐시
    def _np():
        if _notes[0] is None:
            _notes[0] = _fetch_instructor_notes(db, cfg, instructor_id, token)
        return _notes[0]
    for jid, job in pending.items():
        try:
            if job.get("batch"):
                drafts = generate_batch(cfg, job, ai_call=ai_call, notes_provider=_np)
                _patch(db, f"{base}/{jid}", {"drafts": drafts, "status": "done"}, token)
            else:
                draft = generate(cfg, job, ai_call=ai_call, notes_provider=_np)
                _patch(db, f"{base}/{jid}", {"draft": draft, "status": "done"}, token)
            done += 1
        except Exception as e:
            _patch(db, f"{base}/{jid}", {"status": "error", "error": str(e)[:200]}, token)
    return done


# ── 전송 워커 (sendJobs, 본인 카톡) ──────────────────────────────────
def decode_image(data_url):
    """job.image(base64 dataURL) → 임시파일 경로(일괄 공지 이미지 첨부). 없으면 None."""
    if not data_url or "," not in data_url:
        return None
    import base64, os, tempfile
    header, b64 = data_url.split(",", 1)
    ext = "png" if "png" in header.lower() else "jpg"
    path = os.path.join(tempfile.gettempdir(), f"_drw_send_{os.getpid()}.{ext}")
    with open(path, "wb") as f:
        f.write(base64.b64decode(b64))
    return path


def _send_real(cfg, msgs, item_cb, should_cancel=None):
    """본인 카톡 실발송 — SmartWait 적응. 완료까지 동기 대기. should_cancel(): 건별 취소 폴링."""
    import kakao_send
    if not getattr(kakao_send, "AUTOMATION", False):
        raise RuntimeError("pyautogui/pyperclip 미설치 또는 비-Windows — 실 발송 불가")
    sw = kakao_send.SmartWait(cfg.get("smartWait", cfg.get("waitTime", 0.5)))
    done = threading.Event()
    kakao_send.send_messages(msgs, wait_ctrl=sw, status_cb=lambda t: print("  " + t),
                             item_cb=lambda i, ok, room, err: item_cb(i, ok, err),
                             done_cb=lambda n: done.set(), should_cancel=should_cancel)
    if not done.wait(timeout=25 * len(msgs) + 30):
        raise RuntimeError("발송 타임아웃 — 카톡 응답 없음")


def process_sendjobs(cfg, db, instructor_id, token=None, real=False, progress_cb=None):
    """본인 sendJobs 큐 처리 — 동명이인 가드 + per-recipient 라이브 상태 회신. 반환: 처리 건수.
    progress_cb(state): GUI 오버레이용 진행 콜백(state={active,cls,done,total,fail})."""
    from collections import Counter
    base = f"campus/{cfg['campus']}/sendJobs/{urllib.parse.quote(instructor_id)}"
    jobs = _get(db, base, token) or {}
    pending = {jid: j for jid, j in jobs.items()
               if isinstance(j, dict) and j.get("status") == "queued"}
    prefix = cfg.get("roomPrefix", "")
    done = 0
    for jid, job in pending.items():
        _patch(db, f"{base}/{jid}", {"status": "sending"}, token)
        recs = job.get("recipients", [])
        # 동명이인 오발송 가드(계승) — 같은 표시이름은 카톡방 검색이 합쳐져 타 학부모에게 갈 위험.
        names = [r.get("name", "") for r in recs]
        dups = {n for n, c in Counter(names).items() if n and c > 1}
        send_idx = []
        for i, r in enumerate(recs):
            if r.get("name", "") in dups:
                _patch(db, f"{base}/{jid}/recipients/{i}", {"status": "제외(동명이인)"}, token)
            else:
                send_idx.append(i)
        img_path = decode_image(job.get("image")) if job.get("image") else None   # 일괄 공지 이미지
        msgs = [{"room": (prefix + (recs[i].get("name") or "")).strip(),
                 "msg": recs[i].get("msg", ""),
                 **({"image": img_path, "image_first": bool(job.get("imageFirst"))} if img_path else {})}
                for i in send_idx]
        total = len(msgs)
        cls = job.get("cls", "")
        if progress_cb:
            progress_cb({"active": True, "cls": cls, "done": 0, "total": total, "fail": 0})
        results = []

        def on_item(k, ok, err=None):
            results.append(ok)
            patch = {"status": "완료" if ok else "실패"}
            if err:
                patch["error"] = str(err)[:120]
            _patch(db, f"{base}/{jid}/recipients/{send_idx[k]}", patch, token)
            if progress_cb:
                progress_cb({"active": True, "cls": cls, "done": len(results),
                             "total": total, "fail": results.count(False)})

        # 웹이 sending 중 set 하는 cancel 플래그를 건별 폴링(현재 건 보호, 나머지 중단)
        def _canceled(_jid=jid):
            try:
                return bool(_get(db, f"{base}/{_jid}/cancel", token))
            except Exception:
                return False

        try:
            if real:
                _send_real(cfg, msgs, on_item, should_cancel=_canceled)
            else:
                for k, m in enumerate(msgs):
                    if _canceled():
                        break
                    time.sleep(0.02)
                    on_item(k, True)
            if progress_cb:
                progress_cb({"active": False})
            final = "canceled" if _canceled() else "done"
            _patch(db, f"{base}/{jid}",
                   {"status": final, "fail": results.count(False), "excluded": len(dups)}, token)
            done += 1
        except Exception as e:
            if progress_cb:
                progress_cb({"active": False})
            _patch(db, f"{base}/{jid}", {"status": "error", "error": str(e)[:200]}, token)
        finally:
            if img_path:
                try:
                    import os
                    os.remove(img_path)
                except OSError:
                    pass
    return done


# ── 오케스트레이션 ───────────────────────────────────────────────────
def process_once(cfg, db, instructor_id, token=None, real=False, progress_cb=None):
    """생성 → 전송 큐를 한 번씩 처리. dry(real=False)=AI·카톡 모킹."""
    ai = _call_ai_hub if real else (lambda e, k, p, **kw: f"[dry] {p[:0]}AI 생성 문구(테스트)")
    g = process_genjobs(cfg, db, instructor_id, token, ai_call=ai)
    s = process_sendjobs(cfg, db, instructor_id, token, real=real, progress_cb=progress_cb)
    return g, s


DEFAULT_DB = "https://dailyreportwizard-default-rtdb.firebaseio.com"


def _load_cfg():
    if not CFG_PATH.exists():
        raise SystemExit("agent_config.json 없음 — 'python agent_worker.py --setup' 로 1회 설정하세요.")
    try:
        import secret_codec
        return secret_codec.decrypt_fields(json.loads(CFG_PATH.read_text(encoding="utf-8")))
    except Exception:
        return json.loads(CFG_PATH.read_text(encoding="utf-8"))


def write_agent_config(fields, path=CFG_PATH):
    """1회 설정 저장 — 개인 키는 DPAPI 암호화(secret_codec). 반환: 경로."""
    data = dict(fields)
    try:
        import secret_codec
        data = secret_codec.encrypt_fields(data)
    except Exception:
        pass
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    return path


def register_autostart(name="DRW_Instructor_Agent"):
    """Windows 로그인 시 자동 실행 등록(시작프로그램 .bat). 비-Windows는 no-op."""
    import os
    import sys
    if sys.platform != "win32":
        return False
    try:
        startup = Path(os.environ["APPDATA"]) / "Microsoft/Windows/Start Menu/Programs/Startup"
        startup.mkdir(parents=True, exist_ok=True)
        script = Path(__file__).resolve()
        py = sys.executable.replace("python.exe", "pythonw.exe")  # 콘솔창 없이
        (startup / f"{name}.bat").write_text(
            f'@echo off\ncd /d "{script.parent}"\nstart "" "{py}" "{script}" --loop --real\n',
            encoding="utf-8")
        return True
    except Exception:
        return False


def _setup_cli():
    """턴키 1회 설정 — JSON 편집 없이 대화형. 끝나면 자동시작 등록 후 잊으면 됨."""
    print("=== 강사 에이전트 설정 (1회) ===")
    f = {}
    f["campus"] = input("캠퍼스 id (예: dongsuwon): ").strip()
    f["instructorId"] = input("본인 이름(로그인 id): ").strip()
    f["dbUrl"] = input(f"DB URL [{DEFAULT_DB}]: ").strip() or DEFAULT_DB
    f["roomPrefix"] = input('카톡 방 이름 접두사 (예: "오직 ", 없으면 빈칸): ')
    eng = (input("AI 엔진 [gemini/claude/openai] (기본 gemini): ").strip() or "gemini").lower()
    f["ai_engine_type"] = eng
    f[f"{eng}_api_key"] = input(f"본인 {eng} 개인 API 키: ").strip()
    write_agent_config(f)
    ok = register_autostart()
    print(f"\n설정 저장 완료(개인 키 암호화). 자동시작 등록: {'완료' if ok else '수동 필요(비-Windows)'}")
    print("이제 안 건드려도 됩니다 — 로그인 시 자동 실행, 트레이에서 동작.")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--once", action="store_true")
    ap.add_argument("--loop", action="store_true")
    ap.add_argument("--interval", type=int, default=8)
    ap.add_argument("--real", action="store_true", help="실 AI 생성 + 실 카톡 발송")
    ap.add_argument("--setup", action="store_true", help="턴키 1회 설정(엔진·개인키·자동시작)")
    args = ap.parse_args()
    if args.setup:
        _setup_cli()
        return
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
