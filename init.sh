#!/usr/bin/env bash

set -euo pipefail

# Project root (absolute) so the script can be called from anywhere.
ROOT_DIR="/Users/srikar.kandikonda/Desktop/Claude/Task-management"
PID_DIR="$ROOT_DIR/.pids"
BACKEND_PID="$PID_DIR/backend.pid"
FRONTEND_PID="$PID_DIR/frontend.pid"
BACKEND_LOG="$ROOT_DIR/backend/uvicorn.log"
FRONTEND_LOG="$ROOT_DIR/frontend/next-dev.log"
DOCKER_COMPOSE_FILE="$ROOT_DIR/docker-compose.yml"

ensure_pid_dir() {
  mkdir -p "$PID_DIR"
}

is_running() {
  local pid="$1"
  if [[ -z "$pid" ]]; then
    return 1
  fi
  if kill -0 "$pid" 2>/dev/null; then
    return 0
  fi
  return 1
}

start_docker() {
  echo "[init] Starting docker-compose services..."
  if ! command -v docker >/dev/null 2>&1; then
    echo "[init] docker is not available. Please install/start Docker Desktop."
    exit 1
  fi
  if ! docker info >/dev/null 2>&1; then
    echo "[init] Docker daemon is not running. Start Docker Desktop first."
    exit 1
  fi
  docker compose -f "$DOCKER_COMPOSE_FILE" up -d
}

stop_docker() {
  echo "[init] Stopping docker-compose services..."
  docker compose -f "$DOCKER_COMPOSE_FILE" down
}

start_backend() {
  ensure_pid_dir
  if [[ -f "$BACKEND_PID" ]] && is_running "$(cat "$BACKEND_PID")"; then
    echo "[init] Backend already running (pid $(cat "$BACKEND_PID"))."
    return
  fi

  local uvicorn_bin="$ROOT_DIR/backend/venv/bin/uvicorn"
  if [[ ! -x "$uvicorn_bin" ]]; then
    echo "[init] Backend venv not found or uvicorn missing at $uvicorn_bin"
    echo "[init] Create venv and install deps first."
    exit 1
  fi

  echo "[init] Starting backend (uvicorn)..."
  (cd "$ROOT_DIR/backend" && "$uvicorn_bin" app.main:app --reload --port 8000 >"$BACKEND_LOG" 2>&1 & echo $! >"$BACKEND_PID")
  echo "[init] Backend started (pid $(cat "$BACKEND_PID")), logs -> $BACKEND_LOG"
}

start_frontend() {
  ensure_pid_dir
  if [[ -f "$FRONTEND_PID" ]] && is_running "$(cat "$FRONTEND_PID")"; then
    echo "[init] Frontend already running (pid $(cat "$FRONTEND_PID"))."
    return
  fi

  if ! command -v npm >/dev/null 2>&1; then
    echo "[init] npm is not available. Install Node/npm first."
    exit 1
  fi

  echo "[init] Starting frontend (Next.js dev server)..."
  (cd "$ROOT_DIR/frontend" && npm run dev >"$FRONTEND_LOG" 2>&1 & echo $! >"$FRONTEND_PID")
  echo "[init] Frontend started (pid $(cat "$FRONTEND_PID")), logs -> $FRONTEND_LOG"
}

stop_service() {
  local name="$1"
  local pid_file="$2"

  if [[ ! -f "$pid_file" ]]; then
    echo "[init] $name not running (no pid file)."
    return
  fi

  local pid
  pid="$(cat "$pid_file")"
  if is_running "$pid"; then
    echo "[init] Stopping $name (pid $pid)..."
    kill "$pid" >/dev/null 2>&1 || true
    wait "$pid" 2>/dev/null || true
    echo "[init] $name stopped."
  else
    echo "[init] $name pid file exists but process not running."
  fi
  rm -f "$pid_file"
}

start_all() {
  start_docker
  start_backend
  start_frontend
}

stop_all() {
  stop_service "frontend" "$FRONTEND_PID"
  stop_service "backend" "$BACKEND_PID"
  stop_docker
}

restart_all() {
  stop_all
  start_all
}

start_target() {
  case "$1" in
    all) start_all ;;
    docker) start_docker ;;
    backend) start_backend ;;
    frontend) start_frontend ;;
    *) echo "[init] Unknown target '$1'"; usage; exit 1 ;;
  esac
}

stop_target() {
  case "$1" in
    all) stop_all ;;
    docker) stop_docker ;;
    backend) stop_service "backend" "$BACKEND_PID" ;;
    frontend) stop_service "frontend" "$FRONTEND_PID" ;;
    *) echo "[init] Unknown target '$1'"; usage; exit 1 ;;
  esac
}

restart_target() {
  case "$1" in
    all)
      restart_all
      ;;
    docker)
      stop_docker
      start_docker
      ;;
    backend)
      stop_service "backend" "$BACKEND_PID"
      start_backend
      ;;
    frontend)
      stop_service "frontend" "$FRONTEND_PID"
      start_frontend
      ;;
    *)
      echo "[init] Unknown target '$1'"; usage; exit 1
      ;;
  esac
}

usage() {
  cat <<EOF
Usage: ./init.sh <start|stop|restart> [all|docker|backend|frontend]

Default target is 'all'.

start    Start docker-compose + backend (uvicorn) + frontend (Next.js)
stop     Stop frontend, backend, then docker-compose
restart  Restart everything

Examples:
  ./init.sh start          # start all
  ./init.sh stop frontend  # stop only frontend
  ./init.sh restart docker # restart docker compose only
EOF
}

main() {
  if [[ $# -lt 1 || $# -gt 2 ]]; then
    usage
    exit 1
  fi

  local action="$1"
  local target="${2:-all}"

  case "$action" in
    start) start_target "$target" ;;
    stop) stop_target "$target" ;;
    restart) restart_target "$target" ;;
    *) usage; exit 1 ;;
  esac
}

main "$@"

