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
    "カメラが向いたらかくれろ"
    "あぶなくなったら飛び込め"
    "おちる！"
    "おにぎりでハートがもどる"
    "したみち"
    "おしてかがむはなしてとぶ"
    "水たまりは音が出る"
    "のぼれ！"
    "れんだであがれ"
    "むれより先に"
    "みつかった！"
    "上の帯が網のくる列"
    "秒しのげば逃げきり"
    "０１２３４５６７８９"
)

# 字幅・字高・使うフォント・大きさ・二値化の閾値
# 一度小さすぎた。実機で読めることを優先して、一段ずつ大きくしてある
SETS = [
    ("F8",  "consolab.ttf", 8, 11, 14, 120),   # 注記・小さい字
    ("F12", "consolab.ttf", 12, 16, 20, 118),  # 見出し・数字
    ("J16", "meiryob.ttc", 17, 19, 17, 118),   # 日本語・本文
    ("J28", "meiryob.ttc", 29, 32, 29, 118),   # 日本語・見出し
]


def build(name, ttf, cw, ch, size, thr):
    f = ImageFont.truetype(os.path.join(FONTS, ttf), size)
    rows = {}
    chars = (CHARS + "".join(sorted(set(JP_TEXT)))) if name.startswith("J") else CHARS
    for c in chars:
        im = Image.new("L", (cw*2, ch*2), 0)
        d = ImageDraw.Draw(im)
        # 左上に寄せて描き、二値化してから枠へ収める
        d.text((0, 0), c, font=f, fill=255)
        im = im.point(lambda v: 255 if v >= thr else 0)
        bb = im.getbbox()
        cell = Image.new("L", (cw, ch), 0)
        if bb:
            g = im.crop(bb)
            if g.width > cw or g.height > ch:
                g = g.crop((0, 0, min(cw, g.width), min(ch, g.height)))
            # 横は中央、縦は下揃え（ベースラインを揃える）
            cell.paste(g, ((cw-g.width)//2, ch-g.height-1 if ch-g.height-1 >= 0 else 0))
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
