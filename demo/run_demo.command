#!/bin/bash
set -euo pipefail
cd "$(dirname "$0")/.."
printf 'ASTRAL local integration preview — synthetic signals, real pipeline code.\n'
if [ ! -x .venv/bin/python ]; then
  python3 -m venv .venv
fi
if ! .venv/bin/python -c 'import numpy, scipy' >/dev/null 2>&1; then
  printf 'Installing runtime packages once; this initial setup requires network access.\n'
  .venv/bin/python -m pip install -r demo/requirements-demo.txt
fi
if .venv/bin/python - <<'PY_CHECK'
import json, urllib.request, sys
try:
    with urllib.request.urlopen('http://127.0.0.1:8765/api/health', timeout=1) as response:
        data = json.load(response)
    sys.exit(0 if data.get('status') == 'ready' and data.get('data_origin') == 'synthetic' else 1)
except Exception:
    sys.exit(1)
PY_CHECK
then
  open 'http://127.0.0.1:8765/astral-prototype/'
  exit 0
fi
exec .venv/bin/python -m backend.demo_server --open-browser
