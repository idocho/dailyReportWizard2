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
TEMPLATES_PATH = os.path.join(RUNTIME_DIR, 'templates.json')


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


# 기본 빌트인 템플릿 — templates.json 이 없거나 비어 있을 때 시드.
# 사용자가 수정·삭제하면 그대로 유지(재주입 안 함). 발송 탭 변수: {이름} {반} {날짜}.
DEFAULT_TEMPLATES = [
    {"name": "일반 공지",
     "body": "안녕하세요, {이름} 학부모님.\n{반} 반 안내 말씀드립니다.\n\n(내용을 입력하세요)\n\n감사합니다."},
    {"name": "휴원/일정 변경",
     "body": "안녕하세요, {이름} 학부모님.\n\n학원 일정 안내드립니다.\n○월 ○일(○)은 휴원입니다.\n보강 일정은 정해지는 대로 다시 안내드리겠습니다.\n\n감사합니다."},
    {"name": "시험 안내",
     "body": "안녕하세요, {이름} 학부모님.\n\n{반} 반 시험 일정을 안내드립니다.\n• 일시: ○월 ○일(○) 수업 시간\n• 범위: (범위를 입력하세요)\n\n가정에서도 격려 부탁드립니다.\n감사합니다."},
    {"name": "결석 보강 안내",
     "body": "안녕하세요, {이름} 학부모님.\n\n{날짜} {이름} 학생 결석 관련 안내드립니다.\n보강 일정: ○월 ○일(○) ○시\n\n일정 조율이 필요하시면 회신 부탁드립니다.\n감사합니다."},
    {"name": "교재 준비 안내",
     "body": "안녕하세요, {이름} 학부모님.\n\n{반} 반 교재 안내드립니다.\n다음 수업부터 「(교재명)」 교재를 사용합니다.\n수업 전까지 준비 부탁드립니다.\n\n감사합니다."},
]


def load_templates():
    """메시지 발송 탭 템플릿 목록 로드 → [{name, body}, ...]. 없거나 비면 기본 빌트인 시드."""
    if os.path.exists(TEMPLATES_PATH):
        try:
            with open(TEMPLATES_PATH, 'r', encoding='utf-8') as f:
                data = json.load(f)
            if isinstance(data, list) and data:
                return data
        except Exception:
            pass
    return [dict(t) for t in DEFAULT_TEMPLATES]


def save_templates(templates):
    _ensure_parent(TEMPLATES_PATH)
    with open(TEMPLATES_PATH, 'w', encoding='utf-8') as f:
        json.dump(templates, f, ensure_ascii=False, indent=2)


def has_students(cfg):
    """학생 데이터가 하나라도 있으면 True."""
    for sh in cfg.get('sheets', {}).values():
        for cls_data in sh.get('classes', {}).values():
            if cls_data.get('students'):
                return True
    return False


# ── 일일 캐시 ────────────────────────────────────────────────────────
def save_daily_cache(progress_data, student_data=None, note_data=None, force_data=None):
    """진도/과제(class_data)만 로컬 캐시에 저장 (v2.1.2 간소화).

    student_data·note_data·force_data 는 더 이상 디스크에 영속하지 않는다.
    · 출처가 Firebase(obs/·input/)거나 로컬 전용 세션 상태라 재시작 복원 가치가 없고,
      load_daily_cache 도 progress 만 복원해 왔음 → 죽은 I/O 제거.
    · 인자는 호출부 호환 위해 유지하되 사용하지 않음.
    """
    _ensure_parent(CACHE_PATH)
    data = {"class_data": {}}

    for key, v in progress_data.items():
        data["class_data"]["|".join(key)] = {
            "progress": v.get("progress", ""),
            "homework": v.get("homework", ""),
        }

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
