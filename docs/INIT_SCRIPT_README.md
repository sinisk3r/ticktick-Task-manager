# init.sh Service Manager

An improved service orchestration script with robust port conflict detection and graceful fallback mechanisms.

## Features

### Dynamic Port Allocation
- **Automatic port selection** when preferred ports are unavailable
- **Persistent configuration** in `.ports.json` tracks allocated ports
- **Runtime environment file** (`.env.runtime`) shared between services
- **Seamless failover** - services start on alternative ports automatically

### Port Conflict Detection
- **Automatic port checking** before starting services
- **Interactive prompt** to kill processes occupying required ports (interactive mode)
- **Auto-kill in non-interactive mode** or when FORCE_MODE=true
- **Clear error messages** when no ports are available

### Service Health Verification
- **Wait for service startup** (up to 10 seconds per service)
- **Port listening verification** to confirm services are ready
- **Process health checks** during startup
- **Automatic log display** if startup fails

### Graceful Shutdown
- **5-second graceful shutdown** timeout
- **Automatic force kill** if graceful shutdown fails
- **Stale PID file cleanup**

### Status Monitoring
- **Comprehensive status command** showing all services
- **Port and process verification**
- **Visual indicators** (✓ running, ✗ not running, ⚠ issues)

## Usage

```bash
./init.sh <start|stop|restart|status> [all|docker|backend|frontend]
```

### Commands

**start** - Start services with pre-flight checks
- Checks if ports are available
- Offers to kill conflicting processes
- Verifies services started successfully
- Shows last 20 log lines if startup fails

**stop** - Gracefully stop services
- 5-second graceful shutdown timeout
- Force kills if needed
- Cleans up stale PID files

**restart** - Stop then start services

**status** - Check health of all services
- Shows Docker services (PostgreSQL:5432, Redis:6379)
- Shows Backend status (port 8000)
- Shows Frontend status (port 3000)
- Detects stale PID files and orphaned processes

### Targets

- **all** (default) - All services
- **docker** - Docker Compose services (PostgreSQL, Redis)
- **backend** - FastAPI/Uvicorn server
- **frontend** - Next.js dev server

## Examples

```bash
# Check status of all services
./init.sh status

# Start all services (with port conflict detection)
./init.sh start

# Start only backend (will check port 8000)
./init.sh start backend

# Restart frontend if it's stuck
./init.sh restart frontend

# Stop all services gracefully
./init.sh stop
```

## Port Requirements

| Service | Port | Description |
|---------|------|-------------|
| PostgreSQL | 5432 | Database (Docker) |
| Redis | 6379 | Cache/Queue (Docker) |
| Backend | 8000 | FastAPI/Uvicorn |
| Frontend | 3000 | Next.js dev server |

## Dynamic Port Allocation

When a preferred port is unavailable, the script automatically finds an alternative:

```bash
./init.sh start backend
# Output:
[init] Port 8000 is occupied
[init] Finding alternative port for backend...
[init] Updated port config: backend -> 8001
[init] Backend will use port 8001
[init] Starting backend (uvicorn) on port 8001...
[init] backend is ready on port 8001
[init] Backend started successfully (pid 12345) on port 8001
```

The allocated port is:
1. **Saved to `.ports.json`** for persistence
2. **Written to `.env.runtime`** for services to read
3. **Used by backend** via environment variables
4. **Used by frontend** to connect to correct backend URL

## Conflict Resolution

When a port is in use:

1. **Interactive Mode**: Script prompts to kill the occupying process
   ```
   [init] Port 8000 is occupied by process 12345
   [init] Kill process 12345 to free port for backend? [y/N]
   ```
   - If **Yes**: Kills process and uses preferred port
   - If **No**: Finds alternative port automatically

2. **Non-Interactive/Force Mode**: Automatically handles conflicts
   ```bash
   FORCE_MODE=true ./init.sh start
   # or when running from scripts/automation
   ```
   - Auto-kills conflicting processes
   - Or finds alternative ports if kill fails

3. **Docker services**: Script warns but offers to continue
   ```
   [init] WARNING: Port 5432 (PostgreSQL) is already in use by process 12345
   [init] Docker may fail to start PostgreSQL. Consider stopping the conflicting process.
   [init] Continue anyway? [y/N]
   ```

## Startup Verification

After starting a service, the script:

1. Waits up to 10 seconds for the port to be listening
2. Checks if the process is still alive
3. If failure detected:
   - Shows last 20 lines of logs
   - Cleans up PID file if process died
   - Exits with error code

Example:
```
[init] Starting backend (uvicorn)...
[init] Waiting for backend to start on port 8000...
[init] backend is ready on port 8000
[init] Backend started successfully (pid 12345), logs -> backend/uvicorn.log
```

## Troubleshooting

### Service won't start

1. Check status first:
   ```bash
   ./init.sh status
   ```

2. If ports are in use, identify the process:
   ```bash
   lsof -i :8000  # Backend
   lsof -i :3000  # Frontend
   lsof -i :5432  # PostgreSQL
   lsof -i :6379  # Redis
   ```

3. Stop the service cleanly:
   ```bash
   ./init.sh stop backend
   ```

4. Check logs:
   ```bash
   tail -f backend/uvicorn.log
   tail -f frontend/next-dev.log
   ```

### Stale PID files

If status shows "Stale PID file":
```bash
# Clean restart will automatically remove stale PID files
./init.sh restart backend
```

### Docker services not starting

1. Verify Docker Desktop is running:
   ```bash
   docker info
   ```

2. Check Docker logs:
   ```bash
   docker compose logs postgres
   docker compose logs redis
   ```

3. Restart Docker services:
   ```bash
   ./init.sh restart docker
   ```

### Frontend stuck on port 3000

Sometimes Next.js creates a lock file that prevents restart:
```bash
rm -f frontend/.next/dev/lock
./init.sh restart frontend
```

## Configuration Files

### `.ports.json`
Tracks currently allocated ports for all services:
```json
{
  "backend": 8001,
  "frontend": 3000,
  "postgres": 5432,
  "redis": 6379
}
```
- Auto-created on first run
- Updated when ports are dynamically allocated
- Persists across restarts

### `.env.runtime`
Runtime environment variables shared between services:
```bash
# Auto-generated runtime configuration
# DO NOT EDIT MANUALLY - managed by init.sh
BACKEND_PORT=8001
FRONTEND_PORT=3000
BACKEND_URL=http://localhost:8001
FRONTEND_URL=http://localhost:3000
NEXT_PUBLIC_API_URL=http://localhost:8001
```
- Generated on each service start
- Read by backend (FastAPI) and frontend (Next.js)
- Ensures services can find each other on dynamic ports

## Log Files

- Backend: `backend/uvicorn.log`
- Frontend: `frontend/next-dev.log`
- PID files: `.pids/backend.pid`, `.pids/frontend.pid`

## Requirements

- **Docker Desktop** (for docker-compose)
- **Python 3.11+** with venv at `backend/venv`
- **Node.js/npm** for frontend
- **lsof** for port checking (standard on macOS/Linux)

## What Changed

This improved version adds:

1. **Port conflict detection** (`check_port`, `get_port_owner`, `kill_port_owner`)
2. **Service health verification** (`wait_for_service`)
3. **Graceful shutdown** with timeout and force kill
4. **Status command** for health monitoring
5. **Stale PID file detection** and cleanup
6. **Better error messages** with log tails on failure
7. **Interactive prompts** for conflict resolution

The script now fails fast with clear feedback rather than silently creating broken states.
