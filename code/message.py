"""
message.py — 카카오톡 데일리 리포트 메시지 조립
Crafted by IDO(idocho@kakao.com) · Powered by Claude AI
"""
import datetime
import re

from constants import grade_label


# ── 메시지 발송 탭: {변수} 치환 엔진 (공통 변수만) ───────────────────
def render(template, ctx):
    """ctx 키로 {변수} 치환. 미정의 변수는 그대로 유지."""
    def _rep(m):
        return str(ctx.get(m.group(1), m.group(0)))
    return re.sub(r'\{([^}]+)\}', _rep, template or '')


def build_bulk_ctx(name, cls):
    """발송 탭 공통 컨텍스트: {이름} {반} {날짜}."""
    d = datetime.datetime.now()
    return {"이름": name, "반": cls or "", "날짜": f"{d.month}/{d.day}"}


def bulk_variables():
    """발송 탭 변수 힌트 버튼용 목록."""
    return [("{이름}", "학생 이름"), ("{반}", "반 이름"), ("{날짜}", "오늘 (M/D)")]


def today_str():
    d = datetime.datetime.now()
    return f"{d.month}/{d.day} ({'월화수목금토일'[d.weekday()]})"


def get_room(cfg, name):
    """학생 이름으로 톡방 검색어 생성.

    방 이름 규칙은 '오직 XXX' — prefix 설정값의 공백 유무와 무관하게
    prefix와 이름 사이 공백 1개를 보장한다(설정 "오직"/"오직 " 모두 동일 결과)."""
    prefix = (cfg.get('room_prefix') or '오직').strip()
    return f"{prefix} {name}" if prefix else name


def nickname_suffix(full_name):
    """'김지민' → '지민이는' 또는 '지민는' (받침 여부 판단)."""
    nick = full_name[1:] or full_name  # 한 글자 이름 방어
    code = ord(nick[-1])
    if 0xAC00 <= code <= 0xD7A3 and (code - 0xAC00) % 28 != 0:
        return f"{nick}이는"
    return f"{nick}는"


def build_message(date_str, class_info, student_name, assign_map, note, tb_grade=None):
    """
    Args:
        date_str:     "5/22 (금)"
        class_info:   { tb: { progress, homework } }
        student_name: "김지민"
        assign_map:   { tb: "과제 완벽 수행 ✅" }
        note:         "오늘은 근의 공식을 첫 설명에 바로..."
        tb_grade:     { tb: grade_sem } — optional, per-class map
    """
    textbooks = list(class_info.keys())
    multi     = len(textbooks) > 1
    _tg       = tb_grade or {}

    def tb_label(tb):
        """교재 레이블: 멀티 교재 시 '중1-1 최상위수학', 단일 시 None."""
        if not multi:
            return None
        return grade_label(_tg.get(tb, ''), tb)

    def section(field):
        lines = []
        for tb, info in class_info.items():
            v = info.get(field, '').strip()
            if v:
                lbl = tb_label(tb)
                lines.append(f"[{lbl}] {v}" if lbl else v)
        return '\n'.join(lines)

    assign_lines = []
    for tb in textbooks:
        a = assign_map.get(tb, '').strip()
        if a:
            lbl = tb_label(tb)
            assign_lines.append(f"[{lbl}] {a}" if lbl else a)

    return (
        f"[데일리 리포트] {date_str}\n"
        f"-------------------------\n"
        f"▶ 오늘의 진도\n{section('progress')}\n\n"
        f"▶ 오늘의 과제\n{section('homework')}\n\n"
        f"▶ 과제 수행도\n{chr(10).join(assign_lines)}\n\n"
        f"▶ 오늘의 {nickname_suffix(student_name)}?\n{note}"
    )
