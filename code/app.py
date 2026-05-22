"""
app.py — DailyReportWizard 메인 App 클래스
Crafted by IDO(idocho@kakao.com) · Powered by Claude AI

분리된 모듈:
  constants  — 전역 상수·태그 정의
  storage    — 설정·캐시 파일 I/O
  firebase   — Firebase REST CRUD, obs 로드
  ai_engine  — AI 특이사항 생성 (obs 태그 주입 포함)
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
    APP_TITLE, APP_VERSION, APP_CREDIT, AI_COOLDOWN,
    BG, PANEL, DARK, DARK2, ACCENT, INDIGO, INDIGO_L,
    GREEN, YELLOW, GRAY, BORDER, TEXT, SUBTEXT, BLUE,
    STATUS_EMPTY, STATUS_PARTIAL, STATUS_READY, DOT_COLOR,
    FT, FB, FS, FE, _MOD,
)
from storage  import (load_config, save_config, has_students,
                      save_daily_cache, load_daily_cache, set_runtime_cwd, RUNTIME_DIR)
from firebase import firebase_get, firebase_put, firebase_patch, fetch_obs, today_key
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

        self.cfg       = load_config()
        self.date_str  = today_str()
        # v3.0: 학생 수행도·특이사항은 웹에서 입력 → Firebase 가져오기로만 로드
        self.progress_data, _, _, _ = load_daily_cache()  # 진도/과제 캐시만 복원
        self.student_data = {}   # Firebase input/ 로드 시 채워짐
        self.note_data    = {}   # Firebase input/ 로드 시 채워짐
        self.force_data   = {}   # (sheet,cls,name) → bool 강제완료 플래그
        self.obs_data     = {}   # Firebase obs/ 로드 시 채워짐 (v2.0 신규)
        self.status_w  = {}   # (sheet,cls,name) → (canvas, oval_id)
        self.s_btn_map = {}   # (sheet,cls,name) → tk.Button
        # (sheet,cls) -> bool (True if folded/collapsed)
        self.cls_fold_state = {}
        # (sheet,cls) -> frame containing student rows (for show/hide)
        self.cls_container = {}
        # 기본: 모든 학급을 접힌 상태로 시작
        for s, sdata in self.cfg.get('sheets', {}).items():
            for c in sdata.get('classes', {}).keys():
                self.cls_fold_state[(s, c)] = True
        self.cur_sheet = 'M'
        self.cur_cls   = None
        self.cur_name  = None
        self._ai_last_call = 0.0       # 하위 호환용 (AiEngine이 갱신)
        self.ai = AiEngine(self)       # AI 생성 엔진

        self._build_header()
        self._build_sheet_bar()
        self._build_panels()
        self._build_statusbar()
        self._build_footer()
        self._switch_sheet('M')

        # Firebase 미설정 시 설정 안내
        if not self.cfg.get('firebase_url') or not self.cfg.get('firebase_path'):
            self.root.after(300, self._prompt_first_run)

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
        sheet = self.cur_sheet
        for cls, cls_data in self._my_classes(sheet):
            for s in cls_data['students']:
                self._update_dot(sheet, cls, s['name'])

    def _populate_student_list(self, sheet):
        for w in self.sl_inner.winfo_children():
            w.destroy()
        self.s_btn_map.clear()

        # instructor_assignments 기반 담당 반 필터
        assignments = self.cfg.get("instructor_assignments", [])
        assigned_cls = {a['cls'] for a in assignments if a.get('sheet') == sheet}
        show_all = not assignments  # assignments 없으면 전체 표시

        # 부담임 판단용 맵 (sheet|cls → role)
        asgn_role_map = {(a.get('sheet',''), a.get('cls','')): a.get('role','')
                         for a in assignments}

        for cls, cls_data in self.cfg['sheets'][sheet]['classes'].items():
            # 담당 반만 표시
            if not show_all and cls not in assigned_cls:
                continue

            # 부담임 판단: assignments.role 우선, 없으면 is_sub 폴백
            role = asgn_role_map.get((sheet, cls), '')
            if role:
                is_sub = (role == '부담임')
            else:
                is_sub = cls_data.get('is_sub', False)

            # class header with fold/unfold button
            lbl_text = f"🔒 {cls}" if is_sub else cls
            lbl_fg   = "#6B7280" if is_sub else "#475569"
            hdr = tk.Frame(self.sl_inner, bg=DARK)
            hdr.pack(fill='x', pady=(8,0))
            # fold toggle button
            folded = self.cls_fold_state.get((sheet, cls), False)
            tri = '▸' if folded else '▾'
            def _make_toggle(sht, cl, hdr_frame):
                def _toggle():
                    key = (sht, cl)
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
                    btn.configure(text=( '▸' if self.cls_fold_state[key] else '▾') + ' ' + lbl_text)
                return _toggle

            btn = tk.Button(hdr, text=(tri + ' ' + lbl_text), font=FS,
                            bg=DARK, fg=lbl_fg, relief='flat', bd=0,
                            anchor='w', cursor='hand2', command=_make_toggle(sheet, cls, hdr))
            btn.pack(side='left', padx=10)

            # container for student rows
            cont = tk.Frame(self.sl_inner, bg=DARK)
            key = (sheet, cls)
            self.cls_container[key] = cont
            if not folded:
                cont.pack(fill='x')

            for s in cls_data['students']:
                name = s['name']
                row = tk.Frame(cont, bg=DARK)
                row.pack(fill='x')
                sbtn = tk.Button(row, text=name, font=FB,
                                 bg=DARK, fg=GRAY,
                                 relief='flat', bd=0, anchor='w',
                                 cursor='hand2', width=9,
                                 command=lambda c=cls,n=name: self._select_student(sheet,c,n))
                sbtn.pack(side='left', padx=(10,0), pady=1)
                dc = tk.Canvas(row, width=10, height=10, bg=DARK, highlightthickness=0)
                did = dc.create_oval(2,2,9,9, fill="#374151", outline="")
                dc.pack(side='right', padx=8)
                self.s_btn_map[(sheet,cls,name)] = sbtn
                self.status_w[(sheet,cls,name)] = (dc, did)

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

    def _render_student(self, sheet, cls, name):
        """v3.0 — 읽기 전용 뷰어 (입력 위젯 없음, Firebase 데이터 표시)"""
        for w in self.c_inner.winfo_children():
            w.destroy()

        cls_data  = self.cfg['sheets'][sheet]['classes'][cls]
        textbooks = cls_data.get('textbooks', [])
        room      = get_room(self.cfg, name)

        self.c_name.config(text=name)
        self.c_sub.config(text=f"  {cls}")
        self.c_room.config(text=f"→ {room}")

        # ── 강제 완료 토글 버튼 ──
        force_key = (sheet, cls, name)
        is_forced = self.force_data.get(force_key, False)

        def _toggle_force(fk=force_key):
            self.force_data[fk] = not self.force_data.get(fk, False)
            save_daily_cache(self.progress_data, self.student_data,
                             self.note_data, self.force_data)
            self._update_dot(sheet, cls, name)
            self._refresh_send_btn()
            self._refresh_statusbar()
            self._render_student(sheet, cls, name)

        force_btn_frame = tk.Frame(self.c_inner, bg=PANEL)
        force_btn_frame.pack(fill='x', padx=14, pady=(8, 0))
        if self._is_sub_teacher(sheet, cls):
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
            self.progress_data.get((sheet, cls, tb), {}).get('progress') or
            self.progress_data.get((sheet, cls, tb), {}).get('homework')
            for tb in textbooks
        )
        if has_progress:
            pf = tk.LabelFrame(pad, text="  오늘 수업 (반 공통)  ",
                               font=("맑은 고딕", 9, "bold"),
                               fg="#0F6E56", bg="#F0FDF4", padx=10, pady=8,
                               highlightbackground="#BBF7D0")
            pf.pack(fill='x', pady=(0, 12))
            for tb in textbooks:
                pd_val = self.progress_data.get((sheet, cls, tb), {})
                if pd_val.get('progress') or pd_val.get('homework'):
                    tk.Label(pf, text=tb, font=("맑은 고딕", 8, "bold"),
                             bg="#F0FDF4", fg=INDIGO).pack(anchor='w', pady=(2,0))
                    if pd_val.get('progress'):
                        tk.Label(pf, text=f"  진도: {pd_val['progress']}",
                                 font=FS, bg="#F0FDF4", fg=TEXT
                                 ).pack(anchor='w')
                    if pd_val.get('homework'):
                        tk.Label(pf, text=f"  과제: {pd_val['homework']}",
                                 font=FS, bg="#F0FDF4", fg=TEXT
                                 ).pack(anchor='w')

        # ── 교재별 과제수행도 (읽기 전용) ──
        for tb in textbooks:
            student_key = (sheet, cls, name, tb)
            val      = self.student_data.get(student_key, {}).get('value', '')
            filled   = bool(val.strip())

            lf = tk.LabelFrame(pad, text=f"  {tb}  ",
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
        note_key = (sheet, cls, name)
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
        if self._is_sub_teacher(sheet, cls):
            ai_btn.config(state='disabled', text="✨ AI생성 (부담임)",
                          bg="#F1F5F9", fg=GRAY, cursor='arrow')
        else:
            # 쿨다운 잔여 시간에 따라 초기 상태 설정
            _rem = max(0, AI_COOLDOWN - (time.time() - self._ai_last_call))
            if _rem > 0:
                ai_btn.config(state='disabled', text=f"⏳ {int(_rem)}s")
                self._start_cooldown_tick(ai_btn)

        # Text 위젯 — 담임: 편집 가능 / 부담임: 읽기 전용
        is_sub = self._is_sub_teacher(sheet, cls)
        note_txt = tk.Text(pad, font=FE, bg="#F8FAFC", fg=TEXT,
                           relief='flat', wrap='word', height=3,
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
                """FocusOut 시 note_data 로컬 캐시 저장 (DB 쓰기 없음)"""
                raw = note_txt.get('1.0', 'end').rstrip('\n')
                # 이모지 surrogate pair 정규화 (Windows tkinter 대응)
                try:
                    new_val = raw.encode('utf-16', 'surrogatepass').decode('utf-16')
                except Exception:
                    new_val = raw
                self.note_data[note_key] = {'value': new_val}
                save_daily_cache(self.progress_data, self.student_data, self.note_data, self.force_data)
                self._update_preview()

            note_txt.bind('<FocusOut>', _save_note)

        ai_btn.config(command=lambda: self._gen_ai_note(
            sheet, cls, name, textbooks, note_txt, ai_btn))

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
        self._dot_c.itemconfig(self._dot_id, fill=GREEN if on else "#bbf7d0")
        self.root.after(800, lambda: self._pulse(not on))

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
            self._update_dot(self.cur_sheet, self.cur_cls, self.cur_name)
        self._refresh_send_btn()
        self._refresh_statusbar()

    def _save_values(self):
        # v3.0: 입력 위젯 없음 — Firebase 가져오기로만 데이터 로드, no-op
        pass

    def _update_preview(self):
        s, c, n = self.cur_sheet, self.cur_cls, self.cur_name
        if not n: return
        cls_data  = self.cfg['sheets'][s]['classes'][c]
        textbooks = cls_data.get('textbooks', [])
        room      = get_room(self.cfg, n)
        class_info = {tb: self.progress_data.get((s,c,tb), {'progress':'','homework':''})
                      for tb in textbooks}
        assign_map = {tb: self.student_data.get((s,c,n,tb),{}).get('value','')
                      for tb in textbooks}
        note = self.note_data.get((s,c,n),{}).get('value','')
        msg  = build_message(self.date_str, class_info, n, assign_map, note)
        self.to_lbl.config(text=f"→  {room}")
        self.preview.config(state='normal')
        self.preview.delete('1.0','end')
        self.preview.insert('1.0', msg)
        self.preview.config(state='disabled')
        self.char_lbl.config(text=f"{len(msg)}자")

    def _is_sub_teacher(self, sheet, cls):
        """현재 강사가 해당 cls에서 부담임인지 확인"""
        for a in self.cfg.get("instructor_assignments", []):
            if a.get('sheet') == sheet and a.get('cls') == cls:
                return a.get('role') == '부담임'
        return False

    def _my_classes(self, sheet) -> list:
        """내 담당 반만 반환 → [(cls, cls_data), ...] 튜플 리스트
        - assignments 있음: 해당 sheet의 내 담당 반만 (부담임 포함)
        - assignments 없음: 해당 sheet 전체 반 (show_all)
        모든 학생 관련 연산(상태바·이동·전송·초기화·AI)에 일관 적용.
        """
        assignments = self.cfg.get("instructor_assignments", [])
        all_classes = self.cfg['sheets'].get(sheet, {}).get('classes', {})
        if not assignments:
            return list(all_classes.items())
        assigned_cls = {a['cls'] for a in assignments if a.get('sheet') == sheet}
        return [(cls, cd) for cls, cd in all_classes.items() if cls in assigned_cls]

    def _student_status(self, sheet, cls, name):
        # 강제 완료 플래그 우선
        if self.force_data.get((sheet, cls, name)):
            return STATUS_READY
        tbs    = self.cfg['sheets'][sheet]['classes'][cls].get('textbooks', [])
        filled = sum(1 for tb in tbs
                     if self.student_data.get((sheet,cls,name,tb),{}).get('value',''))
        if filled == 0:         return STATUS_EMPTY
        if filled < len(tbs):   return STATUS_PARTIAL
        # 과제수행도 완료 → 반 공통 진도/과제도 하나 이상 있어야 READY
        has_progress = any(
            self.progress_data.get((sheet, cls, tb), {}).get('progress', '') or
            self.progress_data.get((sheet, cls, tb), {}).get('homework', '')
            for tb in tbs
        )
        return STATUS_READY if has_progress else STATUS_PARTIAL

    def _update_dot(self, sheet, cls, name):
        st = self._student_status(sheet, cls, name)
        pair = self.status_w.get((sheet, cls, name))
        if pair:
            pair[0].itemconfig(pair[1], fill=DOT_COLOR[st])

    def _collect_ready(self, sheet):
        """
        전송 준비 완료 학생만 수집
        ─ 조건: STATUS_READY (과제수행도 완료 + 진도/과제 입력)
        ─ 표시 필터(_populate_student_list)와 동일한 화이트리스트 방식 적용
        ─ 부담임 담당 반 → 전송 제외
        """
        result = []
        assignments = self.cfg.get("instructor_assignments", [])
        assigned_cls = {a['cls'] for a in assignments if a.get('sheet') == sheet}
        show_all = not assignments  # assignments 없으면 전체 대상
        asgn_role_map = {(a.get('sheet',''), a.get('cls','')): a.get('role','')
                         for a in assignments}

        for cls, cls_data in self.cfg['sheets'][sheet]['classes'].items():
            # 1차: 화이트리스트 — 내 담당 반이 아니면 제외
            if not show_all and cls not in assigned_cls:
                continue
            # 2차: 부담임 반 제외
            role = asgn_role_map.get((sheet, cls), '')
            if role == '부담임':
                continue
            if not role and cls_data.get('is_sub', False):
                continue

            textbooks  = cls_data.get('textbooks', [])
            class_info = {tb: self.progress_data.get((sheet,cls,tb), {'progress':'','homework':''})
                          for tb in textbooks}
            for s in cls_data['students']:
                name = s['name']
                if self._student_status(sheet, cls, name) != STATUS_READY:
                    continue
                assign_map = {tb: self.student_data.get((sheet,cls,name,tb),{}).get('value','')
                              for tb in textbooks}
                note = self.note_data.get((sheet,cls,name),{}).get('value','')
                msg  = build_message(self.date_str, class_info, name, assign_map, note)
                result.append({'name': name, 'room': get_room(self.cfg, name), 'msg': msg})
        return result

    def _refresh_send_btn(self):
        n = len(self._collect_ready(self.cur_sheet))
        self.send_btn.config(
            text=f"🚀  카카오톡 전송 ({n}명)",
            bg=ACCENT if n>0 else "#E2E8F0",
            fg="#1A1D2E" if n>0 else GRAY)

    def _refresh_statusbar(self):
        sheet = self.cur_sheet
        done, part, empty = [], [], []
        for cls, cls_data in self._my_classes(sheet):
            for s in cls_data['students']:
                st = self._student_status(sheet, cls, s['name'])
                if st == STATUS_READY:     done.append(s['name'])
                elif st == STATUS_PARTIAL: part.append(s['name'])
                else:                     empty.append(s['name'])
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
    def _student_list_flat(self, sheet):
        """◀/▶ 이동용 학생 목록 — _my_classes() 범위만 포함"""
        result = []
        for cls, cd in self._my_classes(sheet):
            for s in cd['students']:
                result.append((cls, s['name']))
        return result

    def _select_student(self, sheet, cls, name):
        if self.cur_name:
            old = self.s_btn_map.get((self.cur_sheet, self.cur_cls, self.cur_name))
            if old: old.config(bg=DARK, fg=GRAY)
        self.cur_sheet, self.cur_cls, self.cur_name = sheet, cls, name
        btn = self.s_btn_map.get((sheet, cls, name))
        if btn: btn.config(bg=INDIGO, fg='white')
        self._render_student(sheet, cls, name)

    def _prev_student(self):
        lst = self._student_list_flat(self.cur_sheet)
        cur = (self.cur_cls, self.cur_name)
        if cur in lst:
            i = lst.index(cur)
            if i > 0:
                c, n = lst[i-1]
                self._select_student(self.cur_sheet, c, n)

    def _next_student(self):
        lst = self._student_list_flat(self.cur_sheet)
        cur = (self.cur_cls, self.cur_name)
        if cur in lst:
            i = lst.index(cur)
            if i < len(lst)-1:
                c, n = lst[i+1]
                self._select_student(self.cur_sheet, c, n)

    def _clear_current(self):
        s, c, n = self.cur_sheet, self.cur_cls, self.cur_name
        if not n: return
        for tb in self.cfg['sheets'][s]['classes'][c].get('textbooks',[]):
            key = (s,c,n,tb)
            if key in self.student_data and 'widget' in self.student_data[key]:
                self.student_data[key]['widget'].delete('1.0','end')
                self.student_data[key]['value'] = ''
        note_key = (s,c,n)
        if note_key in self.note_data and 'widget' in self.note_data[note_key]:
            self.note_data[note_key]['widget'].delete('1.0','end')
            self.note_data[note_key]['value'] = ''
        self._on_change()

    # ── 시트 전환 ────────────────────────────────────────────────────
    def _refresh_student_view(self):
        """프리셋 변경 후 현재 학생 입력 화면 즉시 갱신"""
        if self.cur_sheet and self.cur_cls and self.cur_name:
            self._render_student(self.cur_sheet, self.cur_cls, self.cur_name)

    def _reset_class_data(self, sheet=None, cls=None):
        """반별 학생 입력 데이터 로컬 초기화 (과제수행도·특이사항) — DB 쓰기 없음"""
        s = sheet or self.cur_sheet
        c = cls   or self.cur_cls
        if not c: return
        students = self.cfg['sheets'][s]['classes'].get(c, {}).get('students', [])
        tbs      = self.cfg['sheets'][s]['classes'].get(c, {}).get('textbooks', [])

        for st in students:
            name = st['name']
            for tb in tbs:
                key = (s, c, name, tb)
                if key in self.student_data:
                    self.student_data[key] = {'value': ''}
            note_key = (s, c, name)
            if note_key in self.note_data:
                self.note_data[note_key] = {'value': ''}

        save_daily_cache(self.progress_data, self.student_data, self.note_data, self.force_data)

        if self.cur_name:
            self._render_student(s, c, self.cur_name)
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
            self._render_student(self.cur_sheet, self.cur_cls, self.cur_name)
        self._refresh_status_dots()
        self._refresh_send_btn()
        self._refresh_statusbar()

    def _pull_mobile_data(self):
        """📥 데이터 가져오기 — Firebase input/ + session/class_data 전체 로드 (v3.0)"""
        url  = self.cfg.get('firebase_url', '')
        path = self.cfg.get('firebase_path', '')
        if not url or not path:
            messagebox.showwarning("Firebase 미설정",
                "설정에서 Firebase URL과 경로를 입력해 주세요.")
            return

        try:
            # ── 0. config/ (sheets + presets + 강사 데이터) ──
            config_data = firebase_get(self.cfg, "config") or {}
            if config_data.get("sheets"):
                self.cfg["sheets"] = config_data["sheets"]

            # 강사별 presets + assignments 우선, 없으면 전역 presets 사용
            instructor_id = self.cfg.get('instructor_id', '')
            if instructor_id and config_data.get("instructors", {}).get(instructor_id):
                instr_data = config_data["instructors"][instructor_id]
                if instr_data.get("presets"):
                    self.cfg["presets"] = {"과제수행도": instr_data["presets"]}
                # assignments 저장 → 담당 반 필터링·부담임 판단에 사용
                self.cfg["instructor_assignments"] = instr_data.get("assignments", [])
                instr_name = instr_data.get("name", instructor_id)
            elif config_data.get("presets"):
                self.cfg["presets"] = config_data["presets"]
                self.cfg["instructor_assignments"] = []
                instr_name = ""
            else:
                self.cfg["instructor_assignments"] = []
                instr_name = ""

            save_config(self.cfg)
            # 학생 목록 갱신
            self.root.after(0, lambda: self._switch_sheet(self.cur_sheet))

            # ── 1. 학생별 수행도·특이사항 (input/ 노드) ──
            input_data = firebase_get(self.cfg, "input") or {}

            # ── 2. 반 공통 진도/과제 (session/class_data) ──
            session_raw = firebase_get(self.cfg, "session") or {}
            class_data  = session_raw.get("class_data", {})
            date_str    = session_raw.get("date", "")
            if not class_data:
                # lastSent 폴백
                last_raw  = firebase_get(self.cfg, "lastSent") or {}
                class_data = last_raw.get("class_data", {})
                date_str   = last_raw.get("date", "")

            # ── 3. 수업 관찰 태그 (obs/ 노드, v2.0 신규) ──
            obs_raw = fetch_obs(self.cfg)
            if obs_raw:
                self.obs_data.update(obs_raw)

            if not input_data and not class_data:
                messagebox.showinfo("알림", "웹 입력 데이터가 없습니다.\n웹에서 먼저 수업을 입력해 주세요.")
                return

            # ── input/ 처리 ──
            # 과제수행도·진도/과제: 항상 웹 데이터로 교체
            # 특이사항: 로컬에 값이 있으면 보호 (PC 직접 편집·AI생성 결과 유지)
            self._import_mobile_data(input_data)

            # ── session/class_data → progress_data (항상 덮어쓰기) ──
            applied_prog = 0
            for key_str, v in class_data.items():
                parts = key_str.split('|')
                if len(parts) != 3:
                    continue
                sheet, cls, tb = parts
                tk_key = (sheet, cls, tb)
                prog = v.get('progress', '') if isinstance(v, dict) else ''
                hw   = v.get('homework',  '') if isinstance(v, dict) else ''
                self.progress_data[tk_key] = {'progress': prog, 'homework': hw}
                applied_prog += 1

            save_daily_cache(self.progress_data, self.student_data, self.note_data, self.force_data)
            self._refresh_status_dots()
            self._refresh_send_btn()
            self._refresh_statusbar()
            if self.cur_name:
                self._render_student(self.cur_sheet, self.cur_cls, self.cur_name)

            date_info = f"  ({date_str} 기준)" if date_str else ""
            messagebox.showinfo("가져오기 완료",
                f"웹 입력 데이터를 가져왔습니다.{date_info}\n"
                f"과제수행도: 웹 데이터로 교체 / 진도·과제: {applied_prog}개 반영\n"
                "특이사항: 기존 입력값 보호 (비어있는 경우만 채움)")
        except Exception as e:
            messagebox.showerror("오류", f"가져오기 실패:\n{e}")

    def _import_mobile_data(self, data):
        """Firebase input/ 노드에서 학생 데이터 반영
        progress/homework managed via session/ node — skip here
        · 과제수행도: 항상 웹 데이터로 교체
        · 특이사항: 로컬에 값이 있으면 보호 (PC 직접 편집·AI생성 결과 유지), 비어있을 때만 채움
        """
        if not data:
            return

        for key_str, v in data.items():
            parts = key_str.split('|')

            # 진도/과제 키 → 무시 (session/ 노드로 별도 관리)
            if parts[0] in ('progress', 'homework'):
                continue

            # 특이사항 — 로컬 값 보호
            if len(parts) == 4 and parts[3] == '__note__':
                sheet, cls, name, _ = parts
                note_key = (sheet, cls, name)
                val = v.get('note', '') if isinstance(v, dict) else str(v)
                if not self.note_data.get(note_key, {}).get('value', ''):
                    self.note_data[note_key] = {'value': val}

            # 과제수행도 — 항상 교체
            elif len(parts) == 4:
                sheet, cls, name, tb = parts
                student_key = (sheet, cls, name, tb)
                val = v.get('assign', '') if isinstance(v, dict) else str(v)
                self.student_data[student_key] = {'value': val}

        save_daily_cache(self.progress_data, self.student_data, self.note_data, self.force_data)
        if self.cur_name:
            self._render_student(self.cur_sheet, self.cur_cls, self.cur_name)
        self._refresh_send_btn()
        self._refresh_statusbar()


    def _switch_sheet(self, sheet):
        self._save_values()
        self.cur_sheet = sheet
        self.cur_cls = self.cur_name = None
        self._populate_student_list(sheet)
        for s, b in self.sheet_btns.items():
            b.config(bg=PANEL if s==sheet else "#E2E8F0",
                     fg=TEXT  if s==sheet else SUBTEXT)
        # 첫 학생 선택 (_my_classes 범위 내에서)
        for cls, cd in self._my_classes(sheet):
            if cd['students']:
                self._select_student(sheet, cls, cd['students'][0]['name'])
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

    # ── 반별 진도/과제 창 ────────────────────────────────────────────
    def _open_progress_window(self):
        if hasattr(self, '_progress_win') and self._progress_win.winfo_exists():
            self._progress_win.lift()
            self._progress_win.focus_force()
            return
        win = tk.Toplevel(self.root)
        self._progress_win = win
        win.title("반별 진도 / 과제")
        win.geometry("580x520")
        win.configure(bg=BG)
        win.resizable(True, True)

        # 헤더
        tk.Label(win, text="반별 진도 / 과제 입력",
                 font=("맑은 고딕", 12, "bold"), bg=BG, fg=TEXT
                 ).pack(anchor='w', padx=16, pady=(12,4))

        # 버튼 영역 — 스크롤 프레임보다 먼저 pack (bottom 고정)
        foot = tk.Frame(win, bg=PANEL,
                        highlightbackground=BORDER, highlightthickness=1)
        foot.pack(fill='x', side='bottom')

        def _clear_progress():
            if not messagebox.askyesno("초기화", "진도/과제 데이터를 모두 초기화합니까?"):
                return
            self.progress_data.clear()
            save_daily_cache(self.progress_data, self.student_data, self.note_data, self.force_data)
            win.destroy()
            self._open_progress_window()

        def _on_close():
            win.destroy()

        tk.Button(foot, text="✅ 저장",
                  font=FT, bg=DARK, fg='white', relief='flat',
                  cursor='hand2', command=_on_close
                  ).pack(fill='x', padx=10, pady=(8,3))
        tk.Button(foot, text="닫기",
                  font=FT, bg="#F1F5F9", fg=SUBTEXT,
                  relief='flat', cursor='hand2',
                  command=win.destroy
                  ).pack(fill='x', padx=10, pady=(0, 3))
        tk.Button(foot, text="🗑 진도/과제 초기화",
                  font=FT, bg="#FEF2F2", fg="#EF4444",
                  relief='flat', cursor='hand2',
                  command=_clear_progress
                  ).pack(fill='x', padx=10, pady=(0, 8))

        # 스크롤 영역
        _, inner = make_scroll_frame(win, bg=BG)
        sheet = self.cur_sheet

        # Tab 순서 관리용 위젯 목록
        all_texts = []

        for cls, cls_data in self.cfg['sheets'][sheet]['classes'].items():
            tbs = cls_data.get('textbooks', [])
            lf  = tk.LabelFrame(inner, text=f"  {cls}  ", font=FT,
                                 fg=DARK, bg=BG, padx=10, pady=8)
            lf.pack(fill='x', padx=14, pady=8)
            lf.columnconfigure(2, weight=1)

            row_idx = 0
            for tb in tbs:
                tk.Label(lf, text=tb, font=("맑은 고딕", 9, "bold"),
                         bg=BG, fg=SUBTEXT).grid(
                    row=row_idx, column=0, columnspan=3,
                    sticky='w', pady=(6,2))
                row_idx += 1

                for label, field in [("진도", "progress"), ("과제", "homework")]:
                    tk.Label(lf, text=label, font=FS, bg=BG, fg=GRAY
                             ).grid(row=row_idx, column=1, sticky='nw',
                                    padx=(14,6), pady=2)
                    t = tk.Text(lf, height=1, font=FE, wrap='word',
                                relief='flat', bg="#F8FAFC", bd=1,
                                highlightbackground=BORDER, highlightthickness=1)
                    t.grid(row=row_idx, column=2, sticky='ew', pady=2)

                    class_key = (sheet, cls, tb)
                    old = self.progress_data.get(class_key, {}).get(field, '')
                    if old: t.insert('1.0', old)

                    def _make_saver(key, f2, widget):
                        def _sv(e=None):
                            if key not in self.progress_data:
                                self.progress_data[key] = {}
                            self.progress_data[key][f2] = widget.get('1.0','end').strip()
                            self._update_preview()
                            save_daily_cache(self.progress_data, self.student_data, self.note_data, self.force_data)
                        return _sv
                    t.bind('<KeyRelease>', _make_saver(class_key, field, t))
                    all_texts.append(t)
                    row_idx += 1

        # Tab / Shift+Tab 으로 텍스트박스 순방향·역방향 이동
        def _make_tab(idx):
            def _tab(e):
                next_idx = (idx + 1) % len(all_texts)
                all_texts[next_idx].focus_set()
                all_texts[next_idx].mark_set('insert', 'end')
                return 'break'
            return _tab

        def _make_shift_tab(idx):
            def _stab(e):
                prev_idx = (idx - 1) % len(all_texts)
                all_texts[prev_idx].focus_set()
                all_texts[prev_idx].mark_set('insert', 'end')
                return 'break'
            return _stab

        for i, t in enumerate(all_texts):
            t.bind('<Tab>',       _make_tab(i))
            t.bind('<Shift-Tab>', _make_shift_tab(i))

        # 첫 번째 텍스트박스에 포커스
        if all_texts:
            all_texts[0].focus_set()

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
        wait_var = tk.StringVar(value=str(self.cfg.get('wait_time', 0.5)))
        tk.Entry(delay_grid, textvariable=wait_var, font=FS, relief='solid', bd=1).grid(row=0, column=1, sticky='ew', ipady=3)

        tk.Label(delay_grid, text="카톡 접두사", font=FS, bg=BG, fg=SUBTEXT).grid(row=1, column=0, sticky='w', pady=3, padx=(0,8))
        prefix_var = tk.StringVar(value=self.cfg.get('room_prefix', '오직 '))
        tk.Entry(delay_grid, textvariable=prefix_var, font=FS, relief='solid', bd=1).grid(row=1, column=1, sticky='ew', ipady=3)

        # ── ② Firebase Database 연결 설정 ───────────────────
        tk.Frame(inner, bg=BORDER, height=1).pack(fill='x', padx=16, pady=(4,0))
        self._settings_section(inner, "Firebase 연결 설정")

        fb_grid = tk.Frame(inner, bg=BG)
        fb_grid.pack(fill='x', padx=16, pady=(0,6))
        fb_grid.columnconfigure(1, weight=1)

        tk.Label(fb_grid, text="DB URL", font=FS, bg=BG, fg=SUBTEXT).grid(row=0, column=0, sticky='w', pady=3, padx=(0,8))
        fb_url_var = tk.StringVar(value=self.cfg.get('firebase_url', ''))
        tk.Entry(fb_grid, textvariable=fb_url_var, font=FS, relief='solid', bd=1).grid(row=0, column=1, sticky='ew', ipady=3)

        tk.Label(fb_grid, text="DB 경로", font=FS, bg=BG, fg=SUBTEXT).grid(row=1, column=0, sticky='w', pady=3, padx=(0,8))
        fb_path_var = tk.StringVar(value=self.cfg.get('firebase_path', ''))
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
                firebase_get(tmp, "config/presets")
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

        cur_name = self.cfg.get('instructor_id', '')
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
            self.cfg['firebase_url'] = url
            self.cfg['firebase_path'] = path
            status_lbl.config(text="조회 중...", fg=GRAY)
            lookup_btn.config(state='disabled')

            def _fetch():
                try:
                    from firebase import firebase_get, firebase_put
                    data = firebase_get(self.cfg, f"config/instructors/{name}")
                    if not data:
                        firebase_put(self.cfg, f"config/instructors/{name}", {"classes": {}})
                        win.after(0, lambda: messagebox.showinfo("안내", f"신규 강사 계정 [{name}]을 등록했습니다.", parent=win))
                    
                    self.cfg['instructor_id'] = name
                    from firebase import firebase_get
                    sheets_data = firebase_get(self.cfg, "config/sheets")
                    if isinstance(sheets_data, dict):
                        self.cfg['sheets'] = sheets_data
                    
                    asgn = firebase_get(self.cfg, f"config/instructors/{name}/classes")
                    self.cfg['instructor_assignments'] = list(asgn.values()) if isinstance(asgn, dict) else []
                    
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
            if not url or not path or not self.cfg.get('instructor_id'):
                messagebox.showwarning("알림", "강사 계정 조회를 먼저 완료해 주세요.", parent=win)
                return
            try:
                from firebase import firebase_get
                s_data = firebase_get(self.cfg, "config/sheets")
                if isinstance(s_data, dict):
                    self.cfg['sheets'] = s_data
                asgn = firebase_get(self.cfg, f"config/instructors/{self.cfg['instructor_id']}/classes")
                self.cfg['instructor_assignments'] = list(asgn.values()) if isinstance(asgn, dict) else []
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

        # 깔끔하게 groq, openai, claude 3가지 항목만 선택하는 드롭다운
        tk.Label(ai_grid, text="AI 엔진 종류", font=FS, bg=BG, fg=SUBTEXT).grid(row=0, column=0, sticky='w', pady=6, padx=(0,8))
        engine_var = tk.StringVar(value=self.cfg.get('ai_engine_type', 'groq'))
        cmb_engine = ttk.Combobox(ai_grid, textvariable=engine_var, state="readonly", font=FS)
        cmb_engine['values'] = ('groq', 'openai', 'claude')
        cmb_engine.grid(row=0, column=1, sticky='ew', pady=6)

        # API Key 입력 폼
        tk.Label(ai_grid, text="API Key", font=FS, bg=BG, fg=SUBTEXT).grid(row=1, column=0, sticky='w', pady=3, padx=(0,8))
        
        default_key = self.cfg.get('ai_api_key', '')
        if not default_key:
            default_key = self.cfg.get('groq_api_key', '')
            
        ai_key_var = tk.StringVar(value=default_key)
        ai_entry = tk.Entry(ai_grid, textvariable=ai_key_var, font=FS, show='*', relief='flat', bg="#F8FAFC", highlightbackground=BORDER, highlightthickness=1)
        ai_entry.grid(row=1, column=1, sticky='ew', ipady=3)

        def _toggle_ai_vis():
            ai_entry.config(show='' if ai_entry.cget('show') == '*' else '*')
        tk.Button(ai_grid, text="👁", font=FS, bg=BG, fg=GRAY, relief='flat', command=_toggle_ai_vis, cursor='hand2').grid(row=1, column=2, padx=4)

        # ── ⑤ 하단 컨트롤 (저장) ───────────────────────────────────
        tk.Frame(inner, bg=BORDER, height=1).pack(fill='x', padx=16, pady=(10,0))
        
        def _save_all():
            try:
                try:
                    self.cfg['wait_time'] = float(wait_var.get().strip())
                except ValueError:
                    self.cfg['wait_time'] = 0.5
                self.cfg['room_prefix'] = prefix_var.get().strip()

                self.cfg['firebase_url'] = fb_url_var.get().strip()
                self.cfg['firebase_path'] = fb_path_var.get().strip()

                # 엔진 다중화 세팅 주입
                chosen_engine = engine_var.get().strip().lower()
                chosen_key = ai_key_var.get().strip()
                
                self.cfg['ai_engine_type'] = chosen_engine
                self.cfg['ai_api_key'] = chosen_key
                
                if chosen_engine == 'groq':
                    self.cfg['groq_api_key'] = chosen_key

                save_config(self.cfg)
                
                self._populate_student_list(self.cur_sheet)
                self._refresh_student_view()
                
                messagebox.showinfo("완료", "모든 설정이 안전하게 로컬에 저장되었습니다.", parent=win)
                win.destroy()
            except Exception as err:
                messagebox.showerror("오류", f"설정 저장 실패:\n{err}", parent=win)

        btn_row = tk.Frame(inner, bg=BG)
        btn_row.pack(fill='x', padx=16, pady=20)
        tk.Button(btn_row, text="💾 설정 저장하기", font=FT, bg=INDIGO, fg='white', relief='flat', padx=20, pady=8, command=_save_all, cursor='hand2').pack(side='right')
        tk.Button(btn_row, text="취소", font=FS, bg="#E2E8F0", fg=TEXT, relief='flat', padx=16, pady=8, command=win.destroy, cursor='hand2').pack(side='right', padx=8)


    def _gen_ai_note(self, sheet, cls, name, textbooks, note_txt, ai_btn=None):
        """AI 특이사항 단건 생성 — AiEngine에 위임."""
        self.ai.gen_single(sheet, cls, name, textbooks, note_txt, ai_btn)

    def _start_cooldown_tick(self, btn):
        """AI 쿨다운 틱 — AiEngine에 위임."""
        self.ai._start_cooldown_tick(btn)

    def _gen_ai_note_all(self):
        """일괄 AI 생성 — AiEngine에 위임."""
        self.ai.gen_all(self.cur_sheet)

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
        sheet  = self.cur_sheet
        ready  = self._collect_ready(sheet)
        if not ready:
            messagebox.showinfo("알림",
                "전송 준비된 학생이 없습니다.\n"
                "모든 교재의 과제수행도를 입력한 학생만 전송됩니다."); return

        all_names = [
            s['name']
            for cls, cd in self._my_classes(sheet)
            if not self._is_sub_teacher(sheet, cls)
            for s in cd['students']
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
        wait  = self.cfg.get('wait_time', 0.5)
        total = len(msgs)
        time.sleep(3)
        for i, m in enumerate(msgs):
            self.send_status.config(text=f"전송 중... ({i+1}/{total})  {m['name']}")
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

        self.send_status.config(text=f"✅ 전송 완료 — {total}명")
        self._reset_after_send()
        messagebox.showinfo("완료", f"{total}명 전송 완료!")

    def _reset_after_send(self):
        """전송 완료 후 로컬 전면 초기화 (진도/과제 포함) — DB 쓰기는 lastSent만"""
        self.student_data.clear()
        self.note_data.clear()
        self.progress_data.clear()
        self.force_data.clear()
        save_daily_cache(self.progress_data, {}, {}, {})

        url  = self.cfg.get('firebase_url', '')
        path = self.cfg.get('firebase_path', '')
        if url and path:
            def _push_last_sent():
                try:
                    firebase_put(self.cfg, "lastSent", {
                        "date": self.date_str,
                        "class_data": {}
                    })
                except Exception as e:
                    print(f"lastSent push 실패: {e}")
            threading.Thread(target=_push_last_sent, daemon=True).start()

        self.root.after(0, self._refresh_after_reset)

    def _refresh_after_reset(self):
        if self.cur_name:
            self._render_student(self.cur_sheet, self.cur_cls, self.cur_name)
        self._refresh_send_btn()
        self._refresh_statusbar()