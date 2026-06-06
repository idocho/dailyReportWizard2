"""migrate_v2_1_2.py — DRW v2.1.2 재구조화 DB 마이그레이션

대상 작업 (Analyzer 정합 + 죽은 데이터 정리):
  1. lastSent/ 노드 삭제 (폐기됨 — date 마커뿐, 의미 데이터 없음)
  2. input/{nameKey} 정리:
     - 과목별 .assign (레거시 죽은 필드) 제거
     - 과목별 .note 잔존분(구 v2.1.0 이전) → __note__.note 로 통합(없을 때만)
  3. obs/ · scores/ : 변경 없음 (이미 Analyzer 정합 구조)
  4. history/ : 신규 노드 — 백필 없음(전송분만 적재, 향후 누적)

사용:
  python migrate_v2_1_2.py                 # 드라이런 (읽기만, 변경 미리보기)
  python migrate_v2_1_2.py --apply         # 실제 적용 (쓰기)
  python migrate_v2_1_2.py --config PATH   # config.json 경로 지정 (기본 dist/config.json)
"""
import json, sys, os, urllib.request, urllib.parse

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DEFAULT_CONFIG = os.path.join(ROOT, "dist", "config.json")


def _args():
    apply = "--apply" in sys.argv
    cfg = DEFAULT_CONFIG
    if "--config" in sys.argv:
        cfg = sys.argv[sys.argv.index("--config") + 1]
    return apply, cfg


def _base(cfg):
    d = json.load(open(cfg, encoding="utf-8"))
    url = d["firebase_url"].rstrip("/")
    path = d.get("firebase_path", "").strip("/")
    return f"{url}/{path}" if path else url


def fb_get(base, node):
    with urllib.request.urlopen(f"{base}/{node}.json", timeout=15) as r:
        return json.loads(r.read())


def fb_write(base, node, data, method):
    payload = json.dumps(data, ensure_ascii=False).encode("utf-8")
    req = urllib.request.Request(f"{base}/{node}.json", data=payload, method=method)
    req.add_header("Content-Type", "application/json; charset=utf-8")
    with urllib.request.urlopen(req, timeout=15) as r:
        return json.loads(r.read())


def main():
    apply, cfg = _args()
    base = _base(cfg)
    mode = "APPLY (쓰기)" if apply else "DRY-RUN (읽기만)"
    print(f"=== DRW v2.1.2 마이그레이션 [{mode}] ===")
    print(f"target: {base}\n")

    # ── 1. lastSent 삭제 ──
    last = fb_get(base, "lastSent")
    if last is not None:
        print(f"[lastSent] 삭제 대상 존재: {json.dumps(last, ensure_ascii=False)[:80]}")
        if apply:
            fb_write(base, "lastSent", None, "PUT")
            print("           → 삭제됨")
    else:
        print("[lastSent] 없음 — 스킵")

    # ── 2. input/ 정리 ──
    inp = fb_get(base, "input") or {}
    n_assign, n_note_migr, n_students = 0, 0, 0
    for nameKey, subjects in inp.items():
        if not isinstance(subjects, dict):
            continue
        has_note = isinstance(subjects.get("__note__"), dict) and subjects["__note__"].get("note")
        stray_notes = []
        touched = False
        for subj, payload in subjects.items():
            if subj == "__note__" or not isinstance(payload, dict):
                continue
            # 죽은 assign 필드 제거
            if "assign" in payload:
                n_assign += 1
                touched = True
                if apply:
                    fb_write(base, f"input/{urllib.parse.quote(nameKey)}/{urllib.parse.quote(subj)}/assign", None, "PUT")
            # 구 과목별 note 통합 후보 (전 과목 수집 — 손실 방지)
            if payload.get("note"):
                stray_notes.append(payload["note"])
        stray_note = " / ".join(stray_notes)
        # __note__ 없고 구 note 있으면 통합
        if not has_note and stray_note:
            n_note_migr += 1
            touched = True
            if apply:
                fb_write(base, f"input/{urllib.parse.quote(nameKey)}/__note__", {"note": stray_note}, "PATCH")
        if touched:
            n_students += 1

    print(f"\n[input] 학생 {n_students}명 영향")
    print(f"        · 죽은 assign 필드 제거: {n_assign}건")
    print(f"        · 구 과목별 note → __note__ 통합: {n_note_migr}건")

    print(f"\n=== 완료 [{mode}] ===")
    if not apply:
        print("실제 적용하려면: python migrate_v2_1_2.py --apply")


if __name__ == "__main__":
    main()
