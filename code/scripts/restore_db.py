"""
restore_db.py — 백업 스냅샷에서 Firebase RTDB 복원 (파괴적 — 신중히)

사용:
  python restore_db.py --file backup/drw2_2026-06-11_1400.json --node students --yes
  python restore_db.py --file backup/drw2_2026-06-11_1400.json --all --yes   # 루트 전체 PUT

  --node <이름>   해당 최상위 노드만 PUT (students/classes/obs/scores/history/input/session/config)
  --all           루트 전체 PUT — 백업 시점 이후의 모든 변경이 사라짐
  --yes           실제 실행 (없으면 dry-run: 대상·크기만 출력)

복원 전 안전장치: 현재 DB 상태를 backup/pre_restore_*.json 으로 자동 저장.
"""
import argparse
import json
import sys
import datetime
import urllib.parse
import urllib.request
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
CONFIG_PATH = SCRIPT_DIR.parent / "config.json"
BACKUP_DIR = SCRIPT_DIR / "backup"

# 인증은 공용 모듈(_fb_auth) — 서비스 계정(권장) 또는 레거시 시크릿.
sys.path.insert(0, str(SCRIPT_DIR.parent))
from _fb_auth import auth_param


def fb_url(cfg, node=""):
    # 루트 백업과 정합 — firebase_path 접두사 없이 루트(/) 기준. node 는 최상위 키(또는 deep path).
    base = cfg["firebase_url"].rstrip("/")
    leaf = f"/{node}.json" if node else "/.json"
    param, _ = auth_param(cfg)
    if not param:
        raise SystemExit("인증 수단 없음 — sa-key.json(서비스 계정) 또는 config.firebase_secret 필요. "
                         "잠긴 DB는 무인증 복원 불가.")
    return f"{base}{leaf}?{param}"


def http(method, url, payload=None):
    data = json.dumps(payload, ensure_ascii=False).encode("utf-8") if payload is not None else None
    req = urllib.request.Request(url, data=data, method=method,
                                 headers={"Content-Type": "application/json; charset=utf-8"})
    with urllib.request.urlopen(req, timeout=120) as r:
        return json.loads(r.read())


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--file", required=True)
    ap.add_argument("--node", default=None)
    ap.add_argument("--all", action="store_true")
    ap.add_argument("--yes", action="store_true")
    args = ap.parse_args()

    if not args.node and not args.all:
        ap.error("--node <이름> 또는 --all 중 하나 필요")
    if args.node and args.all:
        ap.error("--node 와 --all 동시 사용 불가")

    snap = json.loads(Path(args.file).read_text(encoding="utf-8"))
    cfg = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))

    if args.node:
        if args.node not in snap:
            raise SystemExit(f"백업에 '{args.node}' 노드 없음. 보유: {list(snap)}")
        payload, target = snap[args.node], args.node
    else:
        payload, target = snap, "(루트 전체)"

    size = len(json.dumps(payload, ensure_ascii=False))
    print(f"복원 대상: {target}  크기: {size/1024:.0f}KB  원본: {args.file}")

    if not args.yes:
        print("dry-run: 실제 복원하려면 --yes 추가")
        return

    # 복원 직전 현재 상태 자동 백업
    BACKUP_DIR.mkdir(parents=True, exist_ok=True)
    cur = http("GET", fb_url(cfg))
    pre = BACKUP_DIR / f"pre_restore_{datetime.datetime.now():%Y-%m-%d_%H%M%S}.json"
    pre.write_text(json.dumps(cur, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"복원 전 현재 상태 저장: {pre.name}")

    http("PUT", fb_url(cfg, args.node or ""), payload)
    print(f"복원 완료: {target}")


if __name__ == "__main__":
    main()
