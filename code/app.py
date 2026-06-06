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
    ASSIGN_GRADE_LABELS, grade_label, TAGS,
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
        self._send_cancel = None       # 순차 전송 취소 플래그 (threading.Event)
        self._ai_last_call = 0.0       # 하위 호환용 (AiEngine이 갱신)
        self.ai = AiEngine(self)       # AI 생성 엔진

        self._main_built = False
        # Firebase 미설정(최초 실행) 시: 정상 UI 대신 메인 창에 설치 위저드를 띄운다.
        # 위저드 완료/이탈 시 정상 레이아웃을 빌드 → 팝업 없이 한 창에서 단계 전환.
        if not self.config.get('firebase_url') or not self.config.get('firebase_path'):
            self._run_setup_wizard()
        else:
            self._build_main_ui()
            # 공용 교재/학급 목록은 Firebase students/+classes를 단일 원본으로 사용
            self.root.after(300, self._sync_shared_sheets_from_firebase)

    def _build_main_ui(self):
        """정상 3-패널 메인 레이아웃 빌드 (위저드 종료 후/일반 실행 시)."""
        self._build_header()
        self._build_sheet_bar()
        self._build_panels()
        self._build_statusbar()
        self._build_footer()
        self._switch_sheet('M')
        self._main_built = True

    def _sync_shared_sheets_from_firebase(self):
        """시작 시 Firebase students/ + classes/ + config/ 동기화."""
        try:
            config_data = firebase_get(self.config, "config") or {}

            # 학생 명단 및 학급 구조 (v2.0 스키마)
            fetched_students = firebase_get(self.config, "students") or {}
            fetched_classes  = firebase_get(self.config, "classes") or {}
            if isinstance(fetched_students, dict):
                # 표시 순서만 이름 오름차순 — 키(nameKey=출결번호)는 불변.
                # 모든 .items() 순회가 이 순서를 상속 → 빌더별 정렬 불일치 원천 차단.
                # None-safe(이름 누락 폴백 '') + 동명이인 tiebreak(nameKey).
                self.all_students = dict(sorted(
                    fetched_students.items(),
                    key=lambda kv: (
                        (kv[1].get('name') if isinstance(kv[1], dict) else None) or '',
                        kv[0])))
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
        bar = tk.Frame(self.root, bg="#ECECEF")
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
                  bg="#ECECEF", fg=SUBTEXT, relief='flat', cursor='hand2',
                  command=self._open_settings
                  ).pack(side='right', padx=4, pady=3)
        tk.Button(bar, text="🗑 초기화", font=FS,
                  bg="#ECECEF", fg="#EF4444", relief='flat', cursor='hand2',
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
        hdr = tk.Frame(f, bg="#F7F7F9",
                       highlightbackground=BORDER, highlightthickness=1)
        hdr.pack(fill='x')
        self.c_name = tk.Label(hdr, text="—",
                               font=("맑은 고딕", 13, "bold"),
                               bg="#F7F7F9", fg=TEXT)
        self.c_name.pack(side='left', padx=14, pady=10)
        self.c_sub = tk.Label(hdr, text="", font=FS, bg="#F7F7F9", fg=GRAY)
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
                font=FS, bg="#F7F7F9", fg=GRAY,
                relief='flat', padx=8, pady=3, state='disabled')
        elif is_forced:
            force_btn = tk.Button(
                force_btn_frame, text="⚡ 강제 완료 (ON) — 클릭하여 해제",
                font=FS, bg="#ECFDF3", fg="#15803D",
                relief='flat', padx=8, pady=3, cursor='hand2',
                command=_toggle_force)
        else:
            force_btn = tk.Button(
                force_btn_frame, text="⚡ 강제 완료",
                font=FS, bg="#F7F7F9", fg=SUBTEXT,
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
                               fg="#0F6E56", bg="#ECFDF3", padx=10, pady=8,
                               highlightbackground="#BBF7D0")
            pf.pack(fill='x', pady=(0, 12))
            for subject in subjects:
                pd_val = self.progress_data.get((classId, subject), {})
                if pd_val.get('progress') or pd_val.get('homework'):
                    tb_lbl = grade_label(tb_grade.get(subject, ''), subject)
                    tk.Label(pf, text=tb_lbl, font=("맑은 고딕", 8, "bold"),
                             bg="#ECFDF3", fg=INDIGO).pack(anchor='w', pady=(2,0))
                    if pd_val.get('progress'):
                        tk.Label(pf, text=f"  진도: {pd_val['progress']}",
                                 font=FS, bg="#ECFDF3", fg=TEXT
                                 ).pack(anchor='w')
                    if pd_val.get('homework'):
                        tk.Label(pf, text=f"  과제: {pd_val['homework']}",
                                 font=FS, bg="#ECFDF3", fg=TEXT
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

            # ── 오늘 선택된 수업 관찰 태그 (읽기 전용, 한 줄 압축) ──
            self._render_obs_tags(lf, nameKey, subject)

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
                           font=("맑은 고딕", 8), bg="#EEF0FF", fg=INDIGO,
                           relief='flat', padx=8, pady=2, cursor='hand2')
        ai_btn.pack(side='right')

        # 부담임 과목은 AI생성 비활성화
        if self._is_sub_teacher(classId):
            ai_btn.config(state='disabled', text="✨ AI생성 (부담임)",
                          bg="#F7F7F9", fg=GRAY, cursor='arrow')
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
        note_txt = tk.Text(pad, font=_note_font, bg="#F7F7F9", fg=TEXT,
                           relief='flat', wrap='word', height=6,
                           undo=True,
                           highlightbackground=BORDER, highlightthickness=1,
                           padx=6, pady=4)
        note_txt.pack(fill='x', pady=(0, 2))
        if note_val.strip():
            note_txt.insert('1.0', note_val)

        if is_sub:
            # 부담임: 읽기 전용 잠금 — FocusOut·Firebase PATCH 없음
            note_txt.config(state='disabled', bg="#F7F7F9", fg=GRAY)
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

    # ── 오늘 선택된 관찰 태그 (읽기 전용 표시) ──────────────────────────
    def _obs_tag_segments(self, nameKey, subject):
        """오늘(today_key) obs 태그 → [(라벨, 색)] 세그먼트. 빈 카테고리 제외.
        웹에서 선택한 condition/understand/engage/extra/highlight/caution 을
        표시 순서대로 펼친다. highlight=초록, caution=빨강 강조."""
        day = today_key()
        rec = (self.tag_data.get(nameKey, {}) or {}).get(subject, {}) or {}
        t = rec.get(day, {}) or {}
        if not t:
            return []

        def _lut(field):
            return {d['key']: d['label'] for d in TAGS.get(field, [])}

        def _multi(field, color):
            lut = _lut(field)
            return [(lut[k], color) for k in (t.get(field) or []) if k in lut]

        segs = []
        # 컨디션 (단일)
        c = t.get('condition')
        if c and c in _lut('condition'):
            segs.append((_lut('condition')[c], TEXT))
        # 이해도 (단일) + 세부 (멀티)
        u = t.get('understand')
        if u and u in _lut('understand'):
            segs.append((_lut('understand')[u], TEXT))
        segs += _multi('understand_sub', TEXT)
        # 참여·기타 (멀티)
        segs += _multi('engage', TEXT)
        segs += _multi('extra', TEXT)
        # 하이라이트 (초록) — highlight 는 단일/리스트 혼재 가능
        hl = t.get('highlight')
        hl = hl if isinstance(hl, list) else ([hl] if hl else [])
        hlut = _lut('highlight')
        segs += [(hlut[k], GREEN) for k in hl if k in hlut]
        # 주의 (빨강) — 마지막
        segs += _multi('caution', "#DC2626")
        return segs

    def _render_obs_tags(self, parent, nameKey, subject):
        """관찰 태그 세그먼트를 한 줄(가로)로 색별 Label 렌더. 없으면 미표시."""
        segs = self._obs_tag_segments(nameKey, subject)
        if not segs:
            return
        import sys as _sys
        tag_font = ("Segoe UI Emoji", 9) if _sys.platform == "win32" else FE
        bg = parent.cget('bg')
        rowf = tk.Frame(parent, bg=bg)
        rowf.pack(fill='x', pady=(5, 0))
        for i, (text, color) in enumerate(segs):
            if i:
                tk.Label(rowf, text="·", font=tag_font, bg=bg, fg="#D1D5DB"
                         ).pack(side='left', padx=2)
            tk.Label(rowf, text=text, font=tag_font, bg=bg, fg=color
                     ).pack(side='left')

    # ── 우측 ─────────────────────────────────────────────────────────
    def _build_right(self, parent):
        f = tk.Frame(parent, bg=PANEL, width=300,
                     highlightbackground=BORDER, highlightthickness=1)
        f.grid(row=0, column=2, sticky='nsew')
        f.pack_propagate(False)
        parent.columnconfigure(2, minsize=300)
        self.right_frame = f

        # 헤더
        rh = tk.Frame(f, bg="#F7F7F9",
                      highlightbackground=BORDER, highlightthickness=1)
        rh.pack(fill='x')
        self._dot_c = tk.Canvas(rh, width=10, height=10,
                                bg="#F7F7F9", highlightthickness=0)
        self._dot_id = self._dot_c.create_oval(2,2,9,9, fill=GREEN, outline="")
        self._dot_c.pack(side='left', padx=(12,4), pady=10)
        self._pulse()
        tk.Label(rh, text="미리보기",
                 font=FT, bg="#F7F7F9", fg=TEXT).pack(side='left')
        self.char_lbl = tk.Label(rh, text="0자", font=FS, bg="#F7F7F9", fg=GRAY)
        self.char_lbl.pack(side='right', padx=12)

        self.to_lbl = tk.Label(f, text="", font=FS,
                               bg=INDIGO_L, fg=INDIGO, anchor='w', padx=10, pady=3)
        self.to_lbl.pack(fill='x')

        self.preview = tk.Text(f, font=("맑은 고딕", 9), wrap='word',
                               relief='flat', bg="#F7F7F9", bd=0,
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
        sb = tk.Frame(self.root, bg="#ECFDF3",
                      highlightbackground="#BBF7D0", highlightthickness=1)
        sb.pack(fill='x')
        self.status_lbl = tk.Label(sb, text="", font=FS,
                                   bg="#ECFDF3", fg="#15803D", anchor='w')
        self.status_lbl.pack(side='left', padx=12, pady=4)
        tk.Label(sb, text="● 완료   ◐ 진행중   ○ 미입력",
                 font=FS, bg="#ECFDF3", fg=GRAY).pack(side='right', padx=12)
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
            bg="#ECECEF", fg=GRAY, relief='flat',
            padx=14, pady=8, cursor='hand2',
            command=self._send)
        self.send_btn.pack(side='right', padx=10, pady=8)

        # ✨ 전체 AI 생성 버튼 (STATUS_READY 학생 일괄 처리)
        self.ai_all_btn = tk.Button(
            foot, text="✨ 전체 AI 생성",
            font=("맑은 고딕", 9), bg="#EEF0FF", fg=INDIGO,
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
                result.append({'name': display_name, 'room': get_room(self.config, display_name), 'msg': msg,
                               'nameKey': nameKey, 'classId': classId, 'note': note})
        return result

    def _refresh_send_btn(self):
        n = len(self._collect_ready(self.activeGroup))
        self.send_btn.config(
            text=f"🚀  카카오톡 전송 ({n}명)",
            bg=ACCENT if n>0 else "#ECECEF",
            fg="#0E1016" if n>0 else GRAY)

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
                # session 노드 없음 — lastSent 폐기됨, 폴백 없음
                class_data = {}
                date_str   = ""
            else:
                # session 노드 존재 (비어있어도 의도적 상태)
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
        """Firebase input/ 노드에서 특이사항(note) 반영 (v2.1.2 스키마)
        구조: {nameKey: {__note__: {note}}}
        · note(특이사항): 학생별 단일(__note__). 항상 웹 데이터로 교체.
          구 과목별 note 데이터는 fallback 으로 1건 보존(마이그레이션 전 호환).
        · 과제수행도(assign)는 더 이상 input/ 에서 읽지 않음 — obs/assign_grade 가 단일 소스.
        """
        if not data:
            return

        for nameKey, subjects in data.items():
            if not isinstance(subjects, dict):
                continue
            classId = self.all_students.get(nameKey, {}).get('class', '')
            if not classId:
                continue
            note_key   = (classId, nameKey)
            note_val   = ''
            legacy_note = ''   # 구 과목별 note fallback 후보
            for subject, payload in subjects.items():
                if not isinstance(payload, dict):
                    continue
                if subject == '__note__':
                    note_val = payload.get('note', '') or note_val
                elif not legacy_note:
                    legacy_note = payload.get('note', '') or ''
            final = note_val or legacy_note
            if final:
                self.note_data[note_key] = {'value': final}

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
            b.config(bg=PANEL if s==group else "#ECECEF",
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
    # ── 최초 설치 위저드 (온보딩) ─────────────────────────────────
    _WZ_STEPS = [("🔥", "연결"), ("🔑", "계정"), ("🤖", "AI 키")]
    # 엔진별 키 발급 상세 (guide.html 4부 발췌)
    _WZ_GUIDE = {
        'gemini': {'tag': '무료', 'tagc': 'free',
                   'url': 'https://aistudio.google.com/apikey', 'label': 'aistudio.google.com/apikey',
                   'lead': 'Google AI Studio · 카드 등록 불필요, 월 제한 없음(하루 요청 한도만).',
                   'fmt': 'AIza... 또는 AQ.Ab8...',
                   'steps': ['Google 계정 로그인 후 위 링크 접속',
                             '「API 키 만들기」 클릭 → 새 프로젝트에서 생성 권장',
                             '발급된 키 복사'],
                   'warn': '호출 시 limit: 0 오류 → 그 프로젝트 무료 할당 막힘. 새 프로젝트로 재발급.'},
        'claude': {'tag': '유료', 'tagc': 'paid',
                   'url': 'https://console.anthropic.com', 'label': 'console.anthropic.com',
                   'lead': 'Anthropic Console · 문장 품질 최상, 크레딧 충전(결제) 필요.',
                   'fmt': 'sk-ant-...',
                   'steps': ['위 링크에서 Anthropic Console 가입',
                             'Billing 메뉴서 결제수단 등록 + 크레딧 충전(최소 $5)',
                             'Settings › API Keys › Create Key 로 발급'],
                   'warn': '키는 생성 직후 한 번만 표시됨 — 즉시 복사.'},
        'openai': {'tag': '유료', 'tagc': 'paid',
                   'url': 'https://platform.openai.com/api-keys', 'label': 'platform.openai.com/api-keys',
                   'lead': 'OpenAI Platform · 범용 품질, 결제 등록 필요.',
                   'fmt': 'sk-...',
                   'steps': ['위 링크에서 OpenAI Platform 접속',
                             'Billing서 결제수단 등록 + 크레딧 충전',
                             '「Create new secret key」 클릭 → 복사'],
                   'warn': '키는 생성 직후 한 번만 표시됨 — 즉시 복사.'},
        'groq':   {'tag': '무료', 'tagc': 'free',
                   'url': 'https://console.groq.com/keys', 'label': 'console.groq.com/keys',
                   'lead': 'Groq Console · 무료·매우 빠름. 분당 요청수(RPM) 제한 있어 연속 생성 시 대기 가능.',
                   'fmt': 'gsk_...',
                   'steps': ['위 링크에서 Groq Console 가입',
                             '「Create API Key」 클릭 → 복사'],
                   'warn': ''},
    }

    def _prompt_first_run(self):
        """최초 실행 — 3단계 설치 위저드 (Firebase·강사·AI키)."""
        self._run_setup_wizard()

    def _run_setup_wizard(self):
        if getattr(self, '_wz_root', None) is not None and self._wz_root.winfo_exists():
            return

        # 팝업(Toplevel) 대신 메인 창 전체를 덮는 오버레이 프레임. 완료/이탈 시 destroy하여
        # 그 아래 정상 3-패널 레이아웃을 노출(없으면 빌드) → 한 창에서 레이아웃 분기.
        overlay = tk.Frame(self.root, bg=BG)
        overlay.place(x=0, y=0, relwidth=1, relheight=1)
        self._wz_root = overlay

        hdr = tk.Frame(overlay, bg=DARK, height=40); hdr.pack(fill='x'); hdr.pack_propagate(False)
        tk.Label(hdr, text=f"📝 {APP_TITLE} {APP_VERSION} — 최초 설치 설정", font=FT, bg=DARK, fg='white').pack(side='left', padx=16)

        # 가운데 정렬 카드 (메인 창 폭과 무관하게 560px 고정)
        card = tk.Frame(overlay, bg=BG)
        card.place(relx=0.5, rely=0.05, anchor='n', width=560)

        tk.Label(card, text="처음 설치하셨네요 👋", font=("맑은 고딕", 14, "bold"), bg=BG, fg=INDIGO).pack(pady=(8, 0))
        tk.Label(card, text="3단계로 PC 클라이언트를 설정합니다", font=FS, bg=BG, fg=GRAY).pack()

        self._wz_steps_canvas = tk.Canvas(card, bg=BG, height=56, highlightthickness=0)
        self._wz_steps_canvas.pack(fill='x', padx=30, pady=(12, 2))

        self._wz_foot = tk.Frame(card, bg=BG)
        self._wz_foot.pack(fill='x', side='bottom')
        self._wz_body = tk.Frame(card, bg=BG)
        self._wz_body.pack(fill='both', expand=True)

        self._wz_step = 0
        self._wz_url_var  = tk.StringVar(value=self.config.get('firebase_url', ''))
        self._wz_path_var = tk.StringVar(value=self.config.get('firebase_path', ''))
        self._wz_name_var = tk.StringVar(value=self.config.get('instructor_id', ''))
        _cur = self.config.get('ai_engine_type', 'gemini').strip().lower()
        if _cur not in AI_ENGINE_LABELS:
            _cur = 'gemini'
        self._wz_engine_id = _cur
        self._wz_key_var = tk.StringVar(value=self.config.get(f'{_cur}_api_key', ''))
        self._wz_render()

    def _wz_draw_steps(self):
        c = self._wz_steps_canvas
        c.delete('all'); c.update_idletasks()
        w = c.winfo_width()
        if w < 50:
            w = 480
        n = len(self._WZ_STEPS); margin = 44; ys = 18; r = 15
        xs = [margin + (w - 2 * margin) * i / (n - 1) for i in range(n)]
        for i in range(n - 1):
            done = i < self._wz_step
            c.create_line(xs[i] + r, ys, xs[i + 1] - r, ys, fill=(GREEN if done else "#E2E6EE"), width=2)
        for i, (ic, lbl) in enumerate(self._WZ_STEPS):
            if i < self._wz_step:
                fill = GREEN; txt = "✓"; tcol = "white"
            elif i == self._wz_step:
                fill = INDIGO; txt = str(i + 1); tcol = "white"
            else:
                fill = "#E2E6EE"; txt = str(i + 1); tcol = GRAY
            c.create_oval(xs[i] - r, ys - r, xs[i] + r, ys + r, fill=fill, outline=fill)
            c.create_text(xs[i], ys, text=txt, fill=tcol, font=("맑은 고딕", 10, "bold"))
            lcol = INDIGO if i == self._wz_step else (GREEN if i < self._wz_step else GRAY)
            c.create_text(xs[i], ys + r + 12, text=lbl, fill=lcol, font=FS)

    def _wz_render(self):
        self._wz_draw_steps()
        for ch in self._wz_body.winfo_children():
            ch.destroy()
        for ch in self._wz_foot.winfo_children():
            ch.destroy()
        b = self._wz_body
        if self._wz_step == 3:
            self._wz_pane_done(b)
        elif self._wz_step == 0:
            self._wz_pane_head(b, "🔥", "Firebase 연결",
                               "데이터를 읽어올 Firebase 주소를 입력하세요. 웹 앱과 동일한 URL·경로를 사용합니다.")
            self._wz_pane_firebase(b)
        elif self._wz_step == 1:
            self._wz_pane_head(b, "🔑", "내 강사 계정",
                               "본인 이름으로 강사 계정을 조회하거나 새로 등록합니다.")
            self._wz_pane_account(b)
        elif self._wz_step == 2:
            self._wz_pane_head(b, "🤖", "AI 엔진 · API 키",
                               "특이사항 자동 생성에 쓸 AI 엔진을 고르고 키를 입력하세요. 지금 건너뛰어도 됩니다.")
            self._wz_pane_ai(b)
        self._wz_build_footer()

    def _wz_pane_head(self, b, ic, ti, de):
        tk.Label(b, text=ic, font=("맑은 고딕", 26), bg=BG).pack(pady=(6, 0))
        tk.Label(b, text=ti, font=("맑은 고딕", 14, "bold"), bg=BG, fg=TEXT).pack()
        tk.Label(b, text=de, font=FS, bg=BG, fg=SUBTEXT, wraplength=440, justify='center').pack(pady=(2, 12))

    def _wz_pane_firebase(self, b):
        g = tk.Frame(b, bg=BG); g.pack(fill='x', padx=40); g.columnconfigure(0, weight=1)
        tk.Label(g, text="Firebase DB URL", font=FS, bg=BG, fg=SUBTEXT).grid(row=0, column=0, sticky='w', pady=(0, 2))
        tk.Entry(g, textvariable=self._wz_url_var, font=FS, relief='solid', bd=1).grid(row=1, column=0, sticky='ew', ipady=4, pady=(0, 8))
        tk.Label(g, text="경로 (Secret Path)", font=FS, bg=BG, fg=SUBTEXT).grid(row=2, column=0, sticky='w', pady=(0, 2))
        tk.Entry(g, textvariable=self._wz_path_var, font=FS, relief='solid', bd=1).grid(row=3, column=0, sticky='ew', ipady=4, pady=(0, 8))
        tk.Button(g, text="⚡ 연결 테스트", font=FS, bg="#EEF0FF", fg=INDIGO, relief='flat', padx=10, pady=4,
                  cursor='hand2', command=self._wz_test_conn).grid(row=4, column=0, sticky='w')
        tk.Label(g, text="💡 웹(index.html)에서 쓰던 URL·경로를 그대로 입력하세요.", font=FS, bg=BG, fg=GRAY,
                 wraplength=440, justify='left').grid(row=5, column=0, sticky='w', pady=(8, 0))

    def _wz_test_conn(self):
        url = self._wz_url_var.get().strip(); path = self._wz_path_var.get().strip()
        if not url or not path:
            messagebox.showwarning("알림", "URL과 경로를 입력하세요.", parent=self.root); return
        try:
            result = firebase_get({'firebase_url': url, 'firebase_path': path}, "config")
            if result is None:
                messagebox.showwarning("주의", "연결은 성공했지만 config 노드가 비어있습니다.\nFirebase 경로를 확인하세요.", parent=self.root)
            else:
                messagebox.showinfo("성공", "Firebase 연결 테스트에 성공했습니다!", parent=self.root)
        except Exception as e:
            messagebox.showerror("실패", f"연결 실패:\n{e}", parent=self.root)

    def _wz_pane_account(self, b):
        cur = self.config.get('instructor_id', '')
        tk.Label(b, text="강사 이름", font=FS, bg=BG, fg=SUBTEXT).pack(anchor='w', padx=40)
        row = tk.Frame(b, bg=BG); row.pack(fill='x', padx=40, pady=(2, 4))
        tk.Entry(row, textvariable=self._wz_name_var, font=FS, relief='solid', bd=1).pack(side='left', fill='x', expand=True, ipady=4, padx=(0, 6))
        self._wz_lookup_btn = tk.Button(row, text="조회 및 설정", font=FS, bg=DARK, fg='white', relief='flat', padx=10, cursor='hand2', command=self._wz_lookup_instr)
        self._wz_lookup_btn.pack(side='left')
        self._wz_acct_status = tk.Label(b, text=(f"✓ {cur} 계정 준비 완료" if cur else ""), font=FS, bg=BG, fg=GREEN if cur else GRAY, anchor='w')
        self._wz_acct_status.pack(anchor='w', padx=40, pady=(2, 0))
        tk.Label(b, text="없으면 자동 등록됩니다. 담당 수업·학생 명단은 웹에서만 구성하고, PC는 📥 데이터 가져오기로 읽어옵니다.",
                 font=FS, bg=BG, fg=GRAY, wraplength=440, justify='left').pack(anchor='w', padx=40, pady=(8, 0))

    def _wz_lookup_instr(self):
        name = self._wz_name_var.get().strip()
        if not name:
            messagebox.showwarning("알림", "강사 이름을 입력하세요.", parent=self.root); return
        url = self._wz_url_var.get().strip(); path = self._wz_path_var.get().strip()
        if not url or not path:
            messagebox.showwarning("알림", "Firebase URL과 경로를 먼저 입력하세요.", parent=self.root); return
        self.config['firebase_url'] = url; self.config['firebase_path'] = path
        self._wz_acct_status.config(text="조회 중...", fg=GRAY)
        self._wz_lookup_btn.config(state='disabled')

        def _fetch():
            try:
                data = firebase_get(self.config, f"config/instructors/{name}")
                is_new = not data
                if is_new:
                    firebase_put(self.config, f"config/instructors/{name}", {"assignments": [], "presets": []})
                self.config['instructor_id'] = name
                self._sync_shared_sheets_from_firebase()
                if is_new:
                    self.config['instructor_assignments'] = []
                    msg = f"신규 강사 계정 [{name}]을 등록했습니다.\n웹에서 담당 수업을 배정하세요."
                else:
                    asgn = data.get("assignments", [])
                    self.config['instructor_assignments'] = asgn if isinstance(asgn, list) else []
                    msg = f"기존 강사 계정 [{name}]을 불러왔습니다."
                self.root.after(0, lambda: [
                    self._wz_acct_status.config(text=f"✓ {name} 계정 준비 완료", fg=GREEN),
                    self._wz_lookup_btn.config(state='normal'),
                    messagebox.showinfo("안내", msg, parent=self.root),
                ])
            except Exception as e:
                self.root.after(0, lambda: [
                    self._wz_acct_status.config(text="조회 실패", fg=YELLOW),
                    self._wz_lookup_btn.config(state='normal'),
                    messagebox.showerror("오류", f"계정 처리 실패:\n{e}", parent=self.root),
                ])
        threading.Thread(target=_fetch, daemon=True).start()

    def _wz_pane_ai(self, b):
        g = tk.Frame(b, bg=BG); g.pack(fill='x', padx=40); g.columnconfigure(0, weight=1)
        tk.Label(g, text="AI 엔진", font=FS, bg=BG, fg=SUBTEXT).grid(row=0, column=0, sticky='w', pady=(0, 2))
        self._wz_engine_var = tk.StringVar(value=AI_ENGINE_LABELS[self._wz_engine_id])
        cmb = ttk.Combobox(g, textvariable=self._wz_engine_var, state="readonly", font=FS,
                           values=tuple(AI_ENGINE_LABELS[i] for i in AI_ENGINE_ORDER))
        cmb.grid(row=1, column=0, sticky='ew', pady=(0, 8))
        cmb.bind('<<ComboboxSelected>>', self._wz_on_engine)
        self._wz_build_guide(b)
        g2 = tk.Frame(b, bg=BG); g2.pack(fill='x', padx=40, pady=(10, 0)); g2.columnconfigure(0, weight=1)
        tk.Label(g2, text="API 키", font=FS, bg=BG, fg=SUBTEXT).grid(row=0, column=0, sticky='w', pady=(0, 2))
        self._wz_key_entry = tk.Entry(g2, textvariable=self._wz_key_var, font=FS, show='*', relief='solid', bd=1)
        self._wz_key_entry.grid(row=1, column=0, sticky='ew', ipady=4)
        tk.Button(g2, text="👁", font=FS, bg=BG, fg=GRAY, relief='flat', cursor='hand2', command=self._wz_toggle_key).grid(row=1, column=1, padx=4)
        tk.Label(b, text="AI 생성을 안 쓰면 비워도 됩니다 — 건너뛰기 가능.", font=FS, bg=BG, fg=GRAY,
                 wraplength=440, justify='left').pack(anchor='w', padx=40, pady=(6, 0))

    def _wz_on_engine(self, event=None):
        label2id = {AI_ENGINE_LABELS[i]: i for i in AI_ENGINE_ORDER}
        self._wz_engine_id = label2id.get(self._wz_engine_var.get(), 'gemini')
        self._wz_key_var.set(self.config.get(f'{self._wz_engine_id}_api_key', ''))
        self._wz_render()

    def _wz_toggle_key(self):
        self._wz_key_entry.config(show='' if self._wz_key_entry.cget('show') == '*' else '*')

    def _wz_build_guide(self, parent):
        import webbrowser
        gd = self._WZ_GUIDE[self._wz_engine_id]
        box = tk.Frame(parent, bg=PANEL, highlightbackground=BORDER, highlightthickness=1)
        box.pack(fill='x', padx=40)
        hd = tk.Frame(box, bg=PANEL); hd.pack(fill='x', padx=11, pady=(9, 4))
        pill_bg = "#ECFDF3" if gd['tagc'] == 'free' else "#FFFAEB"
        pill_fg = "#15803D" if gd['tagc'] == 'free' else "#92400E"
        tk.Label(hd, text=f" {gd['tag']} ", font=("맑은 고딕", 8, "bold"), bg=pill_bg, fg=pill_fg).pack(side='left')
        tk.Label(hd, text=gd['lead'], font=FS, bg=PANEL, fg=SUBTEXT, wraplength=350, justify='left').pack(side='left', padx=6)
        link = tk.Label(box, text=f"🔗 {gd['label']} 열기", font=("맑은 고딕", 9, "bold", "underline"), bg=PANEL, fg=INDIGO, cursor='hand2')
        link.pack(anchor='w', padx=11, pady=(0, 6))
        link.bind('<Button-1>', lambda e, u=gd['url']: webbrowser.open(u))
        for i, t in enumerate(gd['steps']):
            sr = tk.Frame(box, bg=PANEL); sr.pack(fill='x', padx=11, pady=1)
            tk.Label(sr, text=str(i + 1), font=("맑은 고딕", 8, "bold"), bg=INDIGO, fg='white', width=2).pack(side='left')
            tk.Label(sr, text=t, font=FS, bg=PANEL, fg=TEXT, wraplength=380, justify='left').pack(side='left', padx=6)
        tk.Label(box, text=f"키 형식: {gd['fmt']}", font=FS, bg=PANEL, fg=SUBTEXT).pack(anchor='w', padx=11, pady=(6, 0))
        if gd['warn']:
            tk.Label(box, text=f"⚠️ {gd['warn']}", font=FS, bg="#FFFAEB", fg="#92400E", wraplength=400, justify='left').pack(fill='x', padx=11, pady=(6, 9))
        else:
            tk.Frame(box, bg=PANEL, height=6).pack()

    def _wz_pane_done(self, b):
        tk.Label(b, text="🎉", font=("맑은 고딕", 34), bg=BG).pack(pady=(6, 0))
        tk.Label(b, text="설정 완료!", font=("맑은 고딕", 14, "bold"), bg=BG, fg=TEXT).pack()
        tk.Label(b, text="이제 데이터를 가져와 사용을 시작하세요.", font=FS, bg=BG, fg=SUBTEXT).pack(pady=(2, 10))
        fb_ok = bool(self._wz_url_var.get().strip() and self._wz_path_var.get().strip())
        instr = self.config.get('instructor_id', '')
        key = self._wz_key_var.get().strip()
        eng = AI_ENGINE_LABELS.get(self._wz_engine_id, self._wz_engine_id)
        rows = [
            (fb_ok, "Firebase 연결됨" if fb_ok else "Firebase 미연결"),
            (bool(instr), f"강사 계정: {instr or '미설정'}"),
            (bool(key), f"AI 엔진: {eng}" + ("" if key else " (키 미입력 — 나중에)")),
        ]
        for ok, txt in rows:
            r = tk.Frame(b, bg=PANEL, highlightbackground=BORDER, highlightthickness=1); r.pack(fill='x', padx=40, pady=3)
            tk.Label(r, text=("✓" if ok else "–"), font=("맑은 고딕", 10, "bold"), bg=PANEL, fg=GREEN if ok else GRAY, width=2).pack(side='left', padx=(8, 0), pady=6)
            tk.Label(r, text=txt, font=FS, bg=PANEL, fg=TEXT).pack(side='left', padx=4)
        tk.Label(b, text="📌 다음 단계 — 학생 명단·담당 수업은 웹(index.html)에서 구성한 뒤,\n상단 📥 데이터 가져오기 버튼으로 PC에 불러오세요.",
                 font=FS, bg="#FFFAEB", fg="#92400E", wraplength=420, justify='left').pack(fill='x', padx=40, pady=(12, 0))

    def _wz_build_footer(self):
        f = self._wz_foot
        inner = tk.Frame(f, bg=BG); inner.pack(fill='x', padx=30, pady=12)
        if self._wz_step == 3:
            tk.Button(inner, text="✅ 설정 완료", font=FT, bg=INDIGO, fg='white', relief='flat', pady=8, cursor='hand2', command=self._wz_commit).pack(fill='x')
            return
        if self._wz_step > 0:
            tk.Button(inner, text="← 이전", font=FS, bg="#ECECEF", fg=TEXT, relief='flat', padx=14, pady=6, cursor='hand2', command=self._wz_back).pack(side='left')
        nextlbl = "완료 →" if self._wz_step == 2 else "다음 →"
        tk.Button(inner, text=nextlbl, font=FS, bg=INDIGO, fg='white', relief='flat', padx=16, pady=6, cursor='hand2', command=self._wz_next).pack(side='right')
        if self._wz_step == 2:
            tk.Button(inner, text="건너뛰기", font=FS, bg=BG, fg=SUBTEXT, relief='flat', cursor='hand2', command=self._wz_skip_ai).pack(side='right', padx=8)
        else:
            tk.Button(inner, text="나중에", font=FS, bg=BG, fg=SUBTEXT, relief='flat', cursor='hand2', command=self._wz_close).pack(side='right', padx=8)

    def _wz_next(self):
        if self._wz_step == 0:
            if not self._wz_url_var.get().strip() or not self._wz_path_var.get().strip():
                messagebox.showwarning("알림", "Firebase URL과 경로를 입력하세요.", parent=self.root); return
            self.config['firebase_url'] = self._wz_url_var.get().strip()
            self.config['firebase_path'] = self._wz_path_var.get().strip()
            self._wz_step = 1
        elif self._wz_step == 1:
            if not self.config.get('instructor_id'):
                messagebox.showwarning("알림", "강사 이름 조회·설정을 먼저 완료하세요.", parent=self.root); return
            self._wz_step = 2
        elif self._wz_step == 2:
            self._wz_step = 3
        self._wz_render()

    def _wz_skip_ai(self):
        self._wz_key_var.set('')
        self._wz_step = 3
        self._wz_render()

    def _wz_back(self):
        self._wz_step = max(0, self._wz_step - 1)
        self._wz_render()

    def _wz_exit(self):
        """위저드 오버레이 제거 → 정상 레이아웃 노출(없으면 빌드)."""
        if getattr(self, '_wz_root', None) is not None:
            self._wz_root.destroy()
            self._wz_root = None
        if not self._main_built:
            self._build_main_ui()
        else:
            try:
                self._populate_student_list(self.activeGroup)
                self._refresh_student_view()
            except Exception:
                pass

    def _wz_close(self):
        save_config(self.config)
        self._wz_exit()

    def _wz_commit(self):
        self.config['ai_engine_type'] = self._wz_engine_id
        self.config[f'{self._wz_engine_id}_api_key'] = self._wz_key_var.get().strip()
        self.config['firebase_url'] = self._wz_url_var.get().strip()
        self.config['firebase_path'] = self._wz_path_var.get().strip()
        save_config(self.config)
        self._wz_exit()
        if self.config.get('firebase_url') and self.config.get('firebase_path'):
            self.root.after(100, self._sync_shared_sheets_from_firebase)
        messagebox.showinfo("완료", "설정이 저장되었습니다.\n웹에서 명단 구성 후 📥 데이터 가져오기로 시작하세요.")

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
        tk.Button(test_row, text="⚡ 연결 테스트", font=FS, bg="#EEF0FF", fg=INDIGO, relief='flat', padx=10, pady=4, cursor='hand2', command=_test_connection).pack(side='left')

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

        tk.Button(fetch_row, text="🔄 학급/명단 동기화", font=FS, bg="#F7F7F9", fg=TEXT, relief='solid', bd=1, padx=10, pady=4, cursor='hand2', command=_fetch_class_data).pack(side='left')
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
        ai_entry = tk.Entry(ai_grid, textvariable=ai_key_var, font=FS, show='*', relief='flat', bg="#F7F7F9", highlightbackground=BORDER, highlightthickness=1)
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
        tk.Button(btn_row, text="취소", font=FS, bg="#ECECEF", fg=TEXT, relief='flat', padx=16, pady=8, command=win.destroy, cursor='hand2').pack(side='right', padx=8)


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

        # 대상자 선택 다이얼로그 (체크 해제 = 이번 전송만 제외)
        sel = self._open_send_dialog(ready, skipped)
        if sel is None:
            return  # 취소
        if not sel:
            messagebox.showinfo("알림", "선택된 전송 대상이 없습니다."); return

        # 특이사항 이력은 메시지 확정 시점에 기록 — 카톡 전송 성패/abort 와 무관 (전송 루프 이전 1회 원자적)
        self._push_history(sel)

        self._send_cancel = threading.Event()
        self._set_send_btn_cancel(True)
        threading.Thread(target=self._do_send, args=(sel,), daemon=True).start()

    def _open_send_dialog(self, ready, skipped):
        """전송 대상 체크박스 선택 다이얼로그.
        반환: 선택된 ready 항목 리스트 / 취소 시 None"""
        win = tk.Toplevel(self.root)
        win.title("카카오톡 전송 대상 선택")
        win.geometry("390x540")
        win.configure(bg=BG)
        win.grab_set()
        result = {'sel': None}

        tk.Label(win, text=f"전송 대상 {len(ready)}명 — 제외할 학생은 체크 해제하세요",
                 font=FT, bg=BG, fg=TEXT, wraplength=350, justify='left'
                 ).pack(pady=(14, 6), padx=16, anchor='w')

        top = tk.Frame(win, bg=BG); top.pack(fill='x', padx=16)
        vars_ = []
        def _set_all(val):
            for v, _ in vars_: v.set(val)
        tk.Button(top, text="전체 선택", font=FS, bg=PANEL, fg=INDIGO, relief='flat',
                  cursor='hand2', command=lambda: _set_all(True)).pack(side='left')
        tk.Button(top, text="전체 해제", font=FS, bg=PANEL, fg=GRAY, relief='flat',
                  cursor='hand2', command=lambda: _set_all(False)).pack(side='left', padx=6)

        body = tk.Frame(win, bg=BG); body.pack(fill='both', expand=True, padx=16, pady=8)
        canvas = tk.Canvas(body, bg=PANEL, highlightthickness=0)
        sb = ttk.Scrollbar(body, orient='vertical', command=canvas.yview)
        lst = tk.Frame(canvas, bg=PANEL)
        lst.bind('<Configure>', lambda e: canvas.configure(scrollregion=canvas.bbox('all')))
        canvas.create_window((0, 0), window=lst, anchor='nw')
        canvas.configure(yscrollcommand=sb.set)
        canvas.pack(side='left', fill='both', expand=True)
        sb.pack(side='right', fill='y')

        for r in ready:
            v = tk.BooleanVar(value=True)
            tk.Checkbutton(lst, text=r['name'], variable=v, font=FS,
                           bg=PANEL, fg=TEXT, anchor='w', selectcolor='white',
                           activebackground=PANEL, padx=6, pady=2
                           ).pack(fill='x')
            vars_.append((v, r))

        if skipped:
            tk.Label(win, text=f"미입력 제외 {len(skipped)}명: " + ", ".join(skipped),
                     font=FS, bg=BG, fg=GRAY, wraplength=350, justify='left'
                     ).pack(padx=16, pady=(0, 4), anchor='w')

        tk.Label(win, text="카카오톡 창 활성화 후 [전송 시작]을 누르세요. (3초 후 시작)",
                 font=FS, bg=BG, fg=SUBTEXT, wraplength=350, justify='left'
                 ).pack(padx=16, pady=(4, 8), anchor='w')

        foot = tk.Frame(win, bg=BG); foot.pack(fill='x', padx=16, pady=(0, 14))
        def _ok():
            result['sel'] = [r for v, r in vars_ if v.get()]
            win.destroy()
        def _cancel():
            result['sel'] = None
            win.destroy()
        tk.Button(foot, text="전송 시작", font=("맑은 고딕", 10, "bold"),
                  bg=ACCENT, fg="#0E1016", relief='flat', cursor='hand2',
                  padx=14, pady=7, command=_ok).pack(side='right')
        tk.Button(foot, text="취소", font=FS, bg=PANEL, fg=SUBTEXT, relief='flat',
                  cursor='hand2', padx=12, pady=7, command=_cancel).pack(side='right', padx=6)

        win.wait_window()
        return result['sel']

    def _set_send_btn_cancel(self, on):
        """전송 중 send_btn → 취소 버튼 토글."""
        if on:
            self.send_btn.config(text="⏹  전송 취소", bg="#FEE2E2", fg="#DC2626",
                                 command=self._cancel_send)
        else:
            self.send_btn.config(command=self._send)
            self._refresh_send_btn()

    def _cancel_send(self):
        """순차 전송 취소 요청 — 현재 학생 완료 후 중단."""
        if self._send_cancel:
            self._send_cancel.set()
        self.send_status.config(text="⏹  취소 중... (현재 학생 완료 후 중단)")

    def _do_send(self, msgs):
        cancel = self._send_cancel
        wait   = self.config.get('wait_time', 0.5)
        total  = len(msgs)
        # 3초 카운트다운 — 취소 가능
        for _ in range(30):
            if cancel.is_set(): break
            time.sleep(0.1)
        sent = 0
        for i, m in enumerate(msgs):
            if cancel.is_set(): break
            self.root.after(0, lambda t=f"전송 중... ({i+1}/{total})  {m['name']}":
                            self.send_status.config(text=t))
            # 첫 학생 워밍업 — 카톡 창 포커스/검색 안정화 (첫 전송 오작동 방지)
            warm = 0.6 if i == 0 else 0.0
            try:
                pyperclip.copy(m['room'])
                time.sleep(warm)
                pyautogui.hotkey(_MOD,'f'); time.sleep(0.2 + warm)
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
            sent += 1
            time.sleep(0.8)

        cancelled = cancel.is_set()
        def _on_done():
            self._set_send_btn_cancel(False)
            if cancelled:
                self.send_status.config(text=f"⏹ {sent}/{total}명 전송 후 취소 — 나머지 유지")
                messagebox.showinfo("전송 취소",
                    f"{sent}명 전송 후 취소했습니다.\n"
                    "전송되지 않은 학생 데이터는 유지됩니다.")
            else:
                self.send_status.config(text=f"✅ 전송 완료 — {sent}명")
                self._reset_after_send()
                messagebox.showinfo("완료", f"{sent}명 전송 완료!")
        self.root.after(0, _on_done)

    def _push_history(self, items):
        """최종 메시지에 확정(merge)된 특이사항을 history/{nameKey}/{YYYY-MM-DD} 에 누적.

        · 호출 시점 = 전송 **확정 직후·카톡 루프 이전** (전송 성패와 무관, 메시지 확정 기준)
          → 카톡 전송 중 abort/크래시가 나도 이력은 이미 기록됨.
        · 단일 원자적 multi-path PATCH (history 한 노드에 {nameKey/날짜:..} 일괄) — 1회 HTTP, 부분쓰기 없음.
        · 학생 grain(과목 무관), 날짜키 = today_key()(YYYY-MM-DD) — obs/scores 와 조인.
        · note 비어있으면 생략. 베스트에포트(실패해도 전송은 진행).
        """
        url  = self.config.get('firebase_url', '')
        path = self.config.get('firebase_path', '')
        if not (url and path):
            return
        day   = today_key()
        instr = self.config.get('instructor_id', '')
        updates = {}
        for it in items:
            nk   = it.get('nameKey')
            note = (it.get('note') or '').strip()
            if nk and note:
                updates[f"{nk}/{day}"] = {"note": note, "instructor": instr}
        if not updates:
            return
        try:
            firebase_patch(self.config, "history", updates)
        except Exception as e:
            print(f"history push 실패: {e}")

    def _reset_after_send(self):
        """전송 완료 후 로컬 전면 초기화 (진도/과제 포함).
        DB 쓰기 없음 — 전송 이력은 _send() 가 전송 확정 시점에 history/ 에 이미 기록함."""
        self.student_data.clear()
        self.note_data.clear()
        self.progress_data.clear()
        self.force_data.clear()
        save_daily_cache(self.progress_data, {}, {}, {})
        self.root.after(0, self._refresh_after_reset)

    def _refresh_after_reset(self):
        if self.cur_name:
            self._render_student(self.activeGroup, self.cur_cls, self.cur_name)
        self._refresh_send_btn()
        self._refresh_statusbar()
