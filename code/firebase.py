"""
firebase.py — Firebase Realtime Database REST 유틸
Crafted by IDO(idocho@kakao.com) · Powered by Claude AI

노드 구조 (v2.0 스키마):
  students/        학생 명단 {nameKey: {name, class}}
  classes/         학급 정보 {classId: {group, courses/{subject}/...}}
  config/          강사·프리셋 정보
  input/           과제수행도(과목별) + 특이사항(학생별 단일)
                   {nameKey: {subject: {assign}, __note__: {note}}}
  session/         진도/과제 (class_data)
  obs/             수업 관찰 태그 {nameKey: {subject: {date: {...}}}}

과목 소프트 삭제(v2.2.2): courses/{subject}/archived == true 면 보관 과목 —
표시·입력·전송에서 제외하되 obs/scores/history 기록은 보존. active_courses() 사용.
"""
import json
import urllib.request
import urllib.error
import urllib.parse
import datetime


# ── 내부 헬퍼 ────────────────────────────────────────────────────────
def _fb_url(cfg, node):
    """Firebase REST 엔드포인트 생성 (한글 등 자동 URL 인코딩).

    firebase_url/firebase_path 단일 출처만 사용한다. 설정이 없으면 조용히
    잘못된 URL을 만들지 않고 명시적으로 오류를 낸다.
    """
    base    = (cfg.get('firebase_url') or '').rstrip('/')
    path    = (cfg.get('firebase_path') or '').strip('/')
    if not base or not path:
        raise ValueError(
            "Firebase 경로가 설정되지 않았습니다. 설정에서 URL·경로를 입력하세요."
        )
    enc_path = urllib.parse.quote(path, safe='/')
    encoded  = urllib.parse.quote(node, safe='/')
    return f"{base}/{enc_path}/{encoded}.json"


# ── 기본 CRUD ────────────────────────────────────────────────────────
def firebase_get(cfg, node):
    url = _fb_url(cfg, node)
    req = urllib.request.Request(url)
    with urllib.request.urlopen(req, timeout=10) as r:
        return json.loads(r.read())


def firebase_put(cfg, node, data):
    url     = _fb_url(cfg, node)
    payload = json.dumps(data, ensure_ascii=False).encode('utf-8')
    req     = urllib.request.Request(url, data=payload, method='PUT')
    req.add_header('Content-Type', 'application/json; charset=utf-8')
    with urllib.request.urlopen(req, timeout=10) as r:
        return json.loads(r.read())


def firebase_patch(cfg, node, data):
    url     = _fb_url(cfg, node)
    payload = json.dumps(data, ensure_ascii=False).encode('utf-8')
    req     = urllib.request.Request(url, data=payload, method='PATCH')
    req.add_header('Content-Type', 'application/json; charset=utf-8')
    with urllib.request.urlopen(req, timeout=10) as r:
        return json.loads(r.read())


# ── 데이터 헬퍼 ──────────────────────────────────────────────────────
def active_courses(cls_data):
    """archived(보관) 과목을 제외한 courses dict 반환.

    과목 '삭제'는 웹에서 archived:true 소프트 마킹 — obs/scores/history 기록은
    DB에 보존되고 표시·입력·전송에서만 제외된다. 같은 키로 재추가 시 복원."""
    courses = (cls_data or {}).get('courses', {}) or {}
    return {s: c for s, c in courses.items()
            if not (isinstance(c, dict) and c.get('archived'))}


# ── 태그 전용 (Firebase 경로: obs/) ──────────────────────────────────
def today_key():
    """오늘 날짜 키 (YYYY-MM-DD)."""
    return datetime.date.today().isoformat()


def fetch_tags(config):
    """obs/ 전체 로드. 구조: {nameKey: {subject: {date: {...}}}}"""
    try:
        data = firebase_get(config, "obs")
        return data if isinstance(data, dict) else {}
    except Exception:
        return {}


def fetch_tags_today(config, nameKey, subject):
    """특정 학생의 오늘 obs 로드."""
    try:
        data = firebase_get(config, f"obs/{nameKey}/{subject}/{today_key()}")
        return data if isinstance(data, dict) else {}
    except Exception:
        return {}
