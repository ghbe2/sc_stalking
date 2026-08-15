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

# 監視モニタの画面。暗い地に桃で光る。
# **絵は色を持たない。** 明暗の5段だけで描く（監視カメラの映像なので）。
# 狸・猪・狐の区別は、色ではなくシルエットで付ける。
RAMP = ["#4a2240", "#8e4272", "#d074a4", "#f6b4d2", "#ffe8f2"]
GAMMA = 0.80         # 明暗の伸ばし方。1.0 だと素直、小さいほど明るい側へ寄る
ALPHA_TH = 128       # これ未満は透過。中間の柔らかい縁は作らない

# 焼き込まれた背景（ピンクのベタ）を抜くときの許容差
BG_TOL = 34

# 実機（縦持ちスマホ）は仮想 300x640 になる。レーン幅は約75px。
# 監視モニタの映像なので、絵は明暗の5段だけで描く。
# name: (ファイル, 幅, 高さ, 使わない, 太らせ, 明るさの下駄)
SPRITES = [
    # ── ミナリ ──────────────────────────────────────────────
    ("minariBackA",  "characters/minari_back_run_A.png",   44, 52, 0, 0, 0.22),
    ("minariBackB",  "characters/minari_back_run_B.png",   44, 52, 0, 0, 0.22),
    # トウカ画面はミナリが主役。画面の4割強を占める。
    # この背丈がトウカ画面の遠近の基準で、地平線も他のキャラの立ち位置も
    # ここから逆算される。変えるときは drawTouka の前提も変わる
    ("minariFrontA", "characters/minari_front_run_A.png",  252, 280, 0, 0, 0.22),
    ("minariFrontB", "characters/minari_front_run_B.png",  252, 280, 0, 0, 0.22),
    ("minariDodgeL", "characters/minari_dodge_left.png",   280, 260, 0, 0, 0.22),
    ("minariDodgeR", "characters/minari_dodge_right.png",  280, 260, 0, 0, 0.22),
    # 下水は横向き。立ち60px・伏せ32pxの当たり判定に合わせる
    ("minariSideA",  "characters/minari_side_run_A.png",   52, 60, 0, 0, 0.22),
    ("minariSideB",  "characters/minari_side_run_B.png",   52, 60, 0, 0, 0.22),
    ("minariCrouch", "characters/minari_crouch.png",       60, 32, 0, 0, 0.42),
    ("minariFallA",  "characters/minari_fall_A.png",       64, 68, 0, 0, 0.22),
    ("minariFallB",  "characters/minari_fall_B.png",       64, 68, 0, 0, 0.22),
    ("minariClimbA", "characters/minari_ladder_climb_A.png", 40, 52, 0, 0, 0.22),
    ("minariClimbB", "characters/minari_ladder_climb_B.png", 40, 52, 0, 0, 0.22),
    # ── トウカと部下。背丈比 ミナリ1.0 / トウカ1.35 / 部下1.05 ──
    # 4枚で1周する（A→A′→B→B′）。2枚だと動きが硬い
    ("toukaA",       "characters/touka_approach_A.png",        108, 148, 0, 0, 0.10),
    ("toukaA2",      "characters/touka_approach_A_prime.png",  108, 148, 0, 0, 0.10),
    ("toukaB",       "characters/touka_approach_B.png",        108, 148, 0, 0, 0.10),
    ("toukaB2",      "characters/touka_approach_B_prime.png",  108, 148, 0, 0, 0.10),
    ("lampReady",    "characters/amaru_net_ready.png",      88, 116, 0, 0, 0.10),
    ("lampThrow",    "characters/amaru_net_throw.png",     108, 116, 0, 0, 0.10),
    # 網は奥から手前へ。大きさの段で近づくのを見せる
    ("netFar",       "characters/amaru_cast_net.png",      28, 22, 0, 3, 0.30),
    ("netMid",       "characters/amaru_cast_net_wide.png", 60, 56, 0, 2, 0.30),
    ("netNear",      "characters/amaru_cast_net_wide.png", 112, 104, 0, 1, 0.30),
    # ── 路地の通行人。色を持たないので、見分けはシルエットが担う ──
    ("man",          "characters/npc_boar_man_walk_front.png",  30, 44, 0, 0, 0.05),
    ("woman",        "characters/npc_fox_woman_cross.png",      32, 40, 0, 0, 0.05),
    ("kid",          "characters/npc_tanuki_kid_run_front.png", 26, 34, 0, 0, 0.05),
    # ── 拾うもの。桃の外の色（金）で塗るので、形だけあればいい ──
    ("cheese",       "items/cheese.png",    22, 20, 0, 0, 0.5),
    ("onigiri",      "items/onigiri.png",   20, 18, 0, 0, 0.5),
    ("apple",        "items/apple.png",     18, 18, 0, 0, 0.5),
    ("banana",       "items/banana.png",    22, 16, 0, 0, 0.5),
    ("can",          "items/empty_can.png", 22, 14, 0, 0, 0.5),
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


def luma(rgb):
    return (rgb[0]*0.30 + rgb[1]*0.59 + rgb[2]*0.11)/255


def to_ramp(v, lo, hi, boost=0.0):
    """明るさを段へ落とす。

    元絵は淡い色ばかりで、素の明るさで割り当てると全部が同じ段に寄る
    （実際、最初は2段しか使われなかった）。**その絵の中での明暗の幅**を
    0..1 へ伸ばしてから割り当てる。こうすると、どの絵も5段を使い切る。
    """
    t = 0.5 if hi - lo < 1e-6 else (v - lo)/(hi - lo)
    t = min(1.0, max(0.0, t)) ** GAMMA
    t = min(1.0, t + boost)
    return RAMP[min(len(RAMP)-1, max(0, int(t*len(RAMP)*0.999)))]


def build(name, path, W, H, ncol, bold=0, boost=0.0):
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
    # 一気に縮めない。LANCZOS は縮小率が大きいと輪郭に「鳴き」が出て、
    # 単独の浮いた点になる（これがジャギの見え方になる）。
    # 4倍手前まで LANCZOS で落として、最後は面積平均で均す
    while im.width > tw*4 and im.height > th*4:
        im = im.resize((max(tw, im.width//2), max(th, im.height//2)), Image.LANCZOS)
    im = im.resize((tw, th), Image.BOX)
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
    opaque = Image.new("RGB", (W, H), (0, 0, 0))
    mask = Image.new("L", (W, H), 0)
    for y in range(H):
        for x in range(W):
            r, g, b, a = px[x, y]
            if a:
                opaque.putpixel((x, y), (r, g, b))
                mask.putpixel((x, y), 255)
    q = opaque
    # その絵の中での明暗の幅を測る。段の割り当てはこれを基準にする
    lo, hi = 1.0, 0.0
    for y in range(H):
        for x in range(W):
            if mask.getpixel((x, y)):
                v = luma(q.getpixel((x, y)))
                lo = min(lo, v); hi = max(hi, v)

    # 浮いた1ドットを消す。縮小の過程でどうしても、周りと繋がっていない点が
    # 残る。手で置いたドット絵にはこれが無いので、あるだけで粗く見える
    m = mask.load()
    for _ in range(2):
        drop = []
        for y in range(H):
            for x in range(W):
                if not m[x, y]:
                    continue
                n = sum(1 for dx, dy in ((1,0),(-1,0),(0,1),(0,-1),(1,1),(1,-1),(-1,1),(-1,-1))
                        if 0 <= x+dx < W and 0 <= y+dy < H and m[x+dx, y+dy])
                if n <= 1:
                    drop.append((x, y))
        if not drop:
            break
        for x, y in drop:
            m[x, y] = 0

    pal, order = {}, []
    rows = []
    for y in range(H):
        line = []
        for x in range(W):
            if not mask.getpixel((x, y)):
                line.append(".")
                continue
            key = to_ramp(luma(q.getpixel((x, y))), lo, hi, boost)
            if key not in pal:
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


if __name__ == "__main__":
    main()
