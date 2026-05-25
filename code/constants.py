"""
constants.py — DailyReportWizard 전역 상수
Crafted by IDO(idocho@kakao.com) · Powered by Claude AI
"""
import platform as _platform

# ── 앱 메타 ───────────────────────────────────────────────────────────
APP_TITLE   = "Daily Report Wizard"
APP_VERSION = "v2.0.0"
APP_CREDIT  = "Crafted by IDO(idocho@kakao.com)  ·  Powered by Claude AI"

AI_COOLDOWN_GROQ = 30  # Groq 무료 플랜 RPM 제한 대응
AI_COOLDOWN_PAID = 3   # 유료 엔진 (Claude/OpenAI) 중복 클릭 방지 최소치

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
    "ai_api_key":      "",
    "groq_api_key":    "",
    "openai_api_key":  "",
    "claude_api_key":  "",
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
