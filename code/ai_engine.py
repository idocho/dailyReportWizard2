"""
ai_engine.py — 멀티 LLM API 특이사항 생성 엔진 (Groq / Claude / GPT 선택 대응)
Crafted by IDO(idocho@kakao.com) · Powered by Gemini
"""
import json
import threading
import time
import urllib.request
import urllib.error

from constants import APP_VERSION, AI_COOLDOWN, TAGS
from firebase import fetch_obs_today, today_key
from storage import save_daily_cache


# ── 태그 key → 자연어 변환 테이블 ────────────────────────────────────
_CONDITION_TEXT = {
    "great":  "오늘 특히 집중력이 높고 활발한 날이었음",
    "good":   "평소처럼 성실하게 수업에 임함",
    "normal": "무난하게 수업에 참여함",
    "bad":    "컨디션이 다소 저조하거나 집중력이 흐트러진 날이었음",
}
_UNDERSTAND_TEXT = {
    "fast":     "설명 1회에 바로 이해하고 응용까지 진행함",
    "normal_u": "반복 설명 후 이해함",
    "slow":     "반복 설명에도 어려움이 있어 추가 지도가 필요한 상태",
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
}
_CAUTION_TEXT = {
    "sleepy":   "집중력 저하",
    "phone":    "수업 집중도 저하",
    "chat":     "수업 참여도 저하",
    "attitude": "수업 태도 개선 필요",
}
_EXTRA_TEXT = {
    "self_study":  "자율학습을 실시함",
    "weekly_test": "주간 테스트를 실시함",
    "retest":      "재시험을 실시함",
}


def _build_obs_context(obs: dict) -> str:
    """오늘 obs 태그 dict → 프롬프트용 자연어 블록."""
    if not obs:
        return ""

    lines = []

    cond = obs.get("condition")
    if cond and cond in _CONDITION_TEXT:
        lines.append(f"- 수업 컨디션: {_CONDITION_TEXT[cond]}")

    und = obs.get("understand")
    if und and und in _UNDERSTAND_TEXT:
        lines.append(f"- 이해 속도: {_UNDERSTAND_TEXT[und]}")

    for key in obs.get("understand_sub") or []:
        if key in _UNDERSTAND_SUB_TEXT:
            lines.append(f"- {_UNDERSTAND_SUB_TEXT[key]}")

    engage_notes = [_ENGAGE_TEXT[k] for k in (obs.get("engage") or []) if k in _ENGAGE_TEXT]
    if engage_notes:
        lines.append(f"- 참여 행동: {', '.join(engage_notes)}")

    caution_keys = [k for k in (obs.get("caution") or []) if k in _CAUTION_TEXT]
    if caution_keys:
        lines.append("- 오늘 전반적인 집중도가 평소보다 낮은 편이었음 (참고용, 직접 언급 자제)")

    extra_notes = [_EXTRA_TEXT[k] for k in (obs.get("extra") or []) if k in _EXTRA_TEXT]
    if extra_notes:
        lines.append(f"- 특수 이벤트: {', '.join(extra_notes)}")

    return "\n".join(lines)


def _base_conditions() -> str:
    """모든 AI 생성 호출에 공통으로 들어가는 조건 문자열."""
    return (
        "[작성 지침]\n"
        "1. 문체: ~했습니다 체로 통일 (했어요 혼용 금지). 학생 이름으로 시작.\n"
        "2. 금지: '어머님·학부모님' 호칭, 시스템 표현('미입력·데이터 없음' 등), "
        "제공된 데이터에 없는 사실 추가(할루시네이션) 절대 금지.\n"
        "3. 이벤트 반영: [수업 관찰 및 이벤트 정보]에 명시된 항목만 반영. "
        "데이터에 없는 자율학습·재시험·주간테스트 등은 언급하지 마세요.\n"
        "4. 주의 태그: 직접 지적 금지. '조금 피곤해 보였지만 이내 집중하여~' 수준으로 완곡하게.\n"
        "5. 결석: 데이터가 없으면 안부 인사와 다음 수업 기약 코멘트로 대체.\n"
        "6. 출력: 순수 텍스트만 (JSON·마크다운·따옴표 금지). 2~3문장, 100자 내외."
    )


# ── 단건 생성 프롬프트 ───────────────────────────────────────────────
def build_single_prompt(sheet, cls, name, textbooks, student_data, progress_data,
                        existing_note, obs):
    """단건 AI 생성용 프롬프트 조립 (이벤트 반영 최적화)."""
    lines = []
    for tb in textbooks:
        val = student_data.get((sheet, cls, name, tb), {}).get('value', '')
        if val:
            pd_val = progress_data.get((sheet, cls, tb), {})
            lines.append(
                f"- {tb}: 수행도={val}"
                + (f", 진도={pd_val['progress']}" if pd_val.get('progress') else "")
                + (f", 과제={pd_val['homework']}"  if pd_val.get('homework') else "")
            )
    context = "\n".join(lines) if lines else "수업 진행 완료"

    obs_block = _build_obs_context(obs)

    prompt = (
        "수학학원 교사가 학부모에게 보낼 데일리 리포트 특이사항을 작성합니다.\n"
        "아래 제공된 데이터만을 근거로 작성하고, 데이터에 없는 내용은 절대 추가하지 마세요.\n\n"
        f"[학생 이름]\n{name}\n\n"
        f"[수업 데이터]\n{context}\n\n"
    )
    if obs_block:
        prompt += f"[수업 관찰 및 이벤트 정보]\n{obs_block}\n\n"
    if existing_note:
        prompt += f"[기존 특이사항 참고]\n{existing_note}\n\n"

    prompt += f"{_base_conditions()}"
    return prompt


# ── 일괄 생성 프롬프트 ───────────────────────────────────────────────
def build_batch_prompt(targets):
    """일괄 AI 생성용 프롬프트 조립 (군더더기 제거 및 JSON 안정화)."""
    students_payload = []
    for t in targets:
        valid_data = []
        for tb, val in t["data"].items():
            if val and "미입력" not in str(val):
                valid_data.append(f"{tb}(수행도:{val})")
        
        entry = {
            "name":  t["name"],
            "cls":   t["cls"],
            "수업데이터": ", ".join(valid_data) if valid_data else "정상 수업 진행"
        }
        if t.get("existing"):
            entry["기존특이사항"] = t["existing"]
        obs_block = _build_obs_context(t.get("obs") or {})
        if obs_block:
            entry["수업관찰및이벤트"] = obs_block
        students_payload.append(entry)

    students_json = json.dumps(students_payload, ensure_ascii=False, indent=2)

    prompt = (
        "수학학원 교사가 학부모용 데일리 리포트 특이사항을 일괄 작성합니다.\n"
        "⚠️ 각 학생의 '수업관찰및이벤트' 필드에 명시된 항목만 반영하세요. "
        "필드에 없는 자율학습·재시험·주간테스트 등은 절대 언급하지 마세요.\n\n"
        f"{_base_conditions()}\n\n"
        "⚠️ 반드시 JSON 배열로만 응답 (다른 텍스트 금지):\n"
        '[{"cls":"반명","name":"이름","note":"특이사항"}, ...]\n\n'
        f"[학생데이터]\n{students_json}"
    )
    return prompt


# ── 멀티 엔진 API 허브 (직관적 선택형 분기) ───────────────────────────
def _call_ai_hub(engine_type, api_key, prompt, max_tokens=300, temperature=0.5):
    """설정창에서 선택된 특정 AI 엔진 규격에 맞추어 통신을 처리합니다."""
    engine_type = engine_type.strip().lower()

    if engine_type == "groq":
        url = "https://api.groq.com/openai/v1/chat/completions"
        headers = {
            "Content-Type":  "application/json",
            "Authorization": f"Bearer {api_key}",
            "User-Agent":    f"DailyReportWizard/{APP_VERSION.lstrip('v')}",
        }
        body = {
            "model":       "llama-3.1-8b-instant",  # 무료 최고 가성비 속도 최적화
            "messages":    [{"role": "user", "content": prompt}],
            "max_tokens":  max_tokens,
            "temperature": temperature
        }

    elif engine_type == "claude":
        url = "https://api.anthropic.com/v1/messages"
        headers = {
            "X-API-Key":         api_key,
            "Anthropic-Version": "2023-06-01",
            "Content-Type":      "application/json"
        }
        body = {
            "model":      "claude-sonnet-4-6",            # 최신 Sonnet
            "max_tokens":  max_tokens,
            "temperature": temperature,
            "messages":    [{"role": "user", "content": prompt}]
        }

    elif engine_type == "openai":
        url = "https://api.openai.com/v1/chat/completions"
        headers = {
            "Content-Type":  "application/json",
            "Authorization": f"Bearer {api_key}"
        }
        body = {
            "model":       "gpt-4o-mini",  # 비용 효율 범용
            "messages":    [{"role": "user", "content": prompt}],
            "max_tokens":  max_tokens,
            "temperature": temperature
        }
    else:
        raise ValueError(f"지원하지 않는 엔진 선택 유형: {engine_type}")

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
        remaining = max(0, AI_COOLDOWN - (time.time() - self._last_call))
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
        engine_type = self.app.cfg.get('ai_engine_type', 'groq').strip().lower()
        
        # UI에서 설정한 단일 통합 키 혹은 개별 키 저장값 연동
        api_key = self.app.cfg.get('ai_api_key', '').strip()
        
        # 하위 호환성 케어: 만약 기존 구형 단일 groq 키 필드가 있다면 백업 적용
        if not api_key and engine_type == 'groq':
            api_key = self.app.cfg.get('groq_api_key', '').strip()

        if not api_key:
            from tkinter import messagebox
            messagebox.showwarning("알림", f"설정에서 선택하신 {engine_type.upper()} API Key를 입력해 주세요.")
        
        return engine_type, api_key

    def _mark_called(self):
        self._last_call = time.time()
        self.app._ai_last_call = self._last_call

    # ── 단건 생성 실행 ────────────────────────────────────────────────
    def gen_single(self, sheet, cls, name, textbooks, note_txt, ai_btn=None):
        if not self._check_cooldown():
            return
        engine_type, api_key = self._get_engine_settings()
        if not api_key:
            return

        app = self.app

        existing = app.note_data.get((sheet, cls, name), {}).get('value', '').strip()
        obs = app.obs_data.get(f"{sheet}|{cls}|{name}", {}).get(today_key(), {})

        # 프롬프트 생성
        prompt = build_single_prompt(
            sheet, cls, name, textbooks,
            app.student_data, app.progress_data, existing, obs
        )

        note_txt.config(state='normal')
        note_txt.delete('1.0', 'end')
        note_txt.insert('1.0', '✨ AI 문장 생성 중...')
        if ai_btn:
            ai_btn.config(state='disabled', text="⏳ 생성 중...")

        def _call():
            try:
                # 허브 함수로 분기 처리 토스 (단건은 리스크가 적으므로 max_tokens=400 확보)
                text = _call_ai_hub(engine_type, api_key, prompt, max_tokens=400)
                note_key = (sheet, cls, name)
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
            if app._is_sub_teacher(sheet, cls):
                continue
            tbs = cls_data.get('textbooks', [])
            for stu in cls_data.get('students', []):
                name = stu['name']
                if app._student_status(sheet, cls, name) != 'ready':
                    continue
                
                # 유효 데이터 필터링 맵 구조 조립
                student_book_data = {}
                for tb in tbs:
                    val = app.student_data.get((sheet, cls, name, tb), {}).get('value', '')
                    if val:
                        student_book_data[tb] = val

                obs = app.obs_data.get(f"{sheet}|{cls}|{name}", {}).get(today_key(), {})
                targets.append({
                    "sheet":    sheet,
                    "cls":      cls,
                    "name":     name,
                    "data":     student_book_data,
                    "existing": app.note_data.get((sheet, cls, name), {}).get('value', '').strip(),
                    "obs":      obs,
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
                # 일괄 제어 처리를 위해 응답 최대 토큰 스케일링 확보
                raw = _call_ai_hub(engine_type, api_key, prompt, max_tokens=4096)
                clean = raw.replace('```json', '').replace('```', '').strip()
                parsed = json.loads(clean)

                updated = 0
                for item in parsed:
                    n = item.get('name', '').strip()
                    c = item.get('cls',  '').strip()
                    note_text = item.get('note', '').strip()
                    if not n or not note_text:
                        continue
                    app.note_data[(sheet, c, n)] = {'value': note_text}
                    updated += 1

                save_daily_cache(app.progress_data, app.student_data, app.note_data, app.force_data)

                def _ok(u=updated):
                    self._mark_called()
                    if app.cur_name:
                        app._render_student(app.cur_sheet, app.cur_cls, app.cur_name)
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
                remaining = max(0, AI_COOLDOWN - (time.time() - self._last_call))
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