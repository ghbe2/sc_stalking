# -*- coding: utf-8 -*-
"""
images/ の絵を、ゲームが読めるドット絵データ（SPR）に落とす。

液晶の見た目を壊さないための決まりが3つある。
  1. 半透明を作らない。閾値で切って、透けるか透けないかのどちらかにする
     （合成すると中間色が生まれて、画面の色数が跳ね上がるため）
  2. 1体あたり15色まで（スーファミの規律。ゲーム側の検査もこれを見ている）
  3. パレット全体を液晶の地（薄い薔薇色）へ少し寄せる。
     元絵は白背景で描かれているので、そのまま置くと浮く

使い方:  python tools/mkspr.py          → sprites.js を書き出す
        python tools/mkspr.py --sheet  → 確認用の拡大シートも書き出す
"""
import os, sys, json
from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
IMG  = os.path.join(ROOT, "images")

# 液晶の地。ここへ寄せることで、背景と同じ空気にする
LCD      = (0xed, 0xda, 0xe3)
LCD_MIX  = 0.14      # 地へ寄せる割合
ALPHA_TH = 128       # これ未満は透過。中間の柔らかい縁は作らない

# 地との最低限の差。白いTシャツと淡い肌は地の薄桃に近く、このままだと溶ける。
# 輪郭線は足さない方針なので、色そのものを地から引き離して輪郭を作る
MIN_GAP  = 46

# 焼き込まれた背景（ピンクのベタ）を抜くときの許容差
BG_TOL = 34

# name: (ファイル, 幅, 高さ, 色数)
SPRITES = [
    # ── ミナリ ──────────────────────────────────────────────
    ("minariBackA",  "characters/minari_back_run_A.png",   30, 34, 12),
    ("minariBackB",  "characters/minari_back_run_B.png",   30, 34, 12),
    # トウカ画面はミナリが主役。顔が読める大きさまで上げる
    ("minariFrontA", "characters/minari_front_run_A.png",  44, 50, 15),
    ("minariFrontB", "characters/minari_front_run_B.png",  44, 50, 15),
    ("minariDodgeL", "characters/minari_dodge_left.png",   50, 46, 15),
    ("minariDodgeR", "characters/minari_dodge_right.png",  50, 46, 15),
    # 下水は横向き。立ち30px・伏せ16pxの当たり判定に合わせる
    ("minariSideA",  "characters/minari_side_run_A.png",   26, 30, 13),
    ("minariSideB",  "characters/minari_side_run_B.png",   26, 30, 13),
    ("minariCrouch", "characters/minari_crouch.png",       30, 16, 11),
    # 落下も見せ場。他に描くものが少ないので大きく
    ("minariFallA",  "characters/minari_fall_A.png",       40, 44, 14),
    ("minariFallB",  "characters/minari_fall_B.png",       40, 44, 14),
    ("minariClimbA", "characters/minari_ladder_climb_A.png", 26, 34, 12),
    ("minariClimbB", "characters/minari_ladder_climb_B.png", 26, 34, 12),
    # ── トウカ（奥に立って指す。歩きの2枚 × 2種） ───────────
    ("toukaA",       "characters/touka_approach_A.png",       26, 38, 12),
    ("toukaB",       "characters/touka_approach_B.png",       26, 38, 12),
    # ── ヤツメウナギ（網を投げる部下） ──────────────────────
    ("lampReady",    "characters/amaru_net_ready.png",     22, 28, 10),
    ("lampThrow",    "characters/amaru_net_throw.png",     26, 28, 10),
    ("netFar",       "characters/amaru_cast_net.png",      20, 14,  4, 2),
    ("netNear",      "characters/amaru_cast_net_wide.png", 34, 32,  4, 1),
    # ── 路地の通行人 ────────────────────────────────────────
    ("man",          "characters/npc_boar_man_walk_front.png",  18, 26, 10),
    ("woman",        "characters/npc_fox_woman_cross.png",      20, 24, 10),
    ("kid",          "characters/npc_tanuki_kid_run_front.png", 16, 22, 10),
    # ── 拾うもの ────────────────────────────────────────────
    ("cheese",       "items/cheese.png",    12, 11, 6),
    ("onigiri",      "items/onigiri.png",   11, 10, 5),
    ("apple",        "items/apple.png",     10, 10, 5),
    ("banana",       "items/banana.png",    12,  9, 5),
    ("can",          "items/empty_can.png", 12,  8, 6),
]

CHARS = "123456789abcdef"


def strip_baked_bg(im):
    """四隅が不透明なら、そこから塗りつぶしで背景を抜く。

    色の一致だけで抜くと、肌や白シャツのように背景と近い色まで消える。
    外周から繋がっている範囲だけを背景とみなすので、体の内側は残る。
    """
    w, h = im.size
    c = im.getpixel((0, 0))
    if c[3] == 0:
        return im
    px = im.load()
    seen = bytearray(w*h)
    stack = [(x, y) for x in range(w) for y in (0, h-1)] + \
            [(x, y) for y in range(h) for x in (0, w-1)]
    r0, g0, b0 = c[:3]
    while stack:
        x, y = stack.pop()
        if x < 0 or y < 0 or x >= w or y >= h or seen[y*w+x]:
            continue
        r, g, b, a = px[x, y]
        if not a or abs(r-r0) > BG_TOL or abs(g-g0) > BG_TOL or abs(b-b0) > BG_TOL:
            continue
        seen[y*w+x] = 1
        px[x, y] = (r, g, b, 0)
        stack += [(x+1, y), (x-1, y), (x, y+1), (x, y-1)]
    return im


def main_bbox(im):
    """本体の範囲を返す。

    背景を抜いたあとに隅へ残る小さな染みを範囲に入れると、キャラが極端に
    縮む。かといって一番大きい塊だけを見ると、髪と胴が細い首で切れていた
    ときに頭だけになる。**一番大きい塊のある割合以上の塊をすべて**まとめる。
    """
    w, h = im.size
    mask = im.split()[3].point(lambda v: 255 if v >= ALPHA_TH else 0)
    a = mask.load()
    seen = bytearray(w*h)
    parts = []
    for sy in range(h):
        for sx in range(w):
            if not a[sx, sy] or seen[sy*w+sx]:
                continue
            stack = [(sx, sy)]
            seen[sy*w+sx] = 1
            x0 = x1 = sx; y0 = y1 = sy; n = 0
            while stack:
                x, y = stack.pop(); n += 1
                if x < x0: x0 = x
                if x > x1: x1 = x
                if y < y0: y0 = y
                if y > y1: y1 = y
                for nx, ny in ((x+1, y), (x-1, y), (x, y+1), (x, y-1)):
                    if 0 <= nx < w and 0 <= ny < h and a[nx, ny] and not seen[ny*w+nx]:
                        seen[ny*w+nx] = 1
                        stack.append((nx, ny))
            parts.append((n, (x0, y0, x1+1, y1+1)))
    if not parts:
        return im.split()[3].getbbox()
    big = max(p[0] for p in parts)
    keep = [p[1] for p in parts if p[0] >= big*0.05]     # 染みだけを落とす
    return (min(b[0] for b in keep), min(b[1] for b in keep),
            max(b[2] for b in keep), max(b[3] for b in keep))


def to_lcd(rgb):
    """液晶の地へ少しだけ寄せる。元の色味は残したまま、浮きだけを取る"""
    return tuple(round(c*(1-LCD_MIX) + l*LCD_MIX) for c, l in zip(rgb, LCD))


def lift(rgb):
    """地に溶ける色を、地から引き離す。

    輪郭線を足さずに輪郭を出すための処理。明るさだけを落とすと灰色になるので、
    地の方向から遠ざける形で暗くする（色味は保つ）。
    """
    d = sum(abs(c-l) for c, l in zip(rgb, LCD))
    if d >= MIN_GAP:
        return rgb
    k = 1 - (MIN_GAP-d)/MIN_GAP*0.30       # 最大で3割暗くする
    return tuple(max(0, min(255, round(c*k))) for c in rgb)


def build(name, path, W, H, ncol, bold=0):
    im = Image.open(os.path.join(IMG, path)).convert("RGBA")
    im = strip_baked_bg(im)
    bb = main_bbox(im)
    if bb:
        im = im.crop(bb)
    if bold:
        # 細い線の絵（網）は、そのまま縮めると消える。縮める前に太らせる
        from PIL import ImageFilter
        for _ in range(bold):
            im = im.filter(ImageFilter.MaxFilter(5))

    # 縦横比を保ったまま枠に収め、下端を基準に置く（足元を揃えるため）
    sc = min(W/im.width, H/im.height)
    tw, th = max(1, round(im.width*sc)), max(1, round(im.height*sc))
    im = im.resize((tw, th), Image.LANCZOS)
    canvas = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    canvas.paste(im, ((W-tw)//2, H-th), im)
    im = canvas

    # 半透明を作らない。ここで切っておかないと、合成で中間色が生まれる
    px = im.load()
    for y in range(H):
        for x in range(W):
            r, g, b, a = px[x, y]
            px[x, y] = (r, g, b, 255) if a >= ALPHA_TH else (0, 0, 0, 0)

    # 不透明な部分だけを色数削減にかける
    opaque = Image.new("RGB", (W, H), LCD)
    mask = Image.new("L", (W, H), 0)
    for y in range(H):
        for x in range(W):
            r, g, b, a = px[x, y]
            if a:
                opaque.putpixel((x, y), (r, g, b))
                mask.putpixel((x, y), 255)
    q = opaque.quantize(colors=ncol, method=Image.MEDIANCUT, dither=Image.NONE).convert("RGB")

    pal, order = {}, []
    rows = []
    for y in range(H):
        line = []
        for x in range(W):
            if not mask.getpixel((x, y)):
                line.append(".")
                continue
            col = lift(to_lcd(q.getpixel((x, y))))
            key = "#%02x%02x%02x" % col
            if key not in pal:
                if len(order) >= len(CHARS):
                    key = order[0]                       # 念のための保険
                else:
                    pal[key] = CHARS[len(order)]
                    order.append(key)
            line.append(pal[key])
        rows.append("".join(line))
    return {"name": name, "pal": {pal[k]: k for k in order}, "px": rows}


def main():
    out = [build(*s) for s in SPRITES]

    js = ["const SPR = {"]
    for s in out:
        js.append("  %s: { pal:{%s}, px:[" % (
            s["name"], ",".join('"%s":"%s"' % (c, h) for c, h in s["pal"].items())))
        js.append(",\n".join('    "%s"' % r for r in s["px"]))
        js.append("  ]},")
    js.append("};")

    # 単一HTMLのままにしたいので、印の間へ直に差し込む
    dst = os.path.join(ROOT, "index.html")
    src = open(dst, encoding="utf-8").read()
    i = src.index("*/", src.index("/* ART:BEGIN")) + 3
    j = src.index("/* ART:END */")
    open(dst, "w", encoding="utf-8").write(src[:i] + "\n".join(js) + "\n" + src[j:])

    n = sum(len(s["px"][0])*len(s["px"]) for s in out)
    print("%d 体 / %d ドット / %s" % (len(out), n, dst))
    for s in out:
        print("  %-14s %2dx%-2d %2d色" % (s["name"], len(s["px"][0]), len(s["px"]), len(s["pal"])))

    if "--sheet" in sys.argv:
        sheet(out)


def sheet(out, scale=5):
    from PIL import ImageDraw
    cols = 8
    cw = max(len(s["px"][0]) for s in out)*scale + 12
    ch = max(len(s["px"]) for s in out)*scale + 18
    rows = (len(out)+cols-1)//cols
    im = Image.new("RGB", (cw*cols, ch*rows), LCD)
    d = ImageDraw.Draw(im)
    for i, s in enumerate(out):
        ox, oy = (i % cols)*cw+6, (i//cols)*ch+4
        for y, row in enumerate(s["px"]):
            for x, c in enumerate(row):
                if c == ".":
                    continue
                h = s["pal"][c].lstrip("#")
                col = tuple(int(h[k:k+2], 16) for k in (0, 2, 4))
                d.rectangle([ox+x*scale, oy+y*scale, ox+x*scale+scale-1, oy+y*scale+scale-1], fill=col)
        d.text((ox, oy+ch-16), s["name"][:16], fill=(90, 70, 82))
    p = os.path.join(HERE, "sheet.png")
    im.save(p)
    print("確認用シート:", p)


main()
