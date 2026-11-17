"""Pixel art for Racing Times: studio set, presenter "Pixie", and on-screen graphics.

Everything is drawn on a 320x180 canvas and scaled 4x (nearest neighbour) to 720p,
so the whole show keeps one consistent pixel grid.
"""
from __future__ import annotations

import math
from functools import lru_cache
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

W, H = 320, 180
A = Path(__file__).parent / "assets"

# palette
NIGHT = (12, 16, 30); WALL = (22, 28, 50); WALL2 = (30, 38, 66); PANEL = (40, 52, 88)
RED = (214, 34, 46); RED_D = (140, 18, 30); WHITE = (244, 240, 230); GREY = (150, 150, 162)
DESK = (36, 40, 52); DESK_TOP = (196, 200, 210); DESK_HI = (236, 238, 244); GOLD = (246, 196, 64)
TEAL = (40, 210, 190); SILVER = (190, 200, 210)
SKIN = (238, 186, 150); SKIN_SH = (208, 148, 116); BLUSH = (238, 142, 132)
HAIR = (96, 26, 46); HAIR_HI = (150, 50, 72); EYE = (22, 18, 28)
BLAZER = (26, 56, 86); BLAZER_HI = (48, 88, 124); SHIRT = (240, 236, 226)
MOUTH = (110, 26, 36); TEETH = (252, 248, 242); TONGUE = (210, 86, 96); HEADSET = (36, 36, 44); MIC = (90, 90, 104)

SCREEN = (196, 24, 308, 110)  # video wall in the wide shot
DESK_Y = 124


@lru_cache(None)
def font(name: str, size: int) -> ImageFont.FreeTypeFont:
    return ImageFont.truetype(str(A / f"{name}.ttf"), size)


def px(d, x, y, c):
    d.point((x, y), fill=c)


def rect(d, x0, y0, x1, y1, c):
    d.rectangle((x0, y0, x1, y1), fill=c)


def text_c(d, cx, y, s, f, c, shadow=None):
    w = d.textlength(s, font=f)
    x = int(cx - w / 2)
    if shadow:
        d.text((x + 1, y + 1), s, font=f, fill=shadow)
    d.text((x, y), s, font=f, fill=c)


# ── studio ──────────────────────────────────────────────────
@lru_cache(None)
def studio_back() -> Image.Image:
    im = Image.new("RGB", (W, H), NIGHT)
    d = ImageDraw.Draw(im)
    for y in range(H):  # stepped gradient wall
        k = min(1, y / 120)
        c = tuple(int(WALL[i] + (WALL2[i] - WALL[i]) * k) for i in range(3))
        d.line((0, y, W, y), fill=c)
    for x in range(0, W, 32):  # wall panels
        d.line((x, 0, x, DESK_Y), fill=PANEL)
        d.line((x + 1, 0, x + 1, DESK_Y), fill=WALL)
    for y in range(6, DESK_Y, 8):  # LED dots
        for x in range(4, W, 8):
            if (x // 8 + y // 8) % 5 == 0:
                px(d, x, y, (44, 58, 98))
    rect(d, 0, 112, W, 113, RED)  # neon stripe
    rect(d, 0, 114, W, 114, RED_D)
    rect(d, 0, 162, W, H, (16, 18, 28))  # floor
    for x in range(-40, W, 20):
        d.line((x, 180, x + 30, 162), fill=(24, 26, 40))
    # video wall frame
    x0, y0, x1, y1 = SCREEN
    rect(d, x0 - 3, y0 - 3, x1 + 3, y1 + 3, (10, 10, 16))
    rect(d, x0 - 2, y0 - 2, x1 + 2, y1 + 2, (60, 64, 80))
    rect(d, (x0 + x1) // 2 - 6, y1 + 3, (x0 + x1) // 2 + 6, DESK_Y, (20, 22, 30))  # stand
    return im


@lru_cache(None)
def desk_layer() -> Image.Image:
    im = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    x0, x1 = 22, 182
    rect(d, x0, DESK_Y, x1, DESK_Y + 4, DESK_TOP)
    d.line((x0, DESK_Y, x1, DESK_Y), fill=DESK_HI)
    rect(d, x0 + 4, DESK_Y + 5, x1 - 4, 164, DESK)
    rect(d, x0 + 4, DESK_Y + 5, x1 - 4, DESK_Y + 6, (20, 22, 30))
    rect(d, x0 + 4, 140, x1 - 4, 141, RED)
    for i, x in enumerate(range(x0 + 4, x1 - 4, 4)):  # checkered strip
        for j, y in enumerate((156, 160)):
            rect(d, x, y, x + 3, y + 3, WHITE if (i + j) % 2 == 0 else (10, 10, 14))
    text_c(d, (x0 + x1) / 2, 143, "RACING TIMES", font("silkscreen-bold", 8), WHITE, shadow=(10, 10, 14))
    return im


# ── presenter ───────────────────────────────────────────────
def draw_mouth(d, x, y, shape):
    """Rhubarb mouth shapes A–H, X, drawn around (x, y) = mouth centre-left."""
    if shape == "A":
        rect(d, x, y + 1, x + 3, y + 1, MOUTH)
    elif shape == "B":
        rect(d, x, y + 1, x + 3, y + 2, MOUTH); rect(d, x, y + 1, x + 3, y + 1, TEETH)
    elif shape == "C":
        rect(d, x, y, x + 3, y + 2, MOUTH); rect(d, x + 1, y, x + 2, y, TEETH)
    elif shape == "D":
        rect(d, x - 1, y, x + 4, y + 3, MOUTH); rect(d, x, y, x + 3, y, TEETH); rect(d, x + 1, y + 3, x + 2, y + 3, TONGUE)
    elif shape == "E":
        rect(d, x + 1, y, x + 2, y + 2, MOUTH); px(d, x, y + 1, MOUTH); px(d, x + 3, y + 1, MOUTH)
    elif shape == "F":
        rect(d, x + 1, y + 1, x + 2, y + 2, MOUTH)
    elif shape == "G":
        rect(d, x, y + 1, x + 3, y + 1, TEETH); rect(d, x, y + 2, x + 3, y + 2, MOUTH)
    elif shape == "H":
        rect(d, x, y, x + 3, y + 2, MOUTH); rect(d, x + 1, y + 1, x + 2, y + 1, TONGUE)
    else:  # X: resting smile
        rect(d, x, y + 1, x + 3, y + 1, MOUTH); px(d, x - 1, y, MOUTH); px(d, x + 4, y, MOUTH)


def draw_presenter(im: Image.Image, x0: int, y0: int, mouth="X", blink=False, point=0.0, nod=0):
    """x0,y0 = top-left of the head box (20x22). point: 0..1 arm raise towards the screen."""
    d = ImageDraw.Draw(im)
    hy = y0 + nod
    # torso
    d.polygon([(x0 - 4, y0 + 25), (x0 + 23, y0 + 25), (x0 + 27, y0 + 30), (x0 + 27, y0 + 62),
               (x0 - 8, y0 + 62), (x0 - 8, y0 + 30)], fill=BLAZER)
    d.line((x0 - 3, y0 + 26, x0 + 22, y0 + 26), fill=BLAZER_HI)
    d.polygon([(x0 + 6, y0 + 24), (x0 + 13, y0 + 24), (x0 + 9, y0 + 35)], fill=SHIRT)
    d.line((x0 + 5, y0 + 25, x0 + 9, y0 + 37), fill=RED)
    d.line((x0 + 14, y0 + 25, x0 + 10, y0 + 37), fill=RED)
    px(d, x0 + 18, y0 + 31, GOLD)  # pin
    rect(d, x0 + 8, hy + 21, x0 + 11, y0 + 24, SKIN_SH)  # neck
    # left arm (resting on desk)
    d.polygon([(x0 - 8, y0 + 32), (x0 - 4, y0 + 32), (x0 + 2, DESK_Y - 1), (x0 - 6, DESK_Y - 1)], fill=BLAZER)
    rect(d, x0 + 1, DESK_Y - 3, x0 + 5, DESK_Y - 1, SKIN)
    # right arm: blend between resting and pointing at the video wall
    sx, sy = x0 + 25, y0 + 32
    rest = (x0 + 20, DESK_Y - 2)
    up = (x0 + 44, y0 + 20)
    hx = int(rest[0] + (up[0] - rest[0]) * point)
    hy2 = int(rest[1] + (up[1] - rest[1]) * point)
    d.line((sx, sy, hx, hy2), fill=BLAZER, width=5)
    d.line((sx, sy - 2, hx, hy2 - 2), fill=BLAZER_HI, width=1)
    rect(d, hx - 1, hy2 - 2, hx + 3, hy2 + 1, SKIN)
    if point > 0.6:
        rect(d, hx + 4, hy2 - 2, hx + 6, hy2 - 2, SKIN)  # index finger
    # head
    y0 = hy
    rect(d, x0 - 2, y0 - 1, x0 + 21, y0 + 18, HAIR)            # back hair (bob)
    rect(d, x0 + 1, y0 - 3, x0 + 18, y0, HAIR)
    rect(d, x0 + 2, y0 + 5, x0 + 17, y0 + 20, SKIN)            # face
    rect(d, x0 + 4, y0 + 21, x0 + 15, y0 + 21, SKIN)
    rect(d, x0 + 1, y0 + 1, x0 + 18, y0 + 6, HAIR)             # fringe
    for x in range(x0 + 3, x0 + 17, 3):
        px(d, x, y0 + 7, HAIR)
    for x in range(x0 + 4, x0 + 12):
        px(d, x, y0 - 2, HAIR_HI)
    px(d, x0 + 3, y0 + 1, HAIR_HI); px(d, x0 + 13, y0 - 1, HAIR_HI)
    # headset
    d.line((x0 + 1, y0 - 4, x0 + 18, y0 - 4), fill=HEADSET)
    rect(d, x0 - 3, y0 + 8, x0, y0 + 13, HEADSET)
    d.line((x0, y0 + 13, x0 + 5, y0 + 18), fill=HEADSET)
    rect(d, x0 + 5, y0 + 17, x0 + 6, y0 + 18, MIC)
    # brows, eyes, blush, nose
    rect(d, x0 + 5, y0 + 8, x0 + 7, y0 + 8, HAIR); rect(d, x0 + 12, y0 + 8, x0 + 14, y0 + 8, HAIR)
    for ex in (x0 + 6, x0 + 12):
        if blink:
            rect(d, ex, y0 + 12, ex + 1, y0 + 12, EYE)
        else:
            rect(d, ex, y0 + 10, ex + 1, y0 + 12, EYE); px(d, ex, y0 + 10, TEETH)
    rect(d, x0 + 4, y0 + 14, x0 + 5, y0 + 14, BLUSH); rect(d, x0 + 14, y0 + 14, x0 + 15, y0 + 14, BLUSH)
    px(d, x0 + 10, y0 + 14, SKIN_SH)
    draw_mouth(d, x0 + 8, y0 + 16, mouth)


# ── graphics on the video wall / full screen ─────────────────
def checker(d, x0, y0, x1, y1, s, c1, c2, off=0):
    for y in range(y0, y1, s):
        for x in range(x0 - s * 2, x1, s):
            xx = x + off % (2 * s)
            c = c1 if ((xx // s) + (y // s)) % 2 == 0 else c2
            a, b = max(x0, xx), min(x1, xx + s - 1)
            if b >= a:
                d.rectangle((a, y, b, min(y1, y + s - 1)), fill=c)


def ease(t):
    t = max(0.0, min(1.0, t))
    return 1 - (1 - t) ** 3


TEAMS = {"MCL": (255, 128, 0), "FER": (232, 0, 45), "RBR": (54, 113, 198), "MER": (39, 244, 210), "AMR": (34, 153, 113),
         "ALP": (0, 147, 204), "WIL": (100, 196, 255), "RB": (102, 146, 255), "HAA": (182, 186, 189), "AUD": (200, 204, 208),
         "CAD": (201, 162, 74)}  # same codes as show-catalog/catalog.json


def fit(d, s, maxw, fonts):
    """First font in `fonts` that fits maxw; else the last one with the text trimmed."""
    for f in fonts:
        if d.textlength(s, font=f) <= maxw:
            return s, f
    f = fonts[-1]
    while s and d.textlength(s, font=f) > maxw:
        s = s[:-1]
    return s, f


def wrap2(d, s, maxw, f):
    """Up to two lines that fit maxw (the second trimmed if it still overflows)."""
    if d.textlength(s, font=f) <= maxw:
        return [s]
    words, line1 = s.split(), ""
    while words and d.textlength((line1 + " " + words[0]).strip(), font=f) <= maxw:
        line1 = (line1 + " " + words.pop(0)).strip()
    if not line1:
        return [fit(d, s, maxw, [f])[0]]
    return [line1, fit(d, " ".join(words), maxw, [f])[0]]


def shared_font(d, lines, maxw, fonts):
    """Largest font in which every line fits (so a group of lines matches in size)."""
    for f in fonts:
        if all(d.textlength(l, font=f) <= maxw for l in lines):
            return f
    return fonts[-1]


def graphic(g: dict, w: int, h: int, t: float, full: bool) -> Image.Image:
    """Render graphic g (already normalised, see show-catalog) at w x h; t = seconds since it appeared."""
    im = Image.new("RGB", (w, h), (14, 14, 22))
    d = ImageDraw.Draw(im)
    big = font("pressstart", 16 if full else 8)
    mid = font("silkscreen-bold", 16 if full else 8)
    small = font("silkscreen", 8)
    k = g["kind"]
    if k == "logo":
        checker(d, 0, 0, w, h, 8 if full else 6, (24, 24, 34), (16, 16, 24), off=int(t * 12))
        rect(d, 0, h // 2 - (18 if full else 11), w, h // 2 + (18 if full else 11), RED)
        text_c(d, w / 2, h // 2 - (8 if full else 4), "RACING TIMES", big, WHITE, shadow=RED_D)
        s, f = fit(d, g["sub"], w - 8, [small])
        text_c(d, w / 2, h // 2 + (22 if full else 14), s, f, GREY)
    elif k == "headlines":
        rect(d, 0, 0, w, 14 if not full else 26, RED)
        s, f = fit(d, g["title"], w - 8, [mid, small] if full else [small])
        text_c(d, w / 2, 3 if not full else 6, s, f, WHITE)
        fonts = [shared_font(d, g["items"], w - 30, [mid, small])] if full else [small]
        y = 34 if full else 22
        step = 36 if full else 22
        for i, item in enumerate(g["items"]):
            p = ease((t - 0.6 - i * 1.6) / 0.5)
            if p <= 0:
                continue
            x = int(-w + (w + (14 if full else 6)) * p)
            rect(d, x, y + i * step - 3, x + (6 if full else 3), y + i * step + (12 if full else 7), GOLD)
            label, f = fit(d, item, w - (14 if full else 7) - (14 if full else 6) - 2, fonts)
            d.text((x + (14 if full else 7), y + i * step - (2 if full else 0)), label, font=f, fill=WHITE)
    elif k == "p1":
        accent = TEAMS.get(g.get("team"), WHITE)
        checker(d, w // 2, 0, w, h, 8 if full else 6, accent, (12, 12, 16), off=int(t * 10))
        d.polygon([(0, 0), (w * 0.62, 0), (w * 0.48, h), (0, h)], fill=(14, 14, 22))
        p = ease(t / 0.6)
        x = int(-120 + 132 * p) if full else int(-60 + 66 * p)
        maxw = int(w * 0.48) - 12 if full else int(w * 0.48) - 4
        pos, f = fit(d, g["pos"], maxw, [big, small])
        d.text((x, h // 2 - (20 if full else 10)), pos, font=f, fill=GOLD)
        name = g["name"] if full else g["name"].split()[-1]   # wall shows the surname only
        name, f = fit(d, name, maxw, [big, mid, small])
        d.text((x, h // 2), name, font=f, fill=WHITE)
        if full:
            sub, f = fit(d, g["sub"], w - 24, [small])
            d.text((x, h // 2 + 26), sub, font=f, fill=GREY)
            if g.get("stat"):
                d.text((x, h // 2 + 40), g["stat"], font=mid, fill=GOLD)
        else:
            sub, f = fit(d, g.get("stat") or g["sub"], maxw + 10, [small])
            d.text((x, h // 2 + 14), sub, font=f, fill=GREY)
    elif k == "results":
        rows = g["rows"]
        if full:
            rect(d, 0, 0, w, 26, RED)
            s, f = fit(d, g["title"], w - 86, [mid, small])
            d.text((10, 6 if f is mid else 9), s, font=f, fill=WHITE)
            d.text((w - 74, 9), f"TOP {len(rows)}", font=small, fill=WHITE)
        else:
            rect(d, 0, 0, w, 12, RED)
            s, f = fit(d, g["title"], w - 6, [small])
            text_c(d, w / 2, 2, s, f, WHITE)
        for i, (pos, name, team, gap) in enumerate(rows):
            p = ease((t - 0.25 - i * 0.35) / 0.4)
            if p <= 0:
                continue
            medal = GOLD if i == 0 else SILVER if i == 1 else (206, 128, 70) if i == 2 else GREY
            if full:
                y = 32 + i * 23
                x = int(w - (w - 10) * p)
                rect(d, x, y, x + w - 20, y + 19, (30, 30, 44) if i % 2 else (38, 38, 56))
                rect(d, x, y, x + 22, y + 19, medal)
                rect(d, x + 23, y, x + 24, y + 19, TEAMS.get(team, GREY))
                text_c(d, x + 11, y + 1, pos, mid, (14, 14, 22))
                nm, f = fit(d, name, 160, [mid, small])
                d.text((x + 32, y + (1 if f is mid else 5)), nm, font=f, fill=WHITE)
                d.text((x + 196, y + 5), team, font=small, fill=GREY)
                d.text((x + 240, y + 1), gap, font=mid, fill=GOLD if i == 0 else WHITE)
            else:  # compact list on the small wall: position + surname
                y = 16 + i * 14
                x = int(w - (w - 4) * p)
                rect(d, x, y, x + 10, y + 11, medal)
                text_c(d, x + 5, y + 1, pos, small, (14, 14, 22))
                nm, f = fit(d, name, w - 20, [small])
                d.text((x + 14, y + 1), nm, font=f, fill=WHITE)
    elif k == "champions":
        for i in range(70):  # pixel confetti
            cx = (i * 47 + int(t * 9) * (i % 3 + 1)) % w
            cy = (i * 29 + int(t * 40 * (1 + i % 4))) % h
            rect(d, cx, cy, cx + 1, cy + 1, [GOLD, WHITE, TEAL, SILVER][i % 4])
        p = ease(t / 0.7)
        bw = int(w * p)
        rect(d, (w - bw) // 2, h // 2 - (24 if full else 12), (w + bw) // 2, h // 2 + (24 if full else 12), SILVER)
        if g.get("team") in TEAMS:
            rect(d, (w - bw) // 2, h // 2 + (24 if full else 12) - 2, (w + bw) // 2, h // 2 + (24 if full else 12), TEAMS[g["team"]])
        if p > 0.9:
            s, f = fit(d, g["big"], w - 8, [big, mid, small])
            text_c(d, w / 2, h // 2 - (8 if full else 4), s, f, (14, 14, 22))
            for i, line in enumerate(wrap2(d, g["sub"], w - 6, small)):
                text_c(d, w / 2, h // 2 + (30 if full else 16) + i * 10, line, small, GOLD)
    elif k == "bigword":
        for i in range(-h, w, 14):
            d.line((i, h, i + h * 0.6, 0), fill=(30, 120, 140), width=4 if full else 2)
        p = ease(t / 0.6)
        s, f = fit(d, g["big"], w - 8, [font("pressstart", 32 if full else 16), big, small])
        text_c(d, w / 2, int(h * 0.32 * p) - (4 if full else 2), s, f, WHITE, shadow=(10, 60, 80))
        if full:
            f = shared_font(d, g["lines"], w - 8, [mid, small])
            lines = [fit(d, l, w - 8, [f])[0] for l in g["lines"]]
            step = 20
        else:  # wall shows the first line only, wrapped
            f, lines, step = small, wrap2(d, g["lines"][0], w - 8, small), 10
        for i, line in enumerate(lines):
            if t > 0.8 + (i * 0.6 if full else 0):
                text_c(d, w / 2, int(h * 0.62) + i * step, line, f, TEAL if i == 0 or not full else WHITE, shadow=(10, 10, 14))
    elif k == "photo":  # the 3D show puts the photo on the wall; the pixel show uses a typographic card
        checker(d, 0, 0, w, h, 8 if full else 6, (24, 24, 34), (16, 16, 24), off=int(t * 6))
        rect(d, 0, 0, 3 if not full else 6, h, RED)
        if g.get("kicker"):
            s, f = fit(d, g["kicker"], w - 16, [small])
            d.text((10, 8 if not full else 16), s, font=f, fill=GOLD)
        for i, line in enumerate(wrap2(d, g["title"], w - 16, mid if full else small)):
            d.text((10, (h // 2 - 10 if full else h // 2 - 8) + i * (20 if full else 11)), line, font=mid if full else small, fill=WHITE)
    elif k == "nextup":
        checker(d, 0, 0, w, h, 8 if full else 6, (34, 20, 44), (24, 14, 32), off=int(t * 8))
        rect(d, 0, 0, w, 14 if not full else 24, GOLD)
        s, f = fit(d, g["title"], w - 8, [mid, small] if full else [small])
        text_c(d, w / 2, 3 if not full else 5, s, f, (14, 14, 22))
        s, f = fit(d, g["big"], w - 8, [big, mid, small])
        text_c(d, w / 2, h // 2 - (12 if full else 10), s, f, WHITE, shadow=RED_D)
        if full:
            s, f = fit(d, g["sub"], w - 8, [mid, small])
            text_c(d, w / 2, h // 2 + 10, s, f, GOLD)
        else:
            for i, line in enumerate(wrap2(d, g["sub"], w - 8, small)):
                text_c(d, w / 2, h // 2 + 4 + i * 10, line, small, GOLD)
        if full:
            for i, l in enumerate(g["later"]):
                s, f = fit(d, "LATER: " + l, w - 8, [small])
                text_c(d, w / 2, h // 2 + 28 + i * 13, s, f, GREY)
    # scanlines for that LED-wall feel
    if not full:  # faint LED-wall scanlines
        ov = Image.new("RGBA", (w, h), (0, 0, 0, 0))
        od = ImageDraw.Draw(ov)
        for y in range(1, h, 3):
            od.line((0, y, w, y), fill=(0, 0, 0, 40))
        im.paste(ov, (0, 0), ov)
    return im


def lower_third(im: Image.Image, title: str, sub: str, t: float):
    d = ImageDraw.Draw(im)
    p = ease(t / 0.5)
    w = int(176 * p)
    if w < 4:
        return
    y = 112
    rect(d, 8, y, 8 + w, y + 14, RED)
    rect(d, 8, y + 14, 8 + int(w * 0.92), y + 24, WHITE)
    rect(d, 8, y, 10, y + 24, GOLD)
    if p > 0.85:
        d.text((14, y + 3), title, font=font("silkscreen-bold", 8), fill=WHITE)
        d.text((14, y + 15), sub[:34], font=font("silkscreen", 8), fill=(20, 20, 28))


def bugs(im: Image.Image, t: float, ep: int):
    d = ImageDraw.Draw(im)
    rect(d, 6, 6, 36, 15, RED)
    if int(t * 1.2) % 2 == 0:
        rect(d, 9, 9, 11, 11, WHITE)
    d.text((14, 6), "LIVE", font=font("silkscreen", 8), fill=WHITE)
    rect(d, W - 44, 6, W - 6, 15, (10, 10, 16))
    d.text((W - 41, 6), f"EP {ep:02d}", font=font("silkscreen", 8), fill=GOLD)
