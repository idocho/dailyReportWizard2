"""
backup_db.py — Firebase RTDB 전체 스냅샷 일일 백업 (액션아이템 A1)

동작:
  {firebase_url}/{firebase_path}.json 전체를 GET 하여
  code/scripts/backup/drw2_YYYY-MM-DD_HHMM.json 으로 저장. 30일 경과분 자동 삭제.

설정: code/config.json 의 firebase_url / firebase_path 재사용 (PC 앱과 동일).
실행: python backup_db.py            — 1회 백업
      Windows 작업 스케줄러 일일 등록은 register_backup_task.ps1 참고.
복원: restore_db.py 사용 (파괴적 — --yes 필수).

주의: 백업 파일은 학생 PII 평문 — git 제외(code/scripts/backup/ .gitignore 등록됨),
      외부 업로드 금지.
"""
import json
import sys
import datetime
import urllib.request
from pathlib import Path

RETENTION_DAYS = 30
SCRIPT_DIR = Path(__file__).resolve().parent
BACKUP_DIR = SCRIPT_DIR / "backup"
CONFIG_PATH = SCRIPT_DIR.parent / "config.json"
LOG_PATH = BACKUP_DIR / "backup.log"


def log(msg):
    line = f"[{datetime.datetime.now():%Y-%m-%d %H:%M:%S}] {msg}"
    print(line)
    try:
        with open(LOG_PATH, "a", encoding="utf-8") as f:
            f.write(line + "\n")
    except OSError:
        pass


def main():
    BACKUP_DIR.mkdir(parents=True, exist_ok=True)

    cfg = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
    base = (cfg.get("firebase_url") or "").rstrip("/")
    path = (cfg.get("firebase_path") or "").strip("/")
    if not base or not path:
        log("ERROR: config.json에 firebase_url/firebase_path 없음")
        sys.exit(1)

    url = f"{base}/{path}.json"
    log(f"GET {path} 시작")
    with urllib.request.urlopen(url, timeout=60) as r:
        raw = r.read()
    data = json.loads(raw)
    if data is None:
        # 루트가 비어 있으면 기존 백업을 지우지 않도록 저장하지 않고 경고만 남긴다
        log("WARNING: 루트 노드가 비어 있음(null) — 백업 저장 생략. DB 상태 확인 필요!")
        sys.exit(2)

    now = datetime.datetime.now()
    out = BACKUP_DIR / f"drw2_{now:%Y-%m-%d_%H%M}.json"
    out.write_text(json.dumps(data, ensure_ascii=False, indent=1), encoding="utf-8")
    top = {k: len(v) if isinstance(v, dict) else 1 for k, v in data.items()}
    log(f"저장 완료: {out.name} ({out.stat().st_size/1024:.0f}KB) 최상위 노드 {top}")

    # 보존 기간 경과분 삭제
    cutoff = now - datetime.timedelta(days=RETENTION_DAYS)
    removed = 0
    for f in BACKUP_DIR.glob("drw2_*.json"):
        try:
            stamp = datetime.datetime.strptime(f.name[5:15], "%Y-%m-%d")
        except ValueError:
            continue
        if stamp < cutoff:
            f.unlink()
            removed += 1
    if removed:
        log(f"보존기간({RETENTION_DAYS}일) 경과 {removed}건 삭제")


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        log(f"ERROR: {e}")
        sys.exit(1)
