import json
import urllib.request

with urllib.request.urlopen("http://icecast:8000/status-json.xsl", timeout=5) as response:
    sources = json.load(response)["icestats"].get("source", [])
if isinstance(sources, dict):
    sources = [sources]
raise SystemExit(0 if any(s.get("listenurl", "").endswith("/radio.mp3") for s in sources) else 1)
