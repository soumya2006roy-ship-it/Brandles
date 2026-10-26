#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd -- "$(dirname -- "$0")" && pwd)"
stop_tree() {
  local parent="$1" child
  while IFS= read -r child; do [[ -n "$child" ]] && stop_tree "$child"; done < <(pgrep -P "$parent" 2>/dev/null || true)
  kill -TERM "$parent" 2>/dev/null || true
}
for service in web worker api; do
  pid_file="$ROOT/logs/$service.pid"
  [[ -f "$pid_file" ]] || continue
  pid=$(cat "$pid_file")
  if [[ "$pid" =~ ^[0-9]+$ ]] && kill -0 "$pid" 2>/dev/null; then
    stop_tree "$pid"
    for _ in {1..20}; do kill -0 "$pid" 2>/dev/null || break; sleep 0.25; done
    kill -KILL "$pid" 2>/dev/null || true
  fi
  rm -f -- "$pid_file"
done
if [[ "${1:-}" == --containers ]]; then (cd "$ROOT" && docker compose stop db redis minio minio-init mailpit); fi
echo 'BrandLens web, API and worker processes stopped.'
