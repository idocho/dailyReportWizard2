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
import json
import time
import urllib.request
import urllib.parse

from ai_engine import build_single_prompt, _call_ai_hub, _base_conditions


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


def generate(cfg, job, ai_call=_call_ai_hub):
    """단건 생성 — 본인 로컬 키 사용. ai_call 주입 가능(테스트용 모킹)."""
    engine = cfg.get("ai_engine_type", "gemini").strip().lower()
    key = cfg.get(f"{engine}_api_key", "").strip()
    if not key:
        raise RuntimeError(f"개인 {engine} API 키 미설정 — 에이전트 설정에서 입력 필요")
    c = _reconstruct(job)
    prompt = build_single_prompt(
        c["sheet"], c["cls"], c["name"], c["textbooks"],
        c["student_data"], c["progress_data"], c["note"], c["tags"],
        tb_grade=c["tb_grade"], style_block=c["style_block"], display_name=c["display"])
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
