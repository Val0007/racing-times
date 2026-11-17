# Racing Times: the show

Turns the weekly Racing Times edition into a broadcast with Pixie, a pixel-art presenter.

```
edition.json ──► script_writer.py (Claude) ──► audio.py ──► render.py ──► episode.mp4
                  broadcast script + cues      voice        studio, Pixie, graphics,
                                               lip sync     subtitles, transitions
                                               chiptune     loudness-normalised
```

## Setup (once)

```bash
pip install kokoro-onnx soundfile pillow numpy anthropic httpx
mkdir -p vendor && cd vendor
curl -LO https://github.com/thewh1teagle/kokoro-onnx/releases/download/model-files-v1.0/kokoro-v1.0.int8.onnx && mv kokoro-v1.0.int8.onnx kokoro.onnx
curl -LO https://github.com/thewh1teagle/kokoro-onnx/releases/download/model-files-v1.0/voices-v1.0.bin && mv voices-v1.0.bin voices.bin
curl -LO https://github.com/DanielSWolf/rhubarb-lip-sync/releases/download/v1.13.0/Rhubarb-Lip-Sync-1.13.0-Linux.zip && unzip Rhubarb-Lip-Sync-1.13.0-Linux.zip
```
ffmpeg must be installed. Pixel fonts (Silkscreen, Press Start 2P, VT323; all SIL Open Font License) are in `assets/`.

## Make an episode

```bash
export ANTHROPIC_API_KEY=...
python make_episode.py ../newspaper/editions/2026-11-16.json --minutes 10 --out ep01.mp4
```
Or edit the generated script by hand and re-run with `--script episode_01.json`.

## Premium voice

The default voice is Kokoro (free, runs locally). For a top-tier voice:
```bash
export RT_VOICE=elevenlabs ELEVENLABS_API_KEY=... ELEVENLABS_VOICE_ID=...
```
Lip sync is generated from whatever audio you use, so nothing else changes.

## Notes
- Times: the first run downloads nothing more. A 10-minute episode renders in about a minute; voice generation takes a few minutes on CPU.
- Graphics kinds live in `visuals.graphic()`. Add a new card type there and list it in `script_writer.GRAPHIC_KINDS`.
- Keep footage out: F1 enforces video rights. Use cards, Pixie, and credited team-media photos only.
