"""
storage.py — 설정·캐시 파일 입출력
Crafted by IDO(idocho@kakao.com) · Powered by Claude AI
"""
import json, os, sys
from constants import DEFAULT_CONFIG, DEFAULT_CACHE


# ── 경로 ─────────────────────────────────────────────────────────────
def base_dir():
    if getattr(sys, 'frozen', False):
        return os.path.dirname(os.path.abspath(sys.argv[0]))
    return os.path.dirname(os.path.abspath(__file__))


def resource_path(filename):
    """PyInstaller 번들 실행 시 _MEIPASS, 개발 실행 시 소스 디렉토리."""
    if getattr(sys, 'frozen', False) and hasattr(sys, '_MEIPASS'):
        return os.path.join(sys._MEIPASS, filename)
    return os.path.join(os.path.dirname(os.path.abspath(__file__)), filename)


def _runtime_dir():
    path = base_dir()
    try:
        os.makedirs(path, exist_ok=True)
        test = os.path.join(path, '.drw_write_test')
        with open(test, 'w', encoding='utf-8') as f:
            f.write('ok')
        os.remove(test)
        return path
    except Exception:
        fallback = os.path.expanduser('~')
        os.makedirs(fallback, exist_ok=True)
        return fallback


def set_runtime_cwd():
    path = _runtime_dir()
    try:
        os.chdir(path)
    except Exception:
        pass
    return path


RUNTIME_DIR = _runtime_dir()
CONFIG_PATH = os.path.join(RUNTIME_DIR, 'config.json')
CACHE_PATH  = os.path.join(RUNTIME_DIR, 'daily_cache.json')


# ── 내부 헬퍼 ────────────────────────────────────────────────────────
def _ensure_parent(path):
    parent = os.path.dirname(path)
    if parent and not os.path.exists(parent):
        os.makedirs(parent, exist_ok=True)


# ── 설정 ─────────────────────────────────────────────────────────────
def load_config():
    if os.path.exists(CONFIG_PATH):
        try:
            with open(CONFIG_PATH, 'r', encoding='utf-8') as f:
                cfg = json.load(f)
        except Exception:
            cfg = None
        if isinstance(cfg, dict):
            # 구버전 room_prefix 마이그레이션
            if cfg.get('room_prefix', '').endswith('_'):
                cfg['room_prefix'] = cfg['room_prefix'].rstrip('_') + ' '
                save_config(cfg)
            return cfg
    save_config(DEFAULT_CONFIG)
    return json.loads(json.dumps(DEFAULT_CONFIG))


def save_config(cfg):
    _ensure_parent(CONFIG_PATH)
    with open(CONFIG_PATH, 'w', encoding='utf-8') as f:
        json.dump(cfg, f, ensure_ascii=False, indent=2)


def has_students(cfg):
    """학생 데이터가 하나라도 있으면 True."""
    for sh in cfg.get('sheets', {}).values():
        for cls_data in sh.get('classes', {}).values():
            if cls_data.get('students'):
                return True
    return False


# ── 일일 캐시 ────────────────────────────────────────────────────────
def save_daily_cache(progress_data, student_data=None, note_data=None, force_data=None):
    """진도/과제 + 과제수행도 + 특이사항 + 강제완료를 캐시로 저장."""
    _ensure_parent(CACHE_PATH)
    data = {"class_data": {}, "student_data": {}, "note_data": {}, "force_data": {}}

    for key, v in progress_data.items():
        data["class_data"]["|".join(key)] = {
            "progress": v.get("progress", ""),
            "homework": v.get("homework", ""),
        }

    if student_data:
        for key, v in student_data.items():
            val = v.get("value", "")
            if val:
                data["student_data"]["|".join(key)] = val

    if note_data:
        for key, v in note_data.items():
            val = v.get("value", "")
            if val:
                data["note_data"]["|".join(key)] = val

    if force_data:
        for key, v in force_data.items():
            if v:
                data["force_data"]["|".join(key)] = True

    with open(CACHE_PATH, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def load_daily_cache():
    """캐시 로드 → (progress_data, student_data, note_data, force_data)."""
    if not os.path.exists(CACHE_PATH):
        save_daily_cache({}, {}, {}, {})
        return {}, {}, {}, {}
    try:
        with open(CACHE_PATH, 'r', encoding='utf-8') as f:
            data = json.load(f)

        progress_data = {}
        for k, v in data.get("class_data", {}).items():
            parts = k.split("|")
            if len(parts) >= 2:
                progress_data[tuple(parts)] = v

        student_data = {}
        for k, val in data.get("student_data", {}).items():
            parts = k.split("|")
            if len(parts) >= 2:
                student_data[tuple(parts)] = {'value': val}

        note_data = {}
        for k, val in data.get("note_data", {}).items():
            parts = k.split("|")
            if len(parts) >= 1:
                note_data[tuple(parts)] = {'value': val}

        force_data = {}
        for k, v in data.get("force_data", {}).items():
            parts = k.split("|")
            if len(parts) >= 1 and v:
                force_data[tuple(parts)] = True

        return progress_data, student_data, note_data, force_data

    except Exception:
        save_daily_cache({}, {}, {}, {})
        return {}, {}, {}, {}
