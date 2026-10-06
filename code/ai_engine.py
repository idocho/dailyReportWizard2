"""
ai_engine.py — 멀티 LLM API 특이사항 생성 엔진 (Groq / Claude / GPT 선택 대응)
Crafted by IDO(idocho@kakao.com) · Powered by Gemini
"""
import json
import re
import threading
import time
import urllib.request
import urllib.error

# 외부(main.py)에서 주입 가능한 디버그 플래그 (기본: 비활성)
DEBUG_AI_PROMPT: bool = False

from constants import GEMINI_MODEL, OPENAI_MODEL, grade_label
import ai_style
from ai_model_config import resolve

def dprint(*args, **kwargs):
    """DEBUG_AI_PROMPT 플래그가 True일 때만 출력되는 디버그 프린트."""
    if DEBUG_AI_PROMPT:
        print(*args, **kwargs)

# ── 태그 key → 자연어 변환 테이블 ────────────────────────────────────
# v8.51 컨디션 문구 재작성 — 학부모 발송 적합화.
# ① '무난하게' 등 밋밋·부정 인상 표현 제거(정상도 학습 충실 묘사로).
# ② 긍정/보통(good·normal)은 굳이 따로 언급 말도록 메타 지시 동봉 — 메시지가 컨디션으로
#    시작·도배되는 단조로움 방지(메시지 리드는 학습 내용·성취가 맡음, _base_conditions 11~13 참조).
# ③ low·bad만 완곡·격려 어조로 한 번 녹임.
_CONDITION_TEXT = {
    "great":  "수업 내내 집중력이 높고 적극적으로 참여함(매우 긍정적, 강조 가능)",
    "good":   "차분하고 성실하게 수업에 집중함(긍정적 — 굳이 컨디션을 따로 문장으로 언급하지 않아도 됨)",
    "normal": "평소와 같이 안정적으로 수업에 집중함(특이사항 없음 — 굳이 컨디션을 따로 언급하지 말 것)",
    "low":    "다소 피로한 기색이 있었으나 수업에는 끝까지 참여함(완곡히, 격려 어조로만)",
    "bad":    "컨디션이 좋지 않아 집중 유지에 격려가 필요했던 날(완곡히, 비난 없이)",
}
_UNDERSTAND_TEXT = {
    "top":      "설명 즉시 이해하고 바로 응용까지 진행함",
    "good":     "대체로 빠르게 이해하며 큰 막힘 없이 진행함",
    "normal_u": "설명 후 이해함, 평균적인 흡수 속도",
    "confused": "헷갈리는 부분이 있어 반복 설명 필요",
    "hard":     "반복 설명에도 어려움이 있어 추가 지도 필요",
}
_UNDERSTAND_SUB_TEXT = {
    "self_solve": "막힌 문제를 스스로 돌파하는 모습이 있었음",
    "retry":      "틀린 문제를 다시 풀며 오답을 점검함",
    "confused":   "이전에 배운 개념과 혼동하는 부분이 관찰됨",
}
# v8.30 태그 재구조화: deep_try·slow·calc_miss·process_good 신설.
# 폐기 태그(present·help·preview·error_fix·weekly_test·retest·perfect·improved·attitude)는
# UI에서만 제거 — 과거 날짜 데이터 호환을 위해 매핑은 유지.
_ENGAGE_TEXT = {
    "question": "모르는 부분을 스스로 질문함",
    "deep_try": "심화·복합 유형 문제에 적극적으로 도전함",
    "present":  "수업 중 발표에 적극 참여함",
    "help":     "친구의 이해를 도와주는 모습이 있었음",
    "preview":  "미리 예습하고 수업에 참여함",
    "error_fix": "풀이 오류를 스스로 발견하고 정정함",
}
_CAUTION_TEXT = {
    "sleepy":       "수업 중 졸음 증상",
    "chat":         "잡담으로 수업 참여도 저하",
    "late":         "지각",
    "slow":         "문제 풀이에 시간이 다소 오래 걸리는 편이었음",
    "calc_miss":    "계산 실수가 반복적으로 관찰됨",
    "writeup_weak": "서술형·논술형 풀이 과정 작성이 미흡하여 연습이 필요함",
    "attitude":     "수업 태도 개선 필요",
}
_EXTRA_TEXT = {
    "self_study":  "자율학습을 실시함",
    "weekly_test": "주간 테스트를 실시함",
    "retest":      "재시험을 실시함",
}
_EXAM_TEXT = {
    "top":       "시험 결과 우수(잘 봄) — 구체적으로 칭찬하고 성취를 강조",
    "good":      "시험 결과 양호 — 안정적인 성취를 격려",
    "careless":  "아는 내용인데 단순 실수(계산·조건·검토)로 실점 — 실력은 인정하되 검토·점검 습관을 완곡히 코칭",
    "hard_miss": "기본 개념은 정확하나 고난도·심화에서 실점 — 기본기를 칭찬하고 심화 보강 방향을 제시",
    "low":       "시험 결과가 전반적으로 아쉬움 — 비난 없이 완곡하게, 보완 방향과 격려 중심으로",
}
_HIGHLIGHT_TEXT = {
    "mastered":     "오늘 다룬 개념을 완전히 습득함",
    "effort":       "어려운 문제에도 끝까지 포기하지 않는 집념을 보임",
    "process_good": "풀이 과정을 논리적이고 깔끔하게 서술함",
    "perfect":      "오늘 만점 또는 완벽에 가까운 풀이 성취",
    "improved":     "지난 수업 대비 눈에 띄게 향상된 모습",
}


def _build_tags_context(tags: dict) -> str:
    """오늘 수업 관찰 태그 dict → 프롬프트용 자연어 블록."""
    if not tags:
        return ""

    lines = []

    cond = tags.get("condition")
    if cond and cond in _CONDITION_TEXT:
        lines.append(f"- 수업 컨디션: {_CONDITION_TEXT[cond]}")

    # 과제 커스텀 프리셋(자유 텍스트, 복수) — 강사가 직접 등록한 문구 그대로 전달
    assign_raw = tags.get("assign_tags") or []
    if isinstance(assign_raw, dict):
        assign_raw = list(assign_raw.values())
    elif isinstance(assign_raw, str):
        assign_raw = [assign_raw]
    assign_extra = [t.strip() for t in assign_raw if isinstance(t, str) and t.strip()]
    if assign_extra:
        lines.append("- 과제 관련 특이사항 — 각 항목의 핵심 사실을 반드시 본문에 반영: " + ", ".join(assign_extra))

    und = tags.get("understand")
    if und and und in _UNDERSTAND_TEXT:
        lines.append(f"- 이해 속도: {_UNDERSTAND_TEXT[und]}")

    ex = tags.get("exam")
    if isinstance(ex, str):   # 레거시 단일값 호환
        ex = [ex] if ex else []
    ex_notes = [_EXAM_TEXT[k] for k in (ex or []) if k in _EXAM_TEXT]
    if ex_notes:
        lines.append("- 시험 결과(직접적이되 공격적이지 않게, 이 결과를 메시지 핵심으로): " + "; ".join(ex_notes))

    for key in tags.get("understand_sub") or []:
        if key in _UNDERSTAND_SUB_TEXT:
            lines.append(f"- {_UNDERSTAND_SUB_TEXT[key]}")

    engage_notes = [_ENGAGE_TEXT[k] for k in (tags.get("engage") or []) if k in _ENGAGE_TEXT]
    if engage_notes:
        lines.append(f"- 참여 행동: {', '.join(engage_notes)}")

    caution_notes = [_CAUTION_TEXT[k] for k in (tags.get("caution") or []) if k in _CAUTION_TEXT]
    if caution_notes:
        lines.append(f"- 주의 관찰 (학부모 전달용, 과도한 비난 표현 금지): {', '.join(caution_notes)}")
    extra_notes = [_EXTRA_TEXT[k] for k in (tags.get("extra") or []) if k in _EXTRA_TEXT]
    if extra_notes:
        lines.append(
            f"- 별도 전달 이벤트 (다른 수업 묘사와 섞지 말고 독립 문장으로 강조): "
            f"{', '.join(extra_notes)}"
        )

    hl_raw = tags.get("highlight") or []
    if isinstance(hl_raw, str):  # 구버전 단일값 호환
        hl_raw = [hl_raw] if hl_raw else []
    hl_texts = [_HIGHLIGHT_TEXT[k] for k in hl_raw if k in _HIGHLIGHT_TEXT]
    if hl_texts:
        lines.insert(0, f"- ⭐ 오늘의 하이라이트: {', '.join(hl_texts)}")

    if DEBUG_AI_PROMPT:
        print(f"[TAGS DEBUG] raw={tags}")
        print(f"[TAGS DEBUG] built=\n{chr(10).join(lines) if lines else '(없음)'}")

    return "\n".join(lines)


def _base_conditions(batch=False) -> str:
    """모든 AI 생성 호출에 공통으로 들어가는 조건 문자열."""
    return (
        "[작성 지침]\n"
        "1. 문체: 선택한 문체 지침의 말투를 따르고, 지정이 없으면 ~했습니다 체로 통일. "
        "강사 개별 지침의 말투·구성·이모지 요청은 기본 및 선택 문체보다 우선합니다. "
        "분량은 별도 메시지 길이 설정을 최우선으로 따릅니다. 사실·안전·출력 형식 규칙은 항상 유지.\n"
        "★ 학생 이름을 주어로 절대 쓰지 마세요. 메시지 바로 위에 '오늘의 OOO는?' 헤더가 "
        "이미 이름을 표시하므로, 본문에서 'OOO는'·'OOO 학생은'·'OO이는' 같은 이름 주어는 "
        "중복이라 금지합니다. 이름·호칭 없이 곧바로 수업 내용·성취·이해도·관찰된 행동으로 시작하세요.\n"
        "2. 직접 작성 메모: [직접 작성 메모 — 반드시 반영] 섹션이 있으면 핵심 사실을 빠뜨리지 말고 "
        "최종 문장에 자연스럽게 포함하세요. 특히 일정·보강·시험·상담·준비물 등 운영 메모는 반드시 보존.\n"
        "3. 금지: '어머님·학부모님' 호칭, 시스템 표현('미입력·데이터 없음' 등), "
        "제공된 데이터에 없는 사실 추가(할루시네이션) 절대 금지.\n"
        "4. 이벤트 반영: [수업 관찰 및 이벤트 정보]에 명시된 항목만 반영. "
        "이 섹션에 없는 자율학습·재시험·주간테스트 등을 임의로 추가하지 마세요.\n"
        "5. 별도 전달 이벤트: 자율학습·주간 테스트·재시험 등은 수업 태도/이해도 문장에 섞지 말고 "
        "가능하면 별도 문장으로 분리해 명확히 전달하세요.\n"
        "6. 주의 태그: '졸음·잡담·태도불량' 등 직접 단어 사용 절대 금지. "
        "'오늘은 조금 피곤해 보이는 날이었습니다' / '집중이 다소 어려웠던 날이었지만' 수준으로 완곡하게 녹여 작성.\n"
        "7. 하이라이트: ⭐ 오늘의 하이라이트가 있으면 메시지에서 가장 먼저 또는 가장 인상적으로 표현.\n"
        "8. 과제 반복 금지: 진도·과제 정보(페이지·번호 등)는 메시지에 별도 항목으로 이미 전달됩니다. "
        "특이사항에서 '다음 과제는 p.XX입니다' 식으로 그대로 읽어주는 문장 절대 금지.\n"
        "9. 입력 부족: 데이터가 비었다는 이유로 출석·결석·정상 수업·성취를 단정하지 마세요. "
        "오늘 관찰·메모가 있으면 그 사실만 작성하고, 모두 없으면 짧은 중립적 안부만 작성하세요.\n"
        + ("10. 출력: 지정된 cls·name·note 키의 순수 JSON 배열만. note는 자연어 본문.\n" if batch else
         "10. 출력: 순수 텍스트만 (JSON·마크다운·따옴표 금지).\n")
        + "분량: 기본 2~3문장, 100자 내외. 문체 지침이 있으면 그 분량을 우선하되, "
        "반드시 전달할 메모의 날짜·시간·준비물은 분량 때문에 생략하지 마세요.\n"
        +
        "11. 컨디션 처리: 컨디션은 메시지의 '보조 맥락'입니다. 메시지를 컨디션 묘사로 "
        "시작하지 말고, 반드시 학습 내용·성취·이해도·관찰 행동을 먼저 전달한 뒤 필요한 "
        "경우에만 컨디션을 자연스럽게 녹이세요. great 외의 긍정/보통(good·normal) 컨디션은 "
        "굳이 따로 문장으로 언급하지 않아도 됩니다(좋은 컨디션은 기본 전제). low·bad만 "
        "완곡하게 한 번 부드럽게 덧붙이세요.\n"
        "12. 금지 표현: '무난하게'·'무난한'·'특별한 것 없이'·'그냥' 등 학부모에게 밋밋하거나 "
        "성의 없게 들리는 표현 금지. 보통 수준이어도 '차분히 집중하며'·'안정적으로' 등 "
        "학습에 충실한 묘사로 대체하세요.\n"
        "13. 항상 학부모가 읽고 안심·신뢰할 수 있도록, 사실에 기반하되 건설적이고 "
        "앞을 향한 어조로 마무리하세요.\n"
        "14. 표현 다양화: 같은 학생에게 매일 비슷한 관찰 태그가 반복되더라도, 문장 시작 표현·"
        "문장 구조·어휘를 매번 다르게 쓰세요. '오늘도', '성실하게 참여했습니다' 같은 상투 문구의 "
        "반복 사용 금지. 같은 사실도 관찰 장면(어떤 문제에서·어떤 행동으로), 성취 과정, 변화 추이 등 "
        "매일 다른 각도로 서술하되, 입력에 없는 문제 유형·행동·향상을 만들지 마세요. [지난 발송 이력] 블록이 있으면 그 문구들과 표현이 "
        "겹치지 않게 쓰되, 이력은 과거 기록이므로 오늘 일처럼 가져오지 마세요(블록 내 규칙 준수)."
    )


# ── 단건 생성 프롬프트 ───────────────────────────────────────────────
_DEFAULT_STYLE_BLOCK = (
    "[문체 참고 예시 — 말투만 참고. 예시의 단원·행동·이벤트·성취는 복사 금지. 내용은 아래 학생 데이터로 새로 작성]\n"
    "예1) \"오늘 이차함수 단원에서 막혔던 개념을 반복 설명 후 이해했습니다. 틀린 문항을 스스로 재풀이하며 오답을 정리하는 모습이 인상적이었습니다.\"\n"
    "예2) \"주간 테스트를 실시했으며, 오늘은 다소 피곤해 보이는 날이었지만 끝까지 집중해서 임했습니다.\"\n"
    "예3) \"예습 내용을 바탕으로 설명을 빠르게 이해하고 응용 문제까지 도전했습니다. 오늘 다룬 개념을 완전히 자기 것으로 만든 하루였습니다.\""
)


def _recent_notes_block(recent_notes):
    """학생별 최근 발송 특이사항 [(date, note), ...] → 맥락 참조 프롬프트 블록.

    용도 두 가지:
    ① 맥락 연속성 — 지난 수업 흐름(어려워하던 단원의 극복, 꾸준한 태도 등)을 이어받아
       성장·변화 서사를 자연스럽게 반영. 단 시제 구분 필수: 과거는 반드시
       '지난 수업에서/지난주' 등 과거 표지로만, 오늘 일처럼 서술 금지.
    ② 표현 중복 회피 — 최근 문구와 문장 시작·구조·어휘가 겹치지 않게.
    이력은 날짜 오름차순(과거→최근)으로 제시해 전후 관계 혼동 방지.
    """
    import datetime
    rows = [(d, (n or "").strip()) for d, n in (recent_notes or []) if (n or "").strip()]
    if not rows:
        return ""
    rows = sorted(rows, key=lambda x: x[0])[-3:]          # 과거→최근 오름차순
    lines = "\n".join(f"- {d} (과거): \"{n[:200]}\"" for d, n in rows)
    today = datetime.date.today().isoformat()
    return (
        f"[지난 발송 이력 — 맥락 참고용 · 전부 과거 기록 · 오늘={today}]\n"
        f"{lines}\n"
        "이력 활용 규칙:\n"
        "a) 시제 엄수: 위 이력은 모두 지난 수업의 일입니다. 오늘 있었던 일처럼 쓰는 것 절대 금지. "
        "과거를 언급할 땐 반드시 '지난 수업에서'·'지난주'·'그동안' 같은 과거 표지를 붙이세요.\n"
        "b) 맥락 연결 권장: 이력과 오늘 데이터 사이에 자연스러운 흐름(어려워하던 부분의 극복, "
        "꾸준함의 지속, 눈에 띄는 변화)이 보이면 한 문장 이내로 연결하세요. "
        "단, 메시지의 중심은 항상 오늘의 수업 데이터·관찰이며 오늘 사실은 오늘 데이터만 근거로.\n"
        "c) 과거의 점수·페이지 등 수치는 재인용하지 마세요(옮기다 틀릴 위험). 흐름만 언급.\n"
        "d) 표현 중복 금지: 위 이력 문구들과 문장 시작 표현·문장 구조·핵심 어휘가 겹치지 않게 "
        "새로 쓰세요. 억지 연결이 되면 연결 없이 오늘 내용만 새로운 표현으로 쓰는 것이 낫습니다.\n\n"
    )


def build_single_prompt(sheet, cls, name, textbooks, student_data, progress_data,
                        existing_note, tags, tb_grade=None, style_block="",
                        display_name=None, recent_notes=None):
    """단건 AI 생성용 프롬프트 조립 (v2.0 키 구조).

    name: nameKey(출결번호) — 데이터/태그 조회 키.
    display_name: 프롬프트 [학생 이름]에 노출할 표시 이름. 미지정 시 name 사용
        (구버전 호환). 출결번호가 이름으로 새는 것을 방지하려면 반드시 표시명 전달.
    style_block: ai_style.style_prompt_block() 결과(문체 지침+예시). 비면 기본 예시.
    recent_notes: [(date, note), ...] 학생별 최근 발송 문구 — 표현 중복 회피 블록 주입.
    """
    _tg = tb_grade or {}
    lines = []
    for tb in textbooks:
        # v2.0: student_data 키 = (classId, nameKey, subject)
        val = student_data.get((cls, name, tb), {}).get('value', '')
        if val:
            tb_lbl = grade_label(_tg.get(tb, ''), tb)
            # v2.0: progress_data 키 = (classId, subject)
            pd_val = progress_data.get((cls, tb), {})
            lines.append(
                f"- {tb_lbl}: 수행도={val}"
                + (f", 진도={pd_val['progress']}" if pd_val.get('progress') else "")
                + (f", 과제={pd_val['homework']}"  if pd_val.get('homework') else "")
            )
    context = "\n".join(lines) if lines else "오늘 수업 사실 제공 없음(출결 판단 근거 아님)"

    tags_block = _build_tags_context(tags)

    prompt = (
        "수학학원 교사가 학부모에게 보낼 데일리 리포트 특이사항을 작성합니다.\n"
        "아래 제공된 데이터만을 근거로 작성하고, 데이터에 없는 내용은 절대 추가하지 마세요.\n\n"
        f"{style_block or _DEFAULT_STYLE_BLOCK}\n\n"
        f"[학생 이름 — 식별용 참고, 본문에 주어로 쓰지 말 것]\n{display_name or name}\n\n"
        f"[수업 데이터]\n{context}\n\n"
    )
    if tags_block:
        prompt += f"[수업 관찰 및 이벤트 정보]\n{tags_block}\n\n"
    prompt += _recent_notes_block(recent_notes)
    if existing_note:
        prompt += (
            "[직접 작성 메모 — 반드시 반영]\n"
            f"{existing_note}\n"
            "위 메모는 교사가 직접 입력한 핵심 전달 사항입니다. "
            "최종 특이사항에 빠뜨리지 말고 자연스럽게 포함하세요.\n\n"
        )

    return prompt


# ── 일괄 생성 프롬프트 ───────────────────────────────────────────────
def build_batch_prompt(targets, style_block="", custom_block=""):
    """일괄 AI 생성용 프롬프트 조립 (군더더기 제거 및 JSON 안정화).

    style_block: ai_style.style_prompt_block() 결과. 비면 기본 문체 기준만 사용.
    custom_block: 강사 개별 지침 블록. [학생데이터] 앞에 삽입.
    """
    students_payload = []
    for t in targets:
        valid_data = []
        for tb, val in t["data"].items():
            if val and "미입력" not in str(val):
                prog = t.get("progress", {}).get(tb, {})
                parts = [f"수행도:{val}"]
                if prog.get('progress'):
                    parts.append(f"진도:{prog['progress']}")
                if prog.get('homework'):
                    parts.append(f"과제:{prog['homework']}")
                valid_data.append(f"{tb}({', '.join(parts)})")
        
        entry = {
            "name":  t["name"],
            "cls":   t["cls"],
            "수업데이터": ", ".join(valid_data) if valid_data else "오늘 수업 사실 제공 없음(출결 판단 근거 아님)"
        }
        if t.get("existing"):
            entry["직접작성메모_반드시반영"] = t["existing"]
        tags_block = _build_tags_context(t.get("tags") or {})
        if tags_block:
            entry["수업관찰및이벤트"] = tags_block
        recent = sorted([(d, (n or "").strip()) for d, n in (t.get("recent") or [])
                         if (n or "").strip()], key=lambda x: x[0])[-3:]
        if recent:
            entry["지난발송이력_과거기록_맥락참고"] = [f"{d}: {n[:200]}" for d, n in recent]
        students_payload.append(entry)

    students_json = json.dumps(students_payload, ensure_ascii=False, indent=2)

    prompt = (
        "수학학원 교사가 학부모용 데일리 리포트 특이사항을 일괄 작성합니다.\n"
        "⚠️ 각 학생의 '수업관찰및이벤트' 필드에 명시된 항목만 반영하세요. "
        "필드에 없는 자율학습·재시험·주간테스트 등은 절대 언급하지 마세요.\n\n"
        "[문체 기준] 학부모가 읽기 편한 어조. "
        "★ 학생 이름을 주어로 쓰지 마세요 — 메시지 위에 '오늘의 OOO는?' 헤더로 이름이 이미 "
        "표시되므로 'OOO는'·'OOO 학생은'·'OO이는' 식 이름 주어는 중복이라 금지. 이름 없이 "
        "수업 내용·행동으로 바로 시작하세요. "
        "'졸음·잡담·태도불량' 직접 단어 사용 금지 — 완곡하게 표현.\n"
        + (f"{style_block}\n" if style_block else "기본 분량은 2~3문장 100자 내외.\n")
        + "자율학습·주간 테스트·재시험 등 별도 전달 이벤트는 다른 수업 묘사와 섞지 말고 "
        "가능하면 독립 문장으로 명확히 작성하세요.\n"
        "각 학생의 '직접작성메모_반드시반영' 필드는 교사가 직접 입력한 핵심 전달 사항이므로 "
        "최종 note에 반드시 자연스럽게 포함하세요.\n"
        "'지난발송이력_과거기록_맥락참고' 필드는 그 학생의 지난 수업 기록(날짜 오름차순)입니다. "
        "①시제 엄수 — 전부 과거의 일이므로 오늘 일처럼 쓰지 말고, 언급 시 '지난 수업에서' 등 "
        "과거 표지 필수. 오늘 사실은 그 학생의 오늘 데이터만 근거로. "
        "②흐름이 보이면(극복·지속·변화) 한 문장 이내로 자연스럽게 연결 권장, 억지 연결 금지. "
        "③과거 수치(점수·페이지) 재인용 금지. "
        "④이력 문구들과 문장 시작 표현·구조·핵심 어휘가 겹치지 않게 새로 쓰고, "
        "학생 간에도 같은 상투 문구를 돌려쓰지 말 것 — 학생마다 관찰 각도와 문장 구조를 다르게.\n"
        "⭐ 하이라이트 항목이 있으면 가장 인상적인 표현으로 강조.\n\n"
        "⚠️ 코드블록(```)·머리말·맺음말 없이, '[' 로 시작해 ']' 로 끝나는 순수 JSON 배열만 출력:\n"
        '[{"cls":"반명","name":"이름","note":"특이사항"}, ...]\n\n'
        + (f"{custom_block}\n\n" if custom_block else "")
        + f"[학생데이터]\n{students_json}"
    )
    return prompt


# ── 멀티 엔진 API 허브 (직관적 선택형 분기) ───────────────────────────
class AIHTTPError(RuntimeError):
    def __init__(self, code, message):
        self.code = code
        super().__init__(message)


def _quota_message(response_text):
    """Summarize Google's structured quota failure without exposing raw API output."""
    try:
        error = json.loads(response_text).get("error", {})
    except (ValueError, AttributeError):
        return "Google 사용량 한도 초과(429) — AI Studio에서 프로젝트·모델 한도 확인", False
    violations = [v for d in error.get("details", []) if isinstance(d, dict)
                  and "QuotaFailure" in d.get("@type", "") for v in d.get("violations", [])
                  if isinstance(v, dict)]
    ids = " ".join(str(v.get("quotaId", "")) for v in violations).lower()
    metric = " ".join(str(v.get("quotaMetric", "")) for v in violations).lower()
    detail = str(error.get("message", "")).lower()
    zero_limit = bool(re.search(r"\blimit\s*:\s*0\b", detail))
    if "perday" in ids or "perday" in metric:
        unit = "일일"
    elif "perminute" in ids or "perminute" in metric:
        unit = "분당"
    else:
        unit = "사용량"
    if "token" in ids or "token" in metric:
        target = "토큰"
    elif "request" in ids or "request" in metric:
        target = "요청"
    else:
        target = ""
    label = f"{unit} {target} 한도".replace("  ", " ").strip()
    if zero_limit:
        return f"Google {label}가 0으로 설정됨(429) — 해당 프로젝트·모델의 무료/결제 등급 확인", True
    return f"Google {label} 초과(429) — AI Studio에서 프로젝트·모델 한도 확인", unit == "일일"


def validate_key(engine_type, api_key, model_settings=None):
    """Probe the exact selected model; server failures do not prove key validity."""
    if not (api_key or "").strip():
        return False, "키가 비어 있습니다"
    try:
        _call_ai_hub(engine_type, api_key.strip(), "안녕", max_tokens=64, retries=2,
                     model_settings=model_settings)
        return True, "✅ 유효 — 호출 성공"
    except AIHTTPError as e:
        code = e.code
        if code in (401, 403):
            return False, "❌ 인증 실패 — 키 값 또는 권한 확인"
        if code == 429:
            return False, "⚠️ " + str(e)
        if code == 503 and engine_type.strip().lower() == "gemini":
            try:
                model = resolve("gemini", model_settings)["model"]
                req = urllib.request.Request(
                    f"https://generativelanguage.googleapis.com/v1beta/models/{model}",
                    headers={"x-goog-api-key": api_key.strip()})
                with urllib.request.urlopen(req, timeout=20) as response:
                    info = json.loads(response.read().decode("utf-8"))
                if "generateContent" in info.get("supportedGenerationMethods", []):
                    return True, "⚠️ 키·모델 접근 확인. 생성 서버 503 과부하 — 생성은 나중에 재시도"
                return False, "❌ 모델이 generateContent를 지원하지 않습니다"
            except urllib.error.HTTPError as probe_error:
                if probe_error.code in (401, 403):
                    return False, "❌ 키 인증/모델 권한 오류 (모델 조회)"
                if probe_error.code == 404:
                    return False, "❌ 모델을 찾을 수 없습니다 (모델 조회)"
            except (urllib.error.URLError, OSError, ValueError, KeyError):
                pass
        if code in (500, 502, 503, 504):
            return False, f"⚠️ 생성 서버 HTTP {code} — 키 유효성 미확정, 잠시 후 재시도"
        if code == 404:
            return False, "❌ 모델 접근 불가 — 모델 ID·프로젝트 지원 여부 확인"
        if code == 400:
            return False, "❌ 요청 거부 — 모델·사고 옵션·키 형식 확인"
        return False, f"❌ API 오류 ({code})"
    except Exception as e:
        text = str(e).replace(api_key.strip(), "[REDACTED]")
        if "finishReason=MAX_TOKENS" in text:
            return True, "✅ 유효 — 호출 성공(검사 출력 제한)"
        return False, "❌ 실패: " + text[:100]


def _call_ai_hub(engine_type, api_key, prompt, max_tokens=300, temperature=0.5, system="",
                 retries=4, model_settings=None):
    """설정창에서 선택된 특정 AI 엔진 규격에 맞추어 통신을 처리합니다.
    retries: 일시 오류(429/5xx) 총 시도 횟수 — 키 검증 등 즉답 용도는 1."""
    engine_type = engine_type.strip().lower()
    selected = resolve(engine_type, model_settings)

    if engine_type == "claude":
        # claude-sonnet-5 이행(2026-07): ① temperature 등 샘플링 파라미터 미허용(400) —
        # 문구 다양화는 프롬프트(최근 발송 중복회피 블록·지침 14)로 대체.
        # ② thinking 생략 시 adaptive 기본 → 짧은 생성에 토큰·지연 낭비라 명시적 disabled.
        # ③ 신형 토크나이저(동일 텍스트 ~30% 토큰 증가) → max_tokens 1.3배 보정.
        url = "https://api.anthropic.com/v1/messages"
        headers = {
            "X-API-Key":         api_key,
            "Anthropic-Version": "2023-06-01",
            "Content-Type":      "application/json"
        }
        body = {
            "model":      selected["model"],
            "max_tokens":  int(max_tokens * 1.3),
            "thinking":   {"type": "disabled"},
            "messages":    [{"role": "user", "content": prompt}]
        }
        if system:
            body["system"] = [
                {"type": "text", "text": system, "cache_control": {"type": "ephemeral"}}
            ]

    elif engine_type == "openai":
        # 기본 OPENAI_MODEL=gpt-5.6-luna (2026-08 채택, gpt-4o-mini 공식 후속·GA·저가형):
        # - Chat Completions 엔드포인트 그대로 유지(Responses API 미전환) — 최소 변경으로
        #   안정성 확보, 스키마·엔드포인트 재작성 리스크 회피.
        # - gpt-5.6 계열은 max_tokens 대신 max_completion_tokens, temperature 미지원(제거).
        # - reasoning_effort="none": 짧은 리포트에 불필요한 추론 토큰·지연 방지
        #   (gemini thinkingLevel minimal·claude thinking disabled와 동일 취지).
        # - 실측 비교(8케이스×2회, 2026-08): 4o-mini 평균 129자(목표 100자 초과 잦음·상투구
        #   반복) vs luna 평균 91자(분량 안정·구체적 서술). 규칙 위반은 둘 다 0.
        url = "https://api.openai.com/v1/chat/completions"
        headers = {
            "Content-Type":  "application/json",
            "Authorization": f"Bearer {api_key}"
        }
        messages = []
        if system:
            messages.append({"role": "system", "content": system})
        messages.append({"role": "user", "content": prompt})
        body = {
            "model":                 selected["model"],
            "messages":              messages,
            "max_completion_tokens": max_tokens,
            "reasoning_effort":      "none",
        }

    elif engine_type == "gemini":
        # 2026-09-28: latest/Lite의 503과 2.5 신규 접근 제한을 실측.
        # latest는 장애 우회 라우터가 아닌 이동 별칭이므로 성공한 3.8 GA로 고정.
        # 3.8은 minimal을 거부하며 low/medium/high만 지원한다.
        # 400 thinking 교정 및 일시 오류 백오프는 유지한다.
        url = (f"https://generativelanguage.googleapis.com/v1beta/models/"
               f"{selected['model']}:generateContent")
        headers = {"Content-Type": "application/json", "x-goog-api-key": api_key}
        body = {
            "contents": [{"parts": [{"text": prompt}]}],
            "generationConfig": {
                "maxOutputTokens": int(max_tokens * 1.3),
                "temperature":     temperature,
                "thinkingConfig":  {"thinkingLevel": "low"},
            },
        }
        if system:
            body["system_instruction"] = {"parts": [{"text": system}]}

    else:
        raise ValueError(f"지원하지 않는 엔진 선택 유형: {engine_type}")
    
    # Explicit per-engine settings; omit means use the provider default.
    level = selected["thinking_level"]
    if engine_type == "gemini":
        gc = body["generationConfig"]
        gc.pop("thinkingConfig", None)
        if level != "omit":
            gc["thinkingConfig"] = {"thinkingLevel": level}
    elif engine_type == "claude":
        body.pop("thinking", None)
        if level != "omit":
            body["thinking"] = {"type": level}
    elif engine_type == "openai":
        body.pop("reasoning_effort", None)
        if level != "omit":
            body["reasoning_effort"] = level

    dprint("\n" + "="*60)
    dprint(f"[AI DEBUG] engine={engine_type}  max_tokens={max_tokens}  temp={temperature}")
    dprint(f"[AI DEBUG] URL: {url}")
    dprint(f"[AI DEBUG] PROMPT ↓\n{prompt}")
    dprint("="*60 + "\n")

    req = urllib.request.Request(
        url,
        data=json.dumps(body, ensure_ascii=False).encode('utf-8'),
        headers=headers,
        method='POST'
    )

    # 일시적 서버 오류(503 과부하·429 레이트·500/502/504) 백오프 재시도.
    # Gemini 무료티어는 503 "overloaded"가 잦아 재시도로 대부분 해소.
    _RETRY = {429, 500, 502, 503, 504}
    last_err = None
    _gem_stripped = False   # gemini 별칭 thinkingLevel 미지원 이동 대비 — 1회 무-thinking 재시도
    _n = max(1, int(retries))
    _attempt = 0
    while _attempt < _n:
        try:
            with urllib.request.urlopen(req, timeout=40) as r:
                resp = json.loads(r.read().decode('utf-8'))
            break
        except urllib.error.HTTPError as he:
            last_err = he
            try:
                error_body = he.read(16384).decode('utf-8', 'replace')
            except Exception:
                error_body = ''
            quota_message, long_limit = _quota_message(error_body) if he.code == 429 else (None, False)
            if he.code in _RETRY and not long_limit and _attempt < _n - 1:
                time.sleep(2 ** _attempt)   # 1·2·4초
                _attempt += 1
                continue
            # 404는 대개 모델/엔드포인트 없음(키가 해당 모델 권한 없음 포함) → 재시도 무의미.
            # gemini 별칭(flash-latest)이 thinkingLevel 미지원 모델로 이동한 경우:
            # 400 + 본문에 'thinking' 언급 → thinkingConfig 제거 후 1회 재시도(추가 시도 소비 없음).
            if (model_settings is None and engine_type == "gemini" and he.code == 400 and not _gem_stripped
                    and "thinking" in error_body.lower()):
                _gem_stripped = True
                body_dict = json.loads(req.data.decode('utf-8'))
                body_dict.get("generationConfig", {}).pop("thinkingConfig", None)
                req = urllib.request.Request(
                    url, data=json.dumps(body_dict, ensure_ascii=False).encode('utf-8'),
                    headers=headers, method='POST')
                continue   # _attempt 미증가 — 파라미터 교정 재시도 1회 보장
            if he.code == 404:
                hint = f"모델/엔드포인트를 찾을 수 없음 — 엔진({engine_type})·모델·API 키 권한 확인"
            elif he.code in (401, 403):
                hint = "API 키 인증/권한 오류 — 키 확인"
            elif he.code == 400:
                hint = "요청 형식 오류 — 모델명·파라미터 확인"
            elif he.code == 429:
                raise AIHTTPError(429, quota_message) from he
            else:
                hint = "API 오류"
            raise AIHTTPError(he.code, f"AI {he.code}: {hint}. {error_body[:400]}".replace(api_key, "[REDACTED]").strip()) from he
        except urllib.error.URLError as ue:   # 네트워크 일시 단절
            last_err = ue
            if _attempt < _n - 1:
                time.sleep(2 ** _attempt)
                _attempt += 1
                continue
            raise
    else:
        raise last_err

    # 엔진별 리턴 데이터 매핑 구조 분기 파싱
    if engine_type == "claude":
        return resp['content'][0]['text'].strip()
    elif engine_type == "gemini":
        cands = resp.get('candidates', [])
        if not cands:
            # safety filter 등으로 후보 없음
            raise RuntimeError(f"Gemini 빈 응답: {json.dumps(resp, ensure_ascii=False)[:300]}")
        # flash-latest(이동 별칭)가 parts 없는 후보를 줄 수 있음(thinking-only·MAX_TOKENS·안전필터).
        # 원시 KeyError 대신 finishReason 포함 명확한 메시지로 표면화.
        c0 = cands[0]
        parts = (c0.get('content') or {}).get('parts') or []
        texts = [p.get('text', '') for p in parts if p.get('text')]
        if not texts:
            fr = c0.get('finishReason', '?')
            raise RuntimeError(f"Gemini 텍스트 없음(finishReason={fr}) — 재시도 권장. "
                               f"{json.dumps(resp, ensure_ascii=False)[:200]}")
        return "".join(texts).strip()
    else:
        return resp['choices'][0]['message']['content'].strip()
