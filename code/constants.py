"""
constants.py — DailyReportWizard 전역 상수
Crafted by IDO(idocho@kakao.com) · Powered by Claude AI
"""
import platform as _platform

# ── 앱 메타 ───────────────────────────────────────────────────────────
APP_TITLE   = "Daily Report Wizard"
APP_VERSION = "v2.2.2"
APP_CREDIT  = "Crafted by IDO(idocho@kakao.com)  ·  Powered by Claude AI"

AI_COOLDOWN_GROQ   = 30  # Groq 무료 플랜 RPM 제한 대응 (보수적)
AI_COOLDOWN_GEMINI = 7   # Gemini 무료 RPM ~10(=6s) 대응, 마진 포함
AI_COOLDOWN_PAID   = 3   # 유료 엔진 (Claude/OpenAI) 중복 클릭 방지 최소치

# 엔진별 단건 쿨다운(초). 미지정 엔진은 AI_COOLDOWN_PAID 적용.
AI_COOLDOWNS = {'groq': AI_COOLDOWN_GROQ, 'gemini': AI_COOLDOWN_GEMINI}

# 무료 티어 엔진군 (참고용 — RPD/일당 한도 안내 등)
AI_FREE_ENGINES = ('groq', 'gemini')

# 엔진 내부 id ↔ 표시 명칭(공식 표기). 설정 드롭다운·안내문구에서 일관 사용.
AI_ENGINE_ORDER  = ('gemini', 'claude', 'openai', 'groq')  # 표시 순서 (무료·추천 우선)
AI_ENGINE_LABELS = {
    'gemini': 'Gemini',
    'claude': 'Claude',
    'openai': 'GPT (OpenAI)',
    'groq':   'Groq',
}

# Gemini 기본 모델 (무료·stable). 교체 시 이 한 줄만 수정.
GEMINI_MODEL = "gemini-2.5-flash"

# ── 색상 (미니멀·프로 디자인 시스템, v2.1.0 리뉴얼) ──────────────────
BG       = "#FAFAFB"
PANEL    = "#FFFFFF"
PANEL2   = "#F7F7F9"   # 보조 표면 (헤더·우패널 등)
DARK     = "#0E1016"
DARK2    = "#15171F"
ACCENT   = "#FEE500"   # 카카오 브랜드 옐로 (유지)
INDIGO   = "#4F46E5"
INDIGO_INK = "#4338CA" # 진한 인디고 (텍스트·hover)
INDIGO_L = "#EEF0FF"
INDIGO_LINE = "#DDE1FF"
GREEN    = "#16A34A"
YELLOW   = "#D97706"
GRAY     = "#9CA3AF"
BORDER   = "#ECECEF"
LINE_SOFT = "#F3F3F5"
TEXT     = "#18181B"
SUBTEXT  = "#5C6370"
BLUE     = "#2563EB"

# ── 학생 상태 ─────────────────────────────────────────────────────────
STATUS_EMPTY   = "empty"
STATUS_PARTIAL = "partial"
STATUS_READY   = "ready"
DOT_COLOR = {
    STATUS_EMPTY:   "#CBD5E1",
    STATUS_PARTIAL: YELLOW,
    STATUS_READY:   GREEN,
}

# ── 폰트 ─────────────────────────────────────────────────────────────
_SYS  = _platform.system()
_FONT = ("맑은 고딕"            if _SYS == "Windows" else
         "Apple SD Gothic Neo"  if _SYS == "Darwin"  else
         "sans-serif")
FT = (_FONT, 10, "bold")
FB = (_FONT, 9)
FS = (_FONT, 8)
FE = ("맑은 고딕", 9) if _SYS == "Windows" else ("TkDefaultFont", 9)
_MOD = "command" if _SYS == "Darwin" else "ctrl"

# ── obs/ assign_grade key → 한국어 라벨 ──────────────────────────────
ASSIGN_GRADE_LABELS = {
    "done":   "과제 완료",
    "most":   "대부분 수행",
    "half":   "절반 수행",
    "little": "일부 수행",
    "none":   "미수행",
}


def grade_label(grade_sem, subject):
    """과정명(grade_sem)을 과목명 앞에 붙인 표시 라벨.

    subject 키 포맷이 두 가지 공존한다:
      - 구 포맷: 키="라이트쎈"            (curriculum 별도 저장)
      - 신 포맷: 키="중3-1 라이트쎈"       (과정+교재 조합 — app-settings.js)
    신 포맷은 키에 이미 과정명이 들어있으므로 다시 붙이면 "중3-1 중3-1 라이트쎈"
    처럼 중복된다. 키가 이미 "{과정} " 로 시작하면 prepend 하지 않는다.
    """
    gs = (grade_sem or '').strip()
    if gs and not subject.startswith(gs + ' '):
        return f"{gs} {subject}".strip()
    return subject

# ── 관찰 태그 정의 (key=Firebase 저장값, label=표시) ──────────────────
# key는 불변. label만 추후 수정 가능.
TAGS = {
    "condition": [
        {"key": "great",  "label": "↑ 최상"},
        {"key": "good",   "label": "↗ 좋음"},
        {"key": "normal", "label": "→ 보통"},
        {"key": "low",    "label": "↘ 낮음"},
        {"key": "bad",    "label": "↓ 힘듦"},
    ],
    "understand": [
        {"key": "top",      "label": "완벽"},
        {"key": "good",     "label": "잘함"},
        {"key": "normal_u", "label": "이해함"},
        {"key": "confused", "label": "헷갈림"},
        {"key": "hard",     "label": "어려워함"},
    ],
    "understand_sub": [
        {"key": "self_solve", "label": "💪 혼자해결"},
        {"key": "retry",      "label": "🔁 오답재풀이"},
        {"key": "confused",   "label": "😵 개념혼동"},
    ],
    "engage": [
        {"key": "present",   "label": "📣 발표"},
        {"key": "question",  "label": "🙋 질문"},
        {"key": "help",      "label": "🤝 도움"},
        {"key": "preview",   "label": "📖 예습"},
        {"key": "error_fix", "label": "💡 오류정정"},
    ],
    "caution": [
        {"key": "sleepy",   "label": "💤 졸음"},
        {"key": "chat",     "label": "🗣 잡담"},
        {"key": "attitude", "label": "😤 태도불량"},
        {"key": "late",     "label": "⏰ 지각"},
    ],
    "extra": [
        {"key": "self_study",  "label": "📚 자율학습"},
        {"key": "weekly_test", "label": "📝 주간Test"},
        {"key": "retest",      "label": "🔄 재시험"},
    ],
    "highlight": [
        {"key": "perfect",  "label": "🏆 만점·완벽"},
        {"key": "improved", "label": "📈 큰 향상"},
        {"key": "mastered", "label": "✅ 개념완전습득"},
        {"key": "effort",   "label": "💎 끝까지도전"},
    ],
}  # TAGS 닫는 중괄호

# ── 기본 설정값 ───────────────────────────────────────────────────────
DEFAULT_CONFIG = {
    "wait_time":      0.5,
    "room_prefix":    "오직 ",
    "firebase_url":   "",
    "firebase_path":  "",
    "ai_engine_type":  "groq",
    "groq_api_key":    "",
    "openai_api_key":  "",
    "claude_api_key":  "",
    "gemini_api_key":  "",
    "instructor_id":   "",
    "sheets": {
        "M": {"classes": {}},
        "T": {"classes": {}}
    },
    "presets": {
        "과제수행도": [
            "과제 완벽 수행 ✅",
            "과제 수행 양호 👍",
            "풀이 완료, 채점 미실시",
            "거의 완료 (소량 미비)",
            "과반 수행 (절반 이상)",
            "일부만 수행 (다수 미완)",
            "교재 미지참",
            "과제 이행 의지 없어 보임",
            "교재 검사 불가",
            "교재 검사 거부",
            "결석",
        ]
    },
}

DEFAULT_CACHE = {
    "class_data":   {},
    "student_data": {},
    "note_data":    {},
    "force_data":   {},
}
