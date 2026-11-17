"""Editor notes (episodes/<date>/editor_notes.json) -> episode script JSON, written through the API.
In the Claude Code newsroom the rt-writer skill does this job; this file is the API route
(for GitHub Actions or a machine with an API key).

Length: every episode is at most 10:00 (show-catalog/runtime.py). The draft gets a word budget; if the
estimate still runs over 9:30, the writer gets one instruction: cut, in a fixed order, and resubmit.
Characters come from bible/*.md. Byte's anecdotes come ONLY from an anecdotes file produced by the
anecdote-finder agent (.claude/agents/anecdote-finder.md); without one, Byte has no history lines.

    python script_writer.py episodes/<date>/editor_notes.json episodes/<date>/script.json [minutes] [anecdotes.json]
"""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path

import anthropic

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "show-catalog"))
from validate import CAST, describe, validate  # noqa: E402  (the one list of allowed shots + graphics)
import runtime  # noqa: E402  (10-minute limit + estimate)

BIBLE = Path(__file__).resolve().parent.parent / "bible"
def _bible() -> str:
    return "\n\n".join((BIBLE / f).read_text() for f in ("tone.md", "pixie.md", "byte.md"))

MODEL = os.getenv("RT_EDITOR_MODEL", "claude-sonnet-5-5")

PROMPT = """You are the head writer of RACING TIMES, a weekly motorsport news show. Pixie presents from the
studio; Byte reports from the grid. Turn this week's editor notes into a broadcast script in their voices.

Rules
- Spoken English: short sentences, contractions, numbers written as words ("fourteen point six").
- Facts ONLY from each story's "facts" in the editor notes (never from "unverified"). No new claims. No quotes longer than 15 words.
- Every sentence is an object {{"text", "kind"}} with kind fact | opinion | anecdote | link (see the bible).
  Opinions must sound like opinions and contain no new facts.
- Anecdotes and "first since / last time" lines: ONLY from the ANECDOTES list below, worded no stronger
  than its supported_wording, with "source" set to its source_url. If the list is empty, write none.
- Give Byte one or two segments of his own ("speaker": "byte"), each pairing facts with his opinion and,
  where an anecdote exists, his history. Pixie throws to him and takes it back (banter lines may set
  "speaker" per sentence).
- Running order: cold open hook → headlines → lead story → other stories by importance → briefs
  as a rapid-fire round → week ahead → sign-off. HARD LIMIT: about {words} spoken words in total
  (the episode may not run past ten minutes). Put the most important stories first.
- Each segment picks one graphic (and optionally graphic_b with graphic_b_at) and its shots ONLY from
  the catalog below. Respect every max length; use only listed fields and team codes.
- Use "full" when a table/card needs reading, "close" for emotional beats and the sign-off.
  Set "point": true when Pixie introduces the wall graphic on a wide shot.
- Add "say" for names TTS may mangle (e.g. "Jarama" -> "Harama", "GEN4" -> "Gen Four").

CHARACTERS AND TONE
{bible}

CATALOG
{catalog}

Return the script via the tool.

ANECDOTES (verified by the anecdote-finder; the only history you may use):
{anecdotes}

EDITOR NOTES:
{edition}"""

SCHEMA = {
    "type": "object",
    "properties": {
        "segments": {"type": "array", "items": {"type": "object", "properties": {
            "id": {"type": "string"}, "speaker": {"type": "string", "enum": list(CAST)},
            "graphic": {"type": "object"}, "graphic_b": {"type": "object"}, "graphic_b_at": {"type": "number"},
            "shots": {"type": "array"}, "point": {"type": "boolean"},
            "lower_third": {"type": "object"}, "lower_third_at": {"type": "number"},
            "sentences": {"type": "array"}},
            "required": ["id", "graphic", "shots", "sentences"]}},
        "credits": {"type": "array", "items": {"type": "string"}}},
    "required": ["segments", "credits"],
}


def _ask(client, messages) -> dict:
    resp = client.messages.create(
        model=MODEL, max_tokens=16000,
        tools=[{"name": "submit_script", "description": "Return the episode script.", "input_schema": SCHEMA}],
        tool_choice={"type": "tool", "name": "submit_script"}, messages=messages)
    block = next(b for b in resp.content if b.type == "tool_use")
    return block, resp


def write_script(edition: dict, minutes: float = 10, anecdotes: list | None = None, max_fixes: int = 3) -> dict:
    """Draft -> validate -> trim to time. Each round sends back either catalog errors or a cut instruction."""
    client = anthropic.Anthropic()
    target = min(minutes * 60, runtime.LIMIT_S) - (runtime.LIMIT_S - runtime.TARGET_S)
    messages = [{"role": "user", "content": PROMPT.format(
        words=runtime.draft_words(target), catalog=describe(), bible=_bible(),
        anecdotes=json.dumps(anecdotes or [], ensure_ascii=False, indent=1), edition=json.dumps(edition, ensure_ascii=False))}]
    for attempt in range(max_fixes + 1):
        block, resp = _ask(client, messages)
        script = {"show": "Racing Times", "episode": edition["episode"], "date_display": edition["date_display"],
                  "presenter": {"name": "PIXIE", "role": "PRESENTER", "voice": CAST["pixie"]["voice"], "speed": CAST["pixie"]["speed"]},
                  "cast": {k: {"voice": v["voice"], "speed": v["speed"]} for k, v in CAST.items()}, **block.input}
        errs, _ = validate(script, strict=True)
        est = runtime.estimate(script)
        if errs:
            feedback = "Fix these and resubmit the whole script:\n" + "\n".join(errs)
        elif est["total"] > target:
            over = est["total"] - target
            cut = int(over / 60 * runtime.WPM) + 10
            longest = ", ".join(f"{i} {t:.0f}s" for i, t in sorted(est["segments"], key=lambda x: -x[1])[:5])
            feedback = (f"Too long: about {runtime.fmt(est['total'])} against a limit of {runtime.fmt(target)}. "
                        f"Remove about {cut} spoken words, then resubmit the whole script.\n"
                        f"Longest segments: {longest}.\n{runtime.CUT_ORDER}")
        else:
            print(f"script fits: about {runtime.fmt(est['total'])} (limit {runtime.fmt(runtime.LIMIT_S)})")
            return script
        if attempt == max_fixes:
            raise ValueError("script still not ready after the last round:\n" + feedback)
        messages += [{"role": "assistant", "content": resp.content},
                     {"role": "user", "content": [{"type": "tool_result", "tool_use_id": block.id, "is_error": True,
                      "content": feedback}]}]


if __name__ == "__main__":
    ed = json.loads(Path(sys.argv[1]).read_text())
    anec = json.loads(Path(sys.argv[4]).read_text()) if len(sys.argv) > 4 else []
    out = write_script(ed, float(sys.argv[3]) if len(sys.argv) > 3 else 10, anec)
    Path(sys.argv[2]).write_text(json.dumps(out, indent=1, ensure_ascii=False))
    print(f"wrote {sys.argv[2]}: {sum(len(s['sentences']) for s in out['segments'])} sentences")
