# -*- coding: utf-8 -*-
"""OGP の1枚（1200x630）を焼く。

タイトル画面を引き伸ばすのではなく、横長に組み直す。縦持ちの構図は
そのまま入らないし、SNS の一覧では**左に字、右に絵**のほうが読まれる。

見た目はゲームと同じ規律で作る。地は暗く、桃の5段だけ、走査線と四隅の括弧。
「監視モニタの1コマを切り出した」ように見せる。

    python tools/mkogp.py   → ogp.png
"""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import mkspr
from PIL import Image, ImageDraw, ImageFont

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
FONTS = r"C:\Windows\Fonts"
fnt = lambda n, s: ImageFont.truetype(os.path.join(FONTS, n), s)

W, H = 1200, 630
BAR = 54                       # 上下の帯
P = dict(bg=(0x16, 0x0d, 0x15), off=(0x24, 0x14, 0x22), scan=(0x1b, 0x10, 0x19),
         d1=(0x4a, 0x22, 0x40), d2=(0x8e, 0x42, 0x72), d3=(0xd0, 0x74, 0xa4),
         d4=(0xf6, 0xb4, 0xd2), d5=(0xff, 0xe8, 0xf2),
         warn=(0xff, 0x46, 0x6e), gold=(0xff, 0xd2, 0x6c))
RAMP = [P["d1"], P["d2"], P["d3"], P["d4"], P["d5"]]


def txt(im, xy, s, f, fill, anchor=None):
    """字は二値で置く。アンチエイリアスの中間色は液晶に無い色なので使わない"""
    t = Image.new("L", im.size, 0)
    ImageDraw.Draw(t).text(xy, s, font=f, fill=255, anchor=anchor)
    t = t.point(lambda v: 255 if v >= 118 else 0)
    im.paste(Image.new("RGB", im.size, fill), (0, 0), t)


def put(im, spr, cx, by, clip=None):
    """ドット絵を置く。1ドット1画素のまま。拡大は一切しない"""
    rows, pal = spr["px"], spr["pal"]
    w, h = len(rows[0]), len(rows)
    x0, y0 = round(cx - w/2), round(by - h)
    px = im.load()
    for r in range(h):
        for c in range(w):
            ch = rows[r][c]
            if ch == ".":
                continue
            col = tuple(int(pal[ch].lstrip("#")[i:i+2], 16) for i in (0, 2, 4))
            X, Y = x0+c, y0+r
            if clip and not (clip[0] <= X < clip[2] and clip[1] <= Y < clip[3]):
                continue
            if 0 <= X < W and 0 <= Y < H:
                px[X, Y] = col


def ellF(d, cx, cy, rw, rh, c):
    for dy in range(-rh, rh+1):
        w = round(rw * (max(0.0, 1-(dy/rh)**2)) ** 0.5)
        if w > 0:
            d.rectangle([cx-w, cy+dy, cx+w, cy+dy], fill=c)


def beam(d, ax, ay, cx, cy, rw):
    """横から差し込む光。地面に当たったところが円になる"""
    rh = round(rw*0.30)
    for y in range(ay, cy):
        t = (y-ay)/(cy-ay)
        l = ax + (cx-rw-ax)*t
        r = ax + (cx+rw-ax)*t
        d.rectangle([round(l), y, round(r), y], fill=P["off"])
        if y % 2 == 0:
            m, hw = (l+r)/2, (r-l)*0.25
            d.rectangle([round(m-hw), y, round(m+hw), y], fill=P["d1"])
    ellF(d, cx, cy, rw, rh, P["d1"])
    ellF(d, cx, cy, round(rw*0.64), round(rh*0.64), P["d2"])


def main():
    im = Image.new("RGB", (W, H), P["bg"])
    d = ImageDraw.Draw(im)
    f_bar = fnt("consolab.ttf", 22)
    f_sub = fnt("consolab.ttf", 26)
    f_sml = fnt("consolab.ttf", 19)
    f_ttl = fnt("meiryob.ttc", 78)
    f_cpy = fnt("meiryob.ttc", 34)

    inner = (0, BAR, W, H-BAR)

    # ── 絵。右半分。ミナリを大きく、トウカはその奥 ──────────
    mby, tby = H-BAR-26, H-BAR-186
    beam(d, W, BAR+40, 860, mby, 150)           # 右から差し込んでミナリの足元へ
    beam(d, 660, BAR+30, 1036, tby, 74)          # 奥をなめる細い光
    put(im, mkspr.build("t", "characters/touka_approach_A2.png", 200, 274, 0, 0, 0.02),
        1036, tby, inner)
    put(im, mkspr.build("m", "characters/minari_front_run_A2.png", 400, 444, 0, 0, 0.22),
        860, mby, inner)

    # ── 走査線。絵の上から引いて「映像」にする ────────────
    for y in range(BAR, H-BAR, 4):
        d.rectangle([0, y, W, y], fill=P["scan"])

    # ── 字。左半分 ────────────────────────────────────────
    x = 68
    d.rectangle([x, 176, x+430, 177], fill=P["d1"])
    for dx, dy, col in ((3, 3, P["d1"]), (2, 2, P["warn"]), (0, 0, P["d5"])):
        txt(im, (x+dx, 196+dy), "しゅがけ", f_ttl, col)
        txt(im, (x+dx, 286+dy), "ストーキング", f_ttl, col)
    d.rectangle([x, 396, x+430, 397], fill=P["d1"])
    txt(im, (x, 420), "路地裏キッズミナリちゃん", f_cpy, P["d4"])
    txt(im, (x, 474), "SHE IS ALWAYS WATCHING", f_sub, P["d3"])
    txt(im, (x, 506), "RUN, MINARI, RUN", f_sml, P["d2"])

    # ── 四隅の括弧 ────────────────────────────────────────
    T, B, L, R, n, t = BAR+14, H-BAR-16, 16, W-18, 46, 5
    box = lambda x0, y0, x1, y1: d.rectangle(
        [min(x0, x1), min(y0, y1), max(x0, x1), max(y0, y1)], fill=P["d3"])
    for ax, ay, sx, sy in ((L, T, 1, 1), (R, T, -1, 1), (L, B, 1, -1), (R, B, -1, -1)):
        box(ax, ay, ax+n*sx, ay+t*sy)
        box(ax, ay, ax+t*sx, ay+n*sy)

    # ── 上下の帯 ──────────────────────────────────────────
    d.rectangle([0, 0, W, BAR], fill=P["bg"])
    txt(im, (24, 16), "CAM 01  PURSUIT", f_bar, P["d3"])
    txt(im, (W-24, 16), "00:04:17", f_bar, P["d3"], anchor="ra")
    d.rectangle([0, BAR-1, W, BAR-1], fill=P["d1"])
    d.rectangle([0, H-BAR, W, H], fill=P["bg"])
    d.rectangle([0, H-BAR, W, H-BAR], fill=P["d1"])
    d.ellipse([24, H-36, 40, H-20], fill=P["warn"])
    txt(im, (52, H-38), "REC", f_bar, P["warn"])
    txt(im, (W-24, H-38), "ghbe2.github.io/sc_stalking", f_bar, P["d2"], anchor="ra")

    dst = os.path.join(ROOT, "ogp.png")
    im.save(dst, optimize=True)
    print("書き出した", im.size, os.path.getsize(dst)//1024, "KB")


if __name__ == "__main__":
    main()
