"""Cinematic score for the 3D show: riser + impact + brass-style chord for the open,
a low pulsing bed under the voice (ducked), whooshes on every cut, and a big outro chord."""
import json
import sys

import numpy as np
import soundfile as sf
from scipy.signal import butter, sosfilt, fftconvolve

SR = 48000
tl = json.load(open(sys.argv[1]))
narr, nsr = sf.read(sys.argv[2])
if nsr != SR:  # resample narration 24k -> 48k
    x = np.arange(len(narr)) / nsr
    narr = np.interp(np.arange(int(len(narr) * SR / nsr)) / SR, x, narr)
N = int(tl["duration"] * SR) + SR
out = np.zeros((N, 2))
rng = np.random.default_rng(3)
f = lambda n: 440 * 2 ** ((n - 69) / 12)


def lp(x, hz, order=2):
    return sosfilt(butter(order, hz / (SR / 2), "low", output="sos"), x)


def hp(x, hz, order=2):
    return sosfilt(butter(order, hz / (SR / 2), "high", output="sos"), x)


def env(n, a, r, sustain=1.0):
    e = np.ones(n) * sustain
    na, nr = int(a * SR), int(r * SR)
    e[:na] = np.linspace(0, 1, na)
    if nr:
        e[-nr:] *= np.linspace(1, 0, nr) ** 2
    return e


def saw_stack(notes, dur, detune=0.12, voices=5):
    t = np.arange(int(dur * SR)) / SR
    L = np.zeros_like(t); Rr = np.zeros_like(t)
    for n in notes:
        for v in range(voices):
            d = (v - voices // 2) * detune
            ph = rng.uniform(0, 1)
            w = 2 * ((t * f(n + d / 10) + ph) % 1) - 1
            pan = (v / (voices - 1))
            L += w * (1 - pan); Rr += w * pan
    return np.stack([L, Rr], 1) / (len(notes) * voices)


def add(sig, at, gain=1.0):
    i = int(at * SR)
    if sig.ndim == 1:
        sig = np.stack([sig, sig], 1)
    j = min(N, i + len(sig))
    out[i:j] += sig[: j - i] * gain


def reverb(x, seconds=2.8, mix=0.28):
    n = int(seconds * SR)
    ir = rng.standard_normal((n, 2)) * np.exp(-np.linspace(0, 7, n))[:, None]
    ir[:, 0] = lp(ir[:, 0], 6000); ir[:, 1] = lp(ir[:, 1], 6000)
    wet = np.stack([fftconvolve(x[:, c], ir[:, c])[: len(x)] for c in range(2)], 1)
    wet /= np.abs(wet).max() + 1e-9
    return x * (1 - mix) + wet * mix * np.abs(x).max()


def impact(dur=2.5):
    t = np.arange(int(dur * SR)) / SR
    sub = np.sin(2 * np.pi * (38 + 60 * np.exp(-t * 18)) * t) * np.exp(-t * 2.2)
    noise = lp(rng.standard_normal(len(t)), 900) * np.exp(-t * 9) * 0.6
    return (sub + noise) * 0.9


def riser(dur):
    n = int(dur * SR); t = np.arange(n) / SR
    x = rng.standard_normal(n)
    out_ = np.zeros(n)
    for k in range(8):  # stepped sweeping band
        s, e = int(k * n / 8), int((k + 1) * n / 8)
        out_[s:e] = hp(lp(x[s:e], 400 + 5000 * (k / 7) ** 2), 200)
    return out_ * (t / dur) ** 2.2 * 0.5


def whoosh(dur=0.6):
    n = int(dur * SR); t = np.arange(n) / SR
    x = rng.standard_normal(n)
    half = n // 2
    y = np.concatenate([lp(x[:half], 2500), lp(x[half:], 1200)])
    e = np.sin(np.pi * t / dur) ** 2
    return y * e * 0.35


def chord(notes, dur, a=0.03, r=1.8, bright=2600):
    s = saw_stack(notes, dur)
    for c in range(2):
        s[:, c] = lp(s[:, c], bright, 2)
    return s * env(len(s), a, r)[:, None]


# ── opening ────────────────────────────────────────────────
intro_end = tl["intro"][1]
add(riser(1.1), 0.0, 0.8)
add(impact(), 1.1, 1.0)
open_chord = chord([38, 50, 57, 62, 65, 69], 3.6, a=0.02, r=2.2, bright=3200)   # D minor add
add(open_chord, 1.1, 0.75)
add(chord([46, 58, 62, 65, 70], 2.2, a=0.4, r=1.4, bright=2200), 3.0, 0.45)       # Bb lift into the show

# ── bed under narration ───────────────────────────────────
bed_start, bed_end = intro_end - 0.2, tl["outro"][0] + 0.5
prog = [[38, 50, 57], [46, 53, 58], [41, 53, 60], [36, 48, 55]]  # Dm Bb F C
bar = 2.4
bed = np.zeros((int((bed_end - bed_start) * SR), 2))
for b in range(int(np.ceil((bed_end - bed_start) / bar))):
    notes = prog[b % 4]
    pad = chord(notes[1:], bar + 0.6, a=0.6, r=0.8, bright=1100)
    i = int(b * bar * SR)
    j = min(len(bed), i + len(pad)); bed[i:j] += pad[: j - i] * 0.55
    # pulsing bass eighths
    for k in range(8):
        t = np.arange(int(0.28 * SR)) / SR
        note = notes[0] - 12 + (12 if k % 4 == 3 else 0)
        w = (2 * ((t * f(note)) % 1) - 1)
        w = lp(w, 380) * np.exp(-t * 9)
        ii = i + int(k * bar / 8 * SR); jj = min(len(bed), ii + len(w))
        if ii < len(bed):
            bed[ii:jj] += np.stack([w, w], 1)[: jj - ii] * 0.5
    # soft ticking hat
    for k in range(16):
        t = np.arange(int(0.05 * SR)) / SR
        h = hp(rng.standard_normal(len(t)), 7000) * np.exp(-t * 90) * (0.10 if k % 2 else 0.05)
        ii = i + int(k * bar / 16 * SR); jj = min(len(bed), ii + len(h))
        if ii < len(bed):
            bed[ii:jj] += np.stack([h, h * 0.8], 1)[: jj - ii]
fade = np.minimum(1, np.minimum(np.arange(len(bed)) / SR / 1.2, (len(bed) - np.arange(len(bed))) / SR / 1.5))
add(bed * fade[:, None], bed_start, 0.5)

# ── transitions ────────────────────────────────────────────
bounds = [tl["intro"][1]] + [s["start"] for s in tl["segments"][1:]] + [tl["outro"][0]]
for b in bounds[1:]:
    add(whoosh(), b - 0.32, 0.9)
    add(impact(1.2) * 0.25, b, 1.0)

# ── outro ──────────────────────────────────────────────────
o = tl["outro"][0]
add(impact(), o, 0.9)
add(chord([38, 50, 57, 62, 66, 69], 5.5, a=0.02, r=3.5, bright=3000), o, 0.7)       # D major resolution

out = reverb(out, 2.6, 0.25)

# ── duck music under the voice, then mix ──────────────────
v = np.zeros(N); v[: len(narr)] = narr[:N]
envv = np.sqrt(np.convolve(v ** 2, np.ones(int(0.25 * SR)) / int(0.25 * SR), mode="same"))
duck = 1 - 0.55 * np.clip(envv / (envv.max() * 0.25 + 1e-9), 0, 1)
duck = np.convolve(duck, np.ones(int(0.15 * SR)) / int(0.15 * SR), mode="same")
music = out * duck[:, None]
voice = np.stack([v, v], 1)
voice = voice + reverb(voice, 0.9, 0.08) * 0.0  # dry broadcast voice
mix = voice * 1.0 + music * 0.55
mix /= np.abs(mix).max() / 0.95
sf.write(sys.argv[3], mix[: int(tl["duration"] * SR)], SR)
print("score written", sys.argv[3])
