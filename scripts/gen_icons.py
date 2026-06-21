"""
gen_icons.py — DRW 앱 아이콘(A안: 리포트+반짝임) 래스터 생성. Pillow only.
인디고 라운드 스퀘어 + 흰 리포트 + 노란 반짝임. 1024 슈퍼샘플 → 다운스케일.
출력: 인자로 받은 디렉터리에 icon-512/192/apple-touch-icon(180)/favicon-32 PNG + drw_icon.ico.
실행: python scripts/gen_icons.py <out_dir>
"""
import sys
from pathlib import Path
from PIL import Image, ImageDraw

INDIGO = (79, 70, 229, 255)
WHITE  = (255, 255, 255, 255)
LINE   = (199, 210, 254, 255)   # 연한 인디고
SPARK  = (254, 229, 0, 255)     # 카카오 옐로

S = 1024  # 마스터 슈퍼샘플 크기


def rr(draw, box, r, fill):
    draw.rounded_rectangle(box, radius=r, fill=fill)


def star4(cx, cy, r, k=0.30):
    """4-point 반짝임 폴리곤."""
    return [(cx, cy - r), (cx + r * k, cy - r * k), (cx + r, cy), (cx + r * k, cy + r * k),
            (cx, cy + r), (cx - r * k, cy + r * k), (cx - r, cy), (cx - r * k, cy - r * k)]


def draw_symbol(d, ox, oy, scale):
    """페이지+라인+반짝임을 (ox,oy) 기준 scale*S 크기로 그림."""
    u = S * scale
    px0, py0, px1, py1 = ox + u * 0.30, oy + u * 0.22, ox + u * 0.70, oy + u * 0.75
    rr(d, [px0, py0, px1, py1], int(u * 0.045), WHITE)
    lx = ox + u * 0.375
    for (y, w) in [(0.345, 0.255), (0.455, 0.215), (0.565, 0.165)]:
        yy = oy + u * y
        rr(d, [lx, yy, lx + u * w, yy + u * 0.038], int(u * 0.019), LINE)
    d.polygon(star4(ox + u * 0.715, oy + u * 0.255, u * 0.085), fill=SPARK)


def render_master():
    img = Image.new("RGBA", (S, S), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    rr(d, [0, 0, S - 1, S - 1], int(S * 0.225), INDIGO)   # 라운드 스퀘어
    draw_symbol(d, 0, 0, 1.0)
    return img


def render_maskable():
    """PWA 마스커블: full-bleed 사각 배경 + 심볼을 안전영역(~80%)에 배치."""
    img = Image.new("RGBA", (S, S), INDIGO)              # 전체 불투명 사각
    d = ImageDraw.Draw(img)
    sc = 0.80
    off = S * (1 - sc) / 2
    draw_symbol(d, off, off, sc)
    return img


def main():
    out = Path(sys.argv[1] if len(sys.argv) > 1 else ".")
    out.mkdir(parents=True, exist_ok=True)
    master = render_master()
    sizes = {"icon-512.png": 512, "icon-192.png": 192, "apple-touch-icon.png": 180, "favicon-32.png": 32}
    for name, sz in sizes.items():
        master.resize((sz, sz), Image.LANCZOS).save(out / name)
        print("wrote", out / name)
    # 마스커블(PWA)
    mask = render_maskable()
    for name, sz in {"icon-512-maskable.png": 512, "icon-192-maskable.png": 192}.items():
        mask.resize((sz, sz), Image.LANCZOS).save(out / name)
        print("wrote", out / name)
    # 멀티 해상도 ICO (PC)
    ico = out / "drw_icon.ico"
    master.resize((256, 256), Image.LANCZOS).save(
        ico, format="ICO", sizes=[(16, 16), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)])
    print("wrote", ico)


if __name__ == "__main__":
    main()
