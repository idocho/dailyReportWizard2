"""
secret_codec.py — 민감 설정값(API 키·DB 시크릿) 로컬 암호화
Crafted by IDO(idocho@kakao.com) · Powered by Claude AI

config.json 에 저장되는 다음 필드를 Windows DPAPI 로 암호화한다:
  groq_api_key · openai_api_key · claude_api_key · gemini_api_key · firebase_secret

설계 원칙:
  · 메모리상 cfg dict 는 항상 평문 — 앱 코드(ai_engine·firebase 등)는 무수정.
    디스크에 쓸 때만 protect(), 읽을 때만 unprotect() (storage.py 가 래핑).
  · 하위호환: unprotect() 는 'dpapi:' 프리픽스가 없으면 입력을 그대로 반환.
    → 기존 평문 config.json, 비-Windows 개발 환경에서도 100% 동작.
  · DPAPI 는 현재 Windows 사용자 계정 + 머신에 바인딩 — config.json 파일만
    다른 PC/계정으로 복사해도 복호 불가(파일 탈취만으로는 키 노출 안 됨).
  · 백업/복원 스크립트(backup_db·restore_db)도 firebase_secret 읽을 때
    unprotect() 를 거쳐야 한다(이 모듈 import).
"""
import base64
import sys

# 암호화 대상 필드 — storage.py 와 스크립트가 공유 참조
SENSITIVE_KEYS = (
    "groq_api_key", "openai_api_key", "claude_api_key", "gemini_api_key",
    "firebase_secret",
)

_PREFIX = "dpapi:"  # 암호문 식별 마커. 없으면 평문으로 간주(하위호환)


def _dpapi_available():
    return sys.platform == "win32"


# ── Windows DPAPI (ctypes 직접 호출, pywin32 의존 없음) ────────────────
def _crypt(data: bytes, encrypt: bool) -> bytes:
    """CryptProtectData / CryptUnprotectData 호출. 실패 시 예외 전파."""
    import ctypes
    from ctypes import wintypes

    class DATA_BLOB(ctypes.Structure):
        _fields_ = [("cbData", wintypes.DWORD),
                    ("pbData", ctypes.POINTER(ctypes.c_char))]

    crypt32 = ctypes.windll.crypt32
    kernel32 = ctypes.windll.kernel32

    buf = ctypes.create_string_buffer(data, len(data))
    blob_in = DATA_BLOB(len(data), ctypes.cast(buf, ctypes.POINTER(ctypes.c_char)))
    blob_out = DATA_BLOB()

    CRYPTPROTECT_UI_FORBIDDEN = 0x1
    fn = crypt32.CryptProtectData if encrypt else crypt32.CryptUnprotectData
    # 인자: (pDataIn, szDescr, pOptionalEntropy, pvReserved, pPromptStruct, dwFlags, pDataOut)
    ok = fn(ctypes.byref(blob_in), None, None, None, None,
            CRYPTPROTECT_UI_FORBIDDEN, ctypes.byref(blob_out))
    if not ok:
        raise OSError("DPAPI 호출 실패 (CryptProtectData/CryptUnprotectData)")
    try:
        out = ctypes.string_at(blob_out.pbData, blob_out.cbData)
    finally:
        kernel32.LocalFree(blob_out.pbData)
    return out


# ── 공개 API ─────────────────────────────────────────────────────────
def protect(plaintext: str) -> str:
    """평문 → 'dpapi:<base64>' 암호문. 빈 값·암호화 불가 환경이면 평문 그대로.

    이미 암호문이면(재진입) 그대로 반환 — 이중 암호화 방지."""
    if not plaintext or plaintext.startswith(_PREFIX):
        return plaintext
    if not _dpapi_available():
        return plaintext  # 비-Windows: 평문 유지(개발 환경)
    try:
        enc = _crypt(plaintext.encode("utf-8"), encrypt=True)
        return _PREFIX + base64.b64encode(enc).decode("ascii")
    except Exception:
        return plaintext  # 암호화 실패 시 가용성 우선(데이터 유실 방지)


def unprotect(stored: str) -> str:
    """'dpapi:<base64>' 암호문 → 평문. 프리픽스 없으면 평문으로 간주해 그대로 반환."""
    if not stored or not stored.startswith(_PREFIX):
        return stored  # 평문(레거시/비-Windows) — 하위호환
    b64 = stored[len(_PREFIX):]
    try:
        raw = base64.b64decode(b64.encode("ascii"))
        return _crypt(raw, encrypt=False).decode("utf-8")
    except Exception:
        # 다른 PC/계정에서 복사된 암호문은 복호 불가 → 빈 값 반환(재입력 유도)
        return ""


def encrypt_fields(cfg: dict) -> dict:
    """cfg 의 민감 필드를 암호화한 '복사본' 반환 (원본 dict 비파괴 — 메모리는 평문 유지)."""
    out = dict(cfg)
    for k in SENSITIVE_KEYS:
        v = out.get(k)
        if isinstance(v, str) and v:
            out[k] = protect(v)
    return out


def decrypt_fields(cfg: dict) -> dict:
    """cfg 의 민감 필드를 평문으로 복호한 dict 반환 (in-place 갱신 후 반환)."""
    for k in SENSITIVE_KEYS:
        v = cfg.get(k)
        if isinstance(v, str) and v:
            cfg[k] = unprotect(v)
    return cfg


def has_plaintext_secret(cfg: dict) -> bool:
    """디스크 cfg 에 아직 암호화 안 된 민감 값이 있으면 True (마이그레이션 트리거용)."""
    for k in SENSITIVE_KEYS:
        v = cfg.get(k)
        if isinstance(v, str) and v and not v.startswith(_PREFIX):
            return True
    return False
