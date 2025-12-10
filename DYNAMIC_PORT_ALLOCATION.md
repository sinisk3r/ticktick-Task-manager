# Dynamic Port Allocation System

## Overview

The init.sh script now features intelligent dynamic port allocation that automatically finds available ports when preferred ports are occupied. This eliminates the need for manual intervention and provides a smooth development experience.

## How It Works

### 1. Port Configuration (`.ports.json`)

The system maintains a persistent configuration file tracking allocated ports:

```json
{
  "backend": 8001,
  "frontend": 3000,
  "postgres": 5432,
  "redis": 6379
}
```

**Key Features:**
- Auto-created with defaults on first run
- Automatically updated when alternative ports are allocated
- Persists across system restarts
- Shared state between all init.sh operations

### 2. Runtime Environment (`.env.runtime`)

On each service start, the script generates a runtime environment file:

```bash
# Auto-generated runtime configuration
# DO NOT EDIT MANUALLY - managed by init.sh
BACKEND_PORT=8001
FRONTEND_PORT=3000
BACKEND_URL=http://localhost:8001
FRONTEND_URL=http://localhost:3000
NEXT_PUBLIC_API_URL=http://localhost:8001
```

**Purpose:**
- Provides dynamic configuration to services
- Ensures frontend knows correct backend URL
- Enables CORS configuration with correct ports
- Updates automatically when ports change

### 3. Service Integration

#### Backend (FastAPI)
**File:** `backend/app/main.py`

```python
# Load runtime config if available (created by init.sh)
runtime_env_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "..", ".env.runtime")
if os.path.exists(runtime_env_path):
    load_dotenv(runtime_env_path, override=True)

# Use dynamic ports in CORS configuration
frontend_port = os.getenv("FRONTEND_PORT", "3000")
backend_port = os.getenv("BACKEND_PORT", "8000")

allowed_origins = [
    f"http://localhost:{frontend_port}",
    f"http://127.0.0.1:{frontend_port}",
    # ... etc
]
```

#### Frontend (Next.js)
**File:** `frontend/next.config.ts`

```typescript
// Load runtime configuration from init.sh if available
const runtimeEnvPath = path.join(__dirname, "..", ".env.runtime");
if (fs.existsSync(runtimeEnvPath)) {
  const envContent = fs.readFileSync(runtimeEnvPath, "utf-8");
  envContent.split("\n").forEach((line) => {
    if (line.startsWith("#") || !line.includes("=")) return;
    const [key, ...valueParts] = line.split("=");
    const value = valueParts.join("=").trim();
    if (key && value) {
      process.env[key] = value;
    }
  });
}

const nextConfig: NextConfig = {
  env: {
    NEXT_PUBLIC_API_URL: process.env.NEXT_PUBLIC_API_URL || process.env.BACKEND_URL || "http://localhost:8000",
  },
};
```

## Port Allocation Flow

### Scenario 1: Preferred Port Available

```
User: ./init.sh start backend
Script:
  1. Check if port 8000 is free ✓
  2. Start backend on port 8000
  3. Update .env.runtime with BACKEND_PORT=8000
  4. Verify service started successfully
```

### Scenario 2: Port Occupied (Interactive Mode)

```
User: ./init.sh start backend
Script:
  1. Check if port 8000 is free ✗ (occupied by pid 12345)
  2. Prompt user: "Kill process 12345 to free port? [y/N]"

  If user says YES:
    3a. Kill process 12345
    4a. Start backend on port 8000

  If user says NO:
    3b. Find next available port (8001)
    4b. Update .ports.json: "backend": 8001
    5b. Start backend on port 8001
    6b. Update .env.runtime with BACKEND_PORT=8001
```

### Scenario 3: Non-Interactive Mode

```
Command: FORCE_MODE=true ./init.sh start backend
# or when stdin is not a terminal (automation/scripts)

Script:
  1. Check if port 8000 is free ✗
  2. Automatically kill process on port 8000
  3. If kill fails, find alternative port
  4. Start backend on available port
  5. Update configuration files
```

## Benefits

### 1. Zero Configuration Required
- Services automatically adapt to available ports
- No manual editing of configuration files
- Works out-of-the-box in different environments

### 2. Conflict Resolution
- **Interactive**: User chooses to kill or use alternative port
- **Non-Interactive**: Automatic failover to alternative ports
- **Force Mode**: Aggressive conflict resolution for automation

### 3. Service Discovery
- Frontend always knows correct backend URL
- CORS configuration automatically updated
- Port changes propagate to all services

### 4. Development Workflow
- Multiple developers can run services simultaneously
- CI/CD pipelines work without port conflicts
- Easy testing with multiple instances

### 5. Persistence
- Port allocations survive script restarts
- Services remember their last successful port
- Consistent configuration across sessions

## Command Examples

```bash
# Standard start - prompts if port occupied
./init.sh start backend

# Force mode - automatic conflict resolution
FORCE_MODE=true ./init.sh start all

# Check current port allocations
./init.sh status
# Output shows actual ports:
# Backend (port 8001): ✓ Running (pid 12345)
# Frontend (port 3000): ✓ Running (pid 12346)

# View current configuration
cat .ports.json
cat .env.runtime
```

## Implementation Details

### Port Finding Algorithm

```bash
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

  return 1  # No available port found
}
```

- Starts from preferred port
- Increments until free port found
- Maximum 100 attempts (e.g., 8000-8099)
- Returns error if no port available

### Configuration Update

```bash
set_configured_port() {
  local service="$1"
  local port="$2"

  # Use jq if available, fallback to sed
  if command -v jq >/dev/null 2>&1; then
    jq ".$service = $port" "$PORT_CONFIG_FILE" > tmp && mv tmp "$PORT_CONFIG_FILE"
  else
    sed -i.bak "s/\"$service\": *[0-9]*/\"$service\": $port/" "$PORT_CONFIG_FILE"
  fi
}
```

- Supports both `jq` and `sed` for maximum compatibility
- Atomic updates to prevent corruption
- Immediate feedback to user

## Files Modified

1. **init.sh** - Main orchestration script
   - Port allocation logic
   - Configuration file management
   - Service startup with dynamic ports

2. **backend/app/main.py** - Backend application
   - Runtime config loading
   - Dynamic CORS configuration

3. **frontend/next.config.ts** - Frontend configuration
   - Runtime config parsing
   - Environment variable injection

4. **.gitignore** - Version control
   - Exclude `.ports.json`
   - Exclude `.env.runtime`
   - Exclude `.pids/` directory

## Future Enhancements

Potential improvements:

1. **Port Range Configuration**
   - Allow users to specify preferred port ranges
   - Avoid system/reserved ports automatically

2. **Port Reservation**
   - Reserve ports across multiple projects
   - Prevent conflicts between different development environments

3. **Health-Based Port Selection**
   - Prefer ports with better network performance
   - Avoid problematic port ranges

4. **Web UI for Port Management**
   - Visual dashboard showing all allocated ports
   - Easy reconfiguration through browser

5. **Docker Port Mapping**
   - Automatically update docker-compose.yml
   - Dynamic port forwarding for containerized services

## Troubleshooting

### Port allocation fails after 100 attempts
```bash
# Check what's occupying ports in range
for i in {8000..8100}; do lsof -i :$i; done

# Manually set a specific port
echo '{"backend": 9000, ...}' > .ports.json
./init.sh start backend
```

### Services can't find each other
```bash
# Verify runtime config exists and is correct
cat .env.runtime

# Regenerate runtime config
rm .env.runtime
./init.sh restart all
```

### Port persists incorrectly
```bash
# Reset to defaults
rm .ports.json .env.runtime
./init.sh start all
```

## Conclusion

The dynamic port allocation system provides a robust, user-friendly solution to port conflicts in development environments. By automatically finding available ports and updating service configurations, it eliminates a common source of friction and enables smoother developer workflows.
