"""agent_auth.py — 에이전트 Firebase Auth 로그인 (웹 auth.js·synth_email.js 파이썬 포팅).

강사 신원(캠퍼스+이름+비번)으로 idToken 발급 → DB REST 의 ?auth= 에 사용한다.
웹과 동일 합성이메일·동일 signInWithPassword 엔드포인트라 같은 계정으로 로그인된다.

설계 의도(무중단 전환):
  · 보안 룰 미배포(개방 DB) 동안에는 토큰이 없어도 DB 접근이 되므로,
    비번 미설정·로그인 실패 시 TokenManager.token() 은 None 을 돌려주고
    호출측(agent_worker)은 무인증으로 폴백 → 기존 에이전트 무중단.
  · 룰 배포 후에는 토큰이 필수가 되어, 비번 설정된 에이전트만 동작.

idToken 은 1시간 만료 → TokenManager 가 만료 전 refresh 토큰으로 자동 갱신.
"""
import json
import re
import time
import urllib.request
import urllib.parse
import urllib.error

try:
    from constants import FIREBASE_API_KEY
except Exception:  # pragma: no cover
    FIREBASE_API_KEY = ""

SUFFIX = ".drw.local"
_ASCII_SLUG = re.compile(r"^[a-z0-9-]+$")


def _hex_utf8(s):
    return (s or "").strip().encode("utf-8").hex()


def campus_slug(campus):
    """웹 campusSlug 동일 — ASCII 슬러그면 그대로, 아니면 hex."""
    c = (campus or "").strip().lower()
    return c if _ASCII_SLUG.match(c) else _hex_utf8(c)


def synth_email(name, campus):
    """웹 synthEmail 동일 — n{hexUTF8(name)}@{campusSlug}.drw.local."""
    n = _hex_utf8(name)
    c = campus_slug(campus)
    if not n:
        raise ValueError("synth_email: 이름이 비어 있음")
    if not c:
        raise ValueError("synth_email: 캠퍼스가 비어 있음")
    return f"n{n}@{c}{SUFFIX}"


def _post(url, data, form=False, timeout=20):
    if form:
        body = urllib.parse.urlencode(data).encode("utf-8")
        ct = "application/x-www-form-urlencoded"
    else:
        body = json.dumps(data).encode("utf-8")
        ct = "application/json"
    req = urllib.request.Request(url, data=body, headers={"Content-Type": ct}, method="POST")
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.loads(r.read().decode("utf-8"))


def sign_in(name, campus, password, api_key=None):
    """이름+캠퍼스+비번 → {id_token, refresh_token, uid, expiry(ms epoch sec)}. 실패 시 예외."""
    api_key = api_key or FIREBASE_API_KEY
    email = synth_email(name, campus)
    url = f"https://identitytoolkit.googleapis.com/v1/accounts:signInWithPassword?key={urllib.parse.quote(api_key)}"
    d = _post(url, {"email": email, "password": password, "returnSecureToken": True})
    return {
        "id_token": d["idToken"],
        "refresh_token": d["refreshToken"],
        "uid": d.get("localId", ""),
        "expiry": time.time() + int(d.get("expiresIn", "3600")) - 120,  # 2분 여유
    }


def refresh(refresh_token, api_key=None):
    """refresh 토큰 → 새 {id_token, refresh_token, expiry}. 실패 시 예외."""
    api_key = api_key or FIREBASE_API_KEY
    url = f"https://securetoken.googleapis.com/v1/token?key={urllib.parse.quote(api_key)}"
    d = _post(url, {"grant_type": "refresh_token", "refresh_token": refresh_token}, form=True)
    return {
        "id_token": d["id_token"],
        "refresh_token": d["refresh_token"],
        "expiry": time.time() + int(d.get("expires_in", "3600")) - 120,
    }


class TokenManager:
    """idToken 보유·자동 갱신. token() 호출 시 만료 임박이면 갱신, 실패 시 None(무인증 폴백)."""

    def __init__(self, name, campus, password, api_key=None):
        self.name = name
        self.campus = campus
        self.password = password
        self.api_key = api_key or FIREBASE_API_KEY
        self._id = None
        self._refresh = None
        self._exp = 0.0
        self.uid = ""
        self.last_error = None

    def _login(self):
        s = sign_in(self.name, self.campus, self.password, self.api_key)
        self._id, self._refresh, self._exp, self.uid = (
            s["id_token"], s["refresh_token"], s["expiry"], s["uid"])

    def token(self):
        """현재 유효 idToken 반환. 비번 없으면 None. 로그인/갱신 실패 시 None(폴백)."""
        if not self.password:
            return None
        now = time.time()
        try:
            if not self._id:
                self._login()
            elif now >= self._exp:
                try:
                    r = refresh(self._refresh, self.api_key)
                    self._id, self._refresh, self._exp = r["id_token"], r["refresh_token"], r["expiry"]
                except Exception:
                    self._login()  # refresh 실패 → 재로그인
            self.last_error = None
            return self._id
        except Exception as e:
            self.last_error = str(e)[:200]
            self._id = None
            return None
