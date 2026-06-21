"""
pc_auth.py — PC앱 Firebase Auth (REST). AUTH_DESIGN §3·§6.
강사 캠퍼스+이름+비번 → 합성 이메일 → signInWithPassword → idToken/refreshToken.
acl 조회로 campus·role·instructorId 취득. idToken 1h 만료 → refreshToken으로 갱신.
공식 클라이언트 Auth SDK 없이 stdlib urllib 만 사용(기존 firebase.py와 동일 스타일).
"""
import json
import urllib.request
import urllib.error
import urllib.parse
from constants import FIREBASE_API_KEY, FIREBASE_DB_URL

_IDTK = "https://identitytoolkit.googleapis.com/v1"
_SECTOK = "https://securetoken.googleapis.com/v1/token"


def synth_email(name, campus):
    """이름(한글)+캠퍼스 → 합성 이메일. JS synth_email.js 와 동일 포맷."""
    return "n" + (name or "").strip().encode("utf-8").hex() + "@" + (campus or "").strip().lower() + ".drw.local"


def _post(url, body):
    req = urllib.request.Request(url, data=json.dumps(body).encode(),
                                 headers={"Content-Type": "application/json"}, method="POST")
    with urllib.request.urlopen(req, timeout=20) as r:
        return json.loads(r.read())


def _humanize(code):
    return {
        "INVALID_LOGIN_CREDENTIALS": "이름 또는 비밀번호가 올바르지 않습니다.",
        "INVALID_PASSWORD": "이름 또는 비밀번호가 올바르지 않습니다.",
        "EMAIL_NOT_FOUND": "이름 또는 비밀번호가 올바르지 않습니다.",
        "USER_DISABLED": "비활성화된 계정입니다. 관리자에게 문의하세요.",
        "TOO_MANY_ATTEMPTS_TRY_LATER": "시도가 많아 잠시 후 다시 시도하세요.",
    }.get(code, "로그인 중 문제가 발생했습니다.")


def sign_in(campus, name, password):
    """로그인 → {uid, idToken, refreshToken}. 실패 시 RuntimeError(한국어)."""
    email = synth_email(name, campus)
    try:
        d = _post(f"{_IDTK}/accounts:signInWithPassword?key={FIREBASE_API_KEY}",
                  {"email": email, "password": password, "returnSecureToken": True})
    except urllib.error.HTTPError as e:
        try:
            code = json.loads(e.read())["error"]["message"].split(" ")[0]
        except Exception:
            code = ""
        raise RuntimeError(_humanize(code))
    return {"uid": d["localId"], "idToken": d["idToken"], "refreshToken": d["refreshToken"]}


def refresh(refresh_token):
    """refreshToken → 새 {idToken, refreshToken}. 실패 시 예외."""
    body = urllib.parse.urlencode({"grant_type": "refresh_token", "refresh_token": refresh_token}).encode()
    req = urllib.request.Request(f"{_SECTOK}?key={FIREBASE_API_KEY}", data=body,
                                 headers={"Content-Type": "application/x-www-form-urlencoded"}, method="POST")
    with urllib.request.urlopen(req, timeout=20) as r:
        d = json.loads(r.read())
    return {"idToken": d["id_token"], "refreshToken": d["refresh_token"]}


def update_password(id_token, new_password):
    """첫 로그인 비번 변경 → 새 {idToken, refreshToken}."""
    d = _post(f"{_IDTK}/accounts:update?key={FIREBASE_API_KEY}",
              {"idToken": id_token, "password": new_password, "returnSecureToken": True})
    return {"idToken": d.get("idToken"), "refreshToken": d.get("refreshToken")}


def get_acl(uid, id_token):
    """acl/{uid} 조회 → dict 또는 None."""
    url = f"{FIREBASE_DB_URL.rstrip('/')}/acl/{uid}.json?auth={urllib.parse.quote(id_token)}"
    with urllib.request.urlopen(url, timeout=15) as r:
        return json.loads(r.read())
