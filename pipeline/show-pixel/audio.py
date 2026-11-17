"""Voice, timing, lip sync and chiptune music for a Racing Times episode.

voice_backend "kokoro" runs locally (free, open model). Swap in "elevenlabs"
for a premium voice: same interface, one function.
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

import numpy as np
import soundfile as sf

SR = 24000
HERE = Path(__file__).parent
VENDOR = HERE / "vendor"
INTRO_LEN = 4.2
OUTRO_LEN = 6.0
SENT_GAP = 0.22
SEG_GAP = 0.55

_kokoro = None


def _default_voice_backend() -> str:
    """ElevenLabs when it's set up (key in .env + designed voices), otherwise free local Kokoro. RT_VOICE overrides."""
    root = HERE.parent
    env = root / ".env"
    has_key = os.getenv("ELEVENLABS_API_KEY") or (env.exists() and "ELEVENLABS_API_KEY=" in env.read_text()
                                                   and env.read_text().split("ELEVENLABS_API_KEY=", 1)[1].strip()[:3])
    return "elevenlabs" if has_key and (HERE / "voices" / "voices.json").exists() else "kokoro"


os.environ.setdefault("RT_VOICE", _default_voice_backend())

# ── delivery: how a line is spoken ──────────────────────────
# Kokoro has no emotion control, so tone is built around it, line by line:
#   speed   tempo multiplier
#   pitch   semitones (generate at speed/f, then resample by f: pitch moves, timing stays natural)
#   gain    loudness
#   gap     pause after the line (seconds)
#   blend   share of a second voice mixed into the speaker's voice (timbre)
DELIVERY = {
    "neutral":  dict(speed=1.00, pitch=0.0,  gain=1.00, gap=0.24, blend=0.00),
    "warm":     dict(speed=0.92, pitch=-1.0, gain=0.93, gap=0.36, blend=0.25),
    "excited":  dict(speed=1.16, pitch=2.6,  gain=1.12, gap=0.12, blend=0.35),
    "serious":  dict(speed=0.88, pitch=-1.9, gain=0.90, gap=0.52, blend=0.30),
    "deadpan":  dict(speed=0.95, pitch=-1.3, gain=0.94, gap=0.45, blend=0.00),
    "question": dict(speed=1.04, pitch=1.3,  gain=1.00, gap=0.34, blend=0.15),
    "aside":    dict(speed=1.10, pitch=-0.5, gain=0.84, gap=0.20, blend=0.15),
}
# the second voice each character leans towards, per mood (all original Kokoro voices)
BLEND_VOICE = {
    "pixie": {"excited": "bf_lily", "warm": "bf_isabella", "serious": "bf_alice", "question": "bf_lily", "aside": "bf_isabella"},
    "byte":  {"excited": "am_puck", "warm": "bm_george", "serious": "bm_george", "question": "am_puck", "aside": "bm_fable"},
}


def _engine():
    global _kokoro
    if _kokoro is None:
        from kokoro_onnx import Kokoro
        _kokoro = Kokoro(str(VENDOR / "kokoro.onnx"), str(VENDOR / "voices.bin"))
    return _kokoro


_PREV: dict = {}   # last line per speaker, for ElevenLabs continuity


def delivered(text: str, speaker: str, base_voice: str, base_speed: float, delivery: str, idx: int) -> tuple[np.ndarray, float]:
    """Speak one line with its delivery. Returns (audio, pause after it)."""
    d = DELIVERY.get(delivery or "neutral", DELIVERY["neutral"])
    rnd = np.random.default_rng(1000 + idx)                       # small, repeatable variety per line
    pitch = d["pitch"] + rnd.uniform(-0.45, 0.45)
    speed = base_speed * d["speed"] * rnd.uniform(0.97, 1.03)
    if os.getenv("RT_VOICE", "kokoro") == "elevenlabs":
        # Eleven v3 does the acting itself: the delivery becomes an audio tag + voice settings, no pitch tricks
        import eleven
        return eleven.speak(text, speaker, delivery, d["speed"] * (base_speed if speaker != "byte" else 1.04),
                            previous_text=_PREV.get(speaker)), d["gap"]
    k = _engine()
    style = k.get_voice_style(base_voice)
    other = BLEND_VOICE.get(speaker, {}).get(delivery)
    if other and d["blend"] > 0:
        style = (1 - d["blend"]) * style + d["blend"] * k.get_voice_style(other)
    f = 2 ** (pitch / 12)
    a = tts(text, style, speed / f)
    if abs(f - 1) > 1e-3:                                          # resample: raises/lowers pitch and tempo by f
        from scipy.signal import resample_poly
        up, down = 1000, int(round(1000 * f))
        a = resample_poly(a, up, down).astype(np.float32)
    return np.clip(a * d["gain"], -1, 1), d["gap"]


def tts(text: str, voice, speed: float = 1.0, backend: str | None = None) -> np.ndarray:
    backend = backend or os.getenv("RT_VOICE", "kokoro")
    if backend == "elevenlabs":
        import httpx  # premium voice; needs ELEVENLABS_API_KEY and an ElevenLabs voice id
        r = httpx.post(
            f"https://api.elevenlabs.io/v1/text-to-speech/{os.environ['ELEVENLABS_VOICE_ID']}?output_format=pcm_24000",
            headers={"xi-api-key": os.environ["ELEVENLABS_API_KEY"]},
            json={"text": text, "model_id": "eleven_multilingual_v2"}, timeout=120)
        r.raise_for_status()
        return np.frombuffer(r.content, dtype=np.int16).astype(np.float32) / 32768
    samples, sr = _engine().create(text, voice=voice, speed=speed, lang="en-gb")
    assert sr == SR
    # trim leading/trailing silence
    idx = np.where(np.abs(samples) > 0.01)[0]
    return samples[max(0, idx[0] - 200): idx[-1] + 1200] if len(idx) else samples


# ── chiptune ────────────────────────────────────────────────
def _note(n):  # semitones from A4
    return 440.0 * 2 ** (n / 12)


def _square(f, dur, duty=0.5, vol=0.2):
    t = np.arange(int(dur * SR)) / SR
    w = ((t * f) % 1.0 < duty).astype(np.float32) * 2 - 1
    env = np.minimum(1, np.linspace(1.6, 0, len(t)) ** 0.6)
    return w * vol * env


def _tri(f, dur, vol=0.25):
    t = np.arange(int(dur * SR)) / SR
    w = 2 * np.abs(2 * ((t * f) % 1.0) - 1) - 1
    env = np.minimum(1, np.linspace(1.3, 0.3, len(t)))
    return w.astype(np.float32) * vol * env


def _noise(dur, vol=0.08):
    n = int(dur * SR)
    return (np.random.default_rng(1).uniform(-1, 1, n) * np.linspace(1, 0, n) ** 3 * vol).astype(np.float32)


def _seq(notes, step, fn, **kw):
    out = []
    for n in notes:
        out.append(np.zeros(int(step * SR), np.float32) if n is None else fn(_note(n), step, **kw))
    return np.concatenate(out)


def jingle() -> np.ndarray:
    step = 0.13
    mel = [3, 7, 10, 15, None, 15, 14, 15, 19, None, 22, None, 27, None, None, None,
           26, 22, 19, 22, 27, None, None, None, None, None, None, None, None, None, None, None]
    bass = [-21, None, -21, None, -14, None, -14, None, -16, None, -16, None, -9, None, -9, None,
            -11, None, -11, None, -9, None, None, None, None, None, None, None, None, None, None, None]
    a = _seq(mel, step, _square, duty=0.25, vol=0.16)
    b = _seq(bass, step, _tri, vol=0.32)
    hats = np.concatenate([_noise(step, 0.05 if i % 2 else 0.1) for i in range(len(mel))])
    n = min(len(a), len(b), len(hats))
    return a[:n] + b[:n] + hats[:n]


def bed(seconds: float) -> np.ndarray:
    step = 0.25
    prog = [[-21, -9, -5, -2], [-16, -4, 0, 3], [-18, -6, -2, 1], [-14, -2, 2, 5]]
    bar = []
    for chord in prog:
        bass = _seq([chord[0], None, chord[0] + 12, None] * 2, step, _tri, vol=0.22)
        arp = _seq([chord[1], chord[2], chord[3], chord[2]] * 2, step, _square, duty=0.125, vol=0.05)
        bar.append(bass + arp)
    loop = np.concatenate(bar)
    reps = int(np.ceil(seconds * SR / len(loop)))
    return np.tile(loop, reps)[: int(seconds * SR)]


# ── build ───────────────────────────────────────────────────
def build(script_path: str, out_dir: str) -> dict:
    script = json.loads(Path(script_path).read_text())
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    voice, speed = script["presenter"]["voice"], script["presenter"].get("speed", 1.0)
    cast = script.get("cast", {})

    def voice_for(speaker):  # each character has its own voice; unknown speakers fall back to the presenter
        c = cast.get(speaker or "pixie")
        return (c["voice"], c.get("speed", 1.0)) if c else (voice, speed)

    t = INTRO_LEN
    clips, timeline = [], {"intro": [0, INTRO_LEN], "segments": []}
    n = 0
    if os.getenv("RT_VOICE", "kokoro") == "elevenlabs":
        # ElevenLabs: one take per run of consecutive lines by the same speaker (consistent voice, natural flow)
        import eleven
        for seg in script["segments"]:
            s0, sents, run = t, [], []
            rows = []
            for s in seg["sentences"]:
                text, say = (s, s) if isinstance(s, str) else (s["text"], s.get("say", s["text"]))
                speaker = (s.get("speaker") if isinstance(s, dict) else None) or seg.get("speaker", "pixie")
                rows.append((text, say, speaker, (s.get("delivery") if isinstance(s, dict) else None) or "neutral"))
            i = 0
            while i < len(rows):
                j = i
                while j < len(rows) and rows[j][2] == rows[i][2]:
                    j += 1
                spk = rows[i][2]
                a, times = eleven.speak_run([(r[1], r[3]) for r in rows[i:j]], spk, 1.04 if spk == "byte" else 1.0)
                clips.append((t, a))
                for r, (x, y) in zip(rows[i:j], times):
                    sents.append({"text": r[0], "speaker": spk, "delivery": r[3], "start": round(t + x, 3), "end": round(t + y, 3)})
                t += len(a) / SR + 0.3                     # breath between speakers
                i = j
            timeline["segments"].append({**{k: v for k, v in seg.items() if k != "sentences"},
                                         "start": round(s0, 3), "end": round(t, 3), "sentences": sents})
            t += SEG_GAP
    for seg in ([] if os.getenv("RT_VOICE", "kokoro") == "elevenlabs" else script["segments"]):
        s0 = t
        sents = []
        for s in seg["sentences"]:
            text, say = (s, s) if isinstance(s, str) else (s["text"], s.get("say", s["text"]))
            speaker = (s.get("speaker") if isinstance(s, dict) else None) or seg.get("speaker", "pixie")
            delivery = (s.get("delivery") if isinstance(s, dict) else None) or "neutral"
            a, gap = delivered(say, speaker, *voice_for(speaker), delivery, n)
            _PREV[speaker] = say
            n += 1
            clips.append((t, a))
            sents.append({"text": text, "speaker": speaker, "delivery": delivery, "start": round(t, 3), "end": round(t + len(a) / SR, 3)})
            t += len(a) / SR + gap
        timeline["segments"].append({**{k: v for k, v in seg.items() if k != "sentences"},
                                     "start": round(s0, 3), "end": round(t, 3), "sentences": sents})
        t += SEG_GAP
    timeline["outro"] = [round(t, 3), round(t + OUTRO_LEN, 3)]
    total = t + OUTRO_LEN
    timeline["duration"] = round(total, 3)

    narration = np.zeros(int(total * SR) + SR, np.float32)
    for start, a in clips:
        i = int(start * SR)
        narration[i:i + len(a)] += a
    sf.write(out / "narration.wav", narration, SR)

    # lip sync from the real audio (Rhubarb), guided by the script text
    dialog = out / "dialog.txt"
    dialog.write_text("\n".join(s["text"] for seg in timeline["segments"] for s in seg["sentences"]))
    rh_dir = "Rhubarb-Lip-Sync-1.13.0-macOS" if sys.platform == "darwin" else "Rhubarb-Lip-Sync-1.13.0-Linux"
    rh = subprocess.run([str(VENDOR / rh_dir / "rhubarb"), "-f", "json",
                         "--extendedShapes", "GHX", "-d", str(dialog), str(out / "narration.wav")],
                        capture_output=True, text=True, check=True)
    timeline["mouth"] = [[c["start"], c["end"], c["value"]] for c in json.loads(rh.stdout)["mouthCues"]]

    # music: jingle in, quiet bed under the voice, jingle out
    music = np.zeros_like(narration)
    j = jingle()
    music[: len(j)] += j * 0.9
    b = bed(total - INTRO_LEN)
    fade = np.minimum(1, np.minimum(np.arange(len(b)) / SR / 1.5, (len(b) - np.arange(len(b))) / SR / 1.5))
    i = int((INTRO_LEN - 0.3) * SR)
    music[i:i + len(b)] += b * 0.18 * fade
    o = int(timeline["outro"][0] * SR)
    music[o:o + len(j)] += j[: len(music) - o] * 0.8
    mix = narration * 1.0 + music
    mix /= max(1.0, np.abs(mix).max() / 0.95)
    sf.write(out / "mix.wav", mix[: int(total * SR)], SR)

    (out / "timeline.json").write_text(json.dumps(timeline, indent=1))
    return timeline


if __name__ == "__main__":
    tl = build(sys.argv[1], sys.argv[2])
    print(f"duration {tl['duration']:.1f}s, {len(tl['mouth'])} mouth cues")
