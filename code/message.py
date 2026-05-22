"""
message.py — 카카오톡 데일리 리포트 메시지 조립
Crafted by IDO(idocho@kakao.com) · Powered by Claude AI
"""
import datetime


def today_str():
    d = datetime.datetime.now()
    return f"{d.month}/{d.day} ({'월화수목금토일'[d.weekday()]})"


def get_room(cfg, name):
    """학생 이름으로 톡방 검색어 생성."""
    prefix = cfg.get('room_prefix', '오직 ')
    return f"{prefix}{name}"


def nickname_suffix(full_name):
    """'김지민' → '지민이는' 또는 '지민는' (받침 여부 판단)."""
    nick = full_name[1:]
    code = ord(nick[-1])
    if 0xAC00 <= code <= 0xD7A3 and (code - 0xAC00) % 28 != 0:
        return f"{nick}이는"
    return f"{nick}는"


def build_message(date_str, class_info, student_name, assign_map, note):
    """
    Args:
        date_str:     "5/22 (금)"
        class_info:   { tb: { progress, homework } }
        student_name: "김지민"
        assign_map:   { tb: "과제 완벽 수행 ✅" }
        note:         "오늘은 근의 공식을 첫 설명에 바로..."
    """
    textbooks = list(class_info.keys())
    multi     = len(textbooks) > 1

    def section(field):
        lines = []
        for tb, info in class_info.items():
            v = info.get(field, '').strip()
            if v:
                lines.append(f"[{tb}] {v}" if multi else v)
        return '\n'.join(lines)

    assign_lines = []
    for tb in textbooks:
        a = assign_map.get(tb, '').strip()
        if a:
            assign_lines.append(f"[{tb}] {a}" if multi else a)

    return (
        f"[데일리 리포트] {date_str}\n"
        f"-------------------------\n"
        f"▶ 오늘의 진도\n{section('progress')}\n\n"
        f"▶ 오늘의 과제\n{section('homework')}\n\n"
        f"▶ 과제 수행도\n{chr(10).join(assign_lines)}\n\n"
        f"▶ 오늘의 {nickname_suffix(student_name)}?\n{note}"
    )
