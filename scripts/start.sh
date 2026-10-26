#!/usr/bin/env bash
set -Eeuo pipefail
cd -- "$(dirname -- "$0")/.."
ROOT="$(pwd)"
cd "$ROOT"
MODE="${1:-dev}"
[[ "$MODE" == "dev" || "$MODE" == "prod" ]] || { echo 'Usage: ./start.sh [dev|prod]' >&2; exit 2; }
ROOT="$PWD"
LOG_DIR="$ROOT/logs"
mkdir -p "$LOG_DIR"
DATA_STARTED=0
cleanup_on_error() {
  status=$?
  if (( status != 0 )); then
    echo "Launcher failed (exit $status); stopping processes started by this run." >&2
    if (( DATA_STARTED == 1 )); then ./stop.sh --containers || true; fi
  fi
}
trap cleanup_on_error EXIT
fail() { echo "ERROR: $*" >&2; exit 1; }

command -v node >/dev/null || fail 'Install Node.js 20.9 or newer from https://nodejs.org/.'
node -e 'if (Number(process.versions.node.split(".")[0]) < 20 || (Number(process.versions.node.split(".")[0]) === 20 && Number(process.versions.node.split(".")[1]) < 9)) process.exit(1)' || fail "Node.js 20.9 or newer is required (found $(node --version))."
command -v npm >/dev/null || fail 'npm is required; install Node.js 20.9 or newer.'
npm_version=$(npm --version)
node -e 'if (Number(process.argv[1].split(".")[0]) < 10) process.exit(1)' "$npm_version" || fail "npm 10 or newer is required (found $npm_version)."
command -v python3 >/dev/null || fail 'Install Python 3.12 or newer from https://www.python.org/downloads/.'
python3 -c 'import sys; sys.exit(0 if sys.version_info >= (3, 12) else 1)' || fail "Python 3.12 or newer is required (found $(python3 --version))."
command -v docker >/dev/null || fail 'Install Docker Desktop (https://www.docker.com/products/docker-desktop/) with Compose, start it, and retry.'
docker info >/dev/null 2>&1 || fail 'Docker Desktop is installed but not running. Start it and retry.'
docker compose version >/dev/null 2>&1 || fail 'Docker Compose is unavailable. Update Docker Desktop and retry.'

# A second launch is a no-op when the processes recorded by the previous run are healthy.
if [[ -f "$LOG_DIR/api.pid" && -f "$LOG_DIR/web.pid" && -f "$LOG_DIR/worker.pid" && -f "$LOG_DIR/.mode" ]]; then
  api_pid=$(cat "$LOG_DIR/api.pid"); web_pid=$(cat "$LOG_DIR/web.pid"); worker_pid=$(cat "$LOG_DIR/worker.pid")
  lock_hash_current=$( { sha256sum package-lock.json 2>/dev/null || shasum -a 256 package-lock.json; } | cut -d' ' -f1)
  requirements_hash_current=$( { sha256sum api/requirements.txt 2>/dev/null || shasum -a 256 api/requirements.txt; } | cut -d' ' -f1)
  managed_pids=true
  for service_pid in "$api_pid" "$web_pid" "$worker_pid"; do
    ps -p "$service_pid" -o args= 2>/dev/null | grep -F 'scripts/run-service.sh' >/dev/null || managed_pids=false
  done
  if [[ "$managed_pids" == true && "$(cat "$LOG_DIR/.mode")" == "$MODE $lock_hash_current $requirements_hash_current" ]] \
    && kill -0 "$api_pid" 2>/dev/null && kill -0 "$web_pid" 2>/dev/null && kill -0 "$worker_pid" 2>/dev/null \
    && python3 -c 'import urllib.request; urllib.request.urlopen("http://127.0.0.1:8000/health", timeout=2)' \
    && python3 -c 'import urllib.request; urllib.request.urlopen("http://127.0.0.1:3000/", timeout=2)'; then
    echo 'BrandLens is already running and healthy at http://localhost:3000/.'
    trap - EXIT
    exit 0
  fi
  ./stop.sh
fi

for port in 3000 8000 5432 6379 9000 9001 8025 1025; do
  if command -v ss >/dev/null && ss -ltn "sport = :$port" | tail -n +2 | grep -q .; then
    owner=$(ss -lptn "sport = :$port" | tail -n +2 | head -n 1)
    fail "Port $port is already in use: $owner"
  elif command -v lsof >/dev/null && lsof -nP -iTCP:"$port" -sTCP:LISTEN 2>/dev/null | tail -n +2 | grep -q .; then
    owner=$(lsof -nP -iTCP:"$port" -sTCP:LISTEN 2>/dev/null | tail -n +2 | head -n 1)
    fail "Port $port is already in use: $owner"
  fi
done
if ! command -v ss >/dev/null && ! command -v lsof >/dev/null; then fail 'Install lsof (macOS) or iproute2 (Linux) to detect port conflicts.'; fi

if [[ ! -f .env ]]; then
  cp .env.example .env
  python3 scripts/generate-local-env.py .env
  chmod 600 .env
  echo 'First-run settings created. The development administrator password is stored in .env; change it after signing in.'
fi
[[ -f api/.env ]] || cp .env api/.env

# Import simple KEY=value dotenv entries without evaluating shell code.
while IFS= read -r line || [[ -n "$line" ]]; do
  [[ "$line" =~ ^[[:space:]]*([A-Za-z_][A-Za-z0-9_]*)=(.*)$ ]] || continue
  key="${BASH_REMATCH[1]}"; value="${BASH_REMATCH[2]}"
  if [[ ${#value} -ge 2 && ( ( ${value:0:1} == '"' && ${value: -1} == '"' ) || ( ${value:0:1} == "'" && ${value: -1} == "'" ) ) ]]; then value="${value:1:${#value}-2}"; fi
  export "$key=$value"
done < .env

hash_file() { if command -v sha256sum >/dev/null; then sha256sum "$1" | cut -d' ' -f1; else shasum -a 256 "$1" | cut -d' ' -f1; fi; }
lock_hash=$(hash_file package-lock.json)
if [[ ! -d node_modules || ! -f .brandlens-npm-lock-hash || "$(cat .brandlens-npm-lock-hash)" != "$lock_hash" ]]; then
  npm ci || fail 'npm ci failed; fix the reported dependency error and retry.'
  printf '%s' "$lock_hash" > .brandlens-npm-lock-hash
fi
if [[ ! -x api/.venv/bin/python ]]; then python3 -m venv api/.venv || fail 'Could not create api/.venv.'; fi
venv_python="$ROOT/api/.venv/bin/python"
requirements_hash=$(hash_file api/requirements.txt)
if [[ ! -f api/.venv/.brandlens-requirements-hash || "$(cat api/.venv/.brandlens-requirements-hash)" != "$requirements_hash" ]]; then
  "$venv_python" -m pip install -r api/requirements.txt || fail 'API requirements installation failed.'
  printf '%s' "$requirements_hash" > api/.venv/.brandlens-requirements-hash
fi

DATA_STARTED=1
docker compose up -d db redis minio minio-init mailpit || fail 'Docker Compose could not start local data services; inspect docker compose logs.'
deadline=$((SECONDS + 120))
until docker compose exec -T db pg_isready -U brandlens -d brandlens >/dev/null 2>&1 \
  && docker compose exec -T redis redis-cli ping 2>/dev/null | grep -q PONG \
  && init_id="$(docker compose ps -a -q minio-init)" \
  && [[ -n "$init_id" ]] \
  && [[ "$(docker inspect -f '{{.State.Status}}' "$init_id" 2>/dev/null)" == exited ]] \
  && [[ "$(docker inspect -f '{{.State.ExitCode}}' "$init_id" 2>/dev/null)" == 0 ]]; do
  (( SECONDS < deadline )) || { docker compose ps -a; docker compose logs --tail 80 db redis minio minio-init; fail 'PostgreSQL, Redis or object storage failed its health check within two minutes.'; }
  sleep 2
done
(cd api && "$venv_python" -m alembic upgrade head) || fail 'Alembic migration failed; see the output above.'
(cd api && "$venv_python" -m app.cli bootstrap-platform-admin) || fail 'Bootstrap admin failed; check BOOTSTRAP_ADMIN_EMAIL and BOOTSTRAP_ADMIN_PASSWORD in .env.'
if [[ "$MODE" == prod ]]; then npm run build || fail 'Production web build failed.'; fi

for service in api worker web; do
  : > "$LOG_DIR/$service.log"
  nohup bash scripts/run-service.sh "$service" "$MODE" >>"$LOG_DIR/$service.log" 2>&1 &
  echo $! > "$LOG_DIR/$service.pid"
done
deadline=$((SECONDS + 90))
until python3 -c 'import urllib.request; urllib.request.urlopen("http://127.0.0.1:8000/health", timeout=2)' >/dev/null 2>&1; do
  (( SECONDS < deadline )) || { tail -n 60 "$LOG_DIR/api.log"; fail 'API /health did not respond within 90 seconds.'; }
  sleep 2
done
deadline=$((SECONDS + 90))
until python3 -c 'import urllib.request; urllib.request.urlopen("http://127.0.0.1:3000/", timeout=2)' >/dev/null 2>&1; do
  (( SECONDS < deadline )) || { tail -n 60 "$LOG_DIR/web.log"; fail 'Web home page did not respond within 90 seconds.'; }
  sleep 2
done
for service in api worker web; do
  pid=$(cat "$LOG_DIR/$service.pid")
  kill -0 "$pid" 2>/dev/null || { tail -n 60 "$LOG_DIR/$service.log"; fail "$service exited during startup; see logs/$service.log."; }
  grep -q 'exited with code' "$LOG_DIR/$service.log" && { tail -n 60 "$LOG_DIR/$service.log"; fail "$service exited during startup; see logs/$service.log."; } || true
done
printf '%s %s %s' "$MODE" "$lock_hash" "$requirements_hash" > "$LOG_DIR/.mode"
trap - EXIT
echo 'BrandLens is ready.'
echo 'Website:     http://localhost:3000/'
echo 'Login:       http://localhost:3000/login'
echo 'API health:  http://localhost:8000/health'
echo 'API docs:    http://localhost:8000/docs'
echo "Logs:        $LOG_DIR"
echo 'Stop with ./stop.sh; use ./stop.sh --containers to stop local data services too.'
if command -v xdg-open >/dev/null; then xdg-open http://localhost:3000/ >/dev/null 2>&1 || true; elif command -v open >/dev/null; then open http://localhost:3000/ || true; fi
