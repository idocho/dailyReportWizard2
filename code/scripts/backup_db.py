"""
backup_db.py — Firebase RTDB 전체 스냅샷 일일 백업 (액션아이템 A1)

동작:
  DB 루트(/) 전체를 GET 하여 code/scripts/backup/drw2_YYYY-MM-DD_HHMM.json 으로 저장.
  30일 경과분 자동 삭제(매월 1일분은 영구 보존).

인증(2026-06-25 보안 룰 잠금 후 — 루트 읽기는 룰상 불가):
  ① 서비스 계정(권장) — Admin 권한으로 룰 우회해 루트 전체 읽기.
     콘솔 → 프로젝트 설정 → 서비스 계정 → "새 비공개 키 생성" → JSON 다운로드 →
     code/scripts/sa-key.json 으로 저장(또는 config.json 의 service_account_path 지정).
     필요 패키지:  pip install google-auth
  ② (전환 폴백) 레거시 DB 시크릿 — config.json 의 firebase_secret. ①이 없을 때만 사용.
  둘 다 없으면 에러(잠금 DB라 무인증 백업 불가).

설정: code/config.json 의 firebase_url 재사용. backup_path 지정 시 그 노드만(기본=루트 전체).
실행: python backup_db.py            — 1회 백업
복원: restore_db.py 사용 (파괴적 — --yes 필수).

주의: 백업 파일·sa-key.json 은 학생 PII/관리자격 — git 제외(.gitignore 등록), 외부 업로드 금지.
"""
import json
import sys
import datetime
import urllib.parse
import urllib.request
from pathlib import Path

RETENTION_DAYS = 30
SCRIPT_DIR = Path(__file__).resolve().parent
BACKUP_DIR = SCRIPT_DIR / "backup"
CONFIG_PATH = SCRIPT_DIR.parent / "config.json"
# config.json 의 firebase_secret 은 DPAPI 암호문일 수 있음 → 공용 인증 모듈에서 복호.
sys.path.insert(0, str(SCRIPT_DIR.parent))
from _fb_auth import auth_param
LOG_PATH = BACKUP_DIR / "backup.log"


def log(msg):
    line = f"[{datetime.datetime.now():%Y-%m-%d %H:%M:%S}] {msg}"
    print(line)
    try:
        with open(LOG_PATH, "a", encoding="utf-8") as f:
            f.write(line + "\n")
    except OSError:
        pass


def _resolve_url(cfg):
    """백업 대상 URL 구성. (url, mode) 반환. 인증 불가 시 (None, None)."""
    base = (cfg.get("firebase_url") or "").rstrip("/")
    if not base:
        log("ERROR: config.json 에 firebase_url 없음")
        return None, None
    # backup_path 미지정 = 루트 전체(/) — campus/·acl·sendJobs 등 전부 스냅샷
    path = (cfg.get("backup_path") or "").strip("/")
    leaf = f"/{path}.json" if path else "/.json"
    param, mode = auth_param(cfg, log)
    if not param:
        log("ERROR: 인증 수단 없음 — 잠긴 DB는 무인증 백업 불가. "
            "sa-key.json(서비스 계정) 배치 또는 config.firebase_secret 설정 필요.")
        return None, None
    return f"{base}{leaf}?{param}", mode


def main():
    BACKUP_DIR.mkdir(parents=True, exist_ok=True)
    cfg = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))

    url, mode = _resolve_url(cfg)
    if not url:
        sys.exit(1)

    log(f"GET 루트 스냅샷 시작 (인증={mode})")
    try:
        with urllib.request.urlopen(url, timeout=120) as r:
            raw = r.read()
    except urllib.error.HTTPError as he:
        body = he.read().decode("utf-8", "replace")[:200]
        log(f"ERROR: HTTP {he.code} — {body}  (서비스 계정 권한/키 확인)")
        sys.exit(1)
    data = json.loads(raw)
    if data is None:
        log("WARNING: 루트가 비어 있음(null) — 백업 저장 생략. DB 상태 확인 필요!")
        sys.exit(2)

    now = datetime.datetime.now()
    out = BACKUP_DIR / f"drw2_{now:%Y-%m-%d_%H%M}.json"
    out.write_text(json.dumps(data, ensure_ascii=False, indent=1), encoding="utf-8")
    top = {k: len(v) if isinstance(v, dict) else 1 for k, v in data.items()}
    log(f"저장 완료: {out.name} ({out.stat().st_size/1024:.0f}KB) 최상위 노드 {top}")

    # 보존 기간 경과분 삭제 — 단, 매월 1일 스냅샷은 영구 보존
    cutoff = now - datetime.timedelta(days=RETENTION_DAYS)
    removed = 0
    for f in BACKUP_DIR.glob("drw2_*.json"):
        try:
            stamp = datetime.datetime.strptime(f.name[5:15], "%Y-%m-%d")
        except ValueError:
            continue
        if stamp.day == 1:
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
