# TickTick Integration Troubleshooting

This guide covers common issues encountered when integrating with the TickTick API and their solutions.

---

## Table of Contents

1. [SSL Certificate Verification Errors](#ssl-certificate-verification-errors)
2. [OAuth Redirect URI Mismatch](#oauth-redirect-uri-mismatch)
3. [Port Configuration Issues](#port-configuration-issues)
4. [Testing TickTick Connection](#testing-ticktick-connection)

---

## SSL Certificate Verification Errors

### Problem

When attempting OAuth token exchange with TickTick, you may encounter:

```
[SSL: CERTIFICATE_VERIFY_FAILED] certificate verify failed: unable to get local issuer certificate
```

### Root Cause

This is a **macOS-specific issue** where Python (especially in Anaconda/Homebrew installations) cannot locate SSL certificates correctly. The issue occurs because:

1. Multiple Python installations (system Python, Homebrew, Anaconda) each have different SSL certificate paths
2. The `httpx` library cannot find the correct CA bundle to verify HTTPS connections
3. Environment variables like `SSL_CERT_FILE` may not be set before Python's SSL module loads

### Attempted Solutions (Did Not Work)

❌ **Creating SSL context with certifi** - Passing `ssl.create_default_context(cafile=certifi.where())` to httpx still failed
❌ **Setting SSL_CERT_FILE in init.sh** - Environment variable wasn't picked up by Python process
❌ **Setting SSL_CERT_FILE in main.py** - Already too late; SSL module already loaded by imports

### Working Solution: Disable SSL Verification (Development Only)

**⚠️ SECURITY WARNING:** This solution disables SSL certificate verification. **Only use for local development.** Never deploy to production with SSL verification disabled.

#### Implementation

**File:** `backend/app/services/ticktick.py`

```python
# SSL verification setting for TickTick API
# NOTE: Temporarily disabled due to macOS SSL certificate issues
# TODO: Re-enable once proper certificate configuration is resolved
_SSL_VERIFY = False  # Set to False to disable SSL verification (development only)

class TickTickService:
    def __init__(self, user: Optional[User] = None):
        # ...
        # Create client with SSL verification disabled (temporary workaround)
        self.client = httpx.AsyncClient(verify=_SSL_VERIFY)
```

Replace all `httpx.AsyncClient()` calls with:
```python
async with httpx.AsyncClient(verify=_SSL_VERIFY) as client:
    # API calls here
```

#### Verification

Test that SSL verification is disabled:

```bash
cd backend
source venv/bin/activate
python3 << 'EOF'
import httpx
import asyncio

async def test():
    async with httpx.AsyncClient(verify=False) as client:
        response = await client.post(
            "https://ticktick.com/oauth/token",
            data={"test": "data"},
        )
        print(f"Status: {response.status_code}")  # Should get 401 (expected)

asyncio.run(test())
EOF
```

Expected output: `Status: 401` (authentication error, not SSL error)

### Production Solution (TODO)

For production deployment, implement proper SSL verification:

1. **Use system certificate store** (recommended for Linux/Docker):
   ```python
   import ssl
   import httpx

   ctx = ssl.create_default_context()
   client = httpx.AsyncClient(verify=ctx)
   ```

2. **Install Python certificates** on macOS:
   ```bash
   # For system Python
   /Applications/Python\ 3.x/Install\ Certificates.command

   # For Homebrew Python
   pip install --upgrade certifi
   ```

3. **Use Docker for deployment** - Linux containers don't have this issue

---

## OAuth Redirect URI Mismatch

### Problem

After authorizing on TickTick's website, you get redirected to an error page:

```
OAuth Error: error="invalid_grant", error_description="Invalid redirect: http://localhost:8000/auth/ticktick/callback does not match one of the registered values"
```

### Root Cause

The redirect URI configured in your application doesn't match the one registered in TickTick Developer Console. This can happen when:

1. The backend port changes (e.g., from 5405 to 5407)
2. The `.env` file has the wrong port
3. The TickTick Developer Console has the wrong redirect URI

### Solution

#### Step 1: Identify Current Backend Port

Check which port the backend is running on:

```bash
cat .env.runtime | grep BACKEND_PORT
# Example output: BACKEND_PORT=5407
```

Or check running processes:
```bash
lsof -i :5407
```

#### Step 2: Update Backend Configuration

**File:** `backend/.env`

```bash
# Update to match current port
TICKTICK_REDIRECT_URI=http://localhost:5407/auth/ticktick/callback
```

Restart backend:
```bash
./init.sh restart backend
```

#### Step 3: Update TickTick Developer Console

1. Go to [TickTick Developer Console](https://developer.ticktick.com/manage)
2. Select your OAuth application
3. Update **Redirect URI** to match backend port:
   ```
   http://localhost:5407/auth/ticktick/callback
   ```
4. Save changes

#### Step 4: Update Frontend Backend URL

In the frontend settings page, update the backend URL to match:

1. Open **Settings** page
2. Find **Backend URL** field
3. Enter: `http://localhost:5407`
4. Click **Update** (page will reload)

### Verification

The redirect URI is displayed in the frontend settings page with a convenient copy button:

**Settings → TickTick Integration → Required Redirect URI**

---

## Port Configuration Issues

### Problem

The backend keeps switching ports or starting on unexpected ports (e.g., 5405 → 5406 → 5407).

### Root Cause

The `init.sh` script detects port conflicts and automatically finds the next available port. This happens when:

1. Previous backend processes weren't killed properly
2. Other services are using the desired port
3. macOS doesn't immediately release ports after process termination

### Solution

#### Option 1: Force Kill Processes on Port

```bash
# Kill all processes on port 5405
lsof -ti:5405 | xargs kill -9

# Wait for port to be released
sleep 2

# Start backend
./init.sh start backend
```

#### Option 2: Reset Port Configuration

```bash
# Reset to default port (5400)
cat > .ports.json <<'EOF'
{
  "backend": 5400,
  "frontend": 5401,
  "postgres": 5433,
  "redis": 6379
}
EOF

# Restart backend
./init.sh restart backend
```

#### Option 3: Use FORCE_MODE

```bash
# Automatically kill conflicting processes
FORCE_MODE=true ./init.sh restart backend
```

### Best Practices

1. **Always use `init.sh` to manage services** - Don't manually start uvicorn
2. **Stop services cleanly** - Use `./init.sh stop backend` before restarting
3. **Check logs** if ports keep changing:
   ```bash
   tail -f backend/uvicorn.log
   ```

---

## Testing TickTick Connection

### Quick Connection Test

```bash
cd backend
source venv/bin/activate
python << 'EOF'
import asyncio
import httpx

async def test_ticktick():
    async with httpx.AsyncClient(verify=False) as client:
        # Test OAuth token endpoint
        response = await client.post(
            "https://ticktick.com/oauth/token",
            data={"client_id": "test"},
            headers={"Content-Type": "application/x-www-form-urlencoded"}
        )
        print(f"TickTick API reachable: {response.status_code}")
        # 401 or 400 is expected (invalid credentials),
        # SSL error means connection issue

asyncio.run(test_ticktick())
EOF
```

### Test OAuth Flow End-to-End

1. **Check Backend Status**:
   ```bash
   ./init.sh status
   ```

2. **Verify Configuration**:
   ```bash
   # Check backend port
   grep BACKEND_PORT .env.runtime

   # Check redirect URI
   grep TICKTICK_REDIRECT_URI backend/.env
   ```

3. **Test Connection in Settings**:
   - Open frontend: `http://localhost:5401/settings`
   - Check "Backend & LLM Settings" → Connection Status
   - Should show "Connected" with green checkmark

4. **Test TickTick OAuth**:
   - In Settings → "TickTick Integration"
   - Click "Connect TickTick"
   - Authorize on TickTick website
   - Should redirect back to `http://localhost:5401/auth/callback?status=success`

### Debug OAuth Callback

Check backend logs for OAuth errors:

```bash
tail -n 100 backend/uvicorn.log | grep -A 10 "TickTick\|OAuth\|callback"
```

Common log patterns:

**Success:**
```
[DEBUG] Exchanging code: abc123... for tokens
[DEBUG] Token exchange successful, got access_token
[DEBUG] Tokens stored successfully
[DEBUG] Redirecting to: http://localhost:5401/auth/callback?status=success
```

**SSL Error:**
```
httpcore.ConnectError: [SSL: CERTIFICATE_VERIFY_FAILED]
```

**Redirect URI Mismatch:**
```
error="invalid_grant", error_description="Invalid redirect: ..."
```

---

## Frontend Backend URL Configuration

### Updating Backend URL in Settings

The frontend includes a convenient UI to update the backend URL when ports change:

1. **Navigate to Settings** (`/settings`)
2. **Find "Backend URL" field** at the top of "Backend & LLM Settings"
3. **Enter new URL** (e.g., `http://localhost:5407`)
4. **Click "Update"** button
5. **Page automatically reloads** to apply new configuration

The URL is stored in `localStorage` and persists across sessions.

### Manual Configuration (Alternative)

You can also set the backend URL via browser console:

```javascript
localStorage.setItem('backend_url', 'http://localhost:5407')
location.reload()
```

### Verifying Backend URL

Check current backend URL in browser console:

```javascript
console.log(localStorage.getItem('backend_url'))
```

---

## Common Error Messages

### "Authentication Failed - Redirecting in 1 seconds"

**Cause:** SSL certificate verification failed during token exchange
**Solution:** Verify SSL verification is disabled in `ticktick.py` (see [SSL Certificate Verification Errors](#ssl-certificate-verification-errors))

### "Invalid redirect: http://localhost:XXXX/auth/ticktick/callback"

**Cause:** Redirect URI mismatch between app and TickTick Developer Console
**Solution:** Update redirect URI in both places (see [OAuth Redirect URI Mismatch](#oauth-redirect-uri-mismatch))

### "Not Connected" in TickTick Integration Settings

**Cause:** No OAuth tokens stored, or backend unreachable
**Solution:**
1. Check backend is running: `./init.sh status`
2. Update backend URL in settings
3. Complete OAuth flow by clicking "Connect TickTick"

---

## Architecture Notes

### OAuth Flow Diagram

```
┌─────────┐         ┌──────────┐         ┌──────────┐
│ Frontend│         │  Backend │         │ TickTick │
│ :5401   │         │  :5407   │         │   API    │
└────┬────┘         └─────┬────┘         └─────┬────┘
     │                    │                    │
     │ 1. Click "Connect"│                    │
     ├───────────────────>│                    │
     │                    │                    │
     │ 2. Redirect to authorize URL           │
     │<───────────────────┤                    │
     │                                         │
     │ 3. User authorizes                      │
     ├────────────────────────────────────────>│
     │                                         │
     │ 4. Redirect with code                   │
     │<────────────────────────────────────────┤
     │                                         │
     │ 5. GET /auth/ticktick/callback?code=XXX│
     ├───────────────────>│                    │
     │                    │                    │
     │                    │ 6. Exchange token  │
     │                    ├───────────────────>│
     │                    │                    │
     │                    │ 7. Return tokens   │
     │                    │<───────────────────┤
     │                    │                    │
     │                    │ 8. Store in DB     │
     │                    │                    │
     │ 9. Redirect to     │                    │
     │    /auth/callback  │                    │
     │<───────────────────┤                    │
     │                                         │
```

### Key Files

| File | Purpose |
|------|---------|
| `backend/app/api/auth.py` | OAuth endpoints (`/auth/ticktick/authorize`, `/auth/ticktick/callback`) |
| `backend/app/services/ticktick.py` | TickTick API client, token exchange |
| `backend/.env` | OAuth credentials, redirect URI configuration |
| `frontend/components/LLMSettings.tsx` | Settings UI, OAuth connection status |
| `frontend/lib/api.ts` | Backend API client with dynamic URL support |
| `.env.runtime` | Runtime port configuration (auto-generated by `init.sh`) |

---

## Related Documentation

- [TickTick API Documentation](https://developer.ticktick.com/api)
- [TickTick Developer Console](https://developer.ticktick.com/manage)
- [httpx SSL Configuration](https://www.python-httpx.org/advanced/#ssl-certificates)
- [FastAPI OAuth Guide](https://fastapi.tiangolo.com/advanced/security/oauth2-scopes/)

---

## Support

If you encounter issues not covered here:

1. Check backend logs: `tail -f backend/uvicorn.log`
2. Check init.sh logs for port issues
3. Verify Docker services are running: `docker ps`
4. Test TickTick API directly using the test scripts above
5. Report the issue at: https://github.com/anthropics/claude-code/issues
