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
import sys
import threading
import time
import tkinter as tk
from tkinter import ttk, messagebox

import agent_worker as W
from constants import AI_ENGINE_ORDER, AI_ENGINE_LABELS

try:
    import pystray
    from PIL import Image, ImageDraw
    _HAS_TRAY = True
except Exception:
    _HAS_TRAY = False   # pystray 미설치/실패 → 트레이 비활성(일반 창으로 동작)

INDIGO, INK, GREEN, RED, SUB = "#4F46E5", "#15171F", "#16A34A", "#DC2626", "#94A3B8"
AGENT_VERSION = "0.9"
# 캠퍼스 표시명 → id (app.py / 웹 게이트와 동일 정본). 캠퍼스 추가 시 여기만 갱신.
CAMPUS = {"동수원": "dongsuwon"}
_Q = queue.Queue()


def _progress(state):
    _Q.put(state)


class AgentGUI:
    def __init__(self):
        self.cfg = None
        self.running = False
        self.real = "--dry" not in sys.argv   # 운영=실 발송 기본. 테스트만 --dry로 dry
        self.overlay = None
        self.last = "—"
        self.root = tk.Tk()
        self.root.title(f"DRW Agent v{AGENT_VERSION}")
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
                                 f"DRW Agent v{AGENT_VERSION}", menu)
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
        self.root.geometry("380x560")
        self.root.resizable(True, True)   # 배율(125/150%)로 잘릴 때 대비
        self.root.minsize(360, 420)
        e = existing or {}
        tk.Label(self.root, text=f"DRW Agent Setup · v{AGENT_VERSION}", bg=INK, fg="#fff",
                 font=("맑은 고딕", 13, "bold")).pack(pady=(16, 2))
        tk.Label(self.root, text="키·카톡은 이 PC를 떠나지 않습니다", bg=INK, fg=SUB,
                 font=("맑은 고딕", 9)).pack(pady=(0, 10))
        # 저장 버튼을 하단 고정(항상 보이게) — frm보다 먼저 side=bottom 배치
        tk.Button(self.root, text="저장하고 시작", command=self._save_setup, bg=INDIGO, fg="#fff",
                  relief="flat", font=("맑은 고딕", 12, "bold"), cursor="hand2"
                  ).pack(side="bottom", fill="x", padx=22, pady=14, ipady=5)
        frm = tk.Frame(self.root, bg=INK); frm.pack(padx=22, fill="x")
        self.vars = {}

        def row(label, key, default="", show=None):
            tk.Label(frm, text=label, bg=INK, fg="#cbd5e1", font=("맑은 고딕", 10),
                     anchor="w").pack(fill="x", pady=(7, 1))
            v = tk.StringVar(value=e.get(key, default))
            ent = tk.Entry(frm, textvariable=v, font=("맑은 고딕", 11), show=show)
            ent.pack(fill="x", ipady=3)
            self.vars[key] = v
            return v

        # 캠퍼스 드롭다운 — id 직접 입력 대신 선택(오타·불일치 방지)
        tk.Label(frm, text="캠퍼스", bg=INK, fg="#cbd5e1", font=("맑은 고딕", 10),
                 anchor="w").pack(fill="x", pady=(7, 1))
        _id2name = {cid: nm for nm, cid in CAMPUS.items()}
        cur_campus = e.get("campus", next(iter(CAMPUS.values())))
        self.campus_var = tk.StringVar(value=_id2name.get(cur_campus, next(iter(CAMPUS))))
        ttk.Combobox(frm, textvariable=self.campus_var, state="readonly",
                     values=list(CAMPUS.keys()), font=("맑은 고딕", 11)).pack(fill="x")
        row("본인 이름 (웹 로그인명과 동일)", "instructorId")
        # 엔진 드롭다운
        tk.Label(frm, text="AI 엔진", bg=INK, fg="#cbd5e1", font=("맑은 고딕", 10),
                 anchor="w").pack(fill="x", pady=(7, 1))
        cur_eng = e.get("ai_engine_type", AI_ENGINE_ORDER[0])
        self.eng_var = tk.StringVar(value=AI_ENGINE_LABELS.get(cur_eng, cur_eng))
        ttk.Combobox(frm, textvariable=self.eng_var, state="readonly",
                     values=[AI_ENGINE_LABELS[x] for x in AI_ENGINE_ORDER],
                     font=("맑은 고딕", 11)).pack(fill="x")
        # 키는 엔진별 — 현재 엔진 키 프리필
        cur_key = e.get(f"{cur_eng}_api_key", "")
        row("개인 API 키", "_api_key", cur_key, show="•")
        row('카톡 방 접두사 (예: "오직 ")', "roomPrefix", e.get("roomPrefix", ""))

        self.auto_var = tk.BooleanVar(value=True)
        tk.Checkbutton(frm, text="Windows 시작 시 자동 실행", variable=self.auto_var,
                       bg=INK, fg="#cbd5e1", selectcolor=INK, activebackground=INK,
                       font=("맑은 고딕", 9)).pack(anchor="w", pady=(8, 0))
        # (저장 버튼은 위에서 하단 고정으로 배치됨)

    def _eng_id(self):
        lbl = self.eng_var.get()
        for k, v in AI_ENGINE_LABELS.items():
            if v == lbl:
                return k
        return AI_ENGINE_ORDER[0]

    def _save_setup(self):
        v = {k: var.get().strip() for k, var in self.vars.items()}
        campus = CAMPUS.get(self.campus_var.get(), "")
        if not campus or not v["instructorId"] or not v["_api_key"]:
            messagebox.showwarning("입력 필요", "캠퍼스·이름·API 키는 필수입니다.")
            return
        eng = self._eng_id()
        fields = {
            "campus": campus, "instructorId": v["instructorId"],
            "dbUrl": W.DEFAULT_DB, "roomPrefix": v.get("roomPrefix", ""),
            "ai_engine_type": eng, f"{eng}_api_key": v["_api_key"],
        }
        W.write_agent_config(fields)
        if self.auto_var.get():
            W.register_autostart()
        self.cfg = W._load_cfg()
        self._build_status()
        messagebox.showinfo("완료", "설정 저장 완료. 이제 안 건드려도 됩니다.")

    # ── 상태창 ───────────────────────────────────────────────────────
    def _build_status(self):
        for w in self.root.winfo_children():
            w.destroy()
        self.root.geometry("360x300"); self.root.resizable(False, False)
        tk.Label(self.root, text=f"DRW Agent · v{AGENT_VERSION}", bg=INK, fg="#cbd5e1",
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
        tk.Button(btns, text="설정", command=lambda: self._build_setup(self.cfg), bg="#2A2D3A", fg="#cbd5e1",
                  relief="flat", font=("맑은 고딕", 10), cursor="hand2", width=6).pack(side="left", padx=4, ipady=3)
        tk.Button(self.root, text="종료", command=self._quit, bg="#2A2D3A", fg=SUB,
                  relief="flat", font=("맑은 고딕", 9), cursor="hand2").pack(pady=(6, 0))

    def _toggle_run(self):
        if self.running:
            self.running = False
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
        last_hb = 0.0
        while self.running:
            now = time.time()
            if now - last_hb > 15:           # 하트비트 — 웹이 에이전트 실행 여부 감지(미실행 시 설치 안내)
                W.write_heartbeat(self.cfg, db, instr, real=self.real)
                last_hb = now
            try:
                g, s = W.process_once(self.cfg, db, instr, real=self.real, progress_cb=_progress)
                if g or s:
                    _Q.put({"_log": f"생성 {g} · 전송 {s}"})
                    continue   # 처리분 있으면 즉시 다음 루프 — 백로그 빠르게 소진
            except Exception as ex:
                _Q.put({"_log": "ERROR: " + str(ex)[:60]})
            time.sleep(idle)   # 대기분 없을 때만 짧게 대기(기본 3s)

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
                if "_log" in st:
                    self.last = time.strftime("%H:%M:%S") + " " + st["_log"]
                    if hasattr(self, "last_lbl"): self.last_lbl.config(text="마지막 활동: " + self.last)
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
