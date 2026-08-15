# -*- coding: utf-8 -*-
"""本物のフォントから、ドット絵用のビットマップ字形を起こす。

自作の5x5では、監視モニタの文法（細い罫線・小さな注記・時刻表示）が成立しない。
かといって画面に TTF を直接描くと、アンチエイリアスで中間色が生まれて
液晶の規律が壊れる。**あらかじめ二値で焼いておく**のが唯一の解になる。

等幅であること（数字が揺れない）を優先して Consolas を使う。
"""
import os, io
from PIL import Image, ImageDraw, ImageFont

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
FONTS = r"C:\Windows\Fonts"

CHARS = ("0123456789"
         "ABCDEFGHIJKLMNOPQRSTUVWXYZ"
         "abcdefghijklmnopqrstuvwxyz"
         ".,:;!?-+/*=<>()[]%#'\"& ")

# 日本語は、**実際に使う字だけ**を焼く。全部入れると重すぎるため。
# 文言を変えたらここへ足して、もう一度流すこと。
JP_TEXT = (
    "にげろ！"
    "カメラからかくれろ"
    "あぶなくなったら飛び込め"
    "下水ににげた"
    "おにぎりおいしい"
    "ひそめ！"
    "しゃがめ"
    "跳べ"
    "水たまりをふむとうるさい"
    "はしごをつかんでだっしゅつ"
    "のぼれ！"
    "どれ？"
    "あみだをよんでえらべ"
    "おにぎりにつけばラッキー"
    "みつかった！"
    "上の帯が網のくる列"
    "あと本しのげば逃げきり網を"
    "０１２３４５６７８９"
)

# 字幅・字高・使うフォント・大きさ・二値化の閾値
# 一度小さすぎた。実機で読めることを優先して、一段ずつ大きくしてある
SETS = [
    # 枠は「字の高さ＋下がり」が収まる大きさにする。足りないと上が切れる
    ("F8",  "consolab.ttf", 8, 13, 14, 120),   # 注記・小さい字
    ("F12", "consolab.ttf", 12, 19, 20, 118),  # 見出し・数字
    ("J16", "meiryob.ttc", 17, 22, 17, 118),   # 日本語・本文
    ("J28", "meiryob.ttc", 29, 37, 29, 118),   # 日本語・見出し
]


def build(name, ttf, cw, ch, size, thr):
    f = ImageFont.truetype(os.path.join(FONTS, ttf), size)
    asc, _desc = f.getmetrics()
    # ベースラインを固定する。字ごとに下端で揃えると、p や g の下がりが
    # 持ち上がって別の字に見える（tap! の p が P に見えていた）
    drop = max(1, round(ch*0.22))          # ベースラインより下に残す余白
    base = ch-1-drop                       # 枠の中でのベースラインの行
    rows = {}
    chars = (CHARS + "".join(sorted(set(JP_TEXT)))) if name.startswith("J") else CHARS
    for c in chars:
        im = Image.new("L", (cw*3, ch*3), 0)
        d = ImageDraw.Draw(im)
        d.text((cw, 0), c, font=f, fill=255)
        im = im.point(lambda v: 255 if v >= thr else 0)
        cell = Image.new("L", (cw, ch), 0)
        bb = im.getbbox()
        if bb:
            # 横だけ中央へ寄せ、縦はベースラインで揃える
            x0 = bb[0] - (cw - (bb[2]-bb[0]))//2
            y0 = asc - base
            g = im.crop((x0, y0, x0+cw, y0+ch))
            cell.paste(g, (0, 0))
        px = cell.load()
        rows[c] = ["".join("1" if px[x, y] else "0" for x in range(cw)) for y in range(ch)]
    return rows, chars


def main():
    out = ["/* 自動生成。tools/mkfont.py が本物のフォントから焼いている。",
           "   画面に TTF を直接描くとアンチエイリアスで中間色が出るので、",
           "   あらかじめ二値にしておく。手で編集しないこと */"]
    for name, ttf, cw, ch, size, thr in SETS:
        rows, chars = build(name, ttf, cw, ch, size, thr)
        out.append("const %s = { w:%d, h:%d, g:{" % (name, cw, ch))
        for c in chars:
            key = c.replace("\\", "\\\\").replace('"', '\\"')
            out.append('  "%s":"%s",' % (key, " ".join(rows[c])))
        out.append("}};")
    js = "\n".join(out)

    dst = os.path.join(ROOT, "index.html")
    src = io.open(dst, encoding="utf-8").read()
    A, B = "/* FONT:BEGIN", "/* FONT:END */"
    if A not in src:
        print("印が無い。index.html に FONT:BEGIN / FONT:END を置いてから流すこと")
        print(js[:400])
        return
    i = src.index("*/", src.index(A)) + 3
    j = src.index(B)
    io.open(dst, "w", encoding="utf-8").write(src[:i] + js + "\n" + src[j:])
    print("英数%d字 + 和字%d字 / %d書体 を差し込んだ" % (len(CHARS), len(set(JP_TEXT)), len(SETS)))


if __name__ == "__main__":
    main()
