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
                      save_daily_cache, load_daily_cache, set_runtime_cwd, RUNTIME_DIR,
                      load_templates, save_templates)
from firebase import (firebase_get, firebase_put, firebase_patch, fetch_tags,
                      today_key, active_courses, check_schema)
from ai_engine import AiEngine
import ai_style
from errors import humanize_error
from message   import (today_str, get_room, nickname_suffix, build_message,
                       render, build_bulk_ctx, bulk_variables)
from kakao_image import (copy_image_to_clipboard, focus_kakao,
                         room_opened, copy_text_verified,
                         set_debug_log, send_debug, WIN_VERIFY, foreground_title,
                         prefetch_image, close_rooms)

class App:
    def __init__(self, root):
        self.root = root
        self.root.title(f"{APP_TITLE}  {APP_VERSION}")
        self.root.configure(bg=BG)
        # 전송 게이트 진단 로그 (exe는 콘솔이 없어 print 유실 — 파일 기록)
        set_debug_log(os.path.join(RUNTIME_DIR, 'send_debug.log'))
        self.root.geometry("1100x780")
        self.root.minsize(920, 680)
        self.root.resizable(True, True)

        self.config    = load_config()
        # 스마트 전송 속도 상태 — 학습된 wait 는 config에 영속(다음 실행 이어받음)
        # ※ 반드시 self.config 로드 이후에 초기화
        self._smart_wait        = float(self.config.get('smart_wait', 0.5) or 0.5)
        self._smart_fast_streak = 0
        self._open_ema          = None   # "Enter→방 열림" 실측 지연 EMA
        self._last_open_stats   = None   # (t_open, retried) — 직전 학생 측정값
        self.date_str  = today_str()
        # v3.0: 학생 수행도·특이사항은 웹에서 입력 → Firebase 가져오기로만 로드
        self.progress_data, _, _, _ = load_daily_cache()  # 진도/과제 캐시만 복원
        self.student_data = {}   # Firebase input/ 로드 시 채워짐
        self.note_data    = {}   # Firebase input/ 로드 시 채워짐
        self.force_data   = {}   # (classId, nameKey) → bool 강제완료 플래그
        self.exclude_prog = set()  # {(classId, subject)} — 이번 전송 메시지서 진도/과제 제외 (메모리만)
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

        # 메시지 발송 탭 상태 (ClassManager 발송 기능 이식)
        self.templates        = load_templates()
        self.tmpl_idx         = -1
        self.bulk_sel         = {}     # nameKey → BooleanVar (담당 학생 전체 선택)
        self.bulk_attach_image = ""    # 1회성 첨부 이미지 경로 (templates.json 미저장)
        self.bulk_image_first = tk.BooleanVar(value=False)
        self._bulk_send_cancel = None

        self._main_built = False
        self._token_job  = None
        # 로그인 전환(AUTH_DESIGN): 저장된 refresh_token으로 세션 복원 시도 → 실패 시 로그인 화면.
        if self._try_resume_session():
            self._post_login()
        else:
            self._run_login()

    # ── 로그인(인증) ─────────────────────────────────────────────────
    def _try_resume_session(self):
        """저장된 refresh_token으로 idToken 갱신 + acl 재검증. 성공 시 True(메모리 _id_token 세팅)."""
        rt  = (self.config.get('refresh_token') or '').strip()
        uid = (self.config.get('acl_uid') or '').strip()
        if not rt or not uid:
            return False
        try:
            import pc_auth
            tks = pc_auth.refresh(rt)
            acl = pc_auth.get_acl(uid, tks['idToken'])
            if not acl or acl.get('active') is not True:
                return False
            self.config['_id_token']     = tks['idToken']
            self.config['refresh_token'] = tks['refreshToken']
            self.config['firebase_url']  = pc_auth.FIREBASE_DB_URL
            self.config['firebase_path'] = 'campus/' + acl['campus']
            self.config['instructor_id'] = acl.get('instructorId', self.config.get('instructor_id', ''))
            save_config(self.config)
            return True
        except Exception:
            return False

    def _post_login(self):
        """로그인/복원 후: 스키마 게이트 → 메인 UI → 토큰 갱신 예약."""
        ok, db_ver = check_schema(self.config)
        if not ok:
            from firebase import SCHEMA_MAX
            messagebox.showerror("앱 버전 낮음",
                f"DB 스키마 v{db_ver} > 지원 v{SCHEMA_MAX}\n"
                "데이터 보호를 위해 실행을 중단합니다.\n최신 버전 앱으로 교체해 주세요.")
            self.root.destroy()
            return
        self._build_main_ui()
        self.root.after(300, self._sync_shared_sheets_from_firebase)
        self._schedule_token_refresh()

    def _run_login(self):
        """로그인 화면(캠퍼스+이름+비번)을 메인 창에 빌드."""
        for w in self.root.winfo_children():
            w.destroy()
        wrap = tk.Frame(self.root, bg=BG)
        wrap.place(relx=0.5, rely=0.5, anchor='center')
        tk.Label(wrap, text="DailyReportWizard", font=(FT[0], 18, 'bold'), bg=BG, fg=TEXT).pack(pady=(0, 2))
        tk.Label(wrap, text="강사 로그인", font=FB, bg=BG, fg=SUBTEXT).pack(pady=(0, 18))
        CAMPUS = {'동수원': 'dongsuwon'}
        tk.Label(wrap, text="캠퍼스", font=FS, bg=BG, fg=SUBTEXT, anchor='w').pack(fill='x')
        cv = tk.StringVar(value=list(CAMPUS.keys())[0])
        ttk.Combobox(wrap, textvariable=cv, values=list(CAMPUS.keys()),
                     state='readonly', width=30).pack(pady=(2, 10))
        tk.Label(wrap, text="이름", font=FS, bg=BG, fg=SUBTEXT, anchor='w').pack(fill='x')
        nv = tk.Entry(wrap, width=32); nv.pack(pady=(2, 10)); nv.focus()
        tk.Label(wrap, text="비밀번호", font=FS, bg=BG, fg=SUBTEXT, anchor='w').pack(fill='x')
        pv = tk.Entry(wrap, width=32, show='*'); pv.pack(pady=(2, 10))
        err = tk.Label(wrap, text="", font=FS, bg=BG, fg='#DC2626'); err.pack()
        btn = tk.Button(wrap, text="로그인", bg=INDIGO, fg='white', font=FT,
                        relief='flat', width=26, cursor='hand2')
        btn.pack(pady=(8, 0))
        def submit(*_a):
            err.config(text=""); btn.config(state='disabled', text="로그인 중...")
            self.root.update_idletasks()
            try:
                self._do_login(CAMPUS.get(cv.get(), 'dongsuwon'), nv.get().strip(), pv.get())
            except Exception as e:
                err.config(text=str(e)); btn.config(state='normal', text="로그인")
        btn.config(command=submit)
        nv.bind('<Return>', lambda e: pv.focus())
        pv.bind('<Return>', submit)
        tk.Label(wrap, text="비밀번호 분실 시 관리자에게 문의하세요.",
                 font=FS, bg=BG, fg=SUBTEXT).pack(pady=(16, 0))

    def _do_login(self, campus, name, pw):
        if not name:
            raise RuntimeError("이름을 입력하세요.")
        import pc_auth
        s   = pc_auth.sign_in(campus, name, pw)        # 실패 시 RuntimeError(한국어)
        acl = pc_auth.get_acl(s['uid'], s['idToken'])
        if not acl or acl.get('active') is not True:
            raise RuntimeError("비활성화된 계정입니다. 관리자에게 문의하세요.")
        if acl.get('mustChangePw'):
            if not self._change_password(s):
                raise RuntimeError("비밀번호 변경이 필요합니다.")
        self.config['_id_token']     = s['idToken']
        self.config['refresh_token'] = s['refreshToken']
        self.config['acl_uid']       = s['uid']
        self.config['firebase_url']  = pc_auth.FIREBASE_DB_URL
        self.config['firebase_path'] = 'campus/' + acl['campus']
        self.config['instructor_id'] = acl.get('instructorId', name)
        save_config(self.config)
        for w in self.root.winfo_children():
            w.destroy()
        self._post_login()

    def _change_password(self, s):
        """첫 로그인 비번 변경. 성공 시 acl.mustChangePw 해제. 반환 성공여부."""
        from tkinter import simpledialog
        import pc_auth, urllib.request
        np1 = simpledialog.askstring("비밀번호 변경", "첫 로그인입니다. 새 비밀번호(6자 이상):",
                                     show='*', parent=self.root)
        if not np1:
            return False
        np2 = simpledialog.askstring("비밀번호 변경", "새 비밀번호 확인:", show='*', parent=self.root)
        if np1 != np2:
            messagebox.showwarning("불일치", "두 비밀번호가 일치하지 않습니다."); return False
        if len(np1) < 6:
            messagebox.showwarning("짧음", "비밀번호는 6자 이상이어야 합니다."); return False
        try:
            tks = pc_auth.update_password(s['idToken'], np1)
            if tks.get('idToken'):     s['idToken']     = tks['idToken']
            if tks.get('refreshToken'): s['refreshToken'] = tks['refreshToken']
            url = f"{pc_auth.FIREBASE_DB_URL}/acl/{s['uid']}/mustChangePw.json?auth={s['idToken']}"
            urllib.request.urlopen(urllib.request.Request(url, data=b'false', method='PUT'), timeout=15)
            return True
        except Exception as e:
            messagebox.showerror("변경 실패", str(e)); return False

    def _schedule_token_refresh(self):
        """idToken 1h 만료 대비 — 50분마다 refreshToken으로 갱신."""
        def _do():
            try:
                import pc_auth
                rt = self.config.get('refresh_token')
                if rt:
                    tks = pc_auth.refresh(rt)
                    self.config['_id_token']     = tks['idToken']
                    self.config['refresh_token'] = tks['refreshToken']
                    save_config(self.config)
            except Exception:
                pass
            self._token_job = self.root.after(50 * 60 * 1000, _do)
        self._token_job = self.root.after(50 * 60 * 1000, _do)

    def _build_main_ui(self):
        """헤더 고정 + 노트북(데일리 리포트 / 메시지 발송) 레이아웃 빌드."""
        self._build_header()

        nb = ttk.Notebook(self.root)
        nb.pack(fill='both', expand=True)
        self._nb = nb

        # 탭1 — 기존 데일리 리포트 워크플로우 (시트바+3패널+상태바+푸터)
        tab_report = tk.Frame(nb, bg=BG)
        nb.add(tab_report, text='  📋 데일리 리포트  ')
        self._build_sheet_bar(tab_report)
        self._build_panels(tab_report)
        self._build_statusbar(tab_report)
        self._build_footer(tab_report)

        # 탭2 — 메시지 발송 (ClassManager 발송 기능 이식, 담당 학생 전체)
        tab_bulk = tk.Frame(nb, bg=BG)
        nb.add(tab_bulk, text='  ✉ 메시지 발송  ')
        self._build_bulk_tab(tab_bulk)

        # ⚙ 설정 — 전역: 노트북 탭과 같은 행 우측에 오버레이 (두 탭 공유)
        self.settings_btn = tk.Button(self.root, text="⚙ 설정", font=FS,
                                      bg=BG, fg=INDIGO, relief='flat', bd=0,
                                      cursor='hand2', padx=8,
                                      activebackground="#E4E7FF",
                                      command=self._open_settings)
        self.settings_btn.place(in_=nb, relx=1.0, x=-6, y=3, anchor='ne')

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
            self._bulk_refresh_students()
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

    def _build_sheet_bar(self, parent=None):
        parent = parent or self.root
        bar = tk.Frame(parent, bg="#ECECEF")
        bar.pack(fill='x')
        self.sheet_btns = {}
        for s in ['M', 'T']:
            b = tk.Button(bar, text=f"  {s} 반  ", font=FT,
                          relief='flat', bd=0, cursor='hand2',
                          command=lambda x=s: self._switch_sheet(x))
            b.pack(side='left')
            self.sheet_btns[s] = b
        # v3.0: 진도/과제 버튼 제거 (웹에서 입력), 가져오기 항상 표시
        # ⚙ 설정은 헤더(전역)로 이동 — 메시지 발송 탭과 공유 (v2.2.0)
        tk.Button(bar, text="🗑 초기화", font=FS,
                  bg="#ECECEF", fg="#EF4444", relief='flat', cursor='hand2',
                  command=self._open_reset_dialog
                  ).pack(side='right', padx=0, pady=3)
        tk.Button(bar, text="📥 데이터 가져오기", font=FS,
                  bg=GREEN, fg='white', relief='flat', cursor='hand2',
                  command=self._pull_mobile_data
                  ).pack(side='right', padx=8, pady=3)

    def _build_panels(self, parent=None):
        parent = parent or self.root
        pf = tk.Frame(parent, bg=BG)
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
        courses   = active_courses(cls_data)
        subjects  = sorted(courses.keys())  # 과정→교재명 오름차순 (subject="{과정} {교재}" 복합 키)
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
            _is_sub_pf = self._is_sub_teacher(classId)
            for subject in subjects:
                pd_val = self.progress_data.get((classId, subject), {})
                if pd_val.get('progress') or pd_val.get('homework'):
                    excluded = (classId, subject) in self.exclude_prog
                    tb_lbl = grade_label(tb_grade.get(subject, ''), subject)
                    # 헤더 행: 과목명 + 메시지 제외 토글 (담임만)
                    hdr = tk.Frame(pf, bg="#ECFDF3")
                    hdr.pack(fill='x', pady=(3, 0))
                    tk.Label(hdr, text=tb_lbl, font=("맑은 고딕", 8, "bold"),
                             bg="#ECFDF3", fg=(GRAY if excluded else INDIGO)).pack(side='left')
                    if not _is_sub_pf:
                        if excluded:
                            _xb = tk.Button(hdr, text="↩ 메시지에 포함", font=("맑은 고딕", 8),
                                            bg="#FEE2E2", fg="#B91C1C", relief='flat',
                                            padx=7, pady=0, cursor='hand2',
                                            command=lambda s=subject: self._toggle_exclude_prog(classId, s))
                        else:
                            _xb = tk.Button(hdr, text="✕ 메시지서 제외", font=("맑은 고딕", 8),
                                            bg="#E6F7EF", fg="#0F6E56", relief='flat',
                                            padx=7, pady=0, cursor='hand2',
                                            command=lambda s=subject: self._toggle_exclude_prog(classId, s))
                        _xb.pack(side='right')
                    _fg = GRAY if excluded else TEXT
                    _sfx = "   — 제외됨(메시지 미포함)" if excluded else ""
                    if pd_val.get('progress'):
                        tk.Label(pf, text=f"  진도: {pd_val['progress']}{_sfx}",
                                 font=FS, bg="#ECFDF3", fg=_fg
                                 ).pack(anchor='w')
                    if pd_val.get('homework'):
                        tk.Label(pf, text=f"  과제: {pd_val['homework']}{_sfx}",
                                 font=FS, bg="#ECFDF3", fg=_fg
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
            _engine = self.config.get('ai_engine_type', 'gemini').strip().lower()
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
        """관찰 태그 세그먼트를 박스 폭에 맞춰 자동 줄바꿈(flow-wrap)하여
        색별 Label 렌더. 태그가 많아도 오른쪽으로 넘쳐 잘리지 않고, 창
        리사이즈 시 폭 변화에 맞춰 재배치된다. 없으면 미표시."""
        segs = self._obs_tag_segments(nameKey, subject)
        if not segs:
            return
        import sys as _sys
        import tkinter.font as _tkfont
        tag_font = ("Segoe UI Emoji", 9) if _sys.platform == "win32" else FE
        bg = parent.cget('bg')
        holder = tk.Frame(parent, bg=bg)
        holder.pack(fill='x', pady=(5, 0))

        fnt   = _tkfont.Font(font=tag_font)
        sep_w = fnt.measure("·") + 8   # 구분점 + 좌우 padx 여유(살짝 넉넉히)

        last_w = [0]
        def _reflow(event=None):
            # holder 실폭 기준 재배치 — 폭이 안 바뀌면 무시(자식 변경發 재귀 차단)
            avail = event.width if event is not None else holder.winfo_width()
            if avail <= 1 or avail == last_w[0]:
                return
            last_w[0] = avail
            for w in holder.winfo_children():
                w.destroy()
            row = tk.Frame(holder, bg=bg); row.pack(fill='x', anchor='w')
            used, first = 0, True
            for text, color in segs:
                tw   = fnt.measure(text)
                need = tw if first else tw + sep_w
                if not first and used + need > avail:   # 줄 넘침 → 새 줄
                    row = tk.Frame(holder, bg=bg); row.pack(fill='x', anchor='w')
                    used, first, need = 0, True, tw
                if not first:
                    tk.Label(row, text="·", font=tag_font, bg=bg,
                             fg="#D1D5DB").pack(side='left', padx=2)
                tk.Label(row, text=text, font=tag_font, bg=bg,
                         fg=color).pack(side='left')
                used, first = used + need, False

        holder.bind('<Configure>', _reflow)

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
    def _build_statusbar(self, parent=None):
        parent = parent or self.root
        sb = tk.Frame(parent, bg="#ECFDF3",
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

    def _build_footer(self, parent=None):
        parent = parent or self.root
        foot = tk.Frame(parent, bg=PANEL,
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

    def _class_info_for(self, classId, subjects):
        """진도/과제 class_info — exclude_prog 에 든 (classId,subject)은 빈값(메시지 제외)."""
        info = {}
        for subj in subjects:
            if (classId, subj) in self.exclude_prog:
                info[subj] = {'progress': '', 'homework': ''}
            else:
                info[subj] = self.progress_data.get((classId, subj), {'progress': '', 'homework': ''})
        return info

    def _toggle_exclude_prog(self, classId, subject):
        """진도/과제를 이번 전송 메시지서 제외/포함 토글 (메모리만, DB 무관)."""
        key = (classId, subject)
        if key in self.exclude_prog:
            self.exclude_prog.discard(key)
        else:
            self.exclude_prog.add(key)
        if self.cur_name:
            self._render_student(self.activeGroup, self.cur_cls, self.cur_name)

    def _update_preview(self):
        group, classId, nameKey = self.activeGroup, self.cur_cls, self.cur_name
        if not nameKey: return
        cls_data  = self.all_classes.get(classId, {})
        courses   = active_courses(cls_data)
        subjects  = sorted(courses.keys())  # 과정→교재명 오름차순 (subject="{과정} {교재}" 복합 키)
        tb_grade  = {subj: courses[subj].get('curriculum', '') for subj in subjects}
        display_name = self.all_students.get(nameKey, {}).get('name', nameKey)
        room      = get_room(self.config, display_name)
        class_info = self._class_info_for(classId, subjects)
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
                return sorted(group_classes.items())  # 계정 미설정 → 전체 표시 (반 이름 오름차순)
            return []  # 계정 있고 담당 없음 → 빈 목록
        # cls/classId 둘 다 허용, sheet 없으면 classes group으로 판단
        def _cid(a): return a.get('cls') or a.get('classId', '')
        def _grp_ok(a):
            s = a.get('sheet')
            if s: return s == group
            return self.all_classes.get(_cid(a), {}).get('group') == group
        assigned_cls = {_cid(a) for a in assignments if _grp_ok(a)}
        # 반 이름 오름차순 — 좌측 패널·전송·상태바 등 모든 순회가 등록 순 아닌 정렬 순으로 일관
        return sorted(((cid, cd) for cid, cd in group_classes.items() if cid in assigned_cls))

    def _student_status(self, classId, nameKey):
        # 강제 완료 플래그 우선
        if self.force_data.get((classId, nameKey)):
            return STATUS_READY
        courses  = active_courses(self.all_classes.get(classId, {}))
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
            courses    = active_courses(cls_data)
            subjects   = list(courses.keys())
            tb_grade   = {subj: courses[subj].get('curriculum', '') for subj in subjects}
            class_info = self._class_info_for(classId, subjects)
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

    # ══════════════════════════════════════════════════════════════════
    # 메시지 발송 탭 — ClassManager 발송 기능 이식 (담당 학생 전체 대상)
    # ══════════════════════════════════════════════════════════════════
    def _build_bulk_tab(self, parent):
        parent.columnconfigure(0, weight=0, minsize=250)
        parent.columnconfigure(1, weight=1)
        parent.rowconfigure(0, weight=1)
        self._build_bulk_left(parent)
        self._build_bulk_right(parent)
        self._bulk_refresh_students()
        self._bulk_refresh_tmpl_cb()

    def _build_bulk_left(self, parent):
        frm = tk.Frame(parent, bg=PANEL,
                       highlightbackground=BORDER, highlightthickness=1)
        frm.grid(row=0, column=0, sticky='nsew', padx=(8, 4), pady=8)

        hdr = tk.Frame(frm, bg=PANEL)
        hdr.pack(fill='x', padx=10, pady=(10, 4))
        tk.Label(hdr, text="담당 학생 전체", font=FT, bg=PANEL, fg=TEXT).pack(side='left')
        tk.Button(hdr, text="↺", font=FS, bg=PANEL, fg=INDIGO, relief='flat',
                  cursor='hand2', command=self._bulk_refresh_students).pack(side='right')

        tools = tk.Frame(frm, bg=PANEL)
        tools.pack(fill='x', padx=10, pady=(0, 4))
        tk.Button(tools, text="전체선택", font=FS, bg=PANEL, fg=INDIGO, relief='flat',
                  cursor='hand2', command=lambda: self._bulk_select_all(True)).pack(side='left')
        tk.Button(tools, text="전체해제", font=FS, bg=PANEL, fg=GRAY, relief='flat',
                  cursor='hand2', command=lambda: self._bulk_select_all(False)).pack(side='left', padx=6)

        sc_frm = tk.Frame(frm, bg=PANEL)
        sc_frm.pack(fill='both', expand=True, padx=6, pady=4)
        self.bulk_canvas, self.bulk_list = make_scroll_frame(sc_frm, bg=PANEL)

        self.bulk_count_lbl = tk.Label(frm, text="0명 선택", font=FS, bg=PANEL, fg=SUBTEXT)
        self.bulk_count_lbl.pack(anchor='w', padx=12, pady=(0, 8))

    def _build_bulk_right(self, parent):
        frm = tk.Frame(parent, bg=PANEL,
                       highlightbackground=BORDER, highlightthickness=1)
        frm.grid(row=0, column=1, sticky='nsew', padx=(4, 8), pady=8)
        frm.rowconfigure(3, weight=1)
        frm.columnconfigure(0, weight=1)

        th = tk.Frame(frm, bg=PANEL)
        th.grid(row=0, column=0, sticky='ew', padx=12, pady=(12, 4))
        tk.Label(th, text="메시지 템플릿", font=FT, bg=PANEL, fg=TEXT).pack(side='left')
        tk.Button(th, text="+ 추가", font=FS, bg=INDIGO, fg='white', relief='flat',
                  cursor='hand2', padx=6, command=self._bulk_add_template).pack(side='right')
        tk.Button(th, text="삭제", font=FS, bg=PANEL, fg="#EF4444", relief='flat',
                  cursor='hand2', command=self._bulk_del_template).pack(side='right', padx=4)

        ts = tk.Frame(frm, bg=PANEL)
        ts.grid(row=1, column=0, sticky='ew', padx=12, pady=(0, 6))
        self.bulk_tmpl_var = tk.StringVar()
        self.bulk_tmpl_cb = ttk.Combobox(ts, textvariable=self.bulk_tmpl_var,
                                         state='readonly', width=26, font=FB)
        self.bulk_tmpl_cb.pack(side='left')
        self.bulk_tmpl_cb.bind('<<ComboboxSelected>>', lambda e: self._bulk_on_tmpl_change())

        tk.Label(frm, text="템플릿 편집", font=FS, bg=PANEL, fg=SUBTEXT
                 ).grid(row=2, column=0, sticky='w', padx=12)
        self.bulk_tmpl_text = tk.Text(frm, font=FB, bg=PANEL, fg=TEXT, relief='flat',
                                      wrap='word', highlightbackground=BORDER,
                                      highlightthickness=1, insertbackground=TEXT, height=8)
        self.bulk_tmpl_text.grid(row=3, column=0, sticky='nsew', padx=12, pady=(2, 4))
        self.bulk_tmpl_text.bind('<KeyRelease>', lambda e: self._bulk_on_tmpl_edit())

        hint = tk.Frame(frm, bg=PANEL)
        hint.grid(row=4, column=0, sticky='ew', padx=12, pady=(0, 4))
        tk.Label(hint, text="변수:", font=FS, bg=PANEL, fg=SUBTEXT).pack(side='left')
        for var, _desc in bulk_variables():
            tk.Button(hint, text=var, font=FS, bg=INDIGO_L, fg=INDIGO, relief='flat',
                      cursor='hand2', padx=3,
                      command=lambda v=var: self._bulk_insert_var(v)).pack(side='left', padx=1)

        pv = tk.Frame(frm, bg=INDIGO_L)
        pv.grid(row=5, column=0, sticky='ew', padx=12, pady=(0, 8))
        tk.Label(pv, text="미리보기 (첫 번째 선택 학생)", font=FS, bg=INDIGO_L, fg=INDIGO
                 ).pack(anchor='w', padx=6, pady=(4, 0))
        self.bulk_preview_lbl = tk.Label(pv, text="", font=FS, bg=INDIGO_L, fg=TEXT,
                                         justify='left', anchor='w', wraplength=520)
        self.bulk_preview_lbl.pack(fill='x', padx=6, pady=(0, 6))

        img = tk.Frame(frm, bg=PANEL)
        img.grid(row=6, column=0, sticky='ew', padx=12, pady=(0, 6))
        tk.Button(img, text="📎 이미지 첨부", font=FS, bg=INDIGO_L, fg=INDIGO, relief='flat',
                  cursor='hand2', padx=6, command=self._bulk_choose_image).pack(side='left')
        self.bulk_attach_lbl = tk.Label(img, text="(없음)", font=FS, bg=PANEL, fg=SUBTEXT)
        self.bulk_attach_lbl.pack(side='left', padx=8)
        self.bulk_attach_clear_btn = tk.Button(img, text="✕", font=FS, bg=PANEL, fg="#EF4444",
                                               relief='flat', cursor='hand2',
                                               command=self._bulk_clear_image)
        tk.Checkbutton(img, text="이미지 먼저", variable=self.bulk_image_first, font=FS,
                       bg=PANEL, fg=SUBTEXT, selectcolor='white',
                       activebackground=PANEL).pack(side='right')

        sf = tk.Frame(frm, bg=PANEL)
        sf.grid(row=7, column=0, sticky='ew', padx=12, pady=(0, 6))
        self.bulk_send_btn = tk.Button(sf, text="🚀 카카오톡으로 전송",
                                       font=("맑은 고딕", 10, "bold"), bg=ACCENT, fg="#0E1016",
                                       relief='flat', cursor='hand2', pady=8,
                                       command=self._bulk_send)
        self.bulk_send_btn.pack(fill='x')
        self.bulk_status = tk.Label(frm, text="", font=FS, bg=PANEL, fg=GRAY, anchor='w')
        self.bulk_status.grid(row=8, column=0, sticky='ew', padx=12, pady=(0, 10))

    # ── 담당 학생 전체 수집·렌더 ─────────────────────────────────────
    def _my_students_all(self):
        """담당 학생 전체 (부담임 반 제외, M+T 통합, nameKey 중복 제거).
        → [{nameKey, name, classId}, ...] (이름 정렬은 all_students 순서 상속)."""
        result, seen = [], set()
        for group in ('M', 'T'):
            for classId, _cd in self._my_classes(group):
                if self._is_sub_teacher(classId):
                    continue
                for nk, v in self.all_students.items():
                    if v.get('class') == classId and nk not in seen:
                        seen.add(nk)
                        result.append({'nameKey': nk,
                                       'name': v.get('name', nk),
                                       'classId': classId})
        return result

    def _bulk_refresh_students(self):
        if not hasattr(self, 'bulk_list'):
            return
        for w in self.bulk_list.winfo_children():
            w.destroy()
        students = self._my_students_all()
        valid = {s['nameKey'] for s in students}
        self.bulk_sel = {k: v for k, v in self.bulk_sel.items() if k in valid}

        if not students:
            tk.Label(self.bulk_list,
                     text="담당 학생이 없습니다.\n설정에서 강사 계정·담당 반을 확인하세요.",
                     font=FB, bg=PANEL, fg=SUBTEXT, justify='left'
                     ).pack(padx=14, pady=14, anchor='w')
            self._bulk_update_count()
            return

        by_cls = {}
        for s in students:
            by_cls.setdefault(s['classId'], []).append(s)

        for classId in sorted(by_cls):
            ch = tk.Frame(self.bulk_list, bg=PANEL)
            ch.pack(fill='x', pady=(6, 0))
            tk.Label(ch, text=classId, font=FB, bg=PANEL, fg=INDIGO,
                     anchor='w').pack(side='left', padx=8)
            tk.Button(ch, text="반 선택", font=FS, bg=PANEL, fg=GRAY, relief='flat',
                      cursor='hand2',
                      command=lambda c=classId: self._bulk_select_class(c)
                      ).pack(side='right', padx=4)
            for s in by_cls[classId]:
                nk = s['nameKey']
                if nk not in self.bulk_sel:
                    self.bulk_sel[nk] = tk.BooleanVar(value=False)
                tk.Checkbutton(self.bulk_list, text=s['name'], variable=self.bulk_sel[nk],
                               font=FB, bg=PANEL, fg=TEXT, anchor='w', selectcolor='white',
                               activebackground=PANEL, command=self._bulk_update_count
                               ).pack(fill='x', padx=(16, 4))
        self._bulk_update_count()

    def _bulk_select_class(self, classId):
        for s in self._my_students_all():
            if s['classId'] == classId and s['nameKey'] in self.bulk_sel:
                self.bulk_sel[s['nameKey']].set(True)
        self._bulk_update_count()

    def _bulk_select_all(self, val):
        for v in self.bulk_sel.values():
            v.set(val)
        self._bulk_update_count()

    def _bulk_update_count(self):
        n = sum(1 for v in self.bulk_sel.values() if v.get())
        if hasattr(self, 'bulk_count_lbl'):
            self.bulk_count_lbl.config(text=f"{n}명 선택")
        self._bulk_update_preview()

    def _bulk_selected_students(self):
        """선택된 학생 [{nameKey, name, classId}] (담당 전체 순서 유지)."""
        return [s for s in self._my_students_all()
                if self.bulk_sel.get(s['nameKey']) and self.bulk_sel[s['nameKey']].get()]

    # ── 템플릿 관리 ──────────────────────────────────────────────────
    def _bulk_refresh_tmpl_cb(self):
        names = [t.get('name', '') for t in self.templates]
        self.bulk_tmpl_cb['values'] = names
        if names:
            if not (0 <= self.tmpl_idx < len(names)):
                self.tmpl_idx = 0
            self.bulk_tmpl_var.set(names[self.tmpl_idx])
            self._bulk_load_tmpl(self.tmpl_idx)
        else:
            self.tmpl_idx = -1
            self.bulk_tmpl_var.set('')
            self.bulk_tmpl_text.delete('1.0', 'end')
            self._bulk_update_preview()

    def _bulk_on_tmpl_change(self):
        sel = self.bulk_tmpl_var.get()
        for i, t in enumerate(self.templates):
            if t.get('name') == sel:
                self.tmpl_idx = i
                self._bulk_load_tmpl(i)
                break

    def _bulk_load_tmpl(self, idx):
        self.bulk_tmpl_text.delete('1.0', 'end')
        self.bulk_tmpl_text.insert('1.0', self.templates[idx].get('body', ''))
        self._bulk_update_preview()

    def _bulk_on_tmpl_edit(self):
        if 0 <= self.tmpl_idx < len(self.templates):
            self.templates[self.tmpl_idx]['body'] = self.bulk_tmpl_text.get('1.0', 'end-1c')
            save_templates(self.templates)
        self._bulk_update_preview()

    def _bulk_add_template(self):
        from tkinter import simpledialog
        name = simpledialog.askstring("템플릿 추가", "템플릿 이름:", parent=self.root)
        if not name:
            return
        self.templates.append({'name': name.strip(), 'body': ''})
        self.tmpl_idx = len(self.templates) - 1
        save_templates(self.templates)
        self._bulk_refresh_tmpl_cb()

    def _bulk_del_template(self):
        if not self.templates or self.tmpl_idx < 0:
            return
        name = self.templates[self.tmpl_idx].get('name', '')
        if not messagebox.askyesno("삭제 확인", f'"{name}" 템플릿을 삭제할까요?', parent=self.root):
            return
        self.templates.pop(self.tmpl_idx)
        self.tmpl_idx = max(0, self.tmpl_idx - 1) if self.templates else -1
        save_templates(self.templates)
        self._bulk_refresh_tmpl_cb()

    def _bulk_insert_var(self, var):
        self.bulk_tmpl_text.insert('insert', var)
        self._bulk_on_tmpl_edit()

    def _bulk_update_preview(self):
        if not hasattr(self, 'bulk_preview_lbl'):
            return
        sel = self._bulk_selected_students()
        if not sel:
            self.bulk_preview_lbl.config(text="(선택된 학생 없음)")
            return
        s = sel[0]
        body = (self.bulk_tmpl_text.get('1.0', 'end-1c')
                if self.bulk_tmpl_text.winfo_exists() else '')
        try:
            ctx = build_bulk_ctx(s['name'], s['classId'])
            self.bulk_preview_lbl.config(text=render(body, ctx))
        except Exception as e:
            self.bulk_preview_lbl.config(text=f"[오류] {e}")

    # ── 이미지 첨부 ──────────────────────────────────────────────────
    def _bulk_choose_image(self):
        path = filedialog.askopenfilename(
            title="첨부할 이미지 선택",
            filetypes=[("이미지", "*.png *.jpg *.jpeg *.gif *.bmp"), ("모든 파일", "*.*")],
            parent=self.root)
        if not path:
            return
        self.bulk_attach_image = path
        self.bulk_attach_lbl.config(text=os.path.basename(path), fg=INDIGO)
        self.bulk_attach_clear_btn.pack(side='left')

    def _bulk_clear_image(self):
        self.bulk_attach_image = ""
        self.bulk_attach_lbl.config(text="(없음)", fg=SUBTEXT)
        self.bulk_attach_clear_btn.pack_forget()

    # ── 전송 ─────────────────────────────────────────────────────────
    def _bulk_send(self):
        if not AUTOMATION:
            messagebox.showerror("오류",
                "pyautogui / pyperclip이 설치되어 있지 않습니다.\n"
                "pip install pyautogui pyperclip"); return
        sel = self._bulk_selected_students()
        if not sel:
            messagebox.showinfo("알림", "전송 대상 학생을 선택하세요."); return

        body      = self.bulk_tmpl_text.get('1.0', 'end-1c')
        img_path  = self.bulk_attach_image
        img_first = self.bulk_image_first.get()
        if img_path and not os.path.exists(img_path):
            messagebox.showwarning("이미지 없음",
                f"첨부 이미지를 찾을 수 없습니다:\n{img_path}", parent=self.root); return
        if not body.strip() and not img_path:
            messagebox.showinfo("알림", "본문 또는 첨부 이미지가 필요합니다."); return

        # 동명이인 가드 — 같은 이름은 같은 방으로 검색돼 오발송 위험
        sel, dups = self._dedup_same_name(sel)
        if dups:
            messagebox.showwarning("동명이인 제외",
                "동명이인이 있어 다음 학생은 자동 전송에서 제외했습니다:\n"
                f"{', '.join(dups)}\n\n개별 전송하세요.")
            if not sel:
                return

        msgs = []
        for s in sel:
            ctx = build_bulk_ctx(s['name'], s['classId'])
            # 방 검색어는 get_room 단일 경로 — prefix-이름 공백 1개 보장 (직접 이어붙이기 금지)
            m = {'name': s['name'], 'room': get_room(self.config, s['name']), 'msg': render(body, ctx)}
            if img_path:
                m['image']       = img_path
                m['image_first'] = img_first
            msgs.append(m)

        img_note = ""
        if img_path:
            order = "이미지→본문" if img_first else "본문→이미지"
            img_note = f"\n📎 이미지: {os.path.basename(img_path)} ({order})"
        if not messagebox.askyesno("전송 확인",
                f"전송 대상: {len(msgs)}명{img_note}\n" +
                ", ".join(m['room'] for m in msgs) +
                "\n\n[예]를 누르면 카카오톡 창을 자동으로 찾아 전송을 시작합니다."):
            return

        self._bulk_send_cancel = threading.Event()
        self._bulk_set_cancel(True)
        threading.Thread(target=self._do_bulk_send, args=(msgs,), daemon=True).start()

    def _bulk_set_cancel(self, on):
        if on:
            self.bulk_send_btn.config(text="⏹ 전송 취소", bg="#FEE2E2", fg="#DC2626",
                                      command=self._bulk_cancel)
        else:
            self.bulk_send_btn.config(text="🚀 카카오톡으로 전송",
                                      bg=ACCENT, fg="#0E1016", command=self._bulk_send)

    def _bulk_cancel(self):
        if self._bulk_send_cancel:
            self._bulk_send_cancel.set()
        self.bulk_status.config(text="⏹ 취소 중... (현재 학생 완료 후 중단)")

    def _do_bulk_send(self, msgs):
        cancel = self._bulk_send_cancel
        wait   = self._send_wait()
        total  = len(msgs)
        # v2.2.3: 카톡 창 자동 포커스 (데일리 _do_send 와 동일 정책)
        for _ in range(10):
            if cancel.is_set(): break
            time.sleep(0.1)
        if not cancel.is_set() and not focus_kakao():
            def _no_kakao():
                self._bulk_set_cancel(False)
                self.bulk_status.config(text="❌ 카카오톡 창을 찾지 못해 중단")
                messagebox.showerror("카카오톡 창 없음",
                    "카카오톡 창을 찾을 수 없습니다.\n"
                    "카카오톡 실행·로그인 상태를 확인한 뒤 다시 전송하세요.")
            self.root.after(0, _no_kakao)
            return
        # 이미지 DIB 선행 변환 — 학생별 PowerShell 재기동(1~2s) 제거, 첫 학생부터 무지연
        for _img in {m['image'] for m in msgs if m.get('image')}:
            prefetch_image(_img)
        sent = 0
        failed = []
        focus_lost = False
        lingering = []   # 정리 대상 잔류 방 — 이미지 방(의도적 미닫음) + 오류 중단 방
        for i, m in enumerate(msgs):
            if cancel.is_set(): break
            self.root.after(0, lambda t=f"전송 중... ({i+1}/{total})  {m['name']}":
                            self.bulk_status.config(text=t))
            if i > 0 and not focus_kakao(0.3):
                focus_lost = True
                break
            warm = 0.6 if i == 0 else 0.0
            wait = self._send_wait()   # 스마트 모드: 직전 학생 측정으로 갱신된 값
            try:
                self._kakao_send_one(m, wait, warm)
                sent += 1
                if m.get('image'):
                    lingering.append(m['room'])   # 이미지 방은 미닫음 — 종료 후 일괄 정리
            except Exception as e:
                print(f"오류 [{m['name']}]: {e}")
                send_debug(f"학생 실패 [{m['name']}]: {e}")
                failed.append(m.get('name', '?'))
                if m.get('room'):
                    lingering.append(m['room'])   # 오류 중단 방도 열려 있을 수 있음
            if self._last_open_stats:
                self._smart_adjust(*self._last_open_stats)
                self._last_open_stats = None
            time.sleep(0.3)  # 학생 간 간격 — 게이트 검증으로 단축(기존 0.8)
        cancelled = cancel.is_set()
        self._smart_persist()   # 스마트 모드 학습값 저장 — 다음 실행 이어받기
        self._cleanup_rooms(lingering, lambda t: self.bulk_status.config(text=t))
        def _done():
            self._bulk_set_cancel(False)
            fail_line = f"\n⚠ 실패 {len(failed)}명: {', '.join(failed)}" if failed else ""
            if focus_lost:
                self.bulk_status.config(text=f"❌ 카톡 창 소실 — {sent}/{total}명에서 중단")
                messagebox.showerror("전송 중단",
                    f"{sent}명 전송 후 카카오톡 창을 잃어 중단했습니다.\n"
                    "카카오톡 확인 후 다시 전송하세요." + fail_line)
            elif cancelled:
                self.bulk_status.config(text=f"⏹ {sent}/{total}명 전송 후 취소")
                messagebox.showinfo("전송 취소", f"{sent}명 전송 후 취소했습니다." + fail_line)
            elif failed:
                self.bulk_status.config(text=f"⚠ 전송 {sent}/{total}명 — 실패 {len(failed)}명")
                messagebox.showwarning("일부 실패",
                    f"{sent}명 전송 완료, {len(failed)}명 실패:\n{', '.join(failed)}")
            else:
                self.bulk_status.config(text=f"✅ 전송 완료 — {sent}명")
                messagebox.showinfo("완료", f"{sent}명 전송 완료!")
        self.root.after(0, _done)

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
        courses  = active_courses(self.all_classes.get(cid, {}))
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
            self.exclude_prog.clear()

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
                # 방어: 활성 과목(archived 제외)이 아니면 무시 — 삭제·보관된 과목의 고아 진도/과제 차단
                _courses = active_courses(self.all_classes.get(classId, {}))
                if subject not in _courses:
                    continue
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
            messagebox.showerror("오류", humanize_error(e, "데이터를 가져오지 못했습니다."))

    def _import_mobile_data(self, data):
        """Firebase input/ 노드에서 특이사항(note) 반영 (v2.1.2 스키마)
        구조: {nameKey: {__note__: {note}}}
        · note(특이사항): 학생별 단일(__note__). **항상 웹 데이터로 교체** — 웹에서 비웠으면
          빈값으로 덮어쓴다(기존 기록 잔류 방지). __note__ 없으면 구 과목별 note fallback.
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
            note_key = (classId, nameKey)
            note_rec = subjects.get('__note__')
            if isinstance(note_rec, dict):
                # __note__ 가 authoritative — 빈값이어도 그대로 반영(웹에서 비운 것)
                final = note_rec.get('note', '') or ''
            else:
                # __note__ 없음 → 구 과목별 note fallback (마이그레이션 전 호환)
                final = ''
                for subject, payload in subjects.items():
                    if subject != '__note__' and isinstance(payload, dict) and payload.get('note'):
                        final = payload['note']
                        break
            # 항상 교체(빈값 포함). render/전송 측은 빈 문자열을 '메모 없음'으로 처리.
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
            messagebox.showerror("실패", humanize_error(e, "Firebase에 연결하지 못했습니다."), parent=self.root)

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
                    messagebox.showerror("오류", humanize_error(e, "강사 계정 처리에 실패했습니다."), parent=self.root),
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
        win.geometry("660x700")
        win.configure(bg=BG)
        win.resizable(True, True)     # 가로·세로 모두 조절 가능 (긴 안내문 잘림 방지)
        win.minsize(600, 560)

        # 헤더
        hdr = tk.Frame(win, bg=DARK, height=40)
        hdr.pack(fill='x')
        hdr.pack_propagate(False)
        tk.Label(hdr, text="⚙ 설정", font=FT, bg=DARK, fg='white').pack(side='left', padx=16, pady=8)

        # ── 하단 고정 푸터(저장/취소) — 본문보다 먼저 bottom 배치 ──────
        footer = tk.Frame(win, bg=BG)
        footer.pack(side='bottom', fill='x')
        tk.Frame(win, bg=BORDER, height=1).pack(side='bottom', fill='x')

        # ── 본문: 좌측 탭 레일 + 우측 탭별 스크롤 콘텐츠 ───────────────
        body = tk.Frame(win, bg=BG)
        body.pack(side='top', fill='both', expand=True)
        rail = tk.Frame(body, bg="#F4F4F6", width=132)
        rail.pack(side='left', fill='y')
        rail.pack_propagate(False)
        content = tk.Frame(body, bg=BG)
        content.pack(side='left', fill='both', expand=True)

        # 라벨 실폭에 맞춰 자동 줄바꿈 — 창 가로 리사이즈/탭 폭 변화에 반응(고정 wraplength로
        # 잘리던 문제 해결). 안내문·미리보기·힌트 등 긴 텍스트 라벨에 일괄 적용.
        def _wrap_to_width(lbl, pad=16):
            lbl.bind('<Configure>',
                     lambda e, w=lbl: e.width > 1 and w.config(wraplength=e.width - pad))

        def _mk_tab():
            holder = tk.Frame(content, bg=BG)
            _cv, frm = make_scroll_frame(holder, bg=BG)
            return holder, frm
        ai_hold,   tab_ai      = _mk_tab()
        conn_hold, tab_conn    = _mk_tab()
        acct_hold, tab_account = _mk_tab()
        gen_hold,  tab_general = _mk_tab()

        _TABS = [
            ('ai',      '🤖 AI 생성',  ai_hold),
            ('conn',    '🔥 연결',     conn_hold),
            ('account', '👤 강사 계정', acct_hold),
            ('general', '⚙ 일반',      gen_hold),
        ]
        _tab_btns = {}
        def _show_tab(key):
            for _k, _l, h in _TABS:
                h.pack_forget()
            for _k, _l, h in _TABS:
                if _k == key:
                    h.pack(fill='both', expand=True)
            for _k, b in _tab_btns.items():
                b.config(bg=(INDIGO_L if _k == key else "#F4F4F6"),
                         fg=(INDIGO if _k == key else TEXT))
        for _k, _lbl, _h in _TABS:
            b = tk.Button(rail, text="  " + _lbl, font=FB, bg="#F4F4F6", fg=TEXT,
                          relief='flat', anchor='w', padx=8, pady=8, cursor='hand2',
                          command=lambda kk=_k: _show_tab(kk))
            b.pack(fill='x', padx=6, pady=1)
            _tab_btns[_k] = b

        # ── 일반(매크로) 탭 ───────────────────────────────────
        inner = tab_general
        self._settings_section(inner, "기본 매크로 설정")
        
        delay_grid = tk.Frame(inner, bg=BG)
        delay_grid.pack(fill='x', padx=16, pady=(0,10))
        delay_grid.columnconfigure(1, weight=1)

        tk.Label(delay_grid, text="전송 속도", font=FS, bg=BG, fg=SUBTEXT).grid(row=0, column=0, sticky='w', pady=3, padx=(0,8))
        speed_var = tk.StringVar(value=self.config.get('send_speed', 'smart'))
        speed_row = tk.Frame(delay_grid, bg=BG)
        speed_row.grid(row=0, column=1, sticky='w')
        for _val, _lbl in (('smart', '스마트 (권장)'), ('fast', '고속'),
                           ('normal', '보통'), ('stable', '안정')):
            tk.Radiobutton(speed_row, text=_lbl, variable=speed_var, value=_val,
                           font=FS, bg=BG, fg=TEXT, selectcolor=BG,
                           activebackground=BG).pack(side='left', padx=(0, 8))
        tk.Label(delay_grid, text="스마트=응답 속도를 실측해 자동 가감속 · 고속/보통/안정=수동 고정",
                 font=FS, bg=BG, fg=GRAY).grid(row=1, column=1, sticky='w', pady=(0, 3))

        tk.Label(delay_grid, text="카톡 접두사", font=FS, bg=BG, fg=SUBTEXT).grid(row=2, column=0, sticky='w', pady=3, padx=(0,8))
        prefix_var = tk.StringVar(value=self.config.get('room_prefix', '오직 '))
        tk.Entry(delay_grid, textvariable=prefix_var, font=FS, relief='solid', bd=1).grid(row=2, column=1, sticky='ew', ipady=3)

        # ── 연결 탭 (Firebase) ────────────────────────────────
        inner = tab_conn
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
                messagebox.showerror("실패", humanize_error(e, "Firebase에 연결하지 못했습니다."), parent=win)

        test_row = tk.Frame(inner, bg=BG)
        test_row.pack(fill='x', padx=16, pady=(0,10))
        tk.Button(test_row, text="⚡ 연결 테스트", font=FS, bg="#EEF0FF", fg=INDIGO, relief='flat', padx=10, pady=4, cursor='hand2', command=_test_connection).pack(side='left')

        # ── 강사 계정 탭 ───────────────────────────────────────
        inner = tab_account
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
                        messagebox.showerror("오류", humanize_error(e, "강사 계정 처리에 실패했습니다."), parent=win),
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
                messagebox.showerror("오류", humanize_error(e, "명단을 가져오지 못했습니다."), parent=win)

        tk.Button(fetch_row, text="🔄 학급/명단 동기화", font=FS, bg="#F7F7F9", fg=TEXT, relief='solid', bd=1, padx=10, pady=4, cursor='hand2', command=_fetch_class_data).pack(side='left')
        tk.Label(fetch_row, text="계정 조회 후 클릭하세요", font=FS, bg=BG, fg=GRAY).pack(side='left', padx=8)

        # ── 🤖 AI 생성 탭 (전면·핵심 기능) ────────────────────
        inner = tab_ai
        self._settings_section(inner, "AI 특이사항 생성")
        _ai_intro = tk.Label(inner, text="사용할 AI 엔진·문체·개별 지침을 설정하세요. 중앙 패널 ✨ AI생성 버튼이 연동됩니다.", font=FS, bg=BG, fg=SUBTEXT, justify='left', anchor='w')
        _ai_intro.pack(anchor='w', fill='x', padx=16, pady=(0,6))
        _wrap_to_width(_ai_intro, pad=36)

        ai_grid = tk.Frame(inner, bg=BG)
        ai_grid.pack(fill='x', padx=16, pady=(0,10))
        ai_grid.columnconfigure(1, weight=1)

        # 엔진 드롭다운 — 표시명(공식 표기)을 보여주고 내부 id로 매핑
        _label2id = {AI_ENGINE_LABELS[i]: i for i in AI_ENGINE_ORDER}
        _cur_id = self.config.get('ai_engine_type', 'gemini').strip().lower()
        if _cur_id not in AI_ENGINE_LABELS:
            _cur_id = 'gemini'
        def _selected_engine_id():
            return _label2id.get(engine_var.get(), 'gemini')

        def _key_for_engine(eng):
            # 엔진별 고유 키만 반환 (공유 ai_api_key 폴백 제거 — 엔진 전환 시 타 엔진 키 노출 방지)
            return self.config.get(f'{eng}_api_key', '').strip()

        tk.Label(ai_grid, text="AI 엔진 종류", font=FS, bg=BG, fg=SUBTEXT).grid(row=0, column=0, sticky='w', pady=6, padx=(0,8))
        engine_var = tk.StringVar(value=AI_ENGINE_LABELS[_cur_id])
        cmb_engine = ttk.Combobox(ai_grid, textvariable=engine_var, state="readonly", font=FS)
        cmb_engine['values'] = tuple(AI_ENGINE_LABELS[i] for i in AI_ENGINE_ORDER)
        cmb_engine.grid(row=0, column=1, sticky='ew', pady=6)

        # 엔진 선택 시 무료/유료 배지 + 한 줄 설명 (row 1)
        _ENG_INFO = {
            'gemini': ('무료·추천', GREEN,  '일일 한도만 있고 월 제한 없음. 처음이라면 추천.'),
            'claude': ('유료',      YELLOW, '문장력·감성 표현이 가장 자연스럽습니다.'),
            'openai': ('유료',      YELLOW, '안정적인 범용 성능.'),
            'groq':   ('무료',      GREEN,  '응답 속도가 가장 빠릅니다.'),
        }
        eng_info = tk.Frame(ai_grid, bg=BG)
        eng_info.grid(row=1, column=1, sticky='ew', pady=(0,2))
        eng_badge = tk.Label(eng_info, font=FS, bg=BG)
        eng_badge.pack(side='left')
        eng_desc = tk.Label(eng_info, font=FS, bg=BG, fg=SUBTEXT, justify='left', anchor='w')
        eng_desc.pack(side='left', fill='x', expand=True, padx=(6,0))
        _wrap_to_width(eng_desc, pad=8)
        def _render_eng_info():
            b, c, d = _ENG_INFO.get(_selected_engine_id(), ('', SUBTEXT, ''))
            eng_badge.config(text=f"● {b}", fg=c)
            eng_desc.config(text=d)

        # API Key 입력 폼 (row 2)
        tk.Label(ai_grid, text="API Key", font=FS, bg=BG, fg=SUBTEXT).grid(row=2, column=0, sticky='w', pady=3, padx=(0,8))
        default_key = _key_for_engine(_cur_id)
        ai_key_var = tk.StringVar(value=default_key)
        ai_entry = tk.Entry(ai_grid, textvariable=ai_key_var, font=FS, show='*', relief='flat', bg="#F7F7F9", highlightbackground=BORDER, highlightthickness=1)
        ai_entry.grid(row=2, column=1, sticky='ew', ipady=3)

        def _on_engine_change(event=None):
            ai_key_var.set(_key_for_engine(_selected_engine_id()))
            _render_eng_info()
        cmb_engine.bind('<<ComboboxSelected>>', _on_engine_change)

        def _toggle_ai_vis():
            ai_entry.config(show='' if ai_entry.cget('show') == '*' else '*')
        tk.Button(ai_grid, text="👁", font=FS, bg=BG, fg=GRAY, relief='flat', command=_toggle_ai_vis, cursor='hand2').grid(row=2, column=2, padx=4)

        # 메시지 문체 — '내 말투 자동' 또는 4개 프리셋 (row 3)
        _style_label2id = {ai_style.STYLE_LABELS[i]: i for i in ai_style.STYLE_ORDER}
        _cur_style = self.config.get('ai_style_mode', ai_style.STYLE_AUTO).strip()
        if _cur_style not in ai_style.STYLE_LABELS:
            _cur_style = ai_style.STYLE_AUTO
        tk.Label(ai_grid, text="메시지 문체", font=FS, bg=BG, fg=SUBTEXT).grid(row=3, column=0, sticky='nw', pady=6, padx=(0,8))
        style_var = tk.StringVar(value=ai_style.STYLE_LABELS[_cur_style])
        cmb_style = ttk.Combobox(ai_grid, textvariable=style_var, state="readonly", font=FS)
        cmb_style['values'] = tuple(ai_style.STYLE_LABELS[i] for i in ai_style.STYLE_ORDER)
        cmb_style.grid(row=3, column=1, sticky='ew', pady=6)

        def _selected_style_id():
            return _style_label2id.get(style_var.get(), ai_style.STYLE_AUTO)

        # 문체 미리보기 — 프리셋은 지침+예시, auto는 본인 노트 분석 요약+예시 (row 4)
        style_prev = tk.Label(ai_grid, font=("맑은 고딕", 8), bg="#F7F7F9", fg=SUBTEXT,
                              justify='left', anchor='w', wraplength=340, padx=8, pady=6)
        style_prev.grid(row=4, column=1, sticky='ew', pady=(0,2))
        _wrap_to_width(style_prev)

        def _set_prev(text):
            try:
                if style_prev.winfo_exists():
                    style_prev.config(text=text)
            except Exception:
                pass

        def _render_style_preview():
            mode = _selected_style_id()
            if mode != ai_style.STYLE_AUTO:
                p = ai_style.STYLE_PRESETS.get(mode, {})
                ex = (p.get('examples') or [''])[0]
                _set_prev(f"{p.get('guidance','')}\n\n[생성 예시] {ex}")
                return
            # auto — 본인 노트 백그라운드 분석 (네트워크)
            _set_prev("내 노트 분석 중…")
            instructor = self.config.get('instructor_id', '').strip()
            def _work():
                notes = self.ai._fetch_instructor_notes(instructor)
                prof  = ai_style.analyze_notes(notes)
                summ  = ai_style.profile_summary(prof)
                exs   = ai_style.pick_examples(notes, k=1)
                ex    = exs[0] if exs else ''
                txt   = summ + (f"\n\n[생성 예시] {ex}" if ex else "")
                self.root.after(0, lambda: _set_prev(txt))
            threading.Thread(target=_work, daemon=True).start()

        cmb_style.bind('<<ComboboxSelected>>', lambda e: _render_style_preview())

        # 강사 개별 지침 — 나만의 맞춤 프롬프트 (row 5~6). '프롬프트로 동작'을 직관화:
        # 라벨에 ✏️·"프롬프트" 노출 + 빈칸 placeholder 예시 + 동작 설명 힌트.
        tk.Label(ai_grid, text="✏️ 나만의\n프롬프트", font=FS, bg=BG, fg=INDIGO, justify='left'
                 ).grid(row=5, column=0, sticky='nw', pady=(8,0), padx=(0,8))
        custom_txt = tk.Text(ai_grid, height=3, font=FS, relief='flat', wrap='word',
                             bg="#F7F7F9", highlightbackground=BORDER, highlightthickness=1)
        custom_txt.grid(row=5, column=1, sticky='ew', pady=(8,0))

        # placeholder — 빈 입력 시 회색 예시문(클릭하면 사라짐). 저장 시 placeholder는 빈값 처리.
        _PH_CUSTOM = "예) 항상 존댓말로 써줘 · 끝에 응원 한마디 추가해줘 · 줄임말은 쓰지 마"
        def _ph_show():
            custom_txt.delete('1.0', 'end'); custom_txt.insert('1.0', _PH_CUSTOM)
            custom_txt.config(fg=GRAY); custom_txt._ph_on = True
        def _ph_in(_e=None):
            if getattr(custom_txt, '_ph_on', False):
                custom_txt.delete('1.0', 'end'); custom_txt.config(fg=TEXT); custom_txt._ph_on = False
        def _ph_out(_e=None):
            if not custom_txt.get('1.0', 'end-1c').strip():
                _ph_show()
        custom_txt.bind('<FocusIn>', _ph_in)
        custom_txt.bind('<FocusOut>', _ph_out)
        _saved_cp = (self.config.get('ai_custom_prompt') or '').strip()
        if _saved_cp:
            custom_txt.insert('1.0', _saved_cp); custom_txt.config(fg=TEXT); custom_txt._ph_on = False
        else:
            _ph_show()

        custom_hint = tk.Label(ai_grid, text="💡 여기 적은 문장이 AI에게 그대로 전달돼 매 생성마다 반영됩니다. 이 강사 계정에만 적용돼요.",
                 font=("맑은 고딕", 8), bg=BG, fg=GRAY, justify='left', anchor='w')
        custom_hint.grid(row=6, column=1, sticky='ew', pady=(2,0))
        _wrap_to_width(custom_hint, pad=8)

        _render_eng_info()
        _render_style_preview()

        # ── 하단 고정 컨트롤 (저장) — footer 에 배치 (탭 무관 항상 노출) ──
        def _save_all():
            try:
                self.config['send_speed'] = speed_var.get()  # 프리셋(고속/보통/안정) — wait_time 대체
                self.config.pop('wait_time', None)           # 구 숫자 설정 제거
                self.config['room_prefix'] = prefix_var.get().strip()

                self.config['firebase_url'] = fb_url_var.get().strip()
                self.config['firebase_path'] = fb_path_var.get().strip()

                # 엔진 다중화 세팅 주입 — 키는 엔진별 슬롯에만 저장 (공유 ai_api_key 미사용)
                chosen_engine = _selected_engine_id()
                chosen_key = ai_key_var.get().strip()

                self.config['ai_engine_type'] = chosen_engine
                self.config[f'{chosen_engine}_api_key'] = chosen_key

                self.config['ai_style_mode'] = _selected_style_id()
                # placeholder 표시 상태면 빈값으로 저장(예시문이 지침으로 새는 것 방지)
                self.config['ai_custom_prompt'] = ('' if getattr(custom_txt, '_ph_on', False)
                                                   else custom_txt.get('1.0', 'end').strip())
                try:
                    self.ai.invalidate_style_cache()  # 문체/강사 변경 즉시 반영
                except Exception:
                    pass

                save_config(self.config)

                self._populate_student_list(self.activeGroup)
                self._refresh_student_view()
                
                messagebox.showinfo("완료", "모든 설정이 안전하게 로컬에 저장되었습니다.", parent=win)
                win.destroy()
            except Exception as err:
                messagebox.showerror("오류", f"설정 저장 실패:\n{err}", parent=win)

        tk.Button(footer, text="💾 설정 저장하기", font=FT, bg=INDIGO, fg='white', relief='flat', padx=20, pady=8, command=_save_all, cursor='hand2').pack(side='right', padx=(0,16), pady=12)
        tk.Button(footer, text="취소", font=FS, bg="#ECECEF", fg=TEXT, relief='flat', padx=16, pady=8, command=win.destroy, cursor='hand2').pack(side='right', pady=12)

        _show_tab('ai')   # 기본 탭: AI 생성(전면)


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

        # 동명이인 가드 — 같은 표시이름은 같은 카톡방으로 합쳐져 오발송 위험 → 제외+안내
        sel, dups = self._dedup_same_name(sel)
        if dups:
            messagebox.showwarning("동명이인 제외",
                "동명이인이 있어 다음 학생은 자동 전송에서 제외했습니다:\n"
                f"{', '.join(dups)}\n\n"
                "카톡방 이름을 구분(예: 이름+번호)한 뒤 개별 전송하세요.")
            if not sel:
                return

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
        win.geometry("400x600")
        win.minsize(380, 460)
        win.resizable(True, True)
        win.configure(bg=BG)
        win.grab_set()
        result = {'sel': None}
        vars_ = []

        # ── 상단 안내 + 전체 선택/해제 ──
        tk.Label(win, text=f"전송 대상 {len(ready)}명 — 제외할 학생은 체크 해제하세요",
                 font=FT, bg=BG, fg=TEXT, wraplength=350, justify='left'
                 ).pack(side='top', pady=(14, 6), padx=16, anchor='w')

        top = tk.Frame(win, bg=BG); top.pack(side='top', fill='x', padx=16)
        def _set_all(val):
            for v, _ in vars_: v.set(val)
        tk.Button(top, text="전체 선택", font=FS, bg=PANEL, fg=INDIGO, relief='flat',
                  cursor='hand2', command=lambda: _set_all(True)).pack(side='left')
        tk.Button(top, text="전체 해제", font=FS, bg=PANEL, fg=GRAY, relief='flat',
                  cursor='hand2', command=lambda: _set_all(False)).pack(side='left', padx=6)

        # ── 하단 고정 (버튼이 항상 보이도록 side='bottom' 먼저 배치) ──
        foot = tk.Frame(win, bg=BG); foot.pack(side='bottom', fill='x', padx=16, pady=(6, 14))
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

        tk.Label(win, text="[전송 시작]을 누르면 카카오톡 창을 자동으로 찾아 전송합니다.",
                 font=FS, bg=BG, fg=SUBTEXT, wraplength=350, justify='left'
                 ).pack(side='bottom', padx=16, pady=(4, 8), anchor='w')
        if skipped:
            tk.Label(win, text=f"미입력 제외 {len(skipped)}명: " + ", ".join(skipped),
                     font=FS, bg=BG, fg=GRAY, wraplength=350, justify='left'
                     ).pack(side='bottom', padx=16, pady=(0, 4), anchor='w')

        # ── 중앙 스크롤 학생 리스트 (남은 공간 채움) ──
        body = tk.Frame(win, bg=BG); body.pack(side='top', fill='both', expand=True, padx=16, pady=8)
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

        win.wait_window()
        return result['sel']

    @staticmethod
    def _dedup_same_name(items):
        """동명이인 오발송 가드(B4) — 표시이름이 겹치는 학생은 전송에서 제외하고 명단 반환.

        카톡방 매칭이 '오직 {이름}' 검색이라 동명이인은 같은 방으로 합쳐져
        타 학부모에게 내용이 갈 수 있음. 겹치는 이름 전원 제외 → 수동 전송 안내.
        items: [{'name': 표시이름, ...}] → (safe_items, dup_names)"""
        from collections import Counter
        cnt = Counter(it.get('name', '') for it in items)
        dups = sorted({n for n, c in cnt.items() if n and c > 1})
        if not dups:
            return items, []
        safe = [it for it in items if it.get('name') not in dups]
        return safe, dups

    # 전송 속도 프리셋 → 단계 대기(초). 검증 게이트가 실패를 흡수하므로
    # 프리셋은 "1차 시도 마진"만 결정 — 안정은 저사양/카톡 응답 지연 환경용.
    _SEND_SPEED_WAITS = {'fast': 0.3, 'normal': 0.5, 'stable': 1.0}
    _SMART_MIN, _SMART_MAX = 0.25, 1.2

    def _send_wait(self):
        """현재 전송 속도 — 스마트면 학습값, 수동 프리셋이면 고정값. 미설정은 스마트."""
        mode = self.config.get('send_speed', 'smart')
        if mode == 'smart':
            return self._smart_wait
        return self._SEND_SPEED_WAITS.get(mode, 0.5)

    def _smart_adjust(self, t_open, retried):
        """스마트 모드 적응(AIMD + EMA) — 게이트 실측이 곧 시스템 응답성 신호.

        · 1차 실패(재시도 발생) → wait ×1.6 즉시 감속 (승법 증가)
        · 빠른 통과(t_open≤0.2s) 연속 3회 → wait -0.1s 가속 (가산 감소)
        · 지연 EMA 가 높으면(>0.6s) 선제 감속 — 추세 반영
        범위 [0.25, 1.2]s. 검증 게이트가 바닥을 받치므로 공격적이어도 오발송 불가."""
        if self.config.get('send_speed', 'smart') != 'smart':
            return
        self._open_ema = t_open if self._open_ema is None else 0.6 * self._open_ema + 0.4 * t_open
        if retried:
            self._smart_wait = min(self._SMART_MAX, self._smart_wait * 1.6)
            self._smart_fast_streak = 0
        elif self._open_ema > 0.8:
            self._smart_wait = min(self._SMART_MAX, self._smart_wait + 0.1)
            self._smart_fast_streak = 0
        elif t_open <= 0.2:
            self._smart_fast_streak += 1
            if self._smart_fast_streak >= 2:
                self._smart_wait = max(self._SMART_MIN, self._smart_wait - 0.15)
                self._smart_fast_streak = 0
        else:
            self._smart_fast_streak = 0
        send_debug(f"smart wait={self._smart_wait:.2f} t_open={t_open:.2f} "
                   f"retried={retried} ema={self._open_ema:.2f}")

    def _smart_persist(self):
        """학습된 wait 영속 — 다음 실행이 이어받음 (스마트 모드일 때만)."""
        if self.config.get('send_speed', 'smart') == 'smart':
            self.config['smart_wait'] = round(self._smart_wait, 2)
            try:
                save_config(self.config)
            except Exception:
                pass

    def _cleanup_rooms(self, lingering, status_cb=None):
        """전체 전송 완료 후 자동화로 열어둔 잔류 톡방 일괄 닫기 (이미지 방·오류 중단 방).

        2초 유예: 마지막 이미지 업로드 여유 — 그래도 진행 중이면 카톡이 닫기를
        보류하므로 그 창만 남고 업로드는 보호됨(자동 확인 안 함). 비치명 — 실패 최악도 현행(누적).
        status_cb: 메인 스레드에서 실행할 상태 라벨 갱신 콜백(text 1개 인자). 데일리·발송 탭 공용."""
        if not lingering:
            return
        if status_cb:
            self.root.after(0, lambda: status_cb("🧹 열린 톡방 정리 중..."))
        time.sleep(2.0)
        try:
            closed = close_rooms(lingering)
        except Exception as e:
            send_debug(f"close_rooms 오류: {e}")
            return
        if status_cb:
            left = len(set(lingering)) - closed
            msg = f"🧹 톡방 {closed}개 정리" + (f" · {left}개는 업로드 중이라 유지" if left > 0 else "")
            self.root.after(0, lambda t=msg: status_cb(t))

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

    def _kakao_send_one(self, m, wait, warm=0.0):
        """단일 톡방 전송: 검색→이동→**방 열림 검증**→본문/이미지 송신.
        데일리 리포트·메시지 발송 탭 공용 키 시퀀스.
        m: {room, msg, image(선택), image_first(선택)}.

        v2.2.3 검증 게이트 — 간헐 연쇄 오류(단일 방 연속 전송·미전송) 차단:
        · 클립보드 반영 검증(copy_text_verified) — 이전 내용 붙여넣기 레이스 차단
        · 방 열림 검증(room_opened: 전면 창 제목=방 이름) — 미확인 시 본문 미발사,
          1회 재시도(대기 증가) 후에도 실패면 예외 → 호출측이 해당 학생만 실패 처리
        이미지는 붙여넣기 미리보기 팝업 고려해 img_wait=max(wait,1.0) 사용."""
        img_wait = max(wait, 1.0)
        room = m['room']

        def _open_room(key_gap, search_load, post_enter):
            """검색창 초기화 → 방 이름 검색 → Enter → 방 열림 검증(폴링이 즉시 통과 감지).

            key_gap: 키 입력 간 간격, search_load: 붙여넣기 후 검색 결과 로딩 대기,
            post_enter: Enter 후 방 창 생성까지 최소 대기 — 이후는 room_opened 폴링이 흡수."""
            if not copy_text_verified(room):
                return False
            pyautogui.hotkey(_MOD, 'f'); time.sleep(key_gap)
            pyautogui.press('esc');      time.sleep(key_gap)
            pyautogui.hotkey(_MOD, 'f'); time.sleep(key_gap)
            pyautogui.hotkey(_MOD, 'v'); time.sleep(search_load)
            pyautogui.press('enter')
            _t0 = time.time()
            time.sleep(post_enter)
            ok = room_opened(room)
            self._last_t_open = time.time() - _t0   # 스마트 모드 적응용 실측
            return ok

        send_debug(f"send start room={room!r} wait={wait:.2f} warm={warm}")
        time.sleep(warm)
        self._last_t_open = None
        retried = False
        # 빠른 1차 시도 — 검증 게이트가 실패를 즉시 감지하므로 고정 마진 최소화.
        # 실패 시에만 느린 프로파일로 재시도 (시스템 부하·카톡 응답 지연 흡수).
        if not _open_room(max(0.15, wait * 0.5) + warm, max(0.3, wait), 0.1):
            send_debug(f"1차 열기 실패 → 느린 프로파일 재시도 room={room!r}")
            retried = True
            pyautogui.press('esc'); time.sleep(0.3)
            focus_kakao(0.4)
            if not _open_room(0.3, max(wait, 1.0), 0.5):
                pyautogui.press('esc')
                self._last_open_stats = (1.5, True)   # 완전 실패 — 최대 지연으로 학습
                raise RuntimeError(f"채팅방 열기 실패(검색 미일치/응답 지연): {room}")
        self._last_open_stats = (self._last_t_open if self._last_t_open is not None else 1.5, retried)
        send_debug(f"방 열림 확인 → 본문 전송 room={room!r}")

        def _send_text():
            if not m.get('msg'):
                return
            if not copy_text_verified(m['msg']):
                raise RuntimeError(f"본문 클립보드 복사 실패: {room}")
            pyautogui.hotkey(_MOD, 'v'); time.sleep(0.15)
            pyautogui.press('enter');    time.sleep(0.2)

        def _in_room():
            """전면이 이 방인가 — 팝업이 뜨면 전면 제목이 방을 벗어남(상태 센서)."""
            return room_opened(room, tries=1, interval=0)

        def _send_image():
            img = m.get('image')
            if not img:
                return
            if not copy_image_to_clipboard(img):
                return
            if not WIN_VERIFY:
                # 레거시 경로(비 Windows): 고정 대기
                pyautogui.hotkey(_MOD, 'v'); time.sleep(img_wait)
                pyautogui.press('enter');    time.sleep(img_wait)
                return
            # 이미지 붙여넣기 → 확인 팝업 흐름 (간헐적으로 로딩이 김 — 이벤트 대기로 흡수)
            pyautogui.hotkey(_MOD, 'v')
            deadline = time.time() + 8.0          # ① 팝업 등장 대기 (대용량 이미지 대비)
            while time.time() < deadline and _in_room():
                time.sleep(0.15)
            if _in_room():
                # 팝업이 끝내 안 뜸 = 붙여넣기 미동작 — Enter 미발사(스트레이 입력 방지)
                send_debug(f"이미지 팝업 미표시 room={room!r} fg={foreground_title()!r}")
                raise RuntimeError(f"이미지 팝업 미표시(붙여넣기 실패 추정): {room}")
            send_debug(f"이미지 팝업 확인 → 전송 room={room!r}")
            pyautogui.press('enter')              # 팝업 확인 = 전송
            deadline = time.time() + 8.0          # ② 팝업 닫힘(전송 시작) 검증
            while time.time() < deadline and not _in_room():
                time.sleep(0.15)
            if not _in_room():
                send_debug(f"이미지 팝업 미종료 room={room!r} fg={foreground_title()!r}")
                pyautogui.press('esc')            # 팝업 잔존 → 취소 후 실패 처리
                raise RuntimeError(f"이미지 전송 확인 실패(팝업 미종료): {room}")

        if m.get('image_first'):
            _send_image(); _send_text()
        else:
            _send_text(); _send_image()
        # 방 정리 정책:
        # · 이미지를 보낸 방은 닫지 않는다 — 업로드가 백그라운드 진행 중이라 esc 시
        #   "전송 중인 파일" 확인 팝업이 뜨고(확인 시 업로드 취소 위험) 흐름이 막힘.
        #   방을 열어두면 업로드는 자체 완료되고, 다음 학생은 메인 창 검색으로 진행.
        # · 텍스트만 보낸 방은 esc로 닫되, 전면이 방을 벗어날 때까지 반복(최대 4회).
        if m.get('image'):
            send_debug(f"이미지 업로드 진행 — 방 유지(미닫음) room={room!r}")
        elif WIN_VERIFY:
            for _ in range(4):
                pyautogui.press('esc'); time.sleep(0.2)
                if not _in_room():
                    break
            else:
                send_debug(f"방 탈출 실패(esc 4회) room={room!r}")
        else:
            pyautogui.press('esc')

    def _do_send(self, msgs):
        cancel = self._send_cancel
        wait   = self._send_wait()
        total  = len(msgs)
        # v2.2.3: 카톡 창 자동 포커스 — 기존 "3초 내 직접 클릭" 의존이 간헐 오류 최다 원인.
        # 취소 여유 1초 후 자동 포커스, 실패 시 키 입력 없이 안전 중단.
        for _ in range(10):
            if cancel.is_set(): break
            time.sleep(0.1)
        if not cancel.is_set() and not focus_kakao():
            def _no_kakao():
                self._set_send_btn_cancel(False)
                self.send_status.config(text="❌ 카카오톡 창을 찾지 못해 중단")
                messagebox.showerror("카카오톡 창 없음",
                    "카카오톡 창을 찾을 수 없습니다.\n"
                    "카카오톡 실행·로그인 상태를 확인한 뒤 다시 전송하세요.\n"
                    "(입력 데이터는 유지됩니다. 전송 코멘트는 이미 기록되어 안전합니다)")
            self.root.after(0, _no_kakao)
            return
        sent = 0
        failed = []   # v2.2.3: 카톡 전송 예외 학생 집계 — 기존엔 실패도 sent로 합산돼 유실이 가려짐
        focus_lost = False
        lingering = []   # 정리 대상 잔류 방 — 이미지 방(의도적 미닫음) + 오류 중단 방
        for i, m in enumerate(msgs):
            if cancel.is_set(): break
            self.root.after(0, lambda t=f"전송 중... ({i+1}/{total})  {m['name']}":
                            self.send_status.config(text=t))
            # 매 학생 전 카톡 메인 창 재포커스 — 전송 중 사용자가 다른 창을 만져도 복구
            if i > 0 and not focus_kakao(0.3):
                focus_lost = True
                break
            # 첫 학생 워밍업 — 카톡 창 포커스/검색 안정화 (첫 전송 오작동 방지)
            warm = 0.6 if i == 0 else 0.0
            wait = self._send_wait()   # 스마트 모드: 직전 학생 측정으로 갱신된 값
            try:
                self._kakao_send_one(m, wait, warm)
                sent += 1
                if m.get('image'):
                    lingering.append(m['room'])   # 이미지 방은 미닫음 — 종료 후 일괄 정리
            except Exception as e:
                print(f"오류 [{m['name']}]: {e}")
                send_debug(f"학생 실패 [{m['name']}]: {e}")
                failed.append(m.get('name', '?'))
                if m.get('room'):
                    lingering.append(m['room'])   # 오류 중단 방도 열려 있을 수 있음
            if self._last_open_stats:
                self._smart_adjust(*self._last_open_stats)
                self._last_open_stats = None
            time.sleep(0.3)  # 학생 간 간격 — 게이트 검증으로 단축(기존 0.8)

        cancelled = cancel.is_set()
        self._smart_persist()   # 스마트 모드 학습값 저장 — 다음 실행 이어받기
        self._cleanup_rooms(lingering, lambda t: self.send_status.config(text=t))
        if focus_lost:
            def _lost():
                self._set_send_btn_cancel(False)
                self.send_status.config(text=f"❌ 카톡 창 소실 — {sent}/{total}명에서 중단")
                messagebox.showerror("전송 중단",
                    f"{sent}명 전송 후 카카오톡 창을 잃어 중단했습니다.\n"
                    "카카오톡 확인 후 다시 전송하세요. (입력 데이터 유지)")
            self.root.after(0, _lost)
            return
        def _on_done():
            self._set_send_btn_cancel(False)
            fail_line = f"\n⚠ 전송 실패 {len(failed)}명: {', '.join(failed)}" if failed else ""
            if cancelled:
                self.send_status.config(text=f"⏹ {sent}/{total}명 전송 후 취소 — 나머지 유지")
                messagebox.showinfo("전송 취소",
                    f"{sent}명 전송 후 취소했습니다.\n"
                    "전송되지 않은 학생 데이터는 유지됩니다." + fail_line)
            elif failed:
                self.send_status.config(text=f"⚠ 전송 {sent}/{total}명 — 실패 {len(failed)}명")
                messagebox.showwarning("일부 실패",
                    f"{sent}명 전송 완료, {len(failed)}명 실패:\n{', '.join(failed)}\n\n"
                    "최종 코멘트는 history에 기록되어 있습니다.\n"
                    "실패 학생은 카톡 상태 확인 후 개별 재전송하세요.\n"
                    "(로컬 입력 데이터는 초기화하지 않고 유지합니다)")
            else:
                self.send_status.config(text=f"✅ 전송 완료 — {sent}명")
                self._reset_after_send()
                messagebox.showinfo("완료", f"{sent}명 전송 완료!")
        self.root.after(0, _on_done)

    def _push_history(self, items):
        """전송 확정 시점(카톡 루프 이전)에 ① 최종 note 를 history 에 누적, ② 원본 입력 note 소거.

        · 호출 시점 = 전송 **확정 직후·카톡 루프 이전** (전송 성패와 무관, 메시지 확정 기준)
          → 카톡 전송 중 abort/크래시가 나도 이력 보존 + 원본 draft 정리됨.
        · ① history/{nameKey}/{YYYY-MM-DD} = {note, instructor} — 메시지에 들어간 최종 note (학생 grain, todayKey).
        · ② input/{nameKey}/__note__ = null — 전송된 학생의 원본 입력 특이사항 소거(draft consume).
          → 특이사항이 obs(날짜별)처럼 "당일 소비"로 동작, 다음 가져오기 fresh(옛 메모 잔류 방지).
          최종본은 ①history 에 보존됨.
        · 각각 단일 원자적 multi-path PATCH (1회 HTTP). 베스트에포트(실패해도 전송 진행).
        """
        url  = self.config.get('firebase_url', '')
        path = self.config.get('firebase_path', '')
        if not (url and path):
            return
        day   = today_key()
        instr = self.config.get('instructor_id', '')
        # v2.2.3: history 기록과 note 소거를 루트 단일 multi-path PATCH로 통합 — 원자성 확보.
        # 기존: 별개 PATCH 2회 → history 실패 후 소거 성공 시 최종 코멘트가 양쪽 모두에서 소실되는 유실 경로.
        # 통합 후: 실패하면 둘 다 미적용 → note가 input/에 남아 재시도 가능.
        updates = {}   # 루트 기준: history/{nk}/{date} → {note,instructor}, input/{nk}/__note__ → null
        for it in items:
            nk   = it.get('nameKey')
            if not nk:
                continue
            note = (it.get('note') or '').strip()
            if note:
                updates[f"history/{nk}/{day}"] = {"note": note, "instructor": instr}
            updates[f"input/{nk}/__note__"] = None
        if updates:
            try:
                firebase_patch(self.config, "", updates)
            except Exception as e:
                print(f"history 기록/note 소거 실패: {e}")
                self.root.after(0, lambda e=e: messagebox.showwarning(
                    "기록 실패",
                    "전송 코멘트의 서버 기록(history)에 실패했습니다.\n"
                    "특이사항 원본은 보존되어 있으니 네트워크 확인 후 재전송하면 다시 기록됩니다.\n\n"
                    f"오류: {e}"))

    def _reset_after_send(self):
        """전송 완료 후 로컬 전면 초기화 (진도/과제 포함).
        DB 쓰기 없음 — 전송 이력은 _send() 가 전송 확정 시점에 history/ 에 이미 기록함."""
        self.student_data.clear()
        self.note_data.clear()
        self.progress_data.clear()
        self.force_data.clear()
        self.exclude_prog.clear()
        save_daily_cache(self.progress_data, {}, {}, {})
        self.root.after(0, self._refresh_after_reset)

    def _refresh_after_reset(self):
        if self.cur_name:
            self._render_student(self.activeGroup, self.cur_cls, self.cur_name)
        self._refresh_send_btn()
        self._refresh_statusbar()
