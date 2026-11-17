"""PostToolUse hook: whenever Claude writes or edits a stage file in episodes/, check it at once.
A failed check exits 2 so the problems go straight back to Claude to fix."""
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
NAMES = {"wire.json", "editor_notes.json", "anecdotes.json", "photos.json", "script.json", "factcheck.json"}

try:
    event = json.load(sys.stdin)
except json.JSONDecodeError:
    sys.exit(0)
path = Path((event.get("tool_input") or {}).get("file_path", ""))
if path.name not in NAMES or "episodes" not in path.parts or not path.exists():
    sys.exit(0)
r = subprocess.run([sys.executable, str(ROOT / "newsroom" / "contracts.py"), str(path)], capture_output=True, text=True)
if r.returncode:
    print(f"{path.name} does not pass its check:\n{r.stdout.strip()}", file=sys.stderr)
    sys.exit(2)
