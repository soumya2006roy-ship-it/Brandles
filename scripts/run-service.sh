#!/usr/bin/env bash
set -Eeuo pipefail
ROOT="$(cd -- "$(dirname -- "$0")/.." && pwd)"
service="${1:?service required}"
mode="${2:-dev}"
case "$service" in
  api)
    cd "$ROOT/api"
    if [[ "$mode" == prod ]]; then .venv/bin/python -m uvicorn app.main:app --host 127.0.0.1 --port 8000; else .venv/bin/python -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000; fi
    ;;
  worker) cd "$ROOT/api"; .venv/bin/python -m app.worker ;;
  web)
    cd "$ROOT"
    if [[ "$mode" == prod ]]; then npm run start; else npm run dev -- --hostname 127.0.0.1; fi
    ;;
  *) echo "Unknown service: $service" >&2; exit 2 ;;
esac
