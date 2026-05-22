"""
constants.py — DailyReportWizard 전역 상수
Crafted by IDO(idocho@kakao.com) · Powered by Claude AI
"""
import platform as _platform

# ── 앱 메타 ───────────────────────────────────────────────────────────
APP_TITLE   = "Daily Report Wizard"
APP_VERSION = "v2.0.0"
APP_CREDIT  = "Crafted by IDO(idocho@kakao.com)  ·  Powered by Claude AI"

AI_COOLDOWN = 30  # AI 생성 쿨다운 (초)

# ── 색상 ─────────────────────────────────────────────────────────────
BG       = "#F5F6FA"
PANEL    = "#FFFFFF"
DARK     = "#1A1D2E"
DARK2    = "#252840"
ACCENT   = "#FEE500"
INDIGO   = "#4338CA"
INDIGO_L = "#EEF2FF"
GREEN    = "#22C55E"
YELLOW   = "#F59E0B"
GRAY     = "#94A3B8"
BORDER   = "#E2E8F0"
TEXT     = "#1E293B"
SUBTEXT  = "#64748B"
BLUE     = "#3B82F6"

# ── 학생 상태 ─────────────────────────────────────────────────────────
STATUS_EMPTY   = "empty"
STATUS_PARTIAL = "partial"
STATUS_READY   = "ready"
DOT_COLOR = {
    STATUS_EMPTY:   "#374151",
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
FE = ("Segoe UI Emoji", 9) if _SYS == "Windows" else ("TkDefaultFont", 9)
_MOD = "command" if _SYS == "Darwin" else "ctrl"

# ── 관찰 태그 정의 (key=Firebase 저장값, label=표시) ──────────────────
# key는 불변. label만 추후 수정 가능.
TAGS = {
    "condition": [
        {"key": "great",  "label": "💡 번뜩임"},
        {"key": "good",   "label": "👍 잘함"},
        {"key": "normal", "label": "😐 보통"},
        {"key": "bad",    "label": "😴 힘듦"},
    ],
    "understand": [
        {"key": "fast",     "label": "🟢 빠름"},
        {"key": "normal_u", "label": "🟡 보통"},
        {"key": "slow",     "label": "🔴 느림"},
    ],
    "understand_sub": [
        {"key": "self_solve", "label": "💪 혼자해결"},
        {"key": "retry",      "label": "🔁 오답재풀이"},
        {"key": "confused",   "label": "😵 개념혼동"},
    ],
    "engage": [
        {"key": "present",  "label": "📣 발표"},
        {"key": "question", "label": "🙋 질문"},
        {"key": "help",     "label": "🤝 도움"},
        {"key": "preview",  "label": "📖 예습"},
    ],
    "caution": [
        {"key": "sleepy",   "label": "💤 졸음"},
        {"key": "phone",    "label": "📵 폰사용"},
        {"key": "chat",     "label": "🗣 잡담"},
        {"key": "attitude", "label": "😤 태도불량"},
    ],
     "extra": [
        {"key": "self_study",  "label": "📚 자율학습"},
        {"key": "weekly_test", "label": "📝 주간Test"},
        {"key": "retest",      "label": "🔄 재시험"},
    ],
}  # TAGS 닫는 중괄호

# ── 기본 설정값 ───────────────────────────────────────────────────────
DEFAULT_CONFIG = {
    "wait_time":      0.5,
    "room_prefix":    "오직 ",
    "firebase_url":   "",
    "firebase_path":  "",
    "ai_engine_type": "groq",
    "ai_api_key":     "",
    "instructor_id":  "",
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
            "추가 자율학습 실시",
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
