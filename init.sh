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

# Force mode - automatically kill conflicting processes without prompting
FORCE_MODE="${FORCE_MODE:-false}"

# Port configuration file
PORT_CONFIG_FILE="$ROOT_DIR/.ports.json"
ENV_FILE="$ROOT_DIR/.env.runtime"

ensure_pid_dir() {
  mkdir -p "$PID_DIR"
}

# Load port configuration
load_port_config() {
  if [[ ! -f "$PORT_CONFIG_FILE" ]]; then
    # Create default config
    cat > "$PORT_CONFIG_FILE" <<EOF
{
  "backend": 8000,
  "frontend": 3000,
  "postgres": 5432,
  "redis": 6379
}
EOF
  fi
}

# Get port from config
get_configured_port() {
  local service="$1"
  if command -v jq >/dev/null 2>&1; then
    jq -r ".$service" "$PORT_CONFIG_FILE" 2>/dev/null || echo ""
  else
    # Fallback parsing without jq
    grep "\"$service\"" "$PORT_CONFIG_FILE" | sed 's/.*: *\([0-9]*\).*/\1/'
  fi
}

# Set port in config
set_configured_port() {
  local service="$1"
  local port="$2"

  if command -v jq >/dev/null 2>&1; then
    local tmp_file="${PORT_CONFIG_FILE}.tmp"
    jq ".$service = $port" "$PORT_CONFIG_FILE" > "$tmp_file" && mv "$tmp_file" "$PORT_CONFIG_FILE"
  else
    # Fallback: simple sed replacement
    sed -i.bak "s/\"$service\": *[0-9]*/\"$service\": $port/" "$PORT_CONFIG_FILE"
    rm -f "${PORT_CONFIG_FILE}.bak"
  fi

  echo "[init] Updated port config: $service -> $port"
}

# Find next available port starting from a base port
find_available_port() {
  local base_port="$1"
  local max_attempts=100
  local port=$base_port

  while [[ $max_attempts -gt 0 ]]; do
    if ! check_port "$port"; then
      echo "$port"
      return 0
    fi
    ((port++))
    ((max_attempts--))
  done

  echo "[init] ERROR: Could not find available port starting from $base_port" >&2
  return 1
}

# Update runtime environment file for services to read
update_runtime_env() {
  local backend_port frontend_port
  backend_port=$(get_configured_port "backend")
  frontend_port=$(get_configured_port "frontend")

  cat > "$ENV_FILE" <<EOF
# Auto-generated runtime configuration
# DO NOT EDIT MANUALLY - managed by init.sh
BACKEND_PORT=$backend_port
FRONTEND_PORT=$frontend_port
BACKEND_URL=http://localhost:$backend_port
FRONTEND_URL=http://localhost:$frontend_port
NEXT_PUBLIC_API_URL=http://localhost:$backend_port
EOF

  echo "[init] Updated runtime environment: $ENV_FILE"
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

check_port() {
  local port="$1"
  if lsof -Pi :"$port" -sTCP:LISTEN -t >/dev/null 2>&1; then
    return 0  # Port is in use
  fi
  return 1  # Port is free
}

get_port_owner() {
  local port="$1"
  lsof -Pi :"$port" -sTCP:LISTEN -t 2>/dev/null | head -n1
}

kill_port_owner() {
  local port="$1"
  local name="$2"
  local pid
  pid=$(get_port_owner "$port")

  if [[ -n "$pid" ]]; then
    echo "[init] Port $port is occupied by process $pid"

    # In force mode or non-interactive mode, automatically kill
    if [[ "$FORCE_MODE" == "true" ]] || [[ ! -t 0 ]]; then
      echo "[init] Automatically killing process $pid (force mode or non-interactive)..."
      kill "$pid" 2>/dev/null || kill -9 "$pid" 2>/dev/null || true
      sleep 2
      if check_port "$port"; then
        echo "[init] ERROR: Failed to free port $port"
        return 1
      fi
      echo "[init] Port $port freed successfully"
      return 0
    fi

    # Interactive mode - ask user
    read -p "[init] Kill process $pid to free port for $name? [y/N] " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
      echo "[init] Killing process $pid..."
      kill "$pid" 2>/dev/null || kill -9 "$pid" 2>/dev/null || true
      sleep 2
      if check_port "$port"; then
        echo "[init] ERROR: Failed to free port $port"
        return 1
      fi
      echo "[init] Port $port freed successfully"
      return 0
    else
      echo "[init] Aborting $name start - port $port unavailable"
      return 1
    fi
  fi
  return 0
}

wait_for_service() {
  local name="$1"
  local port="$2"
  local pid="$3"
  local max_wait=10
  local count=0

  echo "[init] Waiting for $name to start on port $port..."
  while [[ $count -lt $max_wait ]]; do
    if check_port "$port"; then
      echo "[init] $name is ready on port $port"
      return 0
    fi

    # Check if process died
    if ! is_running "$pid"; then
      echo "[init] ERROR: $name process died during startup"
      echo "[init] Check logs for details"
      return 1
    fi

    sleep 1
    ((count++))
  done

  echo "[init] WARNING: $name didn't respond on port $port within ${max_wait}s"
  echo "[init] Process is running but may have issues - check logs"
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

  # Check PostgreSQL port (5432) and Redis port (6379)
  local postgres_port=5432
  local redis_port=6379

  # Function to check if port is used by our Docker containers
  is_our_docker_container() {
    local port="$1"
    local container_name="$2"

    # Check if container is running
    if docker ps --filter "name=$container_name" --format "{{.Names}}" 2>/dev/null | grep -q "$container_name"; then
      # Check if this container is using the port
      local container_port
      container_port=$(docker port "$container_name" 2>/dev/null | grep "$port" | head -n1)
      if [[ -n "$container_port" ]]; then
        return 0  # Yes, it's our container
      fi
    fi
    return 1  # Not our container
  }

  if check_port "$postgres_port"; then
    if is_our_docker_container "$postgres_port" "context_postgres"; then
      echo "[init] PostgreSQL container already running on port $postgres_port (this is normal)"
    else
      local postgres_owner
      postgres_owner=$(get_port_owner "$postgres_port")
      echo "[init] WARNING: Port $postgres_port (PostgreSQL) is already in use by process $postgres_owner"
      echo "[init] Docker may fail to start PostgreSQL. Consider stopping the conflicting process."

      if [[ "$FORCE_MODE" == "true" ]] || [[ ! -t 0 ]]; then
        echo "[init] Continuing in force/non-interactive mode..."
      else
        read -p "[init] Continue anyway? [y/N] " -n 1 -r
        echo
        if [[ ! $REPLY =~ ^[Yy]$ ]]; then
          exit 1
        fi
      fi
    fi
  fi

  if check_port "$redis_port"; then
    if is_our_docker_container "$redis_port" "context_redis"; then
      echo "[init] Redis container already running on port $redis_port (this is normal)"
    else
      local redis_owner
      redis_owner=$(get_port_owner "$redis_port")
      echo "[init] WARNING: Port $redis_port (Redis) is already in use by process $redis_owner"
      echo "[init] Docker may fail to start Redis. Consider stopping the conflicting process."

      if [[ "$FORCE_MODE" == "true" ]] || [[ ! -t 0 ]]; then
        echo "[init] Continuing in force/non-interactive mode..."
      else
        read -p "[init] Continue anyway? [y/N] " -n 1 -r
        echo
        if [[ ! $REPLY =~ ^[Yy]$ ]]; then
          exit 1
        fi
      fi
    fi
  fi

  docker compose -f "$DOCKER_COMPOSE_FILE" up -d

  # Wait for services to be ready
  echo "[init] Waiting for Docker services to be ready..."
  local max_wait=30
  local count=0

  while [[ $count -lt $max_wait ]]; do
    if check_port "$postgres_port" && check_port "$redis_port"; then
      echo "[init] Docker services are ready"
      return 0
    fi
    sleep 1
    ((count++))
  done

  echo "[init] WARNING: Docker services didn't start within ${max_wait}s"
  echo "[init] Check 'docker compose logs' for details"
}

stop_docker() {
  echo "[init] Stopping docker-compose services..."
  docker compose -f "$DOCKER_COMPOSE_FILE" down
}

start_backend() {
  ensure_pid_dir
  load_port_config

  local backend_port
  backend_port=$(get_configured_port "backend")

  if [[ -f "$BACKEND_PID" ]] && is_running "$(cat "$BACKEND_PID")"; then
    echo "[init] Backend already running (pid $(cat "$BACKEND_PID")) on port $backend_port."
    return
  fi

  # Check if configured port is already in use
  if check_port "$backend_port"; then
    echo "[init] Port $backend_port is occupied"

    # Try to kill the owner or find a new port
    if kill_port_owner "$backend_port" "backend"; then
      echo "[init] Port $backend_port freed, proceeding with backend startup"
    else
      echo "[init] Finding alternative port for backend..."
      local new_port
      new_port=$(find_available_port $((backend_port + 1)))

      if [[ -z "$new_port" ]]; then
        echo "[init] Cannot start backend - no available ports"
        exit 1
      fi

      backend_port=$new_port
      set_configured_port "backend" "$backend_port"
      echo "[init] Backend will use port $backend_port"
    fi
  fi

  local uvicorn_bin="$ROOT_DIR/backend/venv/bin/uvicorn"
  if [[ ! -x "$uvicorn_bin" ]]; then
    echo "[init] Backend venv not found or uvicorn missing at $uvicorn_bin"
    echo "[init] Create venv and install deps first."
    exit 1
  fi

  echo "[init] Starting backend (uvicorn) on port $backend_port..."
  (cd "$ROOT_DIR/backend" && "$uvicorn_bin" app.main:app --reload --port "$backend_port" >"$BACKEND_LOG" 2>&1 & echo $! >"$BACKEND_PID")

  local backend_pid
  backend_pid=$(cat "$BACKEND_PID")

  if ! wait_for_service "backend" "$backend_port" "$backend_pid"; then
    echo "[init] Backend startup verification failed"
    echo "[init] Last 20 lines of backend log:"
    tail -n 20 "$BACKEND_LOG"
    # Clean up pid file if service failed
    if ! is_running "$backend_pid"; then
      rm -f "$BACKEND_PID"
      exit 1
    fi
  fi

  # Update runtime environment file
  update_runtime_env

  echo "[init] Backend started successfully (pid $backend_pid) on port $backend_port"
  echo "[init] Logs: $BACKEND_LOG"
}

start_frontend() {
  ensure_pid_dir
  load_port_config

  local frontend_port
  frontend_port=$(get_configured_port "frontend")

  if [[ -f "$FRONTEND_PID" ]] && is_running "$(cat "$FRONTEND_PID")"; then
    echo "[init] Frontend already running (pid $(cat "$FRONTEND_PID")) on port $frontend_port."
    return
  fi

  # Check if configured port is already in use
  if check_port "$frontend_port"; then
    echo "[init] Port $frontend_port is occupied"

    # Try to kill the owner or find a new port
    if kill_port_owner "$frontend_port" "frontend"; then
      echo "[init] Port $frontend_port freed, proceeding with frontend startup"
    else
      echo "[init] Finding alternative port for frontend..."
      local new_port
      new_port=$(find_available_port $((frontend_port + 1)))

      if [[ -z "$new_port" ]]; then
        echo "[init] Cannot start frontend - no available ports"
        exit 1
      fi

      frontend_port=$new_port
      set_configured_port "frontend" "$frontend_port"
      echo "[init] Frontend will use port $frontend_port"
    fi
  fi

  if ! command -v npm >/dev/null 2>&1; then
    echo "[init] npm is not available. Install Node/npm first."
    exit 1
  fi

  echo "[init] Starting frontend (Next.js dev server) on port $frontend_port..."

  # Update runtime env before starting so frontend can read it
  update_runtime_env

  # Clear Next.js lock file to prevent conflicts
  rm -f "$ROOT_DIR/frontend/.next/dev/lock"

  # Start frontend with PORT environment variable
  (cd "$ROOT_DIR/frontend" && PORT="$frontend_port" npm run dev >"$FRONTEND_LOG" 2>&1 & echo $! >"$FRONTEND_PID")

  local frontend_pid
  frontend_pid=$(cat "$FRONTEND_PID")

  if ! wait_for_service "frontend" "$frontend_port" "$frontend_pid"; then
    echo "[init] Frontend startup verification failed"

    # Check if Next.js auto-switched to a different port
    local detected_port
    detected_port=$(lsof -Pan -p "$frontend_pid" -i 2>/dev/null | grep LISTEN | awk '{print $9}' | cut -d: -f2 | head -n1)

    if [[ -n "$detected_port" && "$detected_port" != "$frontend_port" ]]; then
      echo "[init] WARNING: Next.js started on port $detected_port instead of $frontend_port"
      echo "[init] This usually means port $frontend_port had issues (lock file, permission, etc.)"
      echo "[init] Updating configuration to use port $detected_port"

      frontend_port=$detected_port
      set_configured_port "frontend" "$frontend_port"
      update_runtime_env

      echo "[init] Frontend is now configured for port $frontend_port"
    else
      echo "[init] Last 20 lines of frontend log:"
      tail -n 20 "$FRONTEND_LOG"
      # Clean up pid file if service failed
      if ! is_running "$frontend_pid"; then
        rm -f "$FRONTEND_PID"
        exit 1
      fi
    fi
  fi

  echo "[init] Frontend started successfully (pid $frontend_pid) on port $frontend_port"
  echo "[init] Logs: $FRONTEND_LOG"
  echo "[init] Access frontend at: http://localhost:$frontend_port"
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

    # Wait for graceful shutdown
    local wait_count=0
    while [[ $wait_count -lt 5 ]] && is_running "$pid"; do
      sleep 1
      ((wait_count++))
    done

    # Force kill if still running
    if is_running "$pid"; then
      echo "[init] $name didn't stop gracefully, forcing kill..."
      kill -9 "$pid" >/dev/null 2>&1 || true
      sleep 1
    fi

    echo "[init] $name stopped."
  else
    echo "[init] $name pid file exists but process not running (cleaning up stale pid file)."
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

status_check() {
  load_port_config

  local backend_port frontend_port
  backend_port=$(get_configured_port "backend")
  frontend_port=$(get_configured_port "frontend")

  echo "[init] Service Status Check:"
  echo "=============================="

  # Docker services
  echo -n "Docker (PostgreSQL:5432): "
  if check_port 5432; then
    echo "✓ Running"
  else
    echo "✗ Not running"
  fi

  echo -n "Docker (Redis:6379): "
  if check_port 6379; then
    echo "✓ Running"
  else
    echo "✗ Not running"
  fi

  # Backend
  echo -n "Backend (port $backend_port): "
  if [[ -f "$BACKEND_PID" ]]; then
    local backend_pid
    backend_pid=$(cat "$BACKEND_PID")
    if is_running "$backend_pid" && check_port "$backend_port"; then
      echo "✓ Running (pid $backend_pid)"
    elif is_running "$backend_pid"; then
      echo "⚠ Process running but port not listening (pid $backend_pid)"
    else
      echo "✗ Stale PID file (process not running)"
    fi
  else
    if check_port "$backend_port"; then
      local port_owner
      port_owner=$(get_port_owner "$backend_port")
      echo "⚠ Port in use by unknown process (pid $port_owner)"
    else
      echo "✗ Not running"
    fi
  fi

  # Frontend
  echo -n "Frontend (port $frontend_port): "
  if [[ -f "$FRONTEND_PID" ]]; then
    local frontend_pid_val
    frontend_pid_val=$(cat "$FRONTEND_PID")
    if is_running "$frontend_pid_val" && check_port "$frontend_port"; then
      echo "✓ Running (pid $frontend_pid_val)"
    elif is_running "$frontend_pid_val"; then
      echo "⚠ Process running but port not listening (pid $frontend_pid_val)"
    else
      echo "✗ Stale PID file (process not running)"
    fi
  else
    if check_port "$frontend_port"; then
      local port_owner
      port_owner=$(get_port_owner "$frontend_port")
      echo "⚠ Port in use by unknown process (pid $port_owner)"
    else
      echo "✗ Not running"
    fi
  fi

  echo "=============================="
  echo "Logs: $BACKEND_LOG, $FRONTEND_LOG"
}

usage() {
  cat <<EOF
Usage: ./init.sh <start|stop|restart|status> [all|docker|backend|frontend]

Default target is 'all'.

start    Start docker-compose + backend (uvicorn) + frontend (Next.js)
         - Checks if ports are available before starting
         - Offers to kill processes occupying required ports (interactive mode)
         - Auto-kills conflicting processes in non-interactive/force mode
         - Verifies services started successfully

stop     Stop frontend, backend, then docker-compose
         - Graceful shutdown with 5s timeout
         - Force kills if graceful shutdown fails

restart  Stop then start services

status   Check status of all services and ports

Environment Variables:
  FORCE_MODE=true    Automatically kill conflicting processes without prompting

Examples:
  ./init.sh start                # start all services (interactive)
  FORCE_MODE=true ./init.sh start # auto-kill conflicts, no prompts
  ./init.sh stop frontend         # stop only frontend
  ./init.sh restart docker        # restart docker compose only
  ./init.sh status                # check status of all services

Ports Used:
  3000 - Frontend (Next.js)
  8000 - Backend (FastAPI/Uvicorn)
  5432 - PostgreSQL (Docker)
  6379 - Redis (Docker)
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
    status)
      if [[ "$target" != "all" ]]; then
        echo "[init] Status command doesn't accept targets, ignoring '$target'"
      fi
      status_check
      ;;
    *) usage; exit 1 ;;
  esac
}

main "$@"

