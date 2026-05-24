"""
main.py — DailyReportWizard 진입점
Crafted by IDO(idocho@kakao.com) · Powered by Claude AI

빌드:
  pyinstaller --onefile --noconsole --name "DailyReportWizard" \
    --add-data "drw_icon.ico;." main.py
"""
import os, sys, tkinter as tk
from tkinter import messagebox

from storage import set_runtime_cwd, RUNTIME_DIR
from app import App

import ai_engine
ai_engine.DEBUG_AI_PROMPT = "--debug-ai" in sys.argv

if __name__ == '__main__':
    runtime_dir = set_runtime_cwd()
    root = None
    try:
        root = tk.Tk()

        # 아이콘 설정
        try:
            from storage import resource_path
            icon_path = resource_path('drw_icon.ico')
            root.iconbitmap(icon_path)
            try:
                from PIL import Image, ImageTk  # type: ignore
                _img   = Image.open(icon_path)
                _photo = ImageTk.PhotoImage(_img.resize((256, 256), Image.LANCZOS))
                root.wm_iconphoto(True, _photo)
            except Exception:
                pass
        except Exception:
            pass

        App(root)
        root.mainloop()
    except Exception as exc:
        try:
            err_path = os.path.join(runtime_dir, 'DailyReportWizard_error.log')
            with open(err_path, 'w', encoding='utf-8') as f:
                import traceback
                traceback.print_exc(file=f)
        except Exception:
            pass
        try:
            messagebox.showerror(
                '실행 오류',
                f'앱 실행 중 오류가 발생했습니다.\n'
                f'로그: {os.path.join(runtime_dir, "DailyReportWizard_error.log")}'
            )
        except Exception:
            pass
        raise
    finally:
        if root is not None:
            try:
                root.destroy()
            except Exception:
                pass
