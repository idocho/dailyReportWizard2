"""
_fb_auth.py — Firebase RTDB REST 인증 (backup_db·restore_db 공용).

보안 룰 잠금(2026-06-25) 후 루트 read/write 는 사용자 토큰으로 불가 → 관리자급 인증 필요:
  ① 서비스 계정(권장) — Admin 권한으로 룰 우회. 콘솔 → 프로젝트 설정 → 서비스 계정 →
     "새 비공개 키 생성" → JSON 을 code/scripts/sa-key.json 으로 저장
     (또는 config.json 의 service_account_path 로 경로 지정). pip install google-auth
  ② (전환 폴백) 레거시 DB 시크릿 — config.json 의 firebase_secret. ①이 없을 때만.

auth_param(cfg) → ("access_token=…"|"auth=…", mode) 또는 (None, None).
"""
import sys
import urllib.parse
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
DEFAULT_SA_PATH = SCRIPT_DIR / "sa-key.json"
SA_SCOPES = [
    "https://www.googleapis.com/auth/firebase.database",
    "https://www.googleapis.com/auth/userinfo.email",
]

sys.path.insert(0, str(SCRIPT_DIR.parent))
from secret_codec import unprotect


def _sa_token(sa_path):
    from google.oauth2 import service_account
    from google.auth.transport.requests import Request as GRequest
    creds = service_account.Credentials.from_service_account_file(str(sa_path), scopes=SA_SCOPES)
    creds.refresh(GRequest())
    return creds.token


def auth_param(cfg, log=print):
    """(param, mode) 반환. param='access_token=…'|'auth=…'(URL 쿼리용). 인증 불가 시 (None,None)."""
    sa = cfg.get("service_account_path") or (str(DEFAULT_SA_PATH) if DEFAULT_SA_PATH.exists() else "")
    if sa and Path(sa).exists():
        try:
            tok = _sa_token(sa)
            return "access_token=" + urllib.parse.quote(tok, safe=""), "service_account"
        except ImportError:
            log("google-auth 미설치 — `pip install google-auth` 후 재시도")
        except Exception as e:
            log(f"서비스 계정 토큰 발급 실패: {e}")
    secret = unprotect(cfg.get("firebase_secret") or "").strip()
    if secret:
        log("주의: 레거시 DB 시크릿 사용 — 서비스 계정(sa-key.json) 전환 권장")
        return "auth=" + urllib.parse.quote(secret, safe=""), "legacy_secret"
    return None, None
