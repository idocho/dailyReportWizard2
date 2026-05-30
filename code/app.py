"""
app.py — DailyReportWizard 메인 App 클래스
Crafted by IDO(idocho@kakao.com) · Powered by Claude AI

분리된 모듈:
  constants  — 전역 상수·태그 정의
  storage    — 설정·캐시 파일 I/O
  firebase   — Firebase REST CRUD, obs 로드
  ai_engine  — AI 특이사항 생성 (수업 관찰 태그 주입 포함)
  message    — 메시지 조립 유틸
"""
import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import json, os, sys, time, threading, datetime, urllib.request, urllib.error, urllib.parse

try:
    import pyautogui, pyperclip  # type: ignore
    AUTOMATION = True
except ImportError:
    AUTOMATION = False

# ── UI 헬퍼 (App 전역) ───────────────────────────────────────────────
def make_scroll_frame(parent, bg=None):
    """스크롤 가능한 캔버스+프레임 조합 반환 → (canvas, inner_frame)."""
    from constants import BG as _BG
    if bg is None:
        bg = _BG
    canvas = tk.Canvas(parent, bg=bg, highlightthickness=0)
    vsb    = ttk.Scrollbar(parent, orient='vertical', command=canvas.yview)
    inner  = tk.Frame(canvas, bg=bg)
    inner.bind('<Configure>',
        lambda e: canvas.configure(scrollregion=canvas.bbox('all')))
    win_id = canvas.create_window((0, 0), window=inner, anchor='nw')
    canvas.bind('<Configure>',
        lambda e: canvas.itemconfig(win_id, width=e.width))
    canvas.configure(yscrollcommand=vsb.set)
    vsb.pack(side='right', fill='y')
    canvas.pack(side='left', fill='both', expand=True)
    canvas.bind('<Enter>',
        lambda e: canvas.bind_all('<MouseWheel>',
            lambda ev: canvas.yview_scroll(-1 * (ev.delta // 120), 'units')))
    canvas.bind('<Leave>', lambda e: canvas.unbind_all('<MouseWheel>'))
    return canvas, inner


from constants import (
    APP_TITLE, APP_VERSION, APP_CREDIT, AI_COOLDOWNS, AI_COOLDOWN_PAID,
    AI_ENGINE_ORDER, AI_ENGINE_LABELS,
    BG, PANEL, DARK, DARK2, ACCENT, INDIGO, INDIGO_L,
    GREEN, YELLOW, GRAY, BORDER, TEXT, SUBTEXT, BLUE,
    STATUS_EMPTY, STATUS_PARTIAL, STATUS_READY, DOT_COLOR,
    FT, FB, FS, FE, _MOD,
    ASSIGN_GRADE_LABELS, grade_label,
)
from storage  import (load_config, save_config, has_students,
                      save_daily_cache, load_daily_cache, set_runtime_cwd, RUNTIME_DIR)
from firebase import firebase_get, firebase_put, firebase_patch, fetch_tags, today_key
from ai_engine import AiEngine
from message   import today_str, get_room, nickname_suffix, build_message

class App:
    def __init__(self, root):
        self.root = root
        self.root.title(f"{APP_TITLE}  {APP_VERSION}")
        self.root.configure(bg=BG)
        self.root.geometry("1100x780")
        self.root.minsize(920, 680)
        self.root.resizable(True, True)

        self.config    = load_config()
        self.date_str  = today_str()
        # v3.0: 학생 수행도·특이사항은 웹에서 입력 → Firebase 가져오기로만 로드
        self.progress_data, _, _, _ = load_daily_cache()  # 진도/과제 캐시만 복원
        self.student_data = {}   # Firebase input/ 로드 시 채워짐
        self.note_data    = {}   # Firebase input/ 로드 시 채워짐
        self.force_data   = {}   # (classId, nameKey) → bool 강제완료 플래그
        self.tag_data     = {}   # Firebase obs/ 노드에서 로드하는 수업 관찰 태그
        self.all_students = {}   # Firebase students/ 전체 {nameKey: {name, class}}
        self.all_classes  = {}   # Firebase classes/ 전체 {classId: {group, courses/...}}
        self.status_w  = {}   # (classId, nameKey) → (canvas, oval_id)
        self.s_btn_map = {}   # (classId, nameKey) → tk.Button
        # (group, classId) -> bool (True if folded/collapsed)
        self.cls_fold_state = {}
        # (group, classId) -> frame containing student rows (for show/hide)
        self.cls_container = {}
        # 기본: 모든 학급을 접힌 상태로 시작
        for classId in self.all_classes.keys():
            grp = self.all_classes[classId].get('group', '')
            self.cls_fold_state[(grp, classId)] = True
        self.activeGroup = 'M'
        self.cur_cls   = None   # classId
        self.cur_name  = None   # nameKey
        self._ai_last_call = 0.0       # 하위 호환용 (AiEngine이 갱신)
        self.ai = AiEngine(self)       # AI 생성 엔진

        self._build_header()
        self._build_sheet_bar()
        self._build_panels()
        self._build_statusbar()
        self._build_footer()
        self._switch_sheet('M')

        # Firebase 미설정 시 설정 안내
        if not self.config.get('firebase_url') or not self.config.get('firebase_path'):
            self.root.after(300, self._prompt_first_run)
        else:
            # 공용 교재/학급 목록은 Firebase students/+classes를 단일 원본으로 사용
            self.root.after(300, self._sync_shared_sheets_from_firebase)

    def _sync_shared_sheets_from_firebase(self):
        """시작 시 Firebase students/ + classes/ + config/ 동기화."""
        try:
            config_data = firebase_get(self.config, "config") or {}

            # 학생 명단 및 학급 구조 (v2.0 스키마)
            fetched_students = firebase_get(self.config, "students") or {}
            fetched_classes  = firebase_get(self.config, "classes") or {}
            if isinstance(fetched_students, dict):
                self.all_students = fetched_students
            if isinstance(fetched_classes, dict):
                self.all_classes = fetched_classes

            # 강사 assignments — instructor_id 있으면 Firebase 값으로 덮어쓰기
            instructor_id = self.config.get("instructor_id", "")
            if instructor_id:
                instr = config_data.get("instructors", {}).get(instructor_id)
                if instr is not None:
                    asgn = instr.get("assignments", [])
                    if isinstance(asgn, list):
                        self.config["instructor_assignments"] = asgn
                    elif isinstance(asgn, dict):
                        self.config["instructor_assignments"] = list(asgn.values())
                    else:
                        self.config["instructor_assignments"] = []
                else:
                    # Firebase에 강사 없음 → 빈 배열로 강제
                    self.config["instructor_assignments"] = []

            save_config(self.config)
            self._switch_sheet(self.activeGroup)
            return True
        except Exception:
            pass
        return False

    # ─────────────────────────────────────────────────────────────────
    def _build_header(self):
        hdr = tk.Frame(self.root, bg=DARK, height=44)
        hdr.pack(fill='x')
        hdr.pack_propagate(False)
        tk.Label(hdr, text=f"📋  {APP_TITLE}",
                 font=("맑은 고딕", 12, "bold"), bg=DARK, fg='white'
                 ).pack(side='left', padx=16, pady=10)
        tk.Label(hdr, text=APP_VERSION,
                 font=("Consolas", 9), bg=DARK, fg=GRAY
                 ).pack(side='left', pady=14)
        tk.Label(hdr, text=f"🗓  {self.date_str}",
                 font=FB, bg=DARK, fg=GRAY).pack(side='right', padx=16)
        if not AUTOMATION:
            tk.Label(hdr, text="⚠ pyautogui 미설치",
                     font=FS, bg=DARK, fg=YELLOW).pack(side='right', padx=8)

        # 크레딧 바
        credit_bar = tk.Frame(self.root, bg='#0d0d1a', height=22)
        credit_bar.pack(fill='x')
        credit_bar.pack_propagate(False)
        tk.Label(credit_bar, text=APP_CREDIT,
                 font=('맑은 고딕', 8), bg='#0d0d1a', fg='#8888cc',
                 anchor='w').pack(side='left', padx=14)
        tk.Label(credit_bar, text='AI-Assisted  ✦',
                 font=('맑은 고딕', 8), bg='#0d0d1a', fg='#5b5bf0',
                 anchor='e').pack(side='right', padx=14)

    def _build_sheet_bar(self):
        bar = tk.Frame(self.root, bg="#E2E8F0")
        bar.pack(fill='x')
        self.sheet_btns = {}
        for s in ['M', 'T']:
            b = tk.Button(bar, text=f"  {s} 반  ", font=FT,
                          relief='flat', bd=0, cursor='hand2',
                          command=lambda x=s: self._switch_sheet(x))
            b.pack(side='left')
            self.sheet_btns[s] = b
        # v3.0: 진도/과제 버튼 제거 (웹에서 입력), 가져오기 항상 표시
        tk.Button(bar, text="⚙ 설정", font=FS,
                  bg="#E2E8F0", fg=SUBTEXT, relief='flat', cursor='hand2',
                  command=self._open_settings
                  ).pack(side='right', padx=4, pady=3)
        tk.Button(bar, text="🗑 초기화", font=FS,
                  bg="#E2E8F0", fg="#EF4444", relief='flat', cursor='hand2',
                  command=self._open_reset_dialog
                  ).pack(side='right', padx=0, pady=3)
        tk.Button(bar, text="📥 데이터 가져오기", font=FS,
                  bg=GREEN, fg='white', relief='flat', cursor='hand2',
                  command=self._pull_mobile_data
                  ).pack(side='right', padx=8, pady=3)

    def _build_panels(self):
        pf = tk.Frame(self.root, bg=BG)
        pf.pack(fill='both', expand=True)
        pf.columnconfigure(1, weight=1)
        pf.rowconfigure(0, weight=1)
        self.panel_frame = pf
        self._build_left(pf)
        self._build_center(pf)
        self._build_right(pf)

    # ── 좌측 ─────────────────────────────────────────────────────────
    def _build_left(self, parent):
        f = tk.Frame(parent, bg=DARK, width=145)
        f.grid(row=0, column=0, sticky='nsew')
        f.pack_propagate(False)
        self.left_frame = f

        tk.Label(f, text="학생 목록", font=FS, bg=DARK, fg=GRAY
                 ).pack(anchor='w', padx=10, pady=(8,2))

        self.sl_canvas, self.sl_inner = make_scroll_frame(f, bg=DARK)

        nav = tk.Frame(f, bg=DARK)
        nav.pack(fill='x', side='bottom', padx=6, pady=6)
        tk.Button(nav, text="◀ 이전", font=FS, bg=DARK2, fg=GRAY,
                  relief='flat', cursor='hand2',
                  command=self._prev_student
                  ).pack(side='left', fill='x', expand=True, padx=2, pady=2)
        tk.Button(nav, text="다음 ▶", font=FS, bg=DARK2, fg=GRAY,
                  relief='flat', cursor='hand2',
                  command=self._next_student
                  ).pack(side='right', fill='x', expand=True, padx=2, pady=2)

    def _refresh_status_dots(self):
        """전체 학생 도트를 캐시 상태에 맞게 일괄 갱신 (_my_classes 범위)"""
        group = self.activeGroup
        for classId, cls_data in self._my_classes(group):
            for nameKey in cls_data.get('student_keys', []):
                self._update_dot(classId, nameKey)

    def _populate_student_list(self, group):
        for w in self.sl_inner.winfo_children():
            w.destroy()
        self.s_btn_map.clear()

        # instructor_assignments 기반 담당 반 필터
        assignments = self.config.get("instructor_assignments", [])
        # cls/classId 둘 다 허용, sheet 없으면 classes에서 group으로 판단
        def _asgn_cls(a): return a.get('cls') or a.get('classId', '')
        def _asgn_matches_group(a):
            s = a.get('sheet')
            if s: return s == group
            cid = _asgn_cls(a)
            return self.all_classes.get(cid, {}).get('group') == group
        assigned_cls = {_asgn_cls(a) for a in assignments if _asgn_matches_group(a)}
        # 강사 계정 미설정 시만 전체 표시; 계정 있고 담당 없으면 빈 목록
        show_all = not self.config.get("instructor_id") and not assignments

        # 부담임 판단용 맵 (classId → role)
        asgn_role_map = {_asgn_cls(a): a.get('role', '') for a in assignments}

        for classId, cls_data in self.all_classes.items():
            # group 필터
            if cls_data.get('group') != group:
                continue
            # 담당 반만 표시
            if not show_all and classId not in assigned_cls:
                continue

            # 이 반 소속 학생 nameKey 목록
            class_student_keys = [k for k, v in self.all_students.items()
                                   if v.get('class') == classId]

            # 부담임 판단
            role = asgn_role_map.get(classId, '')
            if role:
                is_sub = (role == '부담임')
            else:
                is_sub = cls_data.get('is_sub', False)

            # class header with fold/unfold button
            lbl_text = f"🔒 {classId}" if is_sub else classId
            lbl_fg   = "#6B7280" if is_sub else "#475569"
            hdr = tk.Frame(self.sl_inner, bg=DARK)
            hdr.pack(fill='x', pady=(8,0))
            # fold toggle button
            folded = self.cls_fold_state.get((group, classId), False)
            tri = '▸' if folded else '▾'
            def _make_toggle(grp, cl, hdr_frame):
                def _toggle():
                    key = (grp, cl)
                    cur = self.cls_fold_state.get(key, False)
                    cont = self.cls_container.get(key)
                    if cont:
                        if cur:
                            # pack immediately after the header so the list appears in-place
                            try:
                                cont.pack(fill='x', after=hdr_frame)
                            except Exception:
                                cont.pack(fill='x')
                        else:
                            cont.pack_forget()
                    self.cls_fold_state[key] = not cur
                    # update triangle text
                    btn.configure(text=('▸' if self.cls_fold_state[key] else '▾') + ' ' + lbl_text)
                return _toggle

            btn = tk.Button(hdr, text=(tri + ' ' + lbl_text), font=FS,
                            bg=DARK, fg=lbl_fg, relief='flat', bd=0,
                            anchor='w', cursor='hand2', command=_make_toggle(group, classId, hdr))
            btn.pack(side='left', padx=10)

            # container for student rows
            cont = tk.Frame(self.sl_inner, bg=DARK)
            key = (group, classId)
            self.cls_container[key] = cont
            if not folded:
                cont.pack(fill='x')

            for nameKey in class_student_keys:
                display_name = self.all_students[nameKey].get('name', nameKey)
                row = tk.Frame(cont, bg=DARK)
                row.pack(fill='x')
                sbtn = tk.Button(row, text=display_name, font=FB,
                                 bg=DARK, fg=GRAY,
                                 relief='flat', bd=0, anchor='w',
                                 cursor='hand2', width=9,
                                 command=lambda c=classId, nk=nameKey: self._select_student(group, c, nk))
                sbtn.pack(side='left', padx=(10,0), pady=1)
                dc = tk.Canvas(row, width=10, height=10, bg=DARK, highlightthickness=0)
                did = dc.create_oval(2,2,9,9, fill="#374151", outline="")
                dc.pack(side='right', padx=8)
                self.s_btn_map[(classId, nameKey)] = sbtn
                self.status_w[(classId, nameKey)] = (dc, did)

    # ── 중앙 ─────────────────────────────────────────────────────────
    def _build_center(self, parent):
        f = tk.Frame(parent, bg=PANEL,
                     highlightbackground=BORDER, highlightthickness=1)
        f.grid(row=0, column=1, sticky='nsew')
        self.center_frame = f

        # 헤더
        hdr = tk.Frame(f, bg="#F8FAFC",
                       highlightbackground=BORDER, highlightthickness=1)
        hdr.pack(fill='x')
        self.c_name = tk.Label(hdr, text="—",
                               font=("맑은 고딕", 13, "bold"),
                               bg="#F8FAFC", fg=TEXT)
        self.c_name.pack(side='left', padx=14, pady=10)
        self.c_sub = tk.Label(hdr, text="", font=FS, bg="#F8FAFC", fg=GRAY)
        self.c_sub.pack(side='left')
        self.c_room = tk.Label(hdr, text="", font=FS,
                               bg=INDIGO_L, fg=INDIGO, padx=8, pady=3)
        self.c_room.pack(side='right', padx=14)

        # 스크롤 영역
        self.c_canvas, self.c_inner = make_scroll_frame(f, bg=PANEL)

    def _render_student(self, group, classId, nameKey):
        """v3.0 — 읽기 전용 뷰어 (입력 위젯 없음, Firebase 데이터 표시)"""
        for w in self.c_inner.winfo_children():
            w.destroy()

        cls_data  = self.all_classes.get(classId, {})
        courses   = cls_data.get('courses', {})
        subjects  = list(courses.keys())
        tb_grade  = {subj: courses[subj].get('curriculum', '') for subj in subjects}
        display_name = self.all_students.get(nameKey, {}).get('name', nameKey)
        room      = get_room(self.config, display_name)

        self.c_name.config(text=display_name)
        self.c_sub.config(text=f"  {classId}")
        self.c_room.config(text=f"→ {room}")

        # ── 강제 완료 토글 버튼 ──
        force_key = (classId, nameKey)
        is_forced = self.force_data.get(force_key, False)

        def _toggle_force(fk=force_key):
            self.force_data[fk] = not self.force_data.get(fk, False)
            save_daily_cache(self.progress_data, self.student_data,
                             self.note_data, self.force_data)
            self._update_dot(classId, nameKey)
            self._refresh_send_btn()
            self._refresh_statusbar()
            self._render_student(group, classId, nameKey)

        force_btn_frame = tk.Frame(self.c_inner, bg=PANEL)
        force_btn_frame.pack(fill='x', padx=14, pady=(8, 0))
        if self._is_sub_teacher(classId):
            # 부담임 반: 강제 완료 비활성화
            force_btn = tk.Button(
                force_btn_frame, text="⚡ 강제 완료 (부담임 열람만)",
                font=FS, bg="#F1F5F9", fg=GRAY,
                relief='flat', padx=8, pady=3, state='disabled')
        elif is_forced:
            force_btn = tk.Button(
                force_btn_frame, text="⚡ 강제 완료 (ON) — 클릭하여 해제",
                font=FS, bg="#DCFCE7", fg="#166534",
                relief='flat', padx=8, pady=3, cursor='hand2',
                command=_toggle_force)
        else:
            force_btn = tk.Button(
                force_btn_frame, text="⚡ 강제 완료",
                font=FS, bg="#F1F5F9", fg=SUBTEXT,
                relief='flat', padx=8, pady=3, cursor='hand2',
                command=_toggle_force)
        force_btn.pack(side='right')

        pad = tk.Frame(self.c_inner, bg=PANEL)
        pad.pack(fill='x', expand=True, padx=14, pady=10)
        pad.columnconfigure(0, weight=1)

        # ── 진도/과제 요약 (반 공통, session/class_data에서 로드) ──
        has_progress = any(
            self.progress_data.get((classId, subject), {}).get('progress') or
            self.progress_data.get((classId, subject), {}).get('homework')
            for subject in subjects
        )
        if has_progress:
            pf = tk.LabelFrame(pad, text="  오늘 수업 (반 공통)  ",
                               font=("맑은 고딕", 9, "bold"),
                               fg="#0F6E56", bg="#F0FDF4", padx=10, pady=8,
                               highlightbackground="#BBF7D0")
            pf.pack(fill='x', pady=(0, 12))
            for subject in subjects:
                pd_val = self.progress_data.get((classId, subject), {})
                if pd_val.get('progress') or pd_val.get('homework'):
                    tb_lbl = grade_label(tb_grade.get(subject, ''), subject)
                    tk.Label(pf, text=tb_lbl, font=("맑은 고딕", 8, "bold"),
                             bg="#F0FDF4", fg=INDIGO).pack(anchor='w', pady=(2,0))
                    if pd_val.get('progress'):
                        tk.Label(pf, text=f"  진도: {pd_val['progress']}",
                                 font=FS, bg="#F0FDF4", fg=TEXT
                                 ).pack(anchor='w')
                    if pd_val.get('homework'):
                        tk.Label(pf, text=f"  과제: {pd_val['homework']}",
                                 font=FS, bg="#F0FDF4", fg=TEXT
                                 ).pack(anchor='w')

        # ── 과목별 과제수행도 (읽기 전용) ──
        for subject in subjects:
            student_key = (classId, nameKey, subject)
            val      = self.student_data.get(student_key, {}).get('value', '')
            filled   = bool(val.strip())

            tb_lbl = grade_label(tb_grade.get(subject, ''), subject)
            lf = tk.LabelFrame(pad, text=f"  {tb_lbl}  ",
                               font=("맑은 고딕", 9, "bold"),
                               fg=SUBTEXT, bg=PANEL, padx=10, pady=8)
            lf.pack(fill='x', pady=(0, 8))

            dot_ch  = "●" if filled else "○"
            dot_fg  = GREEN if filled else "#9CA3AF"
            disp    = val if filled else "(미입력)"
            txt_fg  = TEXT if filled else GRAY

            row = tk.Frame(lf, bg=PANEL)
            row.pack(fill='x')
            tk.Label(row, text=dot_ch, font=("맑은 고딕", 11),
                     bg=PANEL, fg=dot_fg).pack(side='left', padx=(0, 8))
            tk.Label(row, text=disp, font=FB, bg=PANEL, fg=txt_fg,
                     wraplength=260, justify='left', anchor='w'
                     ).pack(side='left', fill='x', expand=True)

        # ── 특이사항 (편집 가능 + AI 생성) ──
        note_key = (classId, nameKey)
        note_val = self.note_data.get(note_key, {}).get('value', '')
        sep = tk.Frame(pad, height=1, bg=BORDER)
        sep.pack(fill='x', pady=(4, 8))

        note_hdr = tk.Frame(pad, bg=PANEL)
        note_hdr.pack(fill='x', pady=(0, 4))
        tk.Label(note_hdr, text="특이사항", font=("맑은 고딕", 9, "bold"),
                 bg=PANEL, fg=SUBTEXT).pack(side='left')
        ai_btn = tk.Button(note_hdr, text="✨ AI생성",
                           font=("맑은 고딕", 8), bg="#EEF2FF", fg=INDIGO,
                           relief='flat', padx=8, pady=2, cursor='hand2')
        ai_btn.pack(side='right')

        # 부담임 과목은 AI생성 비활성화
        if self._is_sub_teacher(classId):
            ai_btn.config(state='disabled', text="✨ AI생성 (부담임)",
                          bg="#F1F5F9", fg=GRAY, cursor='arrow')
        else:
            # 쿨다운 잔여 시간에 따라 초기 상태 설정
            _engine = self.config.get('ai_engine_type', 'groq').strip().lower()
            _cooldown = AI_COOLDOWNS.get(_engine, AI_COOLDOWN_PAID)
            _rem = max(0, _cooldown - (time.time() - self._ai_last_call))
            if _rem > 0:
                ai_btn.config(state='disabled', text=f"⏳ {int(_rem)}s")
                self._start_cooldown_tick(ai_btn)

        # Text 위젯 — 담임: 편집 가능 / 부담임: 읽기 전용
        is_sub = self._is_sub_teacher(classId)
        import sys as _sys
        _note_font = ("Segoe UI Emoji", 9) if _sys.platform == "win32" else FE
        note_txt = tk.Text(pad, font=_note_font, bg="#F8FAFC", fg=TEXT,
                           relief='flat', wrap='word', height=6,
                           undo=True,
                           highlightbackground=BORDER, highlightthickness=1,
                           padx=6, pady=4)
        note_txt.pack(fill='x', pady=(0, 2))
        if note_val.strip():
            note_txt.insert('1.0', note_val)

        if is_sub:
            # 부담임: 읽기 전용 잠금 — FocusOut·Firebase PATCH 없음
            note_txt.config(state='disabled', bg="#F1F5F9", fg=GRAY)
        else:
            def _save_note(event=None):
                """note_data 로컬 캐시 저장 (DB 쓰기 없음)"""
                raw = note_txt.get('1.0', 'end').rstrip('\n')
                # 이모지 surrogate pair 정규화 (Windows tkinter 대응)
                try:
                    new_val = raw.encode('utf-16', 'surrogatepass').decode('utf-16')
                except Exception:
                    new_val = raw
                self.note_data[note_key] = {'value': new_val}
                save_daily_cache(self.progress_data, self.student_data, self.note_data, self.force_data)
                self._update_preview()

            def _on_return(event):
                """Enter = 저장 트리거 (줄바꿈 방지)"""
                _save_note()
                return 'break'

            def _on_shift_return(event):
                """Shift+Enter = 줄바꿈 삽입"""
                note_txt.insert('insert', '\n')
                return 'break'

            note_txt.bind('<FocusOut>', _save_note)
            note_txt.bind('<Return>', _on_return)
            note_txt.bind('<Shift-Return>', _on_shift_return)

        ai_btn.config(command=lambda: self._gen_ai_note(
            group, classId, nameKey, subjects, note_txt, ai_btn, tb_grade=tb_grade))

        self.c_canvas.yview_moveto(0)
        self._update_preview()

    # ── 우측 ─────────────────────────────────────────────────────────
    def _build_right(self, parent):
        f = tk.Frame(parent, bg=PANEL, width=300,
                     highlightbackground=BORDER, highlightthickness=1)
        f.grid(row=0, column=2, sticky='nsew')
        f.pack_propagate(False)
        parent.columnconfigure(2, minsize=300)
        self.right_frame = f

        # 헤더
        rh = tk.Frame(f, bg="#F8FAFC",
                      highlightbackground=BORDER, highlightthickness=1)
        rh.pack(fill='x')
        self._dot_c = tk.Canvas(rh, width=10, height=10,
                                bg="#F8FAFC", highlightthickness=0)
        self._dot_id = self._dot_c.create_oval(2,2,9,9, fill=GREEN, outline="")
        self._dot_c.pack(side='left', padx=(12,4), pady=10)
        self._pulse()
        tk.Label(rh, text="미리보기",
                 font=FT, bg="#F8FAFC", fg=TEXT).pack(side='left')
        self.char_lbl = tk.Label(rh, text="0자", font=FS, bg="#F8FAFC", fg=GRAY)
        self.char_lbl.pack(side='right', padx=12)

        self.to_lbl = tk.Label(f, text="", font=FS,
                               bg=INDIGO_L, fg=INDIGO, anchor='w', padx=10, pady=3)
        self.to_lbl.pack(fill='x')

        self.preview = tk.Text(f, font=("맑은 고딕", 9), wrap='word',
                               relief='flat', bg="#F8FAFC", bd=0,
                               highlightthickness=0, state='disabled',
                               padx=12, pady=10)
        self.preview.pack(fill='both', expand=True)

        self.send_status = tk.Label(f, text="", font=FS,
                                    bg=PANEL, fg=GRAY, anchor='w', padx=10, pady=4)
        self.send_status.pack(fill='x', side='bottom')

    def _pulse(self, on=True):
        try:
            if not self._dot_c.winfo_exists():
                return
            self._dot_c.itemconfig(self._dot_id, fill=GREEN if on else "#bbf7d0")
            self.root.after(800, lambda: self._pulse(not on))
        except Exception:
            pass

    # ── 상태바 / 푸터 ────────────────────────────────────────────────
    def _build_statusbar(self):
        sb = tk.Frame(self.root, bg="#F0FDF4",
                      highlightbackground="#BBF7D0", highlightthickness=1)
        sb.pack(fill='x')
        self.status_lbl = tk.Label(sb, text="", font=FS,
                                   bg="#F0FDF4", fg="#15803D", anchor='w')
        self.status_lbl.pack(side='left', padx=12, pady=4)
        tk.Label(sb, text="● 완료   ◐ 진행중   ○ 미입력",
                 font=FS, bg="#F0FDF4", fg=GRAY).pack(side='right', padx=12)
        self._status_tooltip_text = ""
        self._attach_status_tooltip(self.status_lbl)

    def _attach_status_tooltip(self, widget):
        """상태바 레이블에 hover 툴팁 연결 — 이름 목록 표시"""
        _tip = [None]
        def _show(e):
            text = self._status_tooltip_text
            if not text or _tip[0]: return
            t = tk.Toplevel(widget)
            t.wm_overrideredirect(True)
            t.wm_geometry(f"+{e.x_root + 8}+{e.y_root + 18}")
            tk.Label(t, text=text, font=FS, bg="#FFFDE7", fg=TEXT,
                     relief='flat', padx=8, pady=5,
                     highlightbackground="#FDE68A", highlightthickness=1
                     ).pack()
            _tip[0] = t
        def _hide(e):
            if _tip[0]:
                try: _tip[0].destroy()
                except Exception: pass
                _tip[0] = None
        widget.bind('<Enter>', _show)
        widget.bind('<Leave>', _hide)

    def _build_footer(self):
        foot = tk.Frame(self.root, bg=PANEL,
                        highlightbackground=BORDER, highlightthickness=1)
        foot.pack(fill='x', side='bottom')
        self.send_btn = tk.Button(
            foot, text="🚀  카카오톡 전송 (0명)",
            font=("맑은 고딕", 10, "bold"),
            bg="#E2E8F0", fg=GRAY, relief='flat',
            padx=14, pady=8, cursor='hand2',
            command=self._send)
        self.send_btn.pack(side='right', padx=10, pady=8)

        # ✨ 전체 AI 생성 버튼 (STATUS_READY 학생 일괄 처리)
        self.ai_all_btn = tk.Button(
            foot, text="✨ 전체 AI 생성",
            font=("맑은 고딕", 9), bg="#EEF2FF", fg=INDIGO,
            relief='flat', padx=10, pady=8, cursor='hand2',
            command=self._gen_ai_note_all)
        self.ai_all_btn.pack(side='right', padx=(0, 4), pady=8)

    # ── 핵심 로직 ────────────────────────────────────────────────────
    def _on_change(self):
        # v3.0: _save_values() 제거 — 입력 위젯 없음, Firebase에서만 로드
        self._update_preview()
        if self.cur_name:
            self._update_dot(self.cur_cls, self.cur_name)
        self._refresh_send_btn()
        self._refresh_statusbar()

    def _save_values(self):
        # v3.0: 입력 위젯 없음 — Firebase 가져오기로만 데이터 로드, no-op
        pass

    def _update_preview(self):
        group, classId, nameKey = self.activeGroup, self.cur_cls, self.cur_name
        if not nameKey: return
        cls_data  = self.all_classes.get(classId, {})
        courses   = cls_data.get('courses', {})
        subjects  = list(courses.keys())
        tb_grade  = {subj: courses[subj].get('curriculum', '') for subj in subjects}
        display_name = self.all_students.get(nameKey, {}).get('name', nameKey)
        room      = get_room(self.config, display_name)
        class_info = {subj: self.progress_data.get((classId, subj), {'progress':'','homework':''})
                      for subj in subjects}
        assign_map = {subj: self.student_data.get((classId, nameKey, subj), {}).get('value','')
                      for subj in subjects}
        note = self.note_data.get((classId, nameKey), {}).get('value','')
        msg  = build_message(self.date_str, class_info, display_name, assign_map, note, tb_grade=tb_grade)
        self.to_lbl.config(text=f"→  {room}")
        self.preview.config(state='normal')
        self.preview.delete('1.0','end')
        self.preview.insert('1.0', msg)
        self.preview.config(state='disabled')
        self.char_lbl.config(text=f"{len(msg)}자")

    def _is_sub_teacher(self, classId):
        """현재 강사가 해당 classId에서 부담임인지 확인"""
        for a in self.config.get("instructor_assignments", []):
            cid = a.get('cls') or a.get('classId', '')
            if cid == classId:
                return a.get('role') == '부담임'
        return False

    def _my_classes(self, group) -> list:
        """내 담당 반만 반환 → [(classId, cls_data), ...] 튜플 리스트
        - instructor_id 미설정 + assignments 없음: 전체 반 (show_all)
        - instructor_id 설정 + assignments 없음: 빈 목록
        - assignments 있음: 해당 group의 담당 반만
        모든 학생 관련 연산(상태바·이동·전송·초기화·AI)에 일관 적용.
        """
        assignments = self.config.get("instructor_assignments", [])
        group_classes = {cid: cd for cid, cd in self.all_classes.items()
                         if cd.get('group') == group}
        if not assignments:
            if not self.config.get("instructor_id"):
                return list(group_classes.items())  # 계정 미설정 → 전체 표시
            return []  # 계정 있고 담당 없음 → 빈 목록
        # cls/classId 둘 다 허용, sheet 없으면 classes group으로 판단
        def _cid(a): return a.get('cls') or a.get('classId', '')
        def _grp_ok(a):
            s = a.get('sheet')
            if s: return s == group
            return self.all_classes.get(_cid(a), {}).get('group') == group
        assigned_cls = {_cid(a) for a in assignments if _grp_ok(a)}
        return [(cid, cd) for cid, cd in group_classes.items() if cid in assigned_cls]

    def _student_status(self, classId, nameKey):
        # 강제 완료 플래그 우선
        if self.force_data.get((classId, nameKey)):
            return STATUS_READY
        courses  = self.all_classes.get(classId, {}).get('courses', {})
        subjects = list(courses.keys())
        filled = sum(1 for subj in subjects
                     if self.student_data.get((classId, nameKey, subj), {}).get('value', ''))
        if filled == 0:             return STATUS_EMPTY
        if filled < len(subjects):  return STATUS_PARTIAL
        # 과제수행도 완료 → 반 공통 진도/과제도 하나 이상 있어야 READY
        has_progress = any(
            self.progress_data.get((classId, subj), {}).get('progress', '') or
            self.progress_data.get((classId, subj), {}).get('homework', '')
            for subj in subjects
        )
        return STATUS_READY if has_progress else STATUS_PARTIAL

    def _update_dot(self, classId, nameKey):
        st = self._student_status(classId, nameKey)
        pair = self.status_w.get((classId, nameKey))
        if pair:
            pair[0].itemconfig(pair[1], fill=DOT_COLOR[st])

    def _collect_ready(self, group):
        """
        전송 준비 완료 학생만 수집
        ─ 조건: STATUS_READY (과제수행도 완료 + 진도/과제 입력)
        ─ _my_classes() 화이트리스트 + _is_sub_teacher() 부담임 제외 일관 적용
        """
        result = []
        for classId, cls_data in self._my_classes(group):
            if self._is_sub_teacher(classId):
                continue
            courses    = cls_data.get('courses', {})
            subjects   = list(courses.keys())
            tb_grade   = {subj: courses[subj].get('curriculum', '') for subj in subjects}
            class_info = {subj: self.progress_data.get((classId, subj), {'progress':'','homework':''})
                          for subj in subjects}
            class_student_keys = [k for k, v in self.all_students.items()
                                   if v.get('class') == classId]
            for nameKey in class_student_keys:
                if self._student_status(classId, nameKey) != STATUS_READY:
                    continue
                display_name = self.all_students[nameKey].get('name', nameKey)
                assign_map = {subj: self.student_data.get((classId, nameKey, subj), {}).get('value','')
                              for subj in subjects}
                note = self.note_data.get((classId, nameKey), {}).get('value','')
                msg  = build_message(self.date_str, class_info, display_name, assign_map, note, tb_grade=tb_grade)
                result.append({'name': display_name, 'room': get_room(self.config, display_name), 'msg': msg})
        return result

    def _refresh_send_btn(self):
        n = len(self._collect_ready(self.activeGroup))
        self.send_btn.config(
            text=f"🚀  카카오톡 전송 ({n}명)",
            bg=ACCENT if n>0 else "#E2E8F0",
            fg="#1A1D2E" if n>0 else GRAY)

    def _refresh_statusbar(self):
        group = self.activeGroup
        done, part, empty = [], [], []
        for classId, cls_data in self._my_classes(group):
            class_student_keys = [k for k, v in self.all_students.items()
                                   if v.get('class') == classId]
            for nameKey in class_student_keys:
                display_name = self.all_students[nameKey].get('name', nameKey)
                st = self._student_status(classId, nameKey)
                if st == STATUS_READY:     done.append(display_name)
                elif st == STATUS_PARTIAL: part.append(display_name)
                else:                     empty.append(display_name)
        parts = []
        if done:  parts.append(f"완료 {len(done)}명")
        if part:  parts.append(f"진행중 {len(part)}명")
        if empty: parts.append(f"미입력 {len(empty)}명")
        self.status_lbl.config(text="   ".join(parts) if parts else "입력 없음")
        # 툴팁용 이름 목록
        tip_lines = []
        if done:  tip_lines.append(f"완료: {', '.join(done)}")
        if part:  tip_lines.append(f"진행중: {', '.join(part)}")
        if empty: tip_lines.append(f"미입력: {', '.join(empty)}")
        self._status_tooltip_text = "\n".join(tip_lines)

    # ── 학생 이동 ────────────────────────────────────────────────────
    def _student_list_flat(self, group):
        """◀/▶ 이동용 학생 목록 — _my_classes() 범위만 포함"""
        result = []
        for classId, cd in self._my_classes(group):
            for nameKey in [k for k, v in self.all_students.items()
                            if v.get('class') == classId]:
                result.append((classId, nameKey))
        return result

    def _select_student(self, group, classId, nameKey):
        if self.cur_name:
            old = self.s_btn_map.get((self.cur_cls, self.cur_name))
            if old: old.config(bg=DARK, fg=GRAY)
        self.activeGroup, self.cur_cls, self.cur_name = group, classId, nameKey
        btn = self.s_btn_map.get((classId, nameKey))
        if btn: btn.config(bg=INDIGO, fg='white')
        self._render_student(group, classId, nameKey)

    def _prev_student(self):
        lst = self._student_list_flat(self.activeGroup)
        cur = (self.cur_cls, self.cur_name)
        if cur in lst:
            i = lst.index(cur)
            if i > 0:
                c, nk = lst[i-1]
                self._select_student(self.activeGroup, c, nk)

    def _next_student(self):
        lst = self._student_list_flat(self.activeGroup)
        cur = (self.cur_cls, self.cur_name)
        if cur in lst:
            i = lst.index(cur)
            if i < len(lst)-1:
                c, nk = lst[i+1]
                self._select_student(self.activeGroup, c, nk)


    # ── 시트 전환 ────────────────────────────────────────────────────
    def _refresh_student_view(self):
        """프리셋 변경 후 현재 학생 입력 화면 즉시 갱신"""
        if self.activeGroup and self.cur_cls and self.cur_name:
            self._render_student(self.activeGroup, self.cur_cls, self.cur_name)

    def _open_reset_dialog(self):
        """🗑 초기화 선택 다이얼로그"""
        win = tk.Toplevel(self.root)
        win.title("초기화")
        win.geometry("320x190")
        win.resizable(False, False)
        win.configure(bg=BG)
        win.grab_set()

        tk.Label(win, text="초기화 범위를 선택하세요", font=FT,
                 bg=BG, fg=TEXT).pack(pady=(16, 10))

        tk.Button(win, text="현재 반 초기화  (수행도·특이사항)",
                  font=FS, bg="#FEF2F2", fg="#EF4444", relief='flat',
                  cursor='hand2', pady=7,
                  command=lambda: [
                      self._reset_class_data(self.activeGroup, self.cur_cls),
                      win.destroy()]
                  ).pack(fill='x', padx=16, pady=2)

        tk.Button(win, text="전체 반 초기화  (수행도·특이사항)",
                  font=FS, bg="#FEF2F2", fg="#EF4444", relief='flat',
                  cursor='hand2', pady=7,
                  command=lambda: [self._reset_all_data(), win.destroy()]
                  ).pack(fill='x', padx=16, pady=2)

        tk.Button(win, text="취소", font=FS, bg=PANEL, fg=SUBTEXT,
                  relief='flat', cursor='hand2', pady=7,
                  command=win.destroy
                  ).pack(fill='x', padx=16, pady=(2, 16))

    def _reset_class_data(self, group=None, classId=None):
        """반별 학생 입력 데이터 로컬 초기화 (과제수행도·특이사항) — DB 쓰기 없음"""
        grp = group   or self.activeGroup
        cid = classId or self.cur_cls
        if not cid: return
        cls_student_keys = [k for k, v in self.all_students.items()
                             if v.get('class') == cid]
        courses  = self.all_classes.get(cid, {}).get('courses', {})
        subjects = list(courses.keys())

        for nameKey in cls_student_keys:
            for subject in subjects:
                key = (cid, nameKey, subject)
                if key in self.student_data:
                    self.student_data[key] = {'value': ''}
            note_key = (cid, nameKey)
            if note_key in self.note_data:
                self.note_data[note_key] = {'value': ''}

        save_daily_cache(self.progress_data, self.student_data, self.note_data, self.force_data)

        if self.cur_name:
            self._render_student(grp, cid, self.cur_name)
        self._refresh_status_dots()
        self._refresh_send_btn()
        self._refresh_statusbar()

    def _reset_all_data(self):
        """전체 입력 데이터 로컬 초기화 (진도/과제 포함) — DB 쓰기 없음"""
        self.student_data.clear()
        self.note_data.clear()
        self.progress_data.clear()
        self.force_data.clear()
        save_daily_cache(self.progress_data, {}, {}, {})

        if self.cur_name:
            self._render_student(self.activeGroup, self.cur_cls, self.cur_name)
        self._refresh_status_dots()
        self._refresh_send_btn()
        self._refresh_statusbar()

    def _pull_mobile_data(self):
        """📥 데이터 가져오기 — Firebase input/ + session/class_data 전체 로드 (v2.0)"""
        url  = self.config.get('firebase_url', '')
        path = self.config.get('firebase_path', '')
        if not url or not path:
            messagebox.showwarning("Firebase 미설정",
                "설정에서 Firebase URL과 경로를 입력해 주세요.")
            return

        try:
            # ── 로컬 데이터 전부 초기화 ──
            self.student_data.clear()
            self.note_data.clear()
            self.progress_data.clear()
            self.force_data.clear()

            # ── 0. config/ + students/ + classes/ 동기화 ──
            config_data = firebase_get(self.config, "config") or {}
            self._sync_shared_sheets_from_firebase()

            # 강사별 presets + assignments 우선, 없으면 전역 presets 사용
            instructor_id = self.config.get('instructor_id', '')
            if instructor_id and config_data.get("instructors", {}).get(instructor_id):
                instr_data = config_data["instructors"][instructor_id]
                if instr_data.get("presets"):
                    self.config["presets"] = {"과제수행도": instr_data["presets"]}
                # assignments 저장 → 담당 반 필터링·부담임 판단에 사용
                self.config["instructor_assignments"] = instr_data.get("assignments", [])
                instr_name = instr_data.get("name", instructor_id)
            elif config_data.get("presets"):
                self.config["presets"] = config_data["presets"]
                self.config["instructor_assignments"] = []
                instr_name = ""
            else:
                self.config["instructor_assignments"] = []
                instr_name = ""

            save_config(self.config)
            # 학생 목록 갱신 — after() 금지 (이벤트 루프 재진입 TclError 방지)
            self._switch_sheet(self.activeGroup)

            # ── 1. 학생별 수행도·특이사항 (input/ 노드) ──
            # 구조: {nameKey: {subject: {assign, note}}}
            input_data = firebase_get(self.config, "input") or {}

            # ── 2. 반 공통 진도/과제 (session/class_data) ──
            session_raw = firebase_get(self.config, "session")
            if session_raw is None:
                # session 노드 자체 없음 → lastSent 폴백
                last_raw   = firebase_get(self.config, "lastSent") or {}
                class_data = last_raw.get("class_data", {})
                date_str   = last_raw.get("date", "")
            else:
                # session 노드 존재 (비어있어도 의도적 상태 — 폴백 없음)
                session_raw = session_raw or {}
                class_data  = session_raw.get("class_data") or {}
                date_str    = session_raw.get("date", "")

            # ── 3. 수업 관찰 태그 (obs/ 노드, v2.0 신규) ──
            # 구조: {nameKey: {subject: {date: {...}}}}
            tag_raw = fetch_tags(self.config)
            if tag_raw:
                self.tag_data.update(tag_raw)

            if not input_data and not class_data:
                messagebox.showinfo("알림", "웹 입력 데이터가 없습니다.\n웹에서 먼저 수업을 입력해 주세요.")
                return

            # ── input/ 처리 ──
            # 과제수행도·메모: 항상 웹 데이터로 교체
            self._import_mobile_data(input_data)

            # ── obs/ assign_grade + assign_tags → student_data 매핑 (v2.0) ──
            # 웹 앱이 assign_grade/assign_tags를 obs/{nameKey}/{subject}/{date} 에 저장
            _today = today_key()
            for _nameKey, _subject_map in self.tag_data.items():
                if not isinstance(_subject_map, dict):
                    continue
                # 이 nameKey 가 속한 classId 조회
                _classId = self.all_students.get(_nameKey, {}).get('class', '')
                if not _classId:
                    continue
                for _subject, _date_map in _subject_map.items():
                    if not isinstance(_date_map, dict):
                        continue
                    _day = _date_map.get(_today, {})
                    if not isinstance(_day, dict):
                        continue

                    # assign_grade → 라벨
                    _gk = _day.get('assign_grade', '')
                    _grade_lbl = ASSIGN_GRADE_LABELS.get(_gk, '') if _gk else ''

                    # assign_tags (복수선택 프리셋 — Firebase 배열/객체 모두 대응)
                    _raw_tags = _day.get('assign_tags') or []
                    if isinstance(_raw_tags, dict):
                        _raw_tags = [v for _, v in sorted(_raw_tags.items())]
                    _tag_lbls = [str(t) for t in _raw_tags if t]

                    # 결합: "대부분 수행 / 교재 미지참 / 오답 풀이 안함"
                    _combined = ' / '.join(p for p in [_grade_lbl] + _tag_lbls if p)
                    if not _combined:
                        continue

                    self.student_data[(_classId, _nameKey, _subject)] = {'value': _combined}

            # ── session/class_data → progress_data (항상 덮어쓰기) ──
            applied_prog = 0
            for key_str, v in class_data.items():
                parts = key_str.split('|')
                if len(parts) != 2:
                    continue
                classId, subject = parts
                tk_key = (classId, subject)
                prog = v.get('progress', '') if isinstance(v, dict) else ''
                hw   = v.get('homework',  '') if isinstance(v, dict) else ''
                self.progress_data[tk_key] = {'progress': prog, 'homework': hw}
                applied_prog += 1

            save_daily_cache(self.progress_data, self.student_data, self.note_data, self.force_data)
            self._refresh_status_dots()
            self._refresh_send_btn()
            self._refresh_statusbar()
            if self.cur_name:
                self._render_student(self.activeGroup, self.cur_cls, self.cur_name)

            date_info = f"  ({date_str} 기준)" if date_str else ""
            messagebox.showinfo("가져오기 완료",
                f"웹 입력 데이터를 가져왔습니다.{date_info}\n"
                f"과제수행도: 웹 데이터로 교체 / 진도·과제: {applied_prog}개 반영\n"
                "메모: 웹 데이터로 교체")
        except Exception as e:
            messagebox.showerror("오류", f"가져오기 실패:\n{e}")

    def _import_mobile_data(self, data):
        """Firebase input/ 노드에서 학생 데이터 반영 (v2.0 스키마)
        구조: {nameKey: {subject: {assign, note}}}
        · 과제수행도: 항상 웹 데이터로 교체
        · 메모/특이사항: 항상 웹 데이터로 교체
        """
        if not data:
            return

        for nameKey, subjects in data.items():
            if not isinstance(subjects, dict):
                continue
            # 이 nameKey 가 속한 classId 조회
            classId = self.all_students.get(nameKey, {}).get('class', '')
            if not classId:
                continue
            for subject, payload in subjects.items():
                if not isinstance(payload, dict):
                    continue
                # 과제수행도
                assign_val = payload.get('assign', '')
                student_key = (classId, nameKey, subject)
                self.student_data[student_key] = {'value': assign_val}
                # 메모/특이사항
                note_val = payload.get('note', '')
                if note_val:
                    note_key = (classId, nameKey)
                    self.note_data[note_key] = {'value': note_val}

        save_daily_cache(self.progress_data, self.student_data, self.note_data, self.force_data)
        if self.cur_name:
            self._render_student(self.activeGroup, self.cur_cls, self.cur_name)
        self._refresh_send_btn()
        self._refresh_statusbar()


    def _switch_sheet(self, group):
        self._save_values()
        self.activeGroup = group
        self.cur_cls = self.cur_name = None
        self._populate_student_list(group)
        for s, b in self.sheet_btns.items():
            b.config(bg=PANEL if s==group else "#E2E8F0",
                     fg=TEXT  if s==group else SUBTEXT)
        # 첫 학생 선택 (_my_classes 범위 내에서)
        for classId, cd in self._my_classes(group):
            first_keys = [k for k, v in self.all_students.items()
                          if v.get('class') == classId]
            if first_keys:
                self._select_student(group, classId, first_keys[0])
                break
        self._refresh_status_dots()
        self._refresh_send_btn()
        self._refresh_statusbar()

    # ── 최초 실행 안내 ────────────────────────────────────────────────
    def _prompt_first_run(self):
        """v3.0 — Firebase 미설정 시 초기 설정 안내"""
        win = tk.Toplevel(self.root)
        win.title("시작하기")
        win.geometry("420x240")
        win.configure(bg=BG)
        win.grab_set()
        win.resizable(False, False)

        tk.Label(win, text=f"📋  {APP_TITLE} {APP_VERSION}",
                 font=("맑은 고딕", 12, "bold"), bg=BG, fg=TEXT
                 ).pack(pady=(24, 6))
        tk.Label(win,
                 text=("먼저 Firebase DB URL과 경로를 설정해 주세요.\n\n"
                       "웹(index.html)에서 강사 등록 및 학생 명단을\n"
                       "구성한 뒤 '📥 데이터 가져오기'를 사용하세요."),
                 font=FB, bg=BG, fg=SUBTEXT, justify='center'
                 ).pack(pady=4)

        def _do():
            win.destroy()
            self._open_settings()

        tk.Button(win, text="⚙  설정 열기",
                  font=FT, bg=BLUE, fg='white', relief='flat',
                  padx=16, pady=8, cursor='hand2',
                  command=_do).pack(pady=18)

# ── 설정 창 ──────────────────────────────────────────────────────
    def _open_settings(self):
        # 이미 열려있으면 앞으로 가져오기
        if hasattr(self, '_settings_win') and self._settings_win.winfo_exists():
            self._settings_win.lift()
            self._settings_win.focus_force()
            return

        win = tk.Toplevel(self.root)
        self._settings_win = win
        win.title("설정")
        win.geometry("520x720")
        win.configure(bg=BG)
        win.resizable(False, True)

        # 헤더
        hdr = tk.Frame(win, bg=DARK, height=40)
        hdr.pack(fill='x')
        hdr.pack_propagate(False)
        tk.Label(hdr, text="⚙ 설정", font=FT, bg=DARK, fg='white').pack(side='left', padx=16, pady=8)

        # 메인 영역 (스크롤 배치)
        canvas, inner = make_scroll_frame(win, bg=BG)
        canvas.pack(fill='both', expand=True)

        # ── ① 기본 환경 매크로 설정 ───────────────────────────
        self._settings_section(inner, "기본 매크로 설정")
        
        delay_grid = tk.Frame(inner, bg=BG)
        delay_grid.pack(fill='x', padx=16, pady=(0,10))
        delay_grid.columnconfigure(1, weight=1)

        tk.Label(delay_grid, text="대기 시간(초)", font=FS, bg=BG, fg=SUBTEXT).grid(row=0, column=0, sticky='w', pady=3, padx=(0,8))
        wait_var = tk.StringVar(value=str(self.config.get('wait_time', 0.5)))
        tk.Entry(delay_grid, textvariable=wait_var, font=FS, relief='solid', bd=1).grid(row=0, column=1, sticky='ew', ipady=3)

        tk.Label(delay_grid, text="카톡 접두사", font=FS, bg=BG, fg=SUBTEXT).grid(row=1, column=0, sticky='w', pady=3, padx=(0,8))
        prefix_var = tk.StringVar(value=self.config.get('room_prefix', '오직 '))
        tk.Entry(delay_grid, textvariable=prefix_var, font=FS, relief='solid', bd=1).grid(row=1, column=1, sticky='ew', ipady=3)

        # ── ② Firebase Database 연결 설정 ───────────────────
        tk.Frame(inner, bg=BORDER, height=1).pack(fill='x', padx=16, pady=(4,0))
        self._settings_section(inner, "Firebase 연결 설정")

        fb_grid = tk.Frame(inner, bg=BG)
        fb_grid.pack(fill='x', padx=16, pady=(0,6))
        fb_grid.columnconfigure(1, weight=1)

        tk.Label(fb_grid, text="DB URL", font=FS, bg=BG, fg=SUBTEXT).grid(row=0, column=0, sticky='w', pady=3, padx=(0,8))
        fb_url_var = tk.StringVar(value=self.config.get('firebase_url', ''))
        tk.Entry(fb_grid, textvariable=fb_url_var, font=FS, relief='solid', bd=1).grid(row=0, column=1, sticky='ew', ipady=3)

        tk.Label(fb_grid, text="DB 경로", font=FS, bg=BG, fg=SUBTEXT).grid(row=1, column=0, sticky='w', pady=3, padx=(0,8))
        fb_path_var = tk.StringVar(value=self.config.get('firebase_path', ''))
        tk.Entry(fb_grid, textvariable=fb_path_var, font=FS, relief='solid', bd=1).grid(row=1, column=1, sticky='ew', ipady=3)

        def _test_connection():
            url = fb_url_var.get().strip()
            path = fb_path_var.get().strip()
            if not url or not path:
                messagebox.showwarning("알림", "URL과 경로를 입력하세요.", parent=win)
                return
            tmp = {'firebase_url': url, 'firebase_path': path}
            try:
                from firebase import firebase_get
                result = firebase_get(tmp, "config")
                if result is None:
                    messagebox.showwarning("주의", "연결은 성공했지만 config 노드가 비어있습니다.\nFirebase 경로를 확인하세요.", parent=win)
                else:
                    messagebox.showinfo("성공", "Firebase 연결 테스트에 성공했습니다!", parent=win)
            except Exception as e:
                messagebox.showerror("실패", f"연결 실패:\n{e}", parent=win)

        test_row = tk.Frame(inner, bg=BG)
        test_row.pack(fill='x', padx=16, pady=(0,10))
        tk.Button(test_row, text="⚡ 연결 테스트", font=FS, bg="#E0E7FF", fg=INDIGO, relief='flat', padx=10, pady=4, cursor='hand2', command=_test_connection).pack(side='left')

        # ── ③ 내 강사 계정 ────────────────────────────────────────
        tk.Frame(inner, bg=BORDER, height=1).pack(fill='x', padx=16, pady=(4,0))
        self._settings_section(inner, "내 강사 계정")
        tk.Label(inner, text="강사 이름을 입력하고 조회하세요. 등록된 계정이 없으면 신규 등록합니다.", font=FS, bg=BG, fg=SUBTEXT, wraplength=460).pack(anchor='w', padx=16, pady=(0,6))

        cur_name = self.config.get('instructor_id', '')
        cur_lbl = tk.Label(inner, text=f"현재 계정: {cur_name or '(없음)'}", font=FB, bg=BG, fg=INDIGO if cur_name else GRAY, anchor='w')
        cur_lbl.pack(fill='x', padx=16, pady=(0,4))

        instr_input_row = tk.Frame(inner, bg=BG)
        instr_input_row.pack(fill='x', padx=16, pady=(0,4))
        instr_name_var = tk.StringVar(value=cur_name)
        instr_entry = tk.Entry(instr_input_row, textvariable=instr_name_var, font=FS, relief='solid', bd=1, highlightthickness=0, width=24)
        instr_entry.pack(side='left', ipady=4, padx=(0, 6))
        status_lbl = tk.Label(instr_input_row, text="", font=FS, bg=BG, fg=GRAY)
        status_lbl.pack(side='left')

        def _lookup_instr():
            name = instr_name_var.get().strip()
            if not name:
                messagebox.showwarning("알림", "강사 이름을 입력하세요.", parent=win)
                return
            url = fb_url_var.get().strip()
            path = fb_path_var.get().strip()
            if not url or not path:
                messagebox.showwarning("알림", "Firebase URL과 경로를 먼저 입력하세요.", parent=win)
                return
            self.config['firebase_url'] = url
            self.config['firebase_path'] = path
            status_lbl.config(text="조회 중...", fg=GRAY)
            lookup_btn.config(state='disabled')

            def _fetch():
                try:
                    from firebase import firebase_get, firebase_put
                    data = firebase_get(self.config, f"config/instructors/{name}")
                    is_new = not data
                    if is_new:
                        firebase_put(self.config, f"config/instructors/{name}", {"assignments": [], "presets": []})

                    self.config['instructor_id'] = name
                    self._sync_shared_sheets_from_firebase()

                    if is_new:
                        # 신규 강사: assignments 없음 → 전체 학생 노출 방지
                        self.config['instructor_assignments'] = []
                        win.after(0, lambda: messagebox.showinfo(
                            "안내",
                            f"신규 강사 계정 [{name}]을 등록했습니다.\n웹에서 담당 수업을 배정하세요.",
                            parent=win))
                    else:
                        asgn = data.get("assignments", [])
                        self.config['instructor_assignments'] = asgn if isinstance(asgn, list) else []
                    
                    win.after(0, lambda: [
                        cur_lbl.config(text=f"현재 계정: {name}", fg=INDIGO),
                        status_lbl.config(text="조회/인증 성공", fg=GREEN),
                        lookup_btn.config(state='normal')
                    ])
                except Exception as e:
                    win.after(0, lambda: [
                        messagebox.showerror("오류", f"계정 처리 실패:\n{e}", parent=win),
                        status_lbl.config(text="조회 실패", fg=YELLOW),
                        lookup_btn.config(state='normal')
                    ])
            threading.Thread(target=_fetch, daemon=True).start()

        lookup_btn = tk.Button(instr_input_row, text="조회 및 설정", font=FS, bg=DARK, fg='white', relief='flat', padx=10, command=_lookup_instr, cursor='hand2')
        lookup_btn.pack(side='left', padx=2)

        fetch_row = tk.Frame(inner, bg=BG)
        fetch_row.pack(fill='x', padx=16, pady=(4,10))
        
        def _fetch_class_data():
            url = fb_url_var.get().strip()
            path = fb_path_var.get().strip()
            if not url or not path or not self.config.get('instructor_id'):
                messagebox.showwarning("알림", "강사 계정 조회를 먼저 완료해 주세요.", parent=win)
                return
            try:
                from firebase import firebase_get
                self._sync_shared_sheets_from_firebase()
                asgn = firebase_get(self.config, f"config/instructors/{self.config['instructor_id']}/assignments")
                if isinstance(asgn, list):
                    self.config['instructor_assignments'] = asgn
                elif isinstance(asgn, dict):
                    self.config['instructor_assignments'] = list(asgn.values())
                else:
                    self.config['instructor_assignments'] = []
                save_config(self.config)
                self._switch_sheet(self.activeGroup)
                messagebox.showinfo("성공", "Firebase로부터 학급 명단 동기화 완료!", parent=win)
            except Exception as e:
                messagebox.showerror("오류", f"명단 가져오기 실패:\n{e}", parent=win)

        tk.Button(fetch_row, text="🔄 학급/명단 동기화", font=FS, bg="#F1F5F9", fg=TEXT, relief='solid', bd=1, padx=10, pady=4, cursor='hand2', command=_fetch_class_data).pack(side='left')
        tk.Label(fetch_row, text="계정 조회 후 클릭하세요", font=FS, bg=BG, fg=GRAY).pack(side='left', padx=8)

        # ── 🤖 ④ AI 특이사항 생성 엔진 다중화 (요청 사항 반영) ───────────────────────────
        tk.Frame(inner, bg=BORDER, height=1).pack(fill='x', padx=16, pady=(4,0))
        self._settings_section(inner, "AI 특이사항 생성 엔진 설정")
        tk.Label(inner, text="사용할 AI 엔진을 선택하고 API Key를 입력하세요. 중앙 패널에서 ✨ AI생성 버튼이 연동됩니다.", font=FS, bg=BG, fg=SUBTEXT, justify='left', wraplength=460).pack(anchor='w', padx=16, pady=(0,6))

        ai_grid = tk.Frame(inner, bg=BG)
        ai_grid.pack(fill='x', padx=16, pady=(0,10))
        ai_grid.columnconfigure(1, weight=1)

        # 엔진 드롭다운 — 표시명(공식 표기)을 보여주고 내부 id로 매핑
        _label2id = {AI_ENGINE_LABELS[i]: i for i in AI_ENGINE_ORDER}
        _cur_id = self.config.get('ai_engine_type', 'gemini').strip().lower()
        if _cur_id not in AI_ENGINE_LABELS:
            _cur_id = 'gemini'
        tk.Label(ai_grid, text="AI 엔진 종류", font=FS, bg=BG, fg=SUBTEXT).grid(row=0, column=0, sticky='w', pady=6, padx=(0,8))
        engine_var = tk.StringVar(value=AI_ENGINE_LABELS[_cur_id])
        cmb_engine = ttk.Combobox(ai_grid, textvariable=engine_var, state="readonly", font=FS)
        cmb_engine['values'] = tuple(AI_ENGINE_LABELS[i] for i in AI_ENGINE_ORDER)
        cmb_engine.grid(row=0, column=1, sticky='ew', pady=6)

        # API Key 입력 폼
        tk.Label(ai_grid, text="API Key", font=FS, bg=BG, fg=SUBTEXT).grid(row=1, column=0, sticky='w', pady=3, padx=(0,8))

        def _selected_engine_id():
            return _label2id.get(engine_var.get(), 'gemini')

        def _key_for_engine(eng):
            # 엔진별 고유 키만 반환 (공유 ai_api_key 폴백 제거 — 엔진 전환 시 타 엔진 키 노출 방지)
            return self.config.get(f'{eng}_api_key', '').strip()

        default_key = _key_for_engine(_cur_id)
        ai_key_var = tk.StringVar(value=default_key)
        ai_entry = tk.Entry(ai_grid, textvariable=ai_key_var, font=FS, show='*', relief='flat', bg="#F8FAFC", highlightbackground=BORDER, highlightthickness=1)
        ai_entry.grid(row=1, column=1, sticky='ew', ipady=3)

        def _on_engine_change(event=None):
            ai_key_var.set(_key_for_engine(_selected_engine_id()))
        cmb_engine.bind('<<ComboboxSelected>>', _on_engine_change)

        def _toggle_ai_vis():
            ai_entry.config(show='' if ai_entry.cget('show') == '*' else '*')
        tk.Button(ai_grid, text="👁", font=FS, bg=BG, fg=GRAY, relief='flat', command=_toggle_ai_vis, cursor='hand2').grid(row=1, column=2, padx=4)

        # ── ⑤ 하단 컨트롤 (저장) ───────────────────────────────────
        tk.Frame(inner, bg=BORDER, height=1).pack(fill='x', padx=16, pady=(10,0))
        
        def _save_all():
            try:
                try:
                    self.config['wait_time'] = float(wait_var.get().strip())
                except ValueError:
                    self.config['wait_time'] = 0.5
                self.config['room_prefix'] = prefix_var.get().strip()

                self.config['firebase_url'] = fb_url_var.get().strip()
                self.config['firebase_path'] = fb_path_var.get().strip()

                # 엔진 다중화 세팅 주입 — 키는 엔진별 슬롯에만 저장 (공유 ai_api_key 미사용)
                chosen_engine = _selected_engine_id()
                chosen_key = ai_key_var.get().strip()

                self.config['ai_engine_type'] = chosen_engine
                self.config[f'{chosen_engine}_api_key'] = chosen_key

                save_config(self.config)

                self._populate_student_list(self.activeGroup)
                self._refresh_student_view()
                
                messagebox.showinfo("완료", "모든 설정이 안전하게 로컬에 저장되었습니다.", parent=win)
                win.destroy()
            except Exception as err:
                messagebox.showerror("오류", f"설정 저장 실패:\n{err}", parent=win)

        btn_row = tk.Frame(inner, bg=BG)
        btn_row.pack(fill='x', padx=16, pady=20)
        tk.Button(btn_row, text="💾 설정 저장하기", font=FT, bg=INDIGO, fg='white', relief='flat', padx=20, pady=8, command=_save_all, cursor='hand2').pack(side='right')
        tk.Button(btn_row, text="취소", font=FS, bg="#E2E8F0", fg=TEXT, relief='flat', padx=16, pady=8, command=win.destroy, cursor='hand2').pack(side='right', padx=8)


    def _gen_ai_note(self, group, classId, nameKey, subjects, note_txt, ai_btn=None, tb_grade=None):
        """AI 특이사항 단건 생성 — AiEngine에 위임."""
        self.ai.gen_single(group, classId, nameKey, subjects, note_txt, ai_btn, tb_grade=tb_grade)

    def _start_cooldown_tick(self, btn):
        """AI 쿨다운 틱 — AiEngine에 위임."""
        self.ai._start_cooldown_tick(btn)

    def _gen_ai_note_all(self):
        """일괄 AI 생성 — AiEngine에 위임."""
        self.ai.gen_all(self.activeGroup)

    def _settings_section(self, parent, title):
        tk.Label(parent, text=title,
                 font=("맑은 고딕", 10, "bold"), bg=BG, fg=TEXT
                 ).pack(anchor='w', padx=16, pady=(12,4))

    # ── 카카오톡 전송 ────────────────────────────────────────────────
    def _send(self):
        if not AUTOMATION:
            messagebox.showerror("오류",
                "pyautogui / pyperclip이 설치되어 있지 않습니다.\n"
                "pip install pyautogui pyperclip"); return
        group  = self.activeGroup
        ready  = self._collect_ready(group)
        if not ready:
            messagebox.showinfo("알림",
                "전송 준비된 학생이 없습니다.\n"
                "모든 교재의 과제수행도를 입력한 학생만 전송됩니다."); return

        all_names = [
            self.all_students[nk].get('name', nk)
            for classId, cd in self._my_classes(group)
            if not self._is_sub_teacher(classId)
            for nk in [k for k, v in self.all_students.items() if v.get('class') == classId]
        ]
        ready_names = [r['name'] for r in ready]
        skipped = [n for n in all_names if n not in ready_names]

        confirm_msg = f"전송 대상: {len(ready)}명\n" + ", ".join(ready_names)
        if skipped:
            confirm_msg += f"\n\n제외 (미입력): {len(skipped)}명\n" + ", ".join(skipped)
        confirm_msg += "\n\n카카오톡 창 활성화 후 [예]를 누르세요. (3초 후 시작)"

        if not messagebox.askyesno("전송 확인", confirm_msg): return
        threading.Thread(target=self._do_send, args=(ready,), daemon=True).start()

    def _do_send(self, msgs):
        wait  = self.config.get('wait_time', 0.5)
        total = len(msgs)
        time.sleep(3)
        for i, m in enumerate(msgs):
            self.root.after(0, lambda t=f"전송 중... ({i+1}/{total})  {m['name']}":
                            self.send_status.config(text=t))
            try:
                pyperclip.copy(m['room'])
                pyautogui.hotkey(_MOD,'f'); time.sleep(0.2)
                pyautogui.press('esc');       time.sleep(0.2)
                pyautogui.hotkey(_MOD,'f'); time.sleep(wait)
                pyautogui.hotkey(_MOD,'v'); time.sleep(wait)
                pyautogui.press('enter');     time.sleep(wait)
                pyperclip.copy(m['msg'])
                pyautogui.hotkey(_MOD,'v'); time.sleep(0.2)
                pyautogui.press('enter');     time.sleep(0.3)
                pyautogui.press('esc')
            except Exception as e:
                print(f"오류 [{m['name']}]: {e}")
            time.sleep(0.8)

        def _on_done():
            self.send_status.config(text=f"✅ 전송 완료 — {total}명")
            self._reset_after_send()
            messagebox.showinfo("완료", f"{total}명 전송 완료!")
        self.root.after(0, _on_done)

    def _reset_after_send(self):
        """전송 완료 후 로컬 전면 초기화 (진도/과제 포함) — DB 쓰기는 lastSent만"""
        self.student_data.clear()
        self.note_data.clear()
        self.progress_data.clear()
        self.force_data.clear()
        save_daily_cache(self.progress_data, {}, {}, {})

        url  = self.config.get('firebase_url', '')
        path = self.config.get('firebase_path', '')
        if url and path:
            def _push_last_sent():
                try:
                    firebase_put(self.config, "lastSent", {
                        "date": self.date_str,
                        "class_data": {}
                    })
                except Exception as e:
                    print(f"lastSent push 실패: {e}")
            threading.Thread(target=_push_last_sent, daemon=True).start()

        self.root.after(0, self._refresh_after_reset)

    def _refresh_after_reset(self):
        if self.cur_name:
            self._render_student(self.activeGroup, self.cur_cls, self.cur_name)
        self._refresh_send_btn()
        self._refresh_statusbar()
