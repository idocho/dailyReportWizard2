"""
ai_engine.py — 멀티 LLM API 특이사항 생성 엔진 (Groq / Claude / GPT 선택 대응)
Crafted by IDO(idocho@kakao.com) · Powered by Gemini
"""
import json
import threading
import time
import urllib.request
import urllib.error

# 외부(main.py)에서 주입 가능한 디버그 플래그 (기본: 비활성)
DEBUG_AI_PROMPT: bool = False

from constants import GEMINI_MODEL, grade_label
import ai_style

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
    assign_extra = [t for t in (tags.get("assign_tags") or []) if t]
    if assign_extra:
        lines.append("- 과제 관련 특이사항: " + ", ".join(assign_extra))

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


def _base_conditions() -> str:
    """모든 AI 생성 호출에 공통으로 들어가는 조건 문자열."""
    return (
        "[작성 지침]\n"
        "1. 문체: ~했습니다 체로 통일 (했어요 혼용 금지).\n"
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
        "9. 결석: 데이터가 없으면 안부 인사와 다음 수업 기약 코멘트로 대체.\n"
        "10. 출력: 순수 텍스트만 (JSON·마크다운·따옴표 금지). 2~3문장, 100자 내외.\n"
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
        "매일 다른 각도로 서술하세요. [최근 발송 특이사항] 블록이 있으면 그 문구들과 "
        "겹치지 않는 것이 최우선입니다."
    )


# ── 단건 생성 프롬프트 ───────────────────────────────────────────────
_DEFAULT_STYLE_BLOCK = (
    "[문체 참고 예시 — 내용은 아래 학생 데이터로 새로 작성]\n"
    "예1) \"오늘 이차함수 단원에서 막혔던 개념을 반복 설명 후 이해했습니다. 틀린 문항을 스스로 재풀이하며 오답을 정리하는 모습이 인상적이었습니다.\"\n"
    "예2) \"주간 테스트를 실시했으며, 오늘은 다소 피곤해 보이는 날이었지만 끝까지 집중해서 임했습니다.\"\n"
    "예3) \"예습 내용을 바탕으로 설명을 빠르게 이해하고 응용 문제까지 도전했습니다. 오늘 다룬 개념을 완전히 자기 것으로 만든 하루였습니다.\""
)


def _recent_notes_block(recent_notes):
    """학생별 최근 발송 특이사항 [(date, note), ...] → 중복회피 프롬프트 블록.

    같은 태그 반복 → 매일 비슷한 문구가 나가는 문제의 핵심 대응: 실제로 학부모에게
    최근 발송된 문구를 보여주고 '이것과 다르게' 쓰도록 강제. 노트는 토큰 절약 위해 절단.
    """
    rows = [(d, (n or "").strip()) for d, n in (recent_notes or []) if (n or "").strip()]
    if not rows:
        return ""
    lines = "\n".join(f"- {d}: \"{n[:160]}\"" for d, n in rows[:3])
    return (
        "[최근 발송 특이사항 — 중복 회피용, 사실은 위 데이터만 사용]\n"
        f"{lines}\n"
        "위 문구들과 문장 시작 표현·문장 구조·핵심 어휘가 겹치지 않게 새로 작성하세요. "
        "같은 내용이라도 다른 관찰 각도(구체 행동·성취 과정·변화 추이)로 서술해야 합니다.\n\n"
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
    context = "\n".join(lines) if lines else "수업 진행 완료"

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
            "수업데이터": ", ".join(valid_data) if valid_data else "정상 수업 진행"
        }
        if t.get("existing"):
            entry["직접작성메모_반드시반영"] = t["existing"]
        tags_block = _build_tags_context(t.get("tags") or {})
        if tags_block:
            entry["수업관찰및이벤트"] = tags_block
        recent = [(n or "").strip()[:160] for _, n in (t.get("recent") or [])[:3]
                  if (n or "").strip()]
        if recent:
            entry["최근발송문구_표현중복금지"] = recent
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
        "'최근발송문구_표현중복금지' 필드가 있으면 그 문구들과 문장 시작 표현·구조·핵심 어휘가 "
        "겹치지 않게 새로 쓰고, 학생 간에도 서로 같은 상투 문구를 돌려쓰지 마세요 — "
        "학생마다 관찰 각도와 문장 구조를 다르게.\n"
        "⭐ 하이라이트 항목이 있으면 가장 인상적인 표현으로 강조.\n\n"
        "⚠️ 코드블록(```)·머리말·맺음말 없이, '[' 로 시작해 ']' 로 끝나는 순수 JSON 배열만 출력:\n"
        '[{"cls":"반명","name":"이름","note":"특이사항"}, ...]\n\n'
        + (f"{custom_block}\n\n" if custom_block else "")
        + f"[학생데이터]\n{students_json}"
    )
    return prompt


# ── 멀티 엔진 API 허브 (직관적 선택형 분기) ───────────────────────────
def _call_ai_hub(engine_type, api_key, prompt, max_tokens=300, temperature=0.5, system=""):
    """설정창에서 선택된 특정 AI 엔진 규격에 맞추어 통신을 처리합니다."""
    engine_type = engine_type.strip().lower()

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
            "model":      "claude-sonnet-5",
            "max_tokens":  int(max_tokens * 1.3),
            "thinking":   {"type": "disabled"},
            "messages":    [{"role": "user", "content": prompt}]
        }
        if system:
            body["system"] = [
                {"type": "text", "text": system, "cache_control": {"type": "ephemeral"}}
            ]

    elif engine_type == "openai":
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
            "model":       "gpt-4o-mini",
            "messages":    messages,
            "max_tokens":  max_tokens,
            "temperature": temperature
        }

    elif engine_type == "gemini":
        # 무료 티어(3.5-flash: 15RPM/1500RPD). key는 헤더 아닌 쿼리파람.
        # gemini-3.x 이행(2026-07): thinkingBudget(2.5 구파라미터)→thinkingLevel 대체.
        # 3.x는 thinking 완전 off 불가(최저 minimal) → 짧은 생성엔 minimal 고정,
        # thinking 토큰이 maxOutputTokens를 잠식하므로 1.3배 보정(출력 잘림 방지).
        url = (f"https://generativelanguage.googleapis.com/v1beta/models/"
               f"{GEMINI_MODEL}:generateContent?key={api_key}")
        headers = {"Content-Type": "application/json"}
        body = {
            "contents": [{"parts": [{"text": prompt}]}],
            "generationConfig": {
                "maxOutputTokens": int(max_tokens * 1.3),
                "temperature":     temperature,
                "thinkingConfig":  {"thinkingLevel": "minimal"},
            },
        }
        if system:
            body["system_instruction"] = {"parts": [{"text": system}]}

    else:
        raise ValueError(f"지원하지 않는 엔진 선택 유형: {engine_type}")
    
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
    for _attempt in range(4):
        try:
            with urllib.request.urlopen(req, timeout=40) as r:
                resp = json.loads(r.read().decode('utf-8'))
            break
        except urllib.error.HTTPError as he:
            last_err = he
            if he.code in _RETRY and _attempt < 3:
                time.sleep(2 ** _attempt)   # 1·2·4초
                continue
            # 비재시도 오류(404·400·401·403 등) — API 에러 본문을 읽어 원인 명확화.
            # 404는 대개 모델/엔드포인트 없음(키가 해당 모델 권한 없음 포함) → 재시도 무의미, 설정 안내.
            try:
                body = he.read().decode('utf-8', 'replace')[:400]
            except Exception:
                body = ''
            if he.code == 404:
                hint = f"모델/엔드포인트를 찾을 수 없음 — 엔진({engine_type})·모델·API 키 권한 확인"
            elif he.code in (401, 403):
                hint = "API 키 인증/권한 오류 — 키 확인"
            elif he.code == 400:
                hint = "요청 형식 오류 — 모델명·파라미터 확인"
            else:
                hint = "API 오류"
            raise RuntimeError(f"AI {he.code}: {hint}. {body}".strip()) from he
        except urllib.error.URLError as ue:   # 네트워크 일시 단절
            last_err = ue
            if _attempt < 3:
                time.sleep(2 ** _attempt)
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
        return cands[0]['content']['parts'][0]['text'].strip()
    else:
        return resp['choices'][0]['message']['content'].strip()
