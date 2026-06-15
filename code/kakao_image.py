"""
kakao_image.py — 카카오톡 자동화 보조 (이미지 클립보드 + 창 포커스)
Crafted by IDO(idocho@kakao.com) · Powered by Claude AI

ClassManager 의 동일 헬퍼를 이식.
추가 pip 의존성 없이 OS 내장 도구로 이미지를 클립보드에 비트맵으로 올리고,
Win32 API(ctypes)로 카카오톡 메인 창을 자동 포커스한다.
"""
import os
import subprocess
import sys
import time

_IS_WIN = sys.platform == "win32"
_IS_MAC = sys.platform == "darwin"
_CREATE_NO_WINDOW = 0x08000000  # Windows: 콘솔 창 깜빡임 방지


# ── 이미지 → DIB 캐시 (v2.2.3 속도 최적화) ──────────────────────────
# 일괄 전송은 같은 이미지를 학생 수만큼 반복 복사 — 매번 PowerShell 기동(1~2s)이
# 텍스트→이미지 사이 체감 지연의 원인. 1회 BMP 변환 후 DIB 바이트를 캐시하고
# 이후엔 ctypes 로 즉시 클립보드 세팅(~ms).
_DIB_CACHE = {}  # path -> (mtime, dib_bytes)


def _image_to_dib(path: str):
    """이미지 파일 → 클립보드용 DIB 바이트 (BMP 변환 1회 + mtime 캐시)."""
    mtime = os.path.getmtime(path)
    cached = _DIB_CACHE.get(path)
    if cached and cached[0] == mtime:
        return cached[1]
    import tempfile
    bmp_path = os.path.join(tempfile.gettempdir(), f"_drw_clip_{os.getpid()}.bmp")
    safe_in  = path.replace("'", "''")
    safe_out = bmp_path.replace("'", "''")
    ps = (
        "Add-Type -AssemblyName System.Drawing;"
        f"$img=[System.Drawing.Image]::FromFile('{safe_in}');"
        "$bmp=New-Object System.Drawing.Bitmap $img;"
        f"$bmp.Save('{safe_out}',[System.Drawing.Imaging.ImageFormat]::Bmp);"
        "$bmp.Dispose();$img.Dispose()"
    )
    subprocess.run(["powershell", "-NoProfile", "-Command", ps],
                   check=True, capture_output=True, creationflags=_CREATE_NO_WINDOW)
    with open(bmp_path, 'rb') as f:
        data = f.read()
    try:
        os.remove(bmp_path)
    except OSError:
        pass
    dib = data[14:]  # BITMAPFILEHEADER(14B) 제거 → CF_DIB 페이로드
    _DIB_CACHE.clear()          # 단일 캐시(일괄 전송은 이미지 1장) — 메모리 무한 적재 방지
    _DIB_CACHE[path] = (mtime, dib)
    return dib


def prefetch_image(path: str) -> bool:
    """전송 루프 시작 전 이미지 DIB 변환을 선행 — 첫 학생도 무지연. 실패해도 무해(폴백)."""
    if not (_IS_WIN and path and os.path.exists(path)):
        return False
    try:
        _image_to_dib(path)
        return True
    except Exception as e:
        _dbg(f"prefetch_image 실패 {path!r}: {e}")
        return False


def _set_clipboard_dib(dib: bytes) -> bool:
    """CF_DIB 를 ctypes 로 클립보드에 세팅 (64bit 핸들 안전)."""
    import ctypes
    from ctypes import wintypes
    k32, u32 = ctypes.windll.kernel32, ctypes.windll.user32
    k32.GlobalAlloc.restype = wintypes.HGLOBAL
    k32.GlobalLock.restype = ctypes.c_void_p
    k32.GlobalLock.argtypes = [wintypes.HGLOBAL]
    k32.GlobalUnlock.argtypes = [wintypes.HGLOBAL]
    u32.SetClipboardData.restype = wintypes.HANDLE
    u32.SetClipboardData.argtypes = [wintypes.UINT, wintypes.HANDLE]
    GMEM_MOVEABLE, CF_DIB = 0x0002, 8
    h = k32.GlobalAlloc(GMEM_MOVEABLE, len(dib))
    if not h:
        return False
    p = k32.GlobalLock(h)
    ctypes.memmove(p, dib, len(dib))
    k32.GlobalUnlock(h)
    for _ in range(10):                      # 클립보드 점유 경합 재시도
        if u32.OpenClipboard(0):
            break
        time.sleep(0.05)
    else:
        k32.GlobalFree(h)
        return False
    try:
        u32.EmptyClipboard()
        ok = bool(u32.SetClipboardData(CF_DIB, h))  # 성공 시 소유권 시스템 이전
        if not ok:
            k32.GlobalFree(h)
        return ok
    finally:
        u32.CloseClipboard()


def copy_image_to_clipboard(path: str) -> bool:
    """
    이미지 파일을 OS 클립보드에 비트맵으로 복사. 성공 시 True.

    Windows: DIB 캐시 + ctypes (반복 복사 ~ms). 실패 시 PowerShell SetImage 폴백.
    macOS:   osascript 로 PNG 데이터를 클립보드에 설정.
    """
    if not path or not os.path.exists(path):
        print(f"이미지 없음: {path}")
        return False
    if _IS_WIN:
        try:
            if _set_clipboard_dib(_image_to_dib(path)):
                return True
            _dbg(f"DIB 클립보드 세팅 실패 → PowerShell 폴백: {path!r}")
        except Exception as e:
            _dbg(f"DIB 경로 실패 → PowerShell 폴백: {path!r} {e!r}")
    try:
        if _IS_WIN:
            safe = path.replace("'", "''")
            ps = (
                "Add-Type -AssemblyName System.Windows.Forms,System.Drawing;"
                f"$img=[System.Drawing.Image]::FromFile('{safe}');"
                "[System.Windows.Forms.Clipboard]::SetImage($img);"
                "$img.Dispose()"
            )
            subprocess.run(
                ["powershell", "-NoProfile", "-STA", "-Command", ps],
                check=True, capture_output=True,
                creationflags=_CREATE_NO_WINDOW,
            )
            return True
        if _IS_MAC:
            safe = path.replace('"', '\\"')
            script = f'set the clipboard to (read (POSIX file "{safe}") as «class PNGf»)'
            subprocess.run(["osascript", "-e", script],
                           check=True, capture_output=True)
            return True
        print(f"이미지 클립보드 복사 미지원 플랫폼: {sys.platform}")
        return False
    except Exception as e:
        print(f"이미지 클립보드 복사 실패 [{path}]: {e}")
        return False


# ── 전송 디버그 로그 (exe는 console=False라 print 유실 — 파일로) ──────
_DBG_PATH = None


def set_debug_log(path):
    """전송 게이트 진단 로그 파일 경로 설정 (앱 시작 시 1회)."""
    global _DBG_PATH
    _DBG_PATH = path


def _dbg(msg):
    if not _DBG_PATH:
        return
    try:
        with open(_DBG_PATH, 'a', encoding='utf-8') as f:
            f.write(f"[{time.strftime('%H:%M:%S')}] {msg}\n")
    except OSError:
        pass


send_debug = _dbg  # 외부(app.py)에서 전송 단계 기록용 공개 별칭


# ── 카카오톡 창 자동 포커스 (v2.2.3) ─────────────────────────────────
# 기존: 전송 시작 후 3초 안에 사용자가 직접 카톡 창을 클릭해야 했음 — 실패 시
# 키 입력이 엉뚱한 창으로 들어가는 간헐 오류의 최다 원인. 자동 포커스로 대체.
_KAKAO_TITLES = ("카카오톡", "KakaoTalk")
WIN_VERIFY = _IS_WIN  # 창 제목 기반 검증 가능 여부 (비 Windows 는 레거시 고정 대기 경로 사용)


def _find_kakao_hwnd():
    """카카오톡 메인 창 HWND 탐색. 없으면 None.

    트레이로 내려가 있으면 메인 창이 invisible 상태라(실측: title='카카오톡',
    class='EVA_Window_Dblclk', visible=0) 가시성 조건 없이 제목으로 찾고,
    메인 UI 클래스(EVA_Window_Dblclk)를 우선한다. 채팅방 팝업은 제목이 방 이름이라 제외됨.
    """
    if not _IS_WIN:
        return None
    import ctypes
    from ctypes import wintypes
    user32 = ctypes.windll.user32
    main, fallback = [], []

    @ctypes.WINFUNCTYPE(ctypes.c_bool, wintypes.HWND, wintypes.LPARAM)
    def _enum(hwnd, _):
        t = ctypes.create_unicode_buffer(64)
        user32.GetWindowTextW(hwnd, t, 64)
        if t.value.strip() in _KAKAO_TITLES:
            c = ctypes.create_unicode_buffer(64)
            user32.GetClassNameW(hwnd, c, 64)
            (main if c.value == 'EVA_Window_Dblclk' else fallback).append(hwnd)
        return True

    user32.EnumWindows(_enum, 0)
    return (main or fallback or [None])[0]


def foreground_title() -> str:
    """현재 전면 창 제목. 비 Windows 는 빈 문자열."""
    if not _IS_WIN:
        return ""
    import ctypes
    user32 = ctypes.windll.user32
    buf = ctypes.create_unicode_buffer(256)
    user32.GetWindowTextW(user32.GetForegroundWindow(), buf, 256)
    return buf.value


def room_opened(room: str, tries: int = 15, interval: float = 0.1) -> bool:
    """카톡 채팅방이 실제로 열렸는지 검증 — 전면 창 제목이 방 이름과 일치할 때까지 폴링.

    검색→Enter 후 방이 안 열린 채 본문을 붙여넣으면 검색창/이전 방으로 발사되는
    연쇄 오류(단일 방 연속 전송·미전송)의 차단 지점. 비 Windows 는 검증 생략(True).
    제목 잔여부가 숫자/공백/괄호뿐이면 허용(그룹방 인원수 표기 대응).
    """
    if not _IS_WIN:
        return True
    import re
    # 포함 비교(공백 무시) — "오직 XXX"는 검색 키워드일 뿐, 실제 창 제목은 친구명 등
    # 다른 텍스트와 섞여 있을 수 있음(실측). 카톡 검색도 공백 무시라 동일 기준 적용.
    # 단, 메인 창 제목('카카오톡')은 방 아님 — 키워드가 제목에 포함될 때만 통과.
    norm = lambda s: re.sub(r'\s+', '', s)
    nr = norm(room)
    if not nr:
        return False
    titles = []
    for _ in range(tries):
        t = foreground_title().strip()
        titles.append(t)
        if nr in norm(t):
            _dbg(f"room_opened OK room={room!r} title={t!r}")
            return True
        time.sleep(interval)
    _dbg(f"room_opened FAIL room={room!r} seen={titles!r}")
    return False


def _norm_title(s: str) -> str:
    """제목 비교용 정규화 — 카톡 검색이 공백을 무시하므로 동일 규칙 적용."""
    import re
    return re.sub(r"\s+", "", s or "")


def close_rooms(rooms) -> int:
    """자동화로 열어둔 채팅방 창 일괄 닫기 (전체 전송 완료 후 호출).

    이미지 방은 업로드 취소 위험("전송 중인 파일" 팝업) 때문에 건별 esc 정리를
    생략하고 잔류시킴(정책 8.8) — 전송이 모두 끝난 시점에 제목 매칭으로 WM_CLOSE 발송.
    · 키 입력이 아니라 창 메시지라 전면 포커스 불필요(다른 작업 중에도 안전)
    · 업로드가 아직 진행 중이면 카톡이 확인 팝업으로 닫기를 보류 — 그 창은
      그대로 두고(자동 확인 금지: 확인=업로드 취소) 미정리 개수만 반환에 반영
    반환: 닫힌 창 수. 비 Windows 는 0 (수동 운용 유지). CM kakao_send.close_rooms 미러."""
    if not _IS_WIN or not rooms:
        return 0
    import ctypes
    from ctypes import wintypes
    user32 = ctypes.windll.user32
    WM_CLOSE = 0x0010
    targets = {_norm_title(r) for r in rooms if _norm_title(r)}
    if not targets:
        return 0

    # 오폐쇄 방지 2중 가드:
    # ① 카카오톡 프로세스 소속 창만 — 학생 이름이 제목에 들어간 타 앱(메모장·브라우저 탭
    #    등)이 매칭돼 닫히는 사고 차단
    # ② 제목 전방일치 — 방 이름으로 시작하는 창만(허용 잔여부 = 인원수 "(3)" 등).
    #    room_opened()의 포함 비교보다 엄격(그쪽은 읽기 검증, 여기는 파괴 동작)
    main_hwnd = _find_kakao_hwnd()
    if not main_hwnd:
        return 0
    kakao_pid = wintypes.DWORD()
    user32.GetWindowThreadProcessId(main_hwnd, ctypes.byref(kakao_pid))

    def _matched():
        found = []

        @ctypes.WINFUNCTYPE(ctypes.c_bool, wintypes.HWND, wintypes.LPARAM)
        def _enum(hwnd, _):
            if not user32.IsWindowVisible(hwnd):
                return True
            pid = wintypes.DWORD()
            user32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
            if pid.value != kakao_pid.value:   # ① 카톡 프로세스 외 제외
                return True
            t = ctypes.create_unicode_buffer(256)
            user32.GetWindowTextW(hwnd, t, 256)
            title = t.value.strip()
            if title in _KAKAO_TITLES:         # 메인 창 제외
                return True
            nt = _norm_title(title)
            if nt and any(nt.startswith(r) for r in targets):   # ② 전방일치
                found.append(hwnd)
            return True

        user32.EnumWindows(_enum, 0)
        return found

    before = _matched()
    for hwnd in before:
        # WM_CLOSE = 사용자의 X 클릭과 동일 경로 — 업로드 진행 중이면 카톡이
        # "전송 중인 파일" 확인을 띄우고 닫기를 보류함. 그 팝업은 절대 자동 조작하지
        # 않음(확인=업로드 취소). 기존 수동 닫기 습관과 동일한 보호 수준.
        user32.PostMessageW(hwnd, WM_CLOSE, 0, 0)
    time.sleep(0.5)
    closed = max(0, len(before) - len(_matched()))
    _dbg(f"close_rooms 대상={len(targets)} 발견={len(before)} 닫힘={closed}")
    return closed


def copy_text_verified(text: str, timeout: float = 1.5) -> bool:
    """클립보드에 텍스트 복사 후 실제 반영을 확인. 클립보드 레이스(이전 내용 붙여넣기) 차단."""
    try:
        import pyperclip
    except ImportError:
        _dbg("copy_text_verified FAIL: pyperclip import 불가")
        return False
    deadline = time.time() + timeout
    last_err = None
    while time.time() < deadline:
        try:
            pyperclip.copy(text)
            time.sleep(0.05)
            got = pyperclip.paste()
            if got == text:
                return True
            last_err = f"불일치 got={got[:40]!r}"
        except Exception as e:
            last_err = repr(e)
        time.sleep(0.1)
    _dbg(f"copy_text_verified FAIL text={text[:40]!r} last={last_err}")
    return False


def focus_kakao(settle: float = 0.6) -> bool:
    """카카오톡 메인 창을 전면으로. 성공(전면 확인) 시 True.

    - 트레이 상태(invisible)·최소화 모두 SW_RESTORE 로 복원.
    - SetForegroundWindow 제한 우회: ALT 키 탭 후 호출 (표준 기법).
    - 비 Windows 플랫폼은 True 반환(기존 수동 방식 유지 — 차단하지 않음).
    """
    if not _IS_WIN:
        return True
    hwnd = _find_kakao_hwnd()
    if not hwnd:
        return False
    import ctypes
    user32 = ctypes.windll.user32
    SW_RESTORE, VK_MENU, KEYEVENTF_KEYUP = 9, 0x12, 2
    # 빠른 경로: 이미 전면이면 복원/ALT/대기 생략 (연속 발송 시 학생당 settle 절약)
    if user32.IsWindowVisible(hwnd) and user32.GetForegroundWindow() == hwnd:
        return True
    try:
        if not user32.IsWindowVisible(hwnd) or user32.IsIconic(hwnd):
            user32.ShowWindow(hwnd, SW_RESTORE)   # 트레이/최소화 → 복원
            time.sleep(0.4)
        # 포그라운드 권한 우회용 ALT 탭
        user32.keybd_event(VK_MENU, 0, 0, 0)
        user32.keybd_event(VK_MENU, 0, KEYEVENTF_KEYUP, 0)
        user32.SetForegroundWindow(hwnd)
        time.sleep(settle)
        return user32.GetForegroundWindow() == hwnd
    except Exception as e:
        print(f"카카오톡 창 포커스 실패: {e}")
        return False
