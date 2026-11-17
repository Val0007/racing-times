"""ElevenLabs for Racing Times: design the two original voices, and speak lines with Eleven v3.

    python show-pixel/eleven.py design            # 3 previews each for Pixie and Byte -> show-pixel/voices/previews/
    python show-pixel/eleven.py save pixie 2      # keep Pixie preview #2 as a permanent voice -> voices/voices.json
    python show-pixel/eleven.py save byte 1

The API key is read from ELEVENLABS_API_KEY (environment or the project's .env file); never commit it.
Voices are designed from text descriptions (Voice Design), not cloned from anyone.
"""
from __future__ import annotations

import base64
import hashlib
import json
import os
import sys
from pathlib import Path

import httpx
import numpy as np

ROOT = Path(__file__).resolve().parent.parent
VOICES = Path(__file__).resolve().parent / "voices"
API = "https://api.elevenlabs.io"
MODEL = os.getenv("RT_EL_MODEL", "eleven_v3")

DESIGN = {
    "pixie": "A real British woman in her late twenties talking to a friend about motor racing: natural, relaxed and conversational, not an announcer. Slightly breathy, warm, a little husky, with small imperfections, natural pauses and laughter in the voice. Light London accent. Sounds like a person, not a narrator.",
    "pixie_v1": "A British woman in her late twenties presenting a fast-paced motorsport news show. Warm, bright and quick-witted, "
             "with a dry sense of humour and lots of natural intonation: she lifts on punchlines, softens for warm moments and "
             "turns serious when needed. Clear, polished studio delivery, standard southern English accent.",
    "byte": "A young British man in his twenties, an excitable paddock reporter standing on a race track. Bursting with energy, "
            "fast and animated, a huge racing fan who gets carried away, then catches himself. Expressive, playful, slightly raspy, "
            "very wide pitch range, outdoor live-reporting feel.",
}
SAMPLE = ("Good evening and welcome to Racing Times! Two weeks of news to catch up on, a brand new world champion, "
          "and honestly? The fight for second is still wide open. Let's go racing, shall we?")
SAMPLE_BYTE = ("Byte here, live from the grid, and the air smells like tyre warmers and destiny! Twenty-first to second? "
               "I nearly dropped my mic. Now THAT takes me back... back to you, before they tow me away!")

# delivery -> Eleven v3 audio tag + voice settings (lower stability = wider emotional range)
TAGS = {"neutral": "", "warm": "[warmly]", "excited": "[excited]", "serious": "[seriously]",
        "deadpan": "[deadpan]", "question": "[curious]", "aside": "[mischievously]"}
STABILITY = {"neutral": 0.5, "warm": 0.45, "excited": 0.3, "serious": 0.55, "deadpan": 0.5, "question": 0.4, "aside": 0.4}


def key() -> str:
    k = os.getenv("ELEVENLABS_API_KEY")
    env = ROOT / ".env"
    if not k and env.exists():
        for line in env.read_text().splitlines():
            if line.strip().startswith("ELEVENLABS_API_KEY="):
                k = line.split("=", 1)[1].strip().strip('"').strip("'")
    if not k:
        sys.exit("ELEVENLABS_API_KEY not set: add it to the project's .env file")
    return k


def voice_ids() -> dict:
    f = VOICES / "voices.json"
    return json.loads(f.read_text()) if f.exists() else {}


def design() -> None:
    out = VOICES / "previews"
    out.mkdir(parents=True, exist_ok=True)
    meta = {}
    for name, desc in DESIGN.items():
        r = httpx.post(f"{API}/v1/text-to-voice/design", params={"output_format": "mp3_44100_128"},
                       headers={"xi-api-key": key()}, timeout=180,
                       json={"voice_description": desc, "model_id": "eleven_ttv_v3",
                             "text": SAMPLE_BYTE if name == "byte" else SAMPLE})
        r.raise_for_status()
        previews = r.json()["previews"][:3]
        meta[name] = []
        for i, p in enumerate(previews, 1):
            f = out / f"{name}_{i}.mp3"
            f.write_bytes(base64.b64decode(p["audio_base_64"]))
            meta[name].append({"n": i, "generated_voice_id": p["generated_voice_id"], "file": f.name})
            print(f"{name} preview {i}: {f}")
    (out / "previews.json").write_text(json.dumps(meta, indent=1))


def save(name: str, n: int) -> None:
    meta = json.loads((VOICES / "previews" / "previews.json").read_text())
    p = [x for x in meta[name] if x["n"] == n][0]
    r = httpx.post(f"{API}/v1/text-to-voice", headers={"xi-api-key": key()}, timeout=60,
                   json={"voice_name": f"Racing Times - {name.title()}", "voice_description": DESIGN[name],
                         "generated_voice_id": p["generated_voice_id"]})
    r.raise_for_status()
    ids = voice_ids()
    ids[name] = r.json()["voice_id"]
    (VOICES / "voices.json").write_text(json.dumps(ids, indent=1))
    print(f"{name}: voice {ids[name]} saved")


def speak(text: str, speaker: str, delivery: str, speed: float = 1.0, previous_text: str | None = None,
          cache_dir: Path | None = None) -> np.ndarray:
    """One line with Eleven v3, 24 kHz float32. Cached on disk by content, so re-runs cost nothing."""
    vid = voice_ids().get(speaker)
    if not vid:
        sys.exit(f"no ElevenLabs voice for {speaker}: run `python show-pixel/eleven.py design` and `save`")
    tag = TAGS.get(delivery or "neutral", "")
    body = {"text": f"{tag} {text}".strip(), "model_id": MODEL,
            "voice_settings": {"stability": STABILITY.get(delivery, 0.5), "similarity_boost": 0.75,
                               "speed": float(min(1.2, max(0.8, speed))), "use_speaker_boost": True}}
    if previous_text and not MODEL.startswith("eleven_v3"):   # v3 doesn't accept request stitching yet
        body["previous_text"] = previous_text
    h = hashlib.sha256(json.dumps([vid, body], sort_keys=True).encode()).hexdigest()[:20]
    cache = (cache_dir or ROOT / "data" / "tts_cache") / f"{h}.pcm"
    if not cache.exists():
        r = httpx.post(f"{API}/v1/text-to-speech/{vid}", params={"output_format": "pcm_24000"},
                       headers={"xi-api-key": key()}, json=body, timeout=180)
        r.raise_for_status()
        cache.parent.mkdir(parents=True, exist_ok=True)
        cache.write_bytes(r.content)
    a = np.frombuffer(cache.read_bytes(), dtype=np.int16).astype(np.float32) / 32768
    idx = np.where(np.abs(a) > 0.01)[0]                     # trim silence at both ends
    return a[max(0, idx[0] - 240): idx[-1] + 1200] if len(idx) else a


# One take per run of lines from the same speaker: the voice stays consistent and flows like real speech.
# Emotion comes from the inline tags; stability is steady and the seed fixed per character.
SEED = {"pixie": 4242, "byte": 7777}
RUN_STABILITY = 0.5


def speak_run(lines: list[tuple[str, str]], speaker: str, speed: float = 1.0, cache_dir: Path | None = None):
    """lines: [(text, delivery)]. Returns (audio float32 24 kHz, [(start_s, end_s) per line])."""
    vid = voice_ids().get(speaker)
    if not vid:
        sys.exit(f"no ElevenLabs voice for {speaker}: run `python show-pixel/eleven.py design` and `save`")
    parts, spans, pos = [], [], 0
    for text, delivery in lines:
        tag = TAGS.get(delivery or "neutral", "")
        piece = f"{tag} {text}".strip() if tag else text
        lead = len(piece) - len(text)                       # characters of the tag before the spoken text
        if parts:
            pos += 1                                       # the joining space
        spans.append((pos + lead, pos + len(piece)))
        parts.append(piece)
        pos += len(piece)
    full = " ".join(parts)
    body = {"text": full, "model_id": MODEL, "seed": SEED.get(speaker, 1),
            "voice_settings": {"stability": RUN_STABILITY, "similarity_boost": 0.8,
                               "speed": float(min(1.2, max(0.8, speed))), "use_speaker_boost": True}}
    h = hashlib.sha256(json.dumps([vid, body], sort_keys=True).encode()).hexdigest()[:20]
    cache = (cache_dir or ROOT / "data" / "tts_cache") / f"run_{h}.json"
    if not cache.exists():
        r = httpx.post(f"{API}/v1/text-to-speech/{vid}/with-timestamps", params={"output_format": "pcm_24000"},
                       headers={"xi-api-key": key()}, json=body, timeout=300)
        r.raise_for_status()
        cache.parent.mkdir(parents=True, exist_ok=True)
        cache.write_text(r.text)
    j = json.loads(cache.read_text())
    a = np.frombuffer(base64.b64decode(j["audio_base64"]), dtype=np.int16).astype(np.float32) / 32768
    al = j.get("alignment") or j.get("normalized_alignment")
    chars, t0s, t1s = al["characters"], al["character_start_times_seconds"], al["character_end_times_seconds"]
    if "".join(chars) != full:                             # alignment text differs: map by proportion as a fallback
        n = len(chars)
        def at(i, ends=False):
            k = min(n - 1, int(i / max(1, len(full)) * n)); return (t1s if ends else t0s)[k]
    else:
        def at(i, ends=False):
            return (t1s if ends else t0s)[min(i, len(chars) - 1)]
    times = []
    for s0, s1 in spans:
        while s0 < s1 - 1 and full[s0].isspace():
            s0 += 1
        times.append((at(s0), at(s1 - 1, ends=True)))
    # trim silence at the very start/end of the run and shift the times to match
    idx = np.where(np.abs(a) > 0.01)[0]
    if len(idx):
        cut0 = max(0, idx[0] - 240)
        a = a[cut0: idx[-1] + 1200]
        times = [(max(0.0, x - cut0 / 24000), max(0.0, y - cut0 / 24000)) for x, y in times]
    return a, times


if __name__ == "__main__":
    if sys.argv[1] == "design":
        design()
    elif sys.argv[1] == "save":
        save(sys.argv[2], int(sys.argv[3]))
