"""
agent_gui.py — 강사 본인 PC 에이전트 GUI (tkinter, 무추가 의존성).

구성:
  · 설정 폼      — 캠퍼스·이름·엔진·개인키·방접두사 입력 → DPAPI 저장 + 자동시작 등록 (1회)
  · 상태창       — 🟢 작동 중 / dry·real / 시작·중지 / 마지막 활동 / 설정 열기
  · 전송중 오버레이 — topmost "전송 중 N/M · 만지지 마세요"(비활성 창, 카톡 포커스 미탈취)

워커는 agent_worker(생성+전송) 재사용. 키·카톡은 이 PC 로컬. JSON 편집 불요.
실행:  python agent_gui.py
"""
import queue
import copy
import hashlib
import json
from ai_model_config import DEFAULTS, OPTIONS, resolve, from_config
import sys
import threading
import time
import tkinter as tk
from tkinter import ttk, messagebox

import agent_worker as W
from constants import AI_ENGINE_ORDER, AI_ENGINE_LABELS
from agent_version import AGENT_VERSION

try:
    import pystray
    from PIL import Image, ImageDraw
    _HAS_TRAY = True
except Exception:
    _HAS_TRAY = False   # pystray 미설치/실패 → 트레이 비활성(일반 창으로 동작)

INDIGO, INK, GREEN, RED, SUB = "#4F46E5", "#15171F", "#16A34A", "#DC2626", "#94A3B8"
# 캠퍼스 표시명 → id (app.py / 웹 게이트와 동일 정본). 캠퍼스 추가 시 여기만 갱신.
CAMPUS = {"동수원": "dongsuwon"}
_Q = queue.Queue()


def _progress(state):
    _Q.put(state)


def _heartbeat_loop(stop, cfg, db, instructor_id, real, interval=15):
    """Keep agent presence fresh even while generation or sending blocks the worker."""
    failed = False
    while not stop.is_set():
        try:
            ok = W.write_heartbeat(cfg, db, instructor_id, token=None, real=real)
        except Exception:
            ok = False
        if ok:
            failed = False
        elif not failed:
            _Q.put({"_log": "상태 신호 전송 실패 — 웹에서 에이전트를 감지하지 못할 수 있습니다"})
            failed = True
        if stop.wait(interval):
            break


class AgentGUI:
    def __init__(self):
        self.cfg = None
        self.running = False
        self.real = "--dry" not in sys.argv   # 운영=실 발송 기본. 테스트만 --dry로 dry
        self.overlay = None
        self.last = "—"
        self.root = tk.Tk()
        self.root.title(f"DRW AI Agent v{AGENT_VERSION}")
        self.root.configure(bg=INK)
        self.root.geometry("360x300")
        self.root.resizable(False, False)
        try:
            self.cfg = W._load_cfg()
        except SystemExit:
            self.cfg = None
        if self.cfg:
            self._build_status()
        else:
            self._build_setup()
        self.root.after(150, self._drain)
        # 시스템 트레이 — 창 닫기/최소화 시 트레이로 숨김(워커는 백그라운드 계속)
        self.tray = None
        if _HAS_TRAY:
            try:   # 트레이 실패해도 앱은 일반 창으로 구동(가드)
                self._init_tray()
                self.root.protocol("WM_DELETE_WINDOW", self._hide_to_tray)
                self.root.bind("<Unmap>", self._on_unmap)
            except Exception:
                self.tray = None

    # ── 시스템 트레이 ─────────────────────────────────────────────────
    def _tray_image(self):
        img = Image.new("RGBA", (64, 64), (0, 0, 0, 0))
        d = ImageDraw.Draw(img)
        d.rounded_rectangle([6, 6, 58, 58], radius=14, fill=(79, 70, 229, 255))
        d.ellipse([25, 25, 39, 39], fill=(255, 255, 255, 255))
        return img

    def _init_tray(self):
        menu = pystray.Menu(
            pystray.MenuItem("열기", lambda i=None: self._show_window(), default=True),
            pystray.MenuItem("종료", lambda i=None: self._quit()),
        )
        self.tray = pystray.Icon("drw_agent", self._tray_image(),
                                 f"DRW AI Agent v{AGENT_VERSION}", menu)
        threading.Thread(target=self.tray.run, daemon=True).start()

    def _hide_to_tray(self):
        self.root.withdraw()   # 트레이 아이콘은 이미 떠 있음

    def _on_unmap(self, e):
        # 최소화(iconic) 시 트레이로 숨김. withdraw는 state=withdrawn이라 재귀 안 됨.
        if _HAS_TRAY and self.root.state() == "iconic":
            self.root.withdraw()

    def _show_window(self):
        self.root.after(0, lambda: (self.root.deiconify(), self.root.state("normal"),
                                    self.root.lift(), self.root.focus_force()))

    # ── 설정 폼 ──────────────────────────────────────────────────────
    def _build_setup(self, existing=None):
        for w in self.root.winfo_children():
            w.destroy()
        self._setup_epoch = getattr(self, "_setup_epoch", 0) + 1
        self.root.geometry("440x660")
        self.root.resizable(True, True)
        self.root.minsize(420, 620)
        e = existing or {}
        self._setup_original = copy.deepcopy(e)
        self._model_drafts = {eng: from_config(e, eng) for eng in AI_ENGINE_ORDER}
        self._eng_keys = {eng: e.get(f"{eng}_api_key", "") for eng in AI_ENGINE_ORDER}
        self._verified = {}
        self._last_good = copy.deepcopy(e.get("ai_models_last_good", {}))
        self.vars = {}
        tk.Label(self.root, text=f"DRW AI Agent 설정 · v{AGENT_VERSION}", bg=INK, fg="#fff",
                 font=("맑은 고딕", 14, "bold")).pack(pady=(14, 8))
        footer = tk.Frame(self.root, bg=INK)
        footer.pack(side="bottom", fill="x", padx=18, pady=12)
        self.save_msg = tk.StringVar(value="탭을 바꿔도 입력 내용은 유지됩니다.")
        tk.Label(footer, textvariable=self.save_msg, bg=INK, fg=SUB,
                 wraplength=395, font=("맑은 고딕", 9)).pack(fill="x")
        tk.Button(footer, text="전체 설정 저장하고 적용", command=self._save_setup,
                  bg=INDIGO, fg="#fff", relief="flat", font=("맑은 고딕", 11, "bold"))
        save_button = footer.winfo_children()[-1]
        save_button.pack(fill="x", pady=(6, 0), ipady=5)
        self.settings_tabs = ttk.Notebook(self.root)
        self.settings_tabs.pack(fill="both", expand=True, padx=18)
        self.ai_panel = tk.Frame(self.settings_tabs, bg=INK)
        self.login_panel = tk.Frame(self.settings_tabs, bg=INK)
        self.settings_tabs.add(self.ai_panel, text="  AI 설정  ")
        self.settings_tabs.add(self.login_panel, text="  강사 · 시작 설정  ")

        def row(parent, label, key, value="", show=None):
            tk.Label(parent, text=label, bg=INK, fg="#cbd5e1", font=("맑은 고딕", 10),
                     anchor="w").pack(fill="x", pady=(9, 3))
            var = tk.StringVar(value=value)
            tk.Entry(parent, textvariable=var, show=show, font=("맑은 고딕", 11)).pack(fill="x", ipady=3)
            self.vars[key] = var
            return var

        ai = self._scroll_settings_tab(self.ai_panel)
        tk.Label(ai, text="AI 엔진", bg=INK, fg=SUB).pack(anchor="w", pady=(8, 3))
        eng = e.get("ai_engine_type", "gemini")
        if eng not in AI_ENGINE_ORDER:
            eng = "gemini"
        self._key_eng = eng
        self.eng_var = tk.StringVar(value=AI_ENGINE_LABELS[eng])
        cb = ttk.Combobox(ai, textvariable=self.eng_var, state="readonly",
                         values=list(AI_ENGINE_LABELS.values()), font=("맑은 고딕", 11))
        cb.pack(fill="x")
        cb.bind("<<ComboboxSelected>>", self._on_eng_change)
        row(ai, "개인 API 키", "_api_key", self._eng_keys[eng], "•")
        row(ai, "모델 ID", "_model", self._model_drafts[eng]["model"])
        tk.Label(ai, text="사고 옵션 (omit = 서버 기본값)", bg=INK, fg=SUB).pack(anchor="w", pady=(9, 3))
        self.thinking_var = tk.StringVar(value=self._model_drafts[eng]["thinking_level"])
        self.thinking_box = ttk.Combobox(ai, textvariable=self.thinking_var, state="readonly",
                                       values=OPTIONS[eng], font=("맑은 고딕", 11))
        self.thinking_box.pack(fill="x")
        tk.Button(ai, text="현재 설정 연결 테스트", command=self._test_key,
                  bg="#334155", fg="#fff", relief="flat").pack(fill="x", pady=(12, 4), ipady=4)
        self.keytest_var = tk.StringVar(value="모델·옵션 변경 후 연결 테스트를 진행하세요.")
        tk.Label(ai, textvariable=self.keytest_var, bg=INK, fg=SUB, wraplength=365,
                 justify="left", font=("맑은 고딕", 9)).pack(fill="x", pady=3)
        buttons = tk.Frame(ai, bg=INK)
        buttons.pack(fill="x", pady=7)
        tk.Button(buttons, text="기본값 불러오기", command=lambda: self._restore_model(False),
                  bg="#334155", fg="#fff", relief="flat").pack(side="left", expand=True, fill="x", padx=(0, 4))
        tk.Button(buttons, text="최근 정상 설정 복원", command=lambda: self._restore_model(True),
                  bg="#334155", fg="#fff", relief="flat").pack(side="left", expand=True, fill="x")
        tk.Label(ai, text="AI 변경은 다음 생성 작업부터 적용됩니다.", bg=INK, fg=SUB,
                 font=("맑은 고딕", 9)).pack(anchor="w", pady=5)
        login = self._scroll_settings_tab(self.login_panel)
        tk.Label(login, text="웹에 등록된 캠퍼스·강사 이름을 입력하세요.", bg=INK, fg=SUB).pack(anchor="w", pady=10)
        tk.Label(login, text="캠퍼스", bg=INK, fg=SUB).pack(anchor="w", pady=(8, 3))
        labels = {cid: name for name, cid in CAMPUS.items()}
        self.campus_var = tk.StringVar(value=labels.get(e.get("campus"), next(iter(CAMPUS))))
        campus_box = ttk.Combobox(login, textvariable=self.campus_var, state="readonly",
                                  values=list(CAMPUS), font=("맑은 고딕", 11))
        campus_box.pack(fill="x")
        tk.Label(login, text="강사", bg=INK, fg=SUB).pack(anchor="w", pady=(9, 3))
        self.vars["instructorId"] = tk.StringVar(value=e.get("instructorId", ""))
        tk.Entry(login, textvariable=self.vars["instructorId"],
                 font=("맑은 고딕", 11)).pack(fill="x", ipady=3)
        self._instructor_names = None
        self.instructor_list_msg = tk.StringVar(value="기존 강사 목록을 불러오는 중…")
        tk.Label(login, textvariable=self.instructor_list_msg, bg=INK, fg=SUB,
                 wraplength=360, font=("맑은 고딕", 9)).pack(anchor="w", pady=(5, 0))
        campus_box.bind("<<ComboboxSelected>>", lambda _e: (self.vars["instructorId"].set(""), self._load_instructors()))
        self._load_instructors()
        self.auto_var = tk.BooleanVar(value=e.get("autostart", True))
        tk.Checkbutton(login, text="Windows 시작 시 자동 실행", variable=self.auto_var,
                       bg=INK, fg="#cbd5e1", selectcolor=INK).pack(anchor="w", pady=18)
        tk.Label(login, text="강사 변경은 에이전트 재시작 후 적용됩니다.", bg=INK,
                 fg=SUB, wraplength=360, font=("맑은 고딕", 9)).pack(anchor="w")
        for v in (self.vars["_model"], self.vars["_api_key"], self.thinking_var):
            v.trace_add("write", lambda *_: self.keytest_var.set("설정 변경됨 — 연결 테스트로 확인하세요."))

    def _scroll_settings_tab(self, panel):
        canvas = tk.Canvas(panel, bg=INK, highlightthickness=0)
        bar = ttk.Scrollbar(panel, orient="vertical", command=canvas.yview)
        canvas.configure(yscrollcommand=bar.set)
        bar.pack(side="right", fill="y")
        canvas.pack(side="left", fill="both", expand=True)
        content = tk.Frame(canvas, bg=INK, padx=12, pady=5)
        item = canvas.create_window((0, 0), window=content, anchor="nw")
        content.bind("<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
        canvas.bind("<Configure>", lambda e: canvas.itemconfigure(item, width=e.width))
        return content

    def _load_instructors(self):
        campus = CAMPUS.get(self.campus_var.get(), "")
        epoch = self._setup_epoch
        self._instructor_names = None
        self.instructor_list_msg.set("기존 강사 목록을 불러오는 중…")
        def worker():
            try:
                names = W.list_existing_instructors(W.DEFAULT_DB, campus)
                error = None
            except Exception as ex:
                names, error = [], str(ex)
            _Q.put({"_instructors": (epoch, campus, names, error)})
        threading.Thread(target=worker, daemon=True).start()

    def _capture_model(self):
        eng = self._key_eng
        self._eng_keys[eng] = self.vars["_api_key"].get().strip()
        self._model_drafts[eng] = {"model": self.vars["_model"].get().strip(),
                                   "thinking_level": self.thinking_var.get()}

    def _model_signature(self, eng):
        # Fingerprint only, never retain an extra plaintext key in test records.
        value = json.dumps([eng, self._eng_keys[eng], self._model_drafts[eng]], sort_keys=True)
        return hashlib.sha256(value.encode()).hexdigest()

    def _test_key(self):
        self._capture_model()
        eng = self._key_eng
        key = self._eng_keys[eng]
        try:
            settings = resolve(eng, self._model_drafts[eng])
        except ValueError as ex:
            self.keytest_var.set(str(ex))
            return
        signature = self._model_signature(eng)
        epoch = self._setup_epoch
        self.keytest_var.set("연결 테스트 중…")
        def run():
            from ai_engine import validate_key
            ok, msg = validate_key(eng, key, model_settings=settings)
            _Q.put({"_model_test": (epoch, eng, signature, ok, msg)})
        threading.Thread(target=run, daemon=True).start()

    def _eng_id(self):
        return next((k for k, v in AI_ENGINE_LABELS.items() if v == self.eng_var.get()), "gemini")

    def _on_eng_change(self, *_):
        self._capture_model()
        self._key_eng = self._eng_id()
        eng = self._key_eng
        self.vars["_api_key"].set(self._eng_keys[eng])
        self.vars["_model"].set(self._model_drafts[eng]["model"])
        self.thinking_box.config(values=OPTIONS[eng])
        self.thinking_var.set(self._model_drafts[eng]["thinking_level"])

    def _restore_model(self, recent):
        eng = self._key_eng
        selected = self._last_good.get(eng) if recent else DEFAULTS[eng]
        if not selected:
            self.keytest_var.set("저장된 정상 설정이 없습니다.")
            return
        self.vars["_model"].set(selected["model"])
        self.thinking_var.set(selected["thinking_level"])

    def _save_setup(self):
        self._capture_model()
        eng = self._key_eng
        old = self._setup_original
        campus = CAMPUS.get(self.campus_var.get(), "")
        name = self.vars["instructorId"].get().strip()
        if not campus or not name:
            self.settings_tabs.select(self.login_panel)
            self.save_msg.set("캠퍼스·이름은 필수입니다.")
            return
        if self._instructor_names is None:
            self.settings_tabs.select(self.login_panel)
            self.save_msg.set("강사 목록을 확인하지 못했습니다. 연결을 확인하고 다시 시도하세요.")
            return
        if name not in self._instructor_names:
            self.settings_tabs.select(self.login_panel)
            self.save_msg.set("등록된 강사 이름과 일치하지 않습니다. 이름을 확인하세요.")
            return
        for item in AI_ENGINE_ORDER:
            changed = (self._model_drafts[item] != from_config(old, item)
                       or self._eng_keys[item] != old.get(f"{item}_api_key", ""))
            if changed or (item == eng and (not old or old.get("ai_engine_type") != eng)):
                if self._verified.get(item) != self._model_signature(item):
                    self.eng_var.set(AI_ENGINE_LABELS[item])
                    self._on_eng_change()
                    self.settings_tabs.select(self.ai_panel)
                    self.save_msg.set("변경한 엔진·키·모델·옵션으로 연결 테스트가 필요합니다.")
                    return
        if not self._eng_keys[eng]:
            self.settings_tabs.select(self.ai_panel)
            self.save_msg.set("선택한 엔진의 API 키가 필요합니다.")
            return
        fields = copy.deepcopy(old)
        fields.update(campus=campus, instructorId=name, dbUrl=W.DEFAULT_DB,
                      ai_engine_type=eng, ai_models=copy.deepcopy(self._model_drafts),
                      autostart=self.auto_var.get())
        good = copy.deepcopy(self._last_good)
        for item in AI_ENGINE_ORDER:
            fields[f"{item}_api_key"] = self._eng_keys[item]
            if self._verified.get(item) == self._model_signature(item):
                good[item] = copy.deepcopy(self._model_drafts[item])
        fields["ai_models_last_good"] = good
        fields.pop("login_password", None)
        try:
            W.write_agent_config(fields)
        except Exception:
            self.save_msg.set("설정 저장 실패 — 기존 설정을 유지합니다.")
            return
        autostart_ok = W.register_autostart() if fields["autostart"] else W.unregister_autostart()
        if self.running:
            # Keep the running worker's identity; replace AI fields atomically.
            updates = {"ai_engine_type": eng, "ai_models": fields["ai_models"],
                       "ai_models_last_good": good}
            updates.update({f"{item}_api_key": fields[f"{item}_api_key"] for item in AI_ENGINE_ORDER})
            self.cfg.update(updates)
        else:
            self.cfg = fields
        self._setup_epoch += 1
        self._build_status()
        msg = "저장 완료. AI 설정은 다음 생성부터, 강사 변경은 재시작 후 적용됩니다."
        if not autostart_ok:
            msg += "\nWindows 자동 시작 설정은 적용하지 못했습니다."
        messagebox.showinfo("설정 저장", msg)

    # ── 상태창 ───────────────────────────────────────────────────────
    def _build_status(self):
        for w in self.root.winfo_children():
            w.destroy()
        self.root.minsize(360, 300)
        self.root.geometry("360x300"); self.root.resizable(False, False)
        tk.Label(self.root, text=f"DRW AI Agent · v{AGENT_VERSION}", bg=INK, fg="#cbd5e1",
                 font=("맑은 고딕", 10)).pack(pady=(16, 2))
        row = tk.Frame(self.root, bg=INK); row.pack(pady=4)
        self.dot = tk.Label(row, text="●", bg=INK, fg=SUB, font=("맑은 고딕", 14)); self.dot.pack(side="left")
        self.state_lbl = tk.Label(row, text="중지됨", bg=INK, fg="#fff",
                                  font=("맑은 고딕", 13, "bold")); self.state_lbl.pack(side="left", padx=6)
        tk.Label(self.root, text=f"{self.cfg['instructorId']} @ {self.cfg['campus']} · "
                 f"{AI_ENGINE_LABELS.get(self.cfg.get('ai_engine_type'),'?')}",
                 bg=INK, fg=SUB, font=("맑은 고딕", 10)).pack()
        self.last_lbl = tk.Label(self.root, text="마지막 활동: —", bg=INK, fg=SUB,
                                 font=("맑은 고딕", 9)); self.last_lbl.pack(pady=(4, 10))

        # 운영=항상 실 발송. dry(테스트)는 --dry CLI 플래그로만 — UI 토글 제거(미발송 footgun 차단)
        if not self.real:
            tk.Label(self.root, text="🧪 DRY 모드 (테스트 · 카톡 미발송)", bg=INK, fg="#FCA5A5",
                     font=("맑은 고딕", 9, "bold")).pack()
        btns = tk.Frame(self.root, bg=INK); btns.pack(pady=12)
        self.start_btn = tk.Button(btns, text="시작", command=self._toggle_run, bg=INDIGO, fg="#fff",
                                   relief="flat", font=("맑은 고딕", 11, "bold"), cursor="hand2", width=8)
        self.start_btn.pack(side="left", padx=4, ipady=3)
        if self.running:
            self.start_btn.config(text="중지")
            self.dot.config(fg=GREEN)
            self.state_lbl.config(text="작동 중 (대기)")
        tk.Button(btns, text="설정", command=lambda: self._build_setup(W._load_cfg()), bg="#2A2D3A", fg="#cbd5e1",
                  relief="flat", font=("맑은 고딕", 10), cursor="hand2", width=6).pack(side="left", padx=4, ipady=3)
        tk.Button(self.root, text="종료", command=self._quit, bg="#2A2D3A", fg=SUB,
                  relief="flat", font=("맑은 고딕", 9), cursor="hand2").pack(pady=(6, 0))

    def _toggle_run(self):
        if self.running:
            self.running = False
            if hasattr(self, "_heartbeat_stop"):
                self._heartbeat_stop.set()
            self.start_btn.config(text="시작")
            self.dot.config(fg=SUB); self.state_lbl.config(text="중지됨")
        else:
            self.running = True
            self.start_btn.config(text="중지")
            self.dot.config(fg=GREEN); self.state_lbl.config(text="작동 중 (대기)")
            threading.Thread(target=self._worker, daemon=True).start()

    def _worker(self):
        db = self.cfg["dbUrl"]; instr = self.cfg["instructorId"]
        idle = self.cfg.get("interval", 2)   # 큐 픽업 지연 단축(2s) — sonnet 호출 구조는 불변
        stop = threading.Event()
        self._heartbeat_stop = stop
        beat = threading.Thread(target=_heartbeat_loop,
                                args=(stop, self.cfg, db, instr, self.real),
                                daemon=True)
        beat.start()
        try:
            while self.running and not stop.is_set():
                try:
                    g, s = W.process_once(self.cfg, db, instr, token=None, real=self.real,
                                          progress_cb=_progress, uid=None)
                    if g or s:
                        _Q.put({"_log": f"생성 {g} · 전송 {s}"})
                        continue   # 처리분 있으면 즉시 다음 루프 — 백로그 빠르게 소진
                except Exception as ex:
                    _Q.put({"_log": "ERROR: " + str(ex)[:60]})
                stop.wait(idle)   # 대기분 없을 때만 짧게 대기
        finally:
            stop.set()

    # ── 오버레이 ─────────────────────────────────────────────────────
    def _make_overlay(self):
        ov = tk.Toplevel(self.root)
        ov.overrideredirect(True); ov.attributes("-topmost", True)
        try: ov.attributes("-alpha", 0.95)
        except tk.TclError: pass
        w, h = 460, 140; sw = ov.winfo_screenwidth()
        ov.geometry(f"{w}x{h}+{(sw - w) // 2}+24"); ov.configure(bg=INDIGO)
        tk.Label(ov, text="전송 중", bg=INDIGO, fg="#fff", font=("맑은 고딕", 18, "bold")).pack(pady=(14, 2))
        self.ov_sub = tk.Label(ov, text="", bg=INDIGO, fg="#E0E7FF", font=("맑은 고딕", 12)); self.ov_sub.pack()
        self.ov_bar = ttk.Progressbar(ov, length=400, mode="determinate"); self.ov_bar.pack(pady=9)
        tk.Label(ov, text="⚠  마우스·키보드를 건드리지 마세요", bg=INDIGO, fg="#FEF08A",
                 font=("맑은 고딕", 11, "bold")).pack()
        self.overlay = ov
        if sys.platform == "win32":
            try:
                import ctypes
                GWL_EXSTYLE, NOACT, TOP = -20, 0x08000000, 0x8
                ov.update_idletasks()
                h2 = ctypes.windll.user32.GetParent(ov.winfo_id()) or ov.winfo_id()
                cur = ctypes.windll.user32.GetWindowLongW(h2, GWL_EXSTYLE)
                ctypes.windll.user32.SetWindowLongW(h2, GWL_EXSTYLE, cur | NOACT | TOP)
            except Exception:
                pass

    def _drain(self):
        try:
            while True:
                st = _Q.get_nowait()
                if "_instructors" in st:
                    epoch, campus, names, error = st["_instructors"]
                    if epoch != self._setup_epoch or campus != CAMPUS.get(self.campus_var.get(), ""):
                        continue
                    if error:
                        self._instructor_names = None
                        self.instructor_list_msg.set("목록 조회 실패 — 연결을 확인하세요. " + error[:70])
                    else:
                        self._instructor_names = set(names)
                        self.instructor_list_msg.set("등록된 강사 이름과 정확히 일치해야 합니다." if names else "등록된 강사가 없습니다.")
                    continue
                if "_model_test" in st:
                    epoch, eng, signature, ok, msg = st["_model_test"]
                    if epoch != getattr(self, "_setup_epoch", None):
                        continue
                    self._capture_model()
                    if signature != self._model_signature(eng):
                        continue
                    if ok:
                        self._verified[eng] = signature
                    else:
                        self._verified.pop(eng, None)
                    if eng == self._key_eng:
                        self.keytest_var.set(msg)
                    continue
                if "_log" in st:
                    self.last = time.strftime("%H:%M:%S") + " " + st["_log"]
                    if hasattr(self, "last_lbl") and self.last_lbl.winfo_exists(): self.last_lbl.config(text="마지막 활동: " + self.last)
                elif st.get("active"):
                    if not self.overlay: self._make_overlay()
                    d, t = st.get("done", 0), st.get("total", 0)
                    self.ov_sub.config(text=f"{st.get('cls','')} · {d}/{t}")
                    self.ov_bar["maximum"] = max(1, t); self.ov_bar["value"] = d
                    self.overlay.deiconify(); self.overlay.lift()
                else:
                    if self.overlay: self.overlay.withdraw()
        except queue.Empty:
            pass
        self.root.after(150, self._drain)

    def _quit(self):
        self.running = False
        if hasattr(self, "_heartbeat_stop"):
            self._heartbeat_stop.set()
        try:
            if self.tray:
                self.tray.stop()
        except Exception:
            pass
        try:
            self.root.after(0, self.root.destroy)   # 트레이 스레드서 호출돼도 안전
        except Exception:
            pass

    def run(self):
        self.root.mainloop()


if __name__ == "__main__":
    import sys
    g = AgentGUI()
    # 자동시작(.bat --auto)으로 켜진 경우: 설정돼 있으면 실 발송 모드로 즉시 가동(턴키)
    if "--auto" in sys.argv and g.cfg:
        try:
            g._toggle_run()                    # self.real은 위에서 결정(기본 실발송, --dry면 dry)
            if _HAS_TRAY: g._hide_to_tray()   # 자동시작 = 트레이서 조용히 백그라운드 가동
        except Exception:
            pass
    g.run()
