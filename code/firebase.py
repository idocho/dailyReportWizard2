"""
firebase.py — Firebase Realtime Database REST 유틸
Crafted by IDO(idocho@kakao.com) · Powered by Claude AI

노드 구조 (v2.0 스키마):
  students/        학생 명단 {nameKey: {name, class}}
  classes/         학급 정보 {classId: {group, courses/{subject}/...}}
  config/          강사·프리셋 정보
  input/           과제수행도 + 특이사항 {nameKey: {subject: {assign, note}}}
  session/         진도/과제 (class_data)
  obs/             수업 관찰 태그 {nameKey: {subject: {date: {...}}}}
  lastSent/        마지막 전송 데이터 (폴백용)
"""
import json
import urllib.request
import urllib.error
import urllib.parse
import datetime


# ── 내부 헬퍼 ────────────────────────────────────────────────────────
def _fb_url(cfg, node):
    """Firebase REST 엔드포인트 생성 (한글 등 자동 URL 인코딩)."""
    base    = cfg.get('firebase_url', '').rstrip('/')
    path    = cfg.get('firebase_path', '').strip('/')
    encoded = urllib.parse.quote(node, safe='/')
    return f"{base}/{path}/{encoded}.json"


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
