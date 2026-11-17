"""Drive the three.js show in headless Chromium and capture frames deterministically.
Needs the server: python3 show-3d/serve.py

    python show-3d/capture.py stills "8.0,22.0,46.0" episodes/<date>/stills/s --episode episodes/<date> [--timeline build/preview_timeline.json]
    python show-3d/capture.py video episodes/<date>/build/video_only.mp4 24 0 999 --episode episodes/<date> [--timeline build/timeline.json]
Without --episode it renders the pilot in show-3d/show/data/.
"""
import argparse
import asyncio
import platform
import subprocess
import time
from pathlib import Path
from urllib.parse import urlencode

from playwright.async_api import async_playwright

BASE = "http://127.0.0.1:8765/show-3d/show/index.html"
# Apple Silicon / real GPUs: hardware WebGL. Linux servers without a GPU: software WebGL (slow, ~1.9 s/frame).
ARGS = ["--hide-scrollbars", "--ignore-gpu-blocklist"] + (
    [] if platform.system() == "Darwin" else ["--no-sandbox", "--use-gl=angle", "--use-angle=swiftshader", "--enable-unsafe-swiftshader"])


def url(episode, timeline):
    q = {}
    if episode:
        q["episode"] = "/" + str(Path(episode)).strip("/")
    if timeline:
        q["timeline"] = timeline
    return BASE + ("?" + urlencode(q) if q else "")


async def open_page(p, page_url):
    b = await p.chromium.launch(args=ARGS)
    pg = await b.new_page(viewport={"width": 1280, "height": 720})
    errors = []
    pg.on("pageerror", lambda e: errors.append(str(e)))
    pg.on("console", lambda m: errors.append(m.text) if m.type == "error" else None)
    await pg.goto(page_url)
    try:
        await pg.wait_for_function("window.ready===true", timeout=120000)
    except Exception:
        raise SystemExit("page did not load:\n  " + "\n  ".join(errors or ["(no errors reported)"]))
    return b, pg


async def stills(times, prefix, page_url):
    Path(prefix).parent.mkdir(parents=True, exist_ok=True)
    async with async_playwright() as p:
        b, pg = await open_page(p, page_url)
        for t in times:
            shot = await pg.evaluate(f"window.renderAt({t})")
            await pg.screenshot(path=f"{prefix}_{t:06.2f}.jpg", type="jpeg", quality=90)
            print(f"{t:7.2f}  {shot}", flush=True)
        await b.close()


async def video(out, fps, start, end, page_url):
    Path(out).parent.mkdir(parents=True, exist_ok=True)
    async with async_playwright() as p:
        b, pg = await open_page(p, page_url)
        end = min(end, await pg.evaluate("window.DURATION"))
        n0, n1 = int(start * fps), int(end * fps)
        ff = subprocess.Popen(["ffmpeg", "-y", "-loglevel", "error", "-f", "image2pipe", "-c:v", "mjpeg", "-r", str(fps), "-i", "-",
                               "-c:v", "libx264", "-preset", "veryfast", "-crf", "17", "-pix_fmt", "yuv420p", out], stdin=subprocess.PIPE)
        t0 = time.time()
        for i in range(n0, n1):
            for attempt in range(4):                 # a sleeping/frozen browser must not kill a 90-minute render
                try:
                    await pg.evaluate(f"window.renderAt({i / fps})")
                    shot = await pg.screenshot(type="jpeg", quality=93, timeout=60000)
                    break
                except Exception as ex:
                    print(f"frame {i}: retry {attempt + 1} after {type(ex).__name__}", flush=True)
                    if attempt >= 1:                 # reopen the browser on the second failure
                        try:
                            await b.close()
                        except Exception:
                            pass
                        b, pg = await open_page(p, page_url)
                    await asyncio.sleep(2)
            else:
                raise SystemExit(f"frame {i} failed 4 times; resume with start={i / fps:.3f}")
            ff.stdin.write(shot)
            if (i - n0) % 48 == 0:
                el = time.time() - t0; done = i - n0 + 1
                print(f"frame {i}/{n1}  {el / done:.2f}s/frame  eta {(n1 - i) * el / done / 60:.1f} min", flush=True)
        ff.stdin.close(); ff.wait(); await b.close()


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("mode", choices=["stills", "video"])
    ap.add_argument("args", nargs="+")
    ap.add_argument("--episode")
    ap.add_argument("--timeline")
    a = ap.parse_args()
    u = url(a.episode, a.timeline)
    if a.mode == "stills":
        asyncio.run(stills([float(x) for x in a.args[0].split(",")], a.args[1], u))
    else:
        out, fps, start, end = a.args
        asyncio.run(video(out, int(fps), float(start), float(end), u))
