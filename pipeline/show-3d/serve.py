"""Static server for the 3D show, rooted at the repo so the page can read episodes/ and show-catalog/.

    python3 show-3d/serve.py      # http://127.0.0.1:8765/show-3d/show/index.html?episode=/episodes/<date>
Local only (127.0.0.1).
"""
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

if __name__ == "__main__":
    ThreadingHTTPServer(("127.0.0.1", 8765), partial(SimpleHTTPRequestHandler, directory=str(ROOT))).serve_forever()
