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

from constants import APP_VERSION, AI_COOLDOWN_GROQ, AI_COOLDOWN_PAID, TAGS
from firebase import fetch_tags_today, today_key
from storage import save_daily_cache

def dprint(*args, **kwargs):
    """DEBUG_AI_PROMPT 플래그가 True일 때만 출력되는 디버그 프린트."""
    if DEBUG_AI_PROMPT:
        print(*args, **kwargs)

# ── 태그 key → 자연어 변환 테이블 ────────────────────────────────────
_CONDITION_TEXT = {
    "great":  "오늘 특히 집중력이 높고 활발한 날이었음",
    "good":   "평소처럼 성실하게 수업에 임함",
    "normal": "무난하게 수업에 참여함",
    "low":    "다소 활력이 부족하고 집중력이 흐트러진 편이었음",
    "bad":    "컨디션이 저조하고 집중력이 크게 흐트러진 날이었음",
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
_ENGAGE_TEXT = {
    "present":  "수업 중 발표에 적극 참여함",
    "question": "모르는 부분을 스스로 질문함",
    "help":     "친구의 이해를 도와주는 모습이 있었음",
    "preview":  "미리 예습하고 수업에 참여함",
    "error_fix": "풀이 오류를 스스로 발견하고 정정함",
}
_CAUTION_TEXT = {
    "sleepy":   "수업 중 졸음 증상",
    "chat":     "잡담으로 수업 참여도 저하",
    "attitude": "수업 태도 개선 필요",
    "late":     "지각",
}
_EXTRA_TEXT = {
    "self_study":  "자율학습을 실시함",
    "weekly_test": "주간 테스트를 실시함",
    "retest":      "재시험을 실시함",
}
_HIGHLIGHT_TEXT = {
    "perfect":  "오늘 만점 또는 완벽에 가까운 풀이 성취",
    "improved": "지난 수업 대비 눈에 띄게 향상된 모습",
    "mastered": "오늘 다룬 개념을 완전히 습득함",
    "effort":   "어려운 문제에도 끝까지 포기하지 않는 집념을 보임",
}


def _merge_student_tags(tag_data: dict, sheet: str, cls: str, name: str, textbooks: list) -> dict:
    """v2.0: tag_data = {nameKey: {subject: {date: {tags}}}}"""
    today = today_key()
    merged = {}
    for tb in textbooks:
        # v2.0 구조: tag_data[nameKey][subject][date]
        tb_tags = tag_data.get(name, {}).get(tb, {}).get(today, {})
        if not tb_tags:
            continue
        for field in ('condition', 'understand', 'highlight'):
            if field not in merged and field in tb_tags:
                merged[field] = tb_tags[field]
        for field in ('understand_sub', 'engage', 'caution', 'extra'):
            if field in tb_tags:
                vals = tb_tags[field]
                if isinstance(vals, str):
                    vals = [vals] if vals else []
                existing = merged.get(field, [])
                merged[field] = list(dict.fromkeys(existing + vals))
    return merged


def _build_tags_context(tags: dict) -> str:
    """오늘 수업 관찰 태그 dict → 프롬프트용 자연어 블록."""
    if not tags:
        return ""

    lines = []

    cond = tags.get("condition")
    if cond and cond in _CONDITION_TEXT:
        lines.append(f"- 수업 컨디션: {_CONDITION_TEXT[cond]}")

    und = tags.get("understand")
    if und and und in _UNDERSTAND_TEXT:
        lines.append(f"- 이해 속도: {_UNDERSTAND_TEXT[und]}")

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
        "첫 문장은 학생 이름('OO 학생은')으로 시작하지 않는 것을 기본 원칙으로 함.\n"
        "수업 내용·성취·이해도·관찰된 행동 중심으로 자연스럽게 시작.\n"
        "학생 이름을 첫 주어로 사용하는 표현은 예외 상황 외 금지.\n"
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
        "10. 출력: 순수 텍스트만 (JSON·마크다운·따옴표 금지). 2~3문장, 100자 내외."
    )


# ── 단건 생성 프롬프트 ───────────────────────────────────────────────
def build_single_prompt(sheet, cls, name, textbooks, student_data, progress_data,
                        existing_note, tags, tb_grade=None):
    """단건 AI 생성용 프롬프트 조립 (v2.0 키 구조)."""
    _tg = tb_grade or {}
    lines = []
    for tb in textbooks:
        # v2.0: student_data 키 = (classId, nameKey, subject)
        val = student_data.get((cls, name, tb), {}).get('value', '')
        if val:
            gs = _tg.get(tb, '')
            tb_lbl = f"{gs} {tb}".strip() if gs else tb
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
        "[문체 참고 예시 — 내용은 아래 학생 데이터로 새로 작성]\n"
        "예1) \"오늘 이차함수 단원에서 막혔던 개념을 반복 설명 후 이해했습니다. 틀린 문항을 스스로 재풀이하며 오답을 정리하는 모습이 인상적이었습니다.\"\n"
        "예2) \"주간 테스트를 실시했으며, 오늘은 다소 피곤해 보이는 날이었지만 끝까지 집중해서 임했습니다.\"\n"
        "예3) \"예습 내용을 바탕으로 설명을 빠르게 이해하고 응용 문제까지 도전했습니다. 오늘 다룬 개념을 완전히 자기 것으로 만든 하루였습니다.\"\n\n"
        f"[학생 이름]\n{name}\n\n"
        f"[수업 데이터]\n{context}\n\n"
    )
    if tags_block:
        prompt += f"[수업 관찰 및 이벤트 정보]\n{tags_block}\n\n"
    if existing_note:
        prompt += (
            "[직접 작성 메모 — 반드시 반영]\n"
            f"{existing_note}\n"
            "위 메모는 교사가 직접 입력한 핵심 전달 사항입니다. "
            "최종 특이사항에 빠뜨리지 말고 자연스럽게 포함하세요.\n\n"
        )

    return prompt


# ── 일괄 생성 프롬프트 ───────────────────────────────────────────────
def build_batch_prompt(targets):
    """일괄 AI 생성용 프롬프트 조립 (군더더기 제거 및 JSON 안정화)."""
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
        students_payload.append(entry)

    students_json = json.dumps(students_payload, ensure_ascii=False, indent=2)

    prompt = (
        "수학학원 교사가 학부모용 데일리 리포트 특이사항을 일괄 작성합니다.\n"
        "⚠️ 각 학생의 '수업관찰및이벤트' 필드에 명시된 항목만 반영하세요. "
        "필드에 없는 자율학습·재시험·주간테스트 등은 절대 언급하지 마세요.\n\n"
        "[문체 기준] 2~3문장 100자 내외. 학부모가 읽기 편한 따뜻한 어조. "
        "학생 이름 또는 수업 내용으로 자연스럽게 시작 (매번 이름으로만 시작하지 말 것). "
        "'졸음·잡담·태도불량' 직접 단어 사용 금지 — 완곡하게 표현.\n"
        "자율학습·주간 테스트·재시험 등 별도 전달 이벤트는 다른 수업 묘사와 섞지 말고 "
        "가능하면 독립 문장으로 명확히 작성하세요.\n"
        "각 학생의 '직접작성메모_반드시반영' 필드는 교사가 직접 입력한 핵심 전달 사항이므로 "
        "최종 note에 반드시 자연스럽게 포함하세요.\n"
        "⭐ 하이라이트 항목이 있으면 가장 인상적인 표현으로 강조.\n\n"
        "⚠️ 반드시 JSON 배열로만 응답 (다른 텍스트 금지):\n"
        '[{"cls":"반명","name":"이름","note":"특이사항"}, ...]\n\n'
        f"[학생데이터]\n{students_json}"
    )
    return prompt


# ── 멀티 엔진 API 허브 (직관적 선택형 분기) ───────────────────────────
def _call_ai_hub(engine_type, api_key, prompt, max_tokens=300, temperature=0.5, system=""):
    """설정창에서 선택된 특정 AI 엔진 규격에 맞추어 통신을 처리합니다."""
    engine_type = engine_type.strip().lower()

    if engine_type == "groq":
        url = "https://api.groq.com/openai/v1/chat/completions"
        headers = {
            "Content-Type":  "application/json",
            "Authorization": f"Bearer {api_key}",
            "User-Agent":    f"DailyReportWizard/{APP_VERSION.lstrip('v')}",
        }
        messages = []
        if system:
            messages.append({"role": "system", "content": system})
        messages.append({"role": "user", "content": prompt})
        body = {
            "model":       "qwen/qwen3-32b",
            "messages":    messages,
            "max_tokens":  max_tokens,
            "temperature": temperature,
            "reasoning_effort": "none"
        }

    elif engine_type == "claude":
        url = "https://api.anthropic.com/v1/messages"
        headers = {
            "X-API-Key":         api_key,
            "Anthropic-Version": "2023-06-01",
            "Content-Type":      "application/json"
        }
        body = {
            "model":      "claude-sonnet-4-6",
            "max_tokens":  max_tokens,
            "temperature": temperature,
            "messages":    [{"role": "user", "content": prompt}]
        }
        if system:
            body["system"] = system

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

    with urllib.request.urlopen(req, timeout=40) as r:
        resp = json.loads(r.read().decode('utf-8'))

    # 엔진별 리턴 데이터 매핑 구조 분기 파싱
    if engine_type == "claude":
        return resp['content'][0]['text'].strip()
    else:
        return resp['choices'][0]['message']['content'].strip()


# ── App 비즈니스 로직 및 인터페이스 ──────────────────────────────────
class AiEngine:
    def __init__(self, app):
        self.app        = app
        self._last_call = 0.0

    def _check_cooldown(self):
        engine_type = self.app.config.get('ai_engine_type', 'groq').strip().lower()
        cooldown = AI_COOLDOWN_GROQ if engine_type == 'groq' else AI_COOLDOWN_PAID
        remaining = max(0, cooldown - (time.time() - self._last_call))
        if remaining > 0:
            from tkinter import messagebox
            messagebox.showwarning(
                "잠시 대기",
                f"API 과부하 방지를 위해 {int(remaining)}초 후에 사용할 수 있습니다."
            )
            return False
        return True

    def _get_engine_settings(self):
        """App 설정 딕셔너리로부터 활성화된 엔진 타입과 해당 Key를 리턴합니다.
        (설정 키 명칭은 사용 중인 app.cfg 규격에 부합하게 맞추어 조율하세요)
        """
        engine_type = self.app.config.get('ai_engine_type', 'groq').strip().lower()
        
        # UI에서 설정한 단일 통합 키 혹은 개별 키 저장값 연동
        api_key = self.app.config.get(f'{engine_type}_api_key', '').strip()
        if not api_key:
            api_key = self.app.config.get('ai_api_key', '').strip()

        if not api_key:
            from tkinter import messagebox
            messagebox.showwarning("알림", f"설정에서 선택하신 {engine_type.upper()} API Key를 입력해 주세요.")
        
        return engine_type, api_key

    def _mark_called(self):
        self._last_call = time.time()
        self.app._ai_last_call = self._last_call

    # ── 단건 생성 실행 ────────────────────────────────────────────────
    def gen_single(self, sheet, cls, name, textbooks, note_txt, ai_btn=None, tb_grade=None):
        if not self._check_cooldown():
            return
        engine_type, api_key = self._get_engine_settings()
        if not api_key:
            return

        app = self.app

        # v2.0: note_data 키 = (classId, nameKey)
        note_key = (cls, name)
        try:
            raw_note = note_txt.get('1.0', 'end').rstrip('\n')
            existing_note = raw_note.encode('utf-16', 'surrogatepass').decode('utf-16')
            app.note_data[note_key] = {'value': existing_note}
            save_daily_cache(app.progress_data, app.student_data, app.note_data, app.force_data)
        except Exception:
            existing_note = app.note_data.get(note_key, {}).get('value', '')
        existing = existing_note.strip()
        tags = _merge_student_tags(app.tag_data, sheet, cls, name, textbooks)

        if DEBUG_AI_PROMPT:
            print(f"\n[SINGLE] student={name}  cls={cls}  today={today_key()}")
            print(f"[SINGLE] tags_today={tags if tags else '(없음)'}")
            print(f"[SINGLE] existing_note={existing if existing else '(없음)'}")

        # 프롬프트 생성
        prompt = build_single_prompt(
            sheet, cls, name, textbooks,
            app.student_data, app.progress_data, existing, tags,
            tb_grade=tb_grade
        )

        note_txt.config(state='normal')
        note_txt.delete('1.0', 'end')
        note_txt.insert('1.0', '✨ AI 문장 생성 중...')
        if ai_btn:
            ai_btn.config(state='disabled', text="⏳ 생성 중...")

        def _call():
            try:
                text = _call_ai_hub(engine_type, api_key, prompt,
                                    max_tokens=400, temperature=0.75,
                                    system=_base_conditions())
                app.note_data[note_key] = {'value': text}
                save_daily_cache(app.progress_data, app.student_data, app.note_data, app.force_data)

                def _ok(t=text):
                    note_txt.config(state='normal')
                    note_txt.delete('1.0', 'end')
                    note_txt.insert('1.0', t)
                    app._update_preview()
                    self._mark_called()
                    if ai_btn:
                        self._start_cooldown_tick(ai_btn)
                app.root.after(0, _ok)

            except urllib.error.HTTPError as e:
                msg = "API 한도를 초과했습니다(429). 잠시 후 다시 시도해 주세요." if e.code == 429 else f"HTTP {e.code}: {e.reason}"
                app.root.after(0, lambda m=msg: self._show_err(note_txt, ai_btn, m))
            except Exception as e:
                app.root.after(0, lambda m=str(e): self._show_err(note_txt, ai_btn, m))

        threading.Thread(target=_call, daemon=True).start()

    # ── 일괄 생성 실행 ────────────────────────────────────────────────
    def gen_all(self, sheet):
        from tkinter import messagebox

        if not self._check_cooldown():
            return
        engine_type, api_key = self._get_engine_settings()
        if not api_key:
            return

        app = self.app

        targets = []
        for cls, cls_data in app._my_classes(sheet):
            if app._is_sub_teacher(cls):
                continue
            # v2.0: 과목은 courses 키, 학생은 all_students에서 필터
            courses  = cls_data.get('courses', {})
            tbs      = list(courses.keys())
            tb_grade = {s: courses[s].get('curriculum', '') for s in tbs}
            class_students = [
                (nk, app.all_students[nk].get('name', nk))
                for nk, v in app.all_students.items()
                if v.get('class') == cls
            ]
            for nameKey, display_name in class_students:
                if app._student_status(cls, nameKey) != 'ready':
                    continue

                student_book_data = {}
                for tb in tbs:
                    # v2.0: student_data 키 = (classId, nameKey, subject)
                    val = app.student_data.get((cls, nameKey, tb), {}).get('value', '')
                    if val:
                        gs = tb_grade.get(tb, '')
                        key = f"{gs} {tb}".strip() if gs else tb
                        student_book_data[key] = val

                tags = _merge_student_tags(app.tag_data, sheet, cls, nameKey, tbs)
                if DEBUG_AI_PROMPT:
                    print(f"[BATCH] {display_name}({cls})  tags={tags if tags else '(없음)'}")
                progress_book_data = {}
                for _tb in tbs:
                    _gs = tb_grade.get(_tb, '')
                    _key = f"{_gs} {_tb}".strip() if _gs else _tb
                    # v2.0: progress_data 키 = (classId, subject)
                    _pd = app.progress_data.get((cls, _tb), {})
                    if _pd.get('progress') or _pd.get('homework'):
                        progress_book_data[_key] = _pd
                targets.append({
                    "sheet":    sheet,
                    "cls":      cls,
                    "name":     display_name,
                    "data":     student_book_data,
                    "progress": progress_book_data,
                    # v2.0: note_data 키 = (classId, nameKey)
                    "existing": app.note_data.get((cls, nameKey), {}).get('value', '').strip(),
                    "tags":     tags,
                })

        if not targets:
            messagebox.showinfo("알림", "AI 생성 대상(STATUS_READY) 학생이 없습니다.")
            return

        if not messagebox.askyesno(
            "전체 일괄 생성",
            f"선택한 엔진: {engine_type.upper()}\n대 상 인 원: {len(targets)}명\n\n특이사항을 일괄 생성하시겠습니까?"
        ):
            return

        prompt = build_batch_prompt(targets)

        def _call():
            try:
                raw = _call_ai_hub(engine_type, api_key, prompt,
                                   max_tokens=4096, temperature=0.5,
                                   system="")
                clean = raw.replace('```json', '').replace('```', '').strip()
                parsed = json.loads(clean)

                # display_name → nameKey 역조회 맵
                name_to_key = {
                    v.get('name', nk): nk
                    for nk, v in app.all_students.items()
                }
                updated = 0
                for item in parsed:
                    display_n = item.get('name', '').strip()
                    c         = item.get('cls',  '').strip()
                    note_text = item.get('note', '').strip()
                    if not display_n or not note_text:
                        continue
                    # v2.0: note_data 키 = (classId, nameKey)
                    nk = name_to_key.get(display_n, display_n)
                    app.note_data[(c, nk)] = {'value': note_text}
                    updated += 1

                save_daily_cache(app.progress_data, app.student_data, app.note_data, app.force_data)

                def _ok(u=updated):
                    self._mark_called()
                    if app.cur_name:
                        app._render_student(app.activeGroup, app.cur_cls, app.cur_name)
                    messagebox.showinfo("일괄 AI 생성 완료", f"{u}명의 특이사항 작성이 완료되었습니다.")
                app.root.after(0, _ok)

            except urllib.error.HTTPError as e:
                msg = "API 한도를 초과했습니다(429). 잠시 후 다시 시도해 주세요." if e.code == 429 else f"HTTP {e.code}: {e.reason}"
                app.root.after(0, lambda m=msg: self._show_batch_err(m))
            except Exception as e:
                app.root.after(0, lambda m=str(e): self._show_batch_err(m))

        threading.Thread(target=_call, daemon=True).start()
        messagebox.showinfo("일괄 AI 생성 진행", f"{len(targets)}명 생성 중입니다...\n완료 알림을 기다려 주세요.")

    def _start_cooldown_tick(self, btn):
        def _tick():
            try:
                if not btn.winfo_exists():
                    return
                engine_type = self.app.config.get('ai_engine_type', 'groq').strip().lower()
                cooldown = AI_COOLDOWN_GROQ if engine_type == 'groq' else AI_COOLDOWN_PAID
                remaining = max(0, cooldown - (time.time() - self._last_call))        
                if remaining > 0:
                    btn.config(state='disabled', text=f"⏳ {int(remaining)}s")
                    self.app.root.after(1000, _tick)
                else:
                    btn.config(state='normal', text="✨ AI생성")
            except Exception:
                pass
        _tick()

    def _show_err(self, note_txt, ai_btn, msg):
        from tkinter import messagebox
        try:
            note_txt.config(state='normal')
            note_txt.delete('1.0', 'end')
            note_txt.insert('1.0', '(생성 실패)')
        except Exception:
            pass
        if ai_btn:
            try:
                ai_btn.config(state='normal', text="✨ AI생성")
            except Exception:
                pass
        root = self.app.root
        root.lift()
        root.attributes('-topmost', True)
        messagebox.showerror("AI 생성 오류", msg, parent=root)
        root.attributes('-topmost', False)

    def _show_batch_err(self, msg):
        from tkinter import messagebox
        root = self.app.root
        root.lift()
        root.attributes('-topmost', True)
        messagebox.showerror("AI 생성 오류", msg, parent=root)
        root.attributes('-topmost', False)
