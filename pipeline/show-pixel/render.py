"""Compose every frame of the episode and encode it with ffmpeg."""
from __future__ import annotations

import bisect
import json
import math
import random
import subprocess
import sys
import textwrap
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

import visuals as V

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "show-catalog"))
from validate import normalize  # noqa: E402  (shared defaults + aliases)

# Timing comes from the timeline; what to show comes from the script (matched by segment id),
# so a graphic can be fixed without re-recording the voice.
CONTENT_KEYS = ("graphic", "graphic_b", "graphic_b_at", "shots", "point", "lower_third", "lower_third_at")


def merge_content(script: dict, tl: dict) -> dict:
    by_id = {s["id"]: s for s in script["segments"]}
    segs = []
    for seg in tl["segments"]:
        sc = by_id.get(seg["id"])
        if sc:
            seg = {k: v for k, v in seg.items() if k not in CONTENT_KEYS} | {k: sc[k] for k in CONTENT_KEYS if k in sc}
        segs.append(seg)
    return {**tl, "segments": segs}

FPS = 24
SCALE = 4
OUT_W, OUT_H = V.W * SCALE, V.H * SCALE
HEAD = (92, 64)  # presenter head position in the wide shot
SUB_FONT = ImageFont.truetype(str(V.A / "vt323.ttf"), 40)


class Episode:
    def __init__(self, script: dict, tl: dict):
        self.s, self.tl = script, merge_content(script, tl)
        tl = self.tl
        self.mouth_starts = [m[0] for m in tl["mouth"]]
        self.bounds = [seg["start"] for seg in tl["segments"]] + [tl["outro"][0]]
        rnd = random.Random(7)
        self.blinks, t = [], 1.0
        while t < tl["duration"]:
            self.blinks.append(t)
            t += rnd.uniform(2.2, 4.8)

    # ── state lookups ───────────────────────────────────────
    def mouth(self, now):
        i = bisect.bisect_right(self.mouth_starts, now) - 1
        if i < 0:
            return "X"
        st, en, v = self.tl["mouth"][i]
        return v if now < en else "X"

    def blink(self, now):
        i = bisect.bisect_right(self.blinks, now) - 1
        return i >= 0 and now - self.blinks[i] < 0.11

    def segment(self, now):
        for seg in self.tl["segments"]:
            if seg["start"] <= now < seg["end"] + 0.55:
                return seg
        return None

    @staticmethod
    def at(seg, frac):
        return seg["start"] + (seg["end"] - seg["start"]) * frac

    def shot(self, seg, now):
        cur = seg["shots"][0][1]
        for frac, name in seg["shots"]:
            if now >= self.at(seg, frac):
                cur = name
        return cur

    def graphic(self, seg, now):
        ep = self.s["episode"]
        if "graphic_b" in seg and now >= self.at(seg, seg["graphic_b_at"]):
            return normalize(seg["graphic_b"], ep), now - self.at(seg, seg["graphic_b_at"])
        return normalize(seg["graphic"], ep), now - seg["start"]

    # ── frame builders ──────────────────────────────────────
    def wide(self, seg, now, with_screen=True):
        im = V.studio_back().copy()
        if with_screen:
            g, gt = self.graphic(seg, now)
            x0, y0, x1, y1 = V.SCREEN
            im.paste(V.graphic(g, x1 - x0 + 1, y1 - y0 + 1, gt, full=False), (x0, y0))
        point = 0.0
        if seg.get("point"):
            lt = now - seg["start"]
            point = V.ease(lt / 0.35) if lt < 1.7 else max(0.0, 1 - (lt - 1.7) / 0.35)
        m = self.mouth(now)
        nod = 1 if (m not in "XA" and int(now * 2.1) % 6 == 0) else 0
        breathe = 1 if math.sin(now * 1.7) > 0.7 else 0
        V.draw_presenter(im, HEAD[0], HEAD[1] + breathe, mouth=m, blink=self.blink(now), point=point, nod=nod)
        im.paste(V.desk_layer(), (0, 0), V.desk_layer())
        return im

    def close(self, seg, now):
        im = self.wide(seg, now, with_screen=False)
        box = (HEAD[0] - 70, HEAD[1] - 22, HEAD[0] + 90, HEAD[1] + 68)  # 160x90 -> 2x zoom
        return im.crop(box).resize((V.W, V.H), Image.NEAREST)

    def full(self, seg, now):
        g, gt = self.graphic(seg, now)
        return V.graphic(g, V.W, V.H, gt, full=True)

    def intro(self, now):
        im = Image.new("RGB", (V.W, V.H), (10, 10, 16))
        d = ImageDraw.Draw(im)
        V.checker(d, 0, 0, V.W, V.H, 10, (26, 26, 38), (14, 14, 22), off=int(now * 30))
        band = V.ease(now / 0.6)
        V.rect(d, 0, 70, int(V.W * band), 108, V.RED)
        V.rect(d, V.W - int(V.W * band), 108, V.W, 110, V.GOLD)
        title, f = "RACING TIMES", V.font("pressstart", 16)
        x = (V.W - d.textlength(title, font=f)) / 2
        for i, ch in enumerate(title):
            p = V.ease((now - 0.5 - i * 0.07) / 0.3)
            if p > 0:
                y = int(-20 + (82 + 20) * p)
                d.text((x + 1, y + 1), ch, font=f, fill=V.RED_D)
                d.text((x, y), ch, font=f, fill=V.WHITE)
            x += d.textlength(ch, font=f)
        if now > 1.9:
            V.text_c(d, V.W / 2, 122, f"EPISODE {self.s['episode']:02d}  ·  {self.s['date_display']}", V.font("silkscreen", 8), V.GOLD)
        if now > 2.4:
            V.text_c(d, V.W / 2, 136, self.s["show"].upper() + " WEEKLY", V.font("silkscreen", 8), V.GREY)
        return im

    def outro(self, now):
        lt = now - self.tl["outro"][0]
        im = Image.new("RGB", (V.W, V.H), (10, 10, 16))
        d = ImageDraw.Draw(im)
        V.checker(d, 0, 0, V.W, V.H, 10, (22, 22, 34), (14, 14, 22), off=int(now * 20))
        V.rect(d, 0, 18, V.W, 46, V.RED)
        V.text_c(d, V.W / 2, 25, "RACING TIMES", V.font("pressstart", 16), V.WHITE, shadow=V.RED_D)
        V.text_c(d, V.W / 2, 58, "STORIES SUMMARISED FROM REPORTING BY", V.font("silkscreen", 8), V.GOLD)
        names = self.s["credits"]
        for i, n in enumerate(names):
            col, row = i % 2, i // 2
            if lt > 0.3 + i * 0.12:
                V.text_c(d, V.W / 2 + (-60 if col == 0 else 60), 74 + row * 12, n.upper(), V.font("silkscreen", 8), V.WHITE)
        if lt > 2.2:
            V.text_c(d, V.W / 2, 150, "READ THE ORIGINALS: LINKS IN THE DESCRIPTION", V.font("silkscreen", 8), V.GREY)
        return im

    def wipe(self, im, now):
        """Checkered-flag transition around segment boundaries."""
        dt = min((abs(now - b) for b in self.bounds), default=9)
        if dt > 0.22:
            return im
        c = 1 - dt / 0.22
        d = ImageDraw.Draw(im)
        s = 10
        rnd = random.Random(3)
        for cy in range(0, V.H, s):
            for cx in range(0, V.W, s):
                v = (cx / V.W) * 0.65 + rnd.random() * 0.35
                if v < c * 1.05:
                    col = V.WHITE if ((cx // s) + (cy // s)) % 2 == 0 else (8, 8, 12)
                    V.rect(d, cx, cy, cx + s - 1, cy + s - 1, col)
        return im

    def frame(self, now) -> Image.Image:
        tl = self.tl
        seg = None
        if now < tl["intro"][1]:
            im = self.intro(now)
        elif now >= tl["outro"][0]:
            im = self.outro(now)
        else:
            seg = self.segment(now)
            shot = self.shot(seg, now)
            im = {"wide": self.wide, "close": self.close, "full": self.full}[shot](seg, now)
            if shot != "full":
                V.bugs(im, now, self.s["episode"])
            lt = seg.get("lower_third")
            if lt and shot in ("close", "wide"):
                t0 = self.at(seg, seg.get("lower_third_at", 0))
                if t0 <= now < t0 + 5:
                    V.lower_third(im, lt["title"], lt["sub"], now - t0)
        im = self.wipe(im, now)
        big = im.resize((OUT_W, OUT_H), Image.NEAREST)
        if seg:
            self.subtitle(big, seg, now)
        return big

    def subtitle(self, big, seg, now):
        for s in seg["sentences"]:
            if s["start"] - 0.05 <= now <= s["end"] + 0.15:
                lines = textwrap.wrap(s["text"], 60)[:2]
                d = ImageDraw.Draw(big, "RGBA")
                lh = 38
                y = OUT_H - 16 - lh * len(lines)
                for i, line in enumerate(lines):
                    w = d.textlength(line, font=SUB_FONT)
                    x = (OUT_W - w) / 2
                    d.rectangle((x - 14, y + i * lh - 2, x + w + 14, y + i * lh + lh - 4), fill=(0, 0, 0, 185))
                    d.text((x, y + i * lh - 6), line, font=SUB_FONT, fill=(255, 255, 255, 255))
                return


def render(script_path, build_dir, out_path, only=None):
    script = json.loads(Path(script_path).read_text())
    tl = json.loads((Path(build_dir) / "timeline.json").read_text())
    ep = Episode(script, tl)
    if only:  # still frames for checking
        for t in only:
            ep.frame(t).save(f"{build_dir}/still_{t:06.2f}.png")
        return
    n = int(tl["duration"] * FPS)
    ff = subprocess.Popen([
        "ffmpeg", "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{OUT_W}x{OUT_H}",
        "-r", str(FPS), "-i", "-", "-i", str(Path(build_dir) / "mix.wav"),
        "-c:v", "libx264", "-preset", "veryfast", "-crf", "18", "-pix_fmt", "yuv420p", "-tune", "animation",
        "-af", "loudnorm=I=-14:TP=-1.5:LRA=11", "-ar", "48000", "-c:a", "aac", "-b:a", "160k", "-shortest", "-movflags", "+faststart", out_path], stdin=subprocess.PIPE)
    for i in range(n):
        ff.stdin.write(ep.frame(i / FPS).tobytes())
        if i % 240 == 0:
            print(f"  frame {i}/{n}", flush=True)
    ff.stdin.close()
    ff.wait()


if __name__ == "__main__":
    if len(sys.argv) > 4:
        render(sys.argv[1], sys.argv[2], None, only=[float(x) for x in sys.argv[4].split(",")])
    else:
        render(sys.argv[1], sys.argv[2], sys.argv[3])
