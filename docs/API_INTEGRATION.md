# API Integration Guide

Complete guide to integrating with external APIs: TickTick, Google Calendar, Gmail, and Azure DevOps.

---

## TickTick API Integration

### Step 1: Register OAuth Application

1. Go to https://developer.ticktick.com/manage
2. Click "+ App Name" to create a new app
3. Fill in details:
   - **App Name:** Context
   - **Description:** AI-powered task intelligence layer
   - **OAuth Redirect URL:** `http://localhost:8000/auth/ticktick/callback` (dev) or `https://your-domain.com/auth/ticktick/callback` (prod)
4. Save and note down:
   - **Client ID:** `your_client_id_here`
   - **Client Secret:** `your_client_secret_here`

### Step 2: OAuth Flow Implementation

**Authorization Request:**
```python
# app/api/auth.py
from fastapi import APIRouter, HTTPException
from fastapi.responses import RedirectResponse

router = APIRouter()

@router.get("/auth/ticktick/authorize")
async def authorize_ticktick():
    """Initiate TickTick OAuth flow"""
    auth_url = (
        "https://ticktick.com/oauth/authorize?"
        f"client_id={TICKTICK_CLIENT_ID}&"
        f"redirect_uri={TICKTICK_REDIRECT_URI}&"
        "state=random_state_string&"
        "response_type=code&"
        "scope=tasks:read tasks:write"
    )
    return RedirectResponse(url=auth_url)
```

**Callback Handler:**
```python
@router.get("/auth/ticktick/callback")
async def ticktick_callback(
    code: str,
    state: str,
    db: AsyncSession = Depends(get_db)
):
    """Handle OAuth callback and exchange code for tokens"""
    
    # Exchange code for access token
    token_url = "https://ticktick.com/oauth/token"
    data = {
        "client_id": TICKTICK_CLIENT_ID,
        "client_secret": TICKTICK_CLIENT_SECRET,
        "code": code,
        "grant_type": "authorization_code",
        "redirect_uri": TICKTICK_REDIRECT_URI
    }
    
    async with httpx.AsyncClient() as client:
        response = await client.post(token_url, data=data)
        tokens = response.json()
    
    # tokens = {
    #     "access_token": "...",
    #     "refresh_token": "...",
    #     "expires_in": 3600,
    #     "token_type": "Bearer"
    # }
    
    # Get user info
    user_info = await get_ticktick_user(tokens["access_token"])
    
    # Store or update user
    user = await upsert_user(
        db,
        ticktick_user_id=user_info["id"],
        email=user_info["email"],
        access_token=tokens["access_token"],
        refresh_token=tokens["refresh_token"]
    )
    
    # Create session
    session_token = create_jwt_token(user.id)
    
    # Redirect to frontend with session
    return RedirectResponse(
        url=f"{FRONTEND_URL}?token={session_token}"
    )
```

**Token Refresh:**
```python
async def refresh_ticktick_token(user: User) -> str:
    """Refresh expired access token"""
    token_url = "https://ticktick.com/oauth/token"
    data = {
        "client_id": TICKTICK_CLIENT_ID,
        "client_secret": TICKTICK_CLIENT_SECRET,
        "refresh_token": user.ticktick_refresh_token,
        "grant_type": "refresh_token"
    }
    
    async with httpx.AsyncClient() as client:
        response = await client.post(token_url, data=data)
        tokens = response.json()
    
    # Update user tokens
    user.ticktick_access_token = tokens["access_token"]
    user.ticktick_refresh_token = tokens["refresh_token"]
    await db.commit()
    
    return tokens["access_token"]
```

### Step 3: TickTick API Calls

**Get All Tasks:**
```python
# app/services/ticktick.py
class TickTickService:
    def __init__(self, access_token: str):
        self.access_token = access_token
        self.base_url = "https://api.ticktick.com/open/v1"
    
    async def get_all_tasks(self) -> List[Dict]:
        """Fetch all tasks for user"""
        headers = {"Authorization": f"Bearer {self.access_token}"}
        
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{self.base_url}/task",
                headers=headers
            )
            response.raise_for_status()
            return response.json()
    
    async def get_task_by_id(self, task_id: str) -> Dict:
        """Fetch single task"""
        headers = {"Authorization": f"Bearer {self.access_token}"}
        
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{self.base_url}/task/{task_id}",
                headers=headers
            )
            response.raise_for_status()
            return response.json()
    
    async def create_task(self, task_data: Dict) -> Dict:
        """Create new task in TickTick"""
        headers = {
            "Authorization": f"Bearer {self.access_token}",
            "Content-Type": "application/json"
        }
        
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{self.base_url}/task",
                headers=headers,
                json=task_data
            )
            response.raise_for_status()
            return response.json()
    
    async def update_task(self, task_id: str, updates: Dict) -> Dict:
        """Update existing task"""
        headers = {
            "Authorization": f"Bearer {self.access_token}",
            "Content-Type": "application/json"
        }
        
        async with httpx.AsyncClient() as client:
            response = await client.put(
                f"{self.base_url}/task/{task_id}",
                headers=headers,
                json=updates
            )
            response.raise_for_status()
            return response.json()
```

### Step 4: Webhook Setup

**Register Webhook:**
```python
async def register_ticktick_webhook(user_id: str, access_token: str):
    """Register webhook for real-time updates"""
    webhook_url = f"{BACKEND_URL}/webhooks/ticktick"
    
    data = {
        "url": webhook_url,
        "events": ["task.created", "task.updated", "task.deleted"]
    }
    
    headers = {"Authorization": f"Bearer {access_token}"}
    
    async with httpx.AsyncClient() as client:
        response = await client.post(
            "https://api.ticktick.com/open/v1/webhook",
            headers=headers,
            json=data
        )
        return response.json()
```

**Handle Webhook:**
```python
@router.post("/webhooks/ticktick")
async def ticktick_webhook(
    payload: Dict,
    background_tasks: BackgroundTasks
):
    """Receive webhook from TickTick"""
    event_type = payload.get("event")
    task_data = payload.get("data")
    
    if event_type == "task.created":
        # Queue analysis
        background_tasks.add_task(
            analyze_and_store_task,
            task_data
        )
    elif event_type == "task.updated":
        background_tasks.add_task(
            update_task_analysis,
            task_data
        )
    
    return {"status": "received"}
```

### Rate Limits
- **Tasks endpoint:** 100 requests/minute
- **Batch operations:** 20 tasks per request max
- **Webhooks:** Retry 3x with exponential backoff

---

## Google Calendar API

### Step 1: Set Up Google Cloud Project

1. Go to https://console.cloud.google.com
2. Create new project: "Context"
3. Enable APIs:
   - Google Calendar API
   - Gmail API (for email drafts)
4. Create OAuth 2.0 credentials:
   - **Application type:** Web application
   - **Authorized redirect URIs:**
     - `http://localhost:8000/auth/google/callback`
     - `https://your-domain.com/auth/google/callback`
5. Download client configuration JSON

### Step 2: OAuth Flow

**Install Library:**
```bash
pip install google-auth google-auth-oauthlib google-auth-httplib2 google-api-python-client
```

**Authorization:**
```python
from google_auth_oauthlib.flow import Flow

SCOPES = [
    'https://www.googleapis.com/auth/calendar',
    'https://www.googleapis.com/auth/gmail.compose'
]

@router.get("/auth/google/authorize")
async def authorize_google():
    flow = Flow.from_client_secrets_file(
        'client_secret.json',
        scopes=SCOPES,
        redirect_uri=GOOGLE_REDIRECT_URI
    )
    
    authorization_url, state = flow.authorization_url(
        access_type='offline',
        include_granted_scopes='true'
    )
    
    # Store state in session
    return RedirectResponse(url=authorization_url)
```

**Callback:**
```python
@router.get("/auth/google/callback")
async def google_callback(code: str, state: str, db: AsyncSession):
    flow = Flow.from_client_secrets_file(
        'client_secret.json',
        scopes=SCOPES,
        redirect_uri=GOOGLE_REDIRECT_URI
    )
    
    flow.fetch_token(code=code)
    credentials = flow.credentials
    
    # Store credentials
    user = await get_current_user(db)
    user.google_access_token = credentials.token
    user.google_refresh_token = credentials.refresh_token
    await db.commit()
    
    return RedirectResponse(url=f"{FRONTEND_URL}/settings?google=success")
```

### Step 3: Calendar Operations

**Block Time for Task:**
```python
from googleapiclient.discovery import build

class GoogleCalendarService:
    def __init__(self, credentials):
        self.service = build('calendar', 'v3', credentials=credentials)
    
    async def create_event(
        self,
        summary: str,
        start_time: datetime,
        end_time: datetime,
        description: str = None
    ) -> str:
        """Create calendar event"""
        event = {
            'summary': summary,
            'description': description,
            'start': {
                'dateTime': start_time.isoformat(),
                'timeZone': 'America/Los_Angeles',
            },
            'end': {
                'dateTime': end_time.isoformat(),
                'timeZone': 'America/Los_Angeles',
            },
            'reminders': {
                'useDefault': False,
                'overrides': [
                    {'method': 'popup', 'minutes': 10},
                ],
            },
        }
        
        event_result = self.service.events().insert(
            calendarId='primary',
            body=event
        ).execute()
        
        return event_result['id']
    
    async def get_free_busy(
        self,
        start_time: datetime,
        end_time: datetime
    ) -> List[Dict]:
        """Check availability"""
        body = {
            "timeMin": start_time.isoformat() + 'Z',
            "timeMax": end_time.isoformat() + 'Z',
            "items": [{"id": "primary"}]
        }
        
        freebusy = self.service.freebusy().query(body=body).execute()
        return freebusy['calendars']['primary']['busy']
    
    async def list_events(
        self,
        time_min: datetime,
        time_max: datetime
    ) -> List[Dict]:
        """List events in time range"""
        events_result = self.service.events().list(
            calendarId='primary',
            timeMin=time_min.isoformat() + 'Z',
            timeMax=time_max.isoformat() + 'Z',
            singleEvents=True,
            orderBy='startTime'
        ).execute()
        
        return events_result.get('items', [])
```

---

## Gmail API

### Step 1: Same Google Cloud Setup as Calendar

Uses same OAuth credentials and scopes.

### Step 2: Draft Email

```python
import base64
from email.mime.text import MIMEText

class GmailService:
    def __init__(self, credentials):
        self.service = build('gmail', 'v1', credentials=credentials)
    
    async def create_draft(
        self,
        to: str,
        subject: str,
        body: str,
        cc: List[str] = None
    ) -> str:
        """Create email draft in Gmail"""
        message = MIMEText(body)
        message['to'] = to
        message['subject'] = subject
        if cc:
            message['cc'] = ', '.join(cc)
        
        raw_message = base64.urlsafe_b64encode(
            message.as_bytes()
        ).decode()
        
        draft = self.service.users().drafts().create(
            userId='me',
            body={'message': {'raw': raw_message}}
        ).execute()
        
        return draft['id']
    
    async def send_email(
        self,
        to: str,
        subject: str,
        body: str
    ) -> str:
        """Send email immediately"""
        message = MIMEText(body)
        message['to'] = to
        message['subject'] = subject
        
        raw_message = base64.urlsafe_b64encode(
            message.as_bytes()
        ).decode()
        
        sent_message = self.service.users().messages().send(
            userId='me',
            body={'raw': raw_message}
        ).execute()
        
        return sent_message['id']
```

---

## Azure DevOps API

### Step 1: Generate Personal Access Token (PAT)

1. Go to https://dev.azure.com/{your-org}
2. Click user icon → Personal access tokens
3. Click "+ New Token"
4. Set scopes:
   - **Work Items:** Read, Write
   - **Project and Team:** Read
5. Copy token (only shown once!)

### Step 2: API Calls

**Install Library:**
```bash
pip install azure-devops
```

**Initialize Client:**
```python
from azure.devops.connection import Connection
from msrest.authentication import BasicAuthentication

class AzureDevOpsService:
    def __init__(self, org_url: str, pat: str):
        credentials = BasicAuthentication('', pat)
        self.connection = Connection(
            base_url=org_url,
            creds=credentials
        )
        self.wit_client = self.connection.clients.get_work_item_tracking_client()
    
    async def create_work_item(
        self,
        project: str,
        work_item_type: str,
        title: str,
        description: str = None,
        assigned_to: str = None,
        tags: List[str] = None
    ) -> int:
        """Create work item"""
        document = [
            {
                "op": "add",
                "path": "/fields/System.Title",
                "value": title
            }
        ]
        
        if description:
            document.append({
                "op": "add",
                "path": "/fields/System.Description",
                "value": description
            })
        
        if tags:
            document.append({
                "op": "add",
                "path": "/fields/System.Tags",
                "value": "; ".join(tags)
            })
        
        work_item = self.wit_client.create_work_item(
            document=document,
            project=project,
            type=work_item_type
        )
        
        return work_item.id
    
    async def get_work_item(self, work_item_id: int) -> Dict:
        """Get work item by ID"""
        work_item = self.wit_client.get_work_item(
            id=work_item_id,
            expand="all"
        )
        
        return {
            "id": work_item.id,
            "title": work_item.fields["System.Title"],
            "state": work_item.fields["System.State"],
            "url": work_item.url
        }
    
    async def update_work_item(
        self,
        work_item_id: int,
        state: str = None,
        assigned_to: str = None
    ):
        """Update work item"""
        document = []
        
        if state:
            document.append({
                "op": "add",
                "path": "/fields/System.State",
                "value": state
            })
        
        if assigned_to:
            document.append({
                "op": "add",
                "path": "/fields/System.AssignedTo",
                "value": assigned_to
            })
        
        self.wit_client.update_work_item(
            document=document,
            id=work_item_id
        )
```

---

## Error Handling Best Practices

### Retry Logic
```python
from tenacity import retry, stop_after_attempt, wait_exponential

@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=4, max=10)
)
async def api_call_with_retry():
    """Retry failed API calls with exponential backoff"""
    async with httpx.AsyncClient() as client:
        response = await client.get(url)
        response.raise_for_status()
        return response.json()
```

### Rate Limit Handling
```python
async def make_api_call_with_rate_limit(user_id: str):
    # Check Redis for rate limit
    key = f"ratelimit:{user_id}:ticktick"
    count = await redis.incr(key)
    
    if count == 1:
        await redis.expire(key, 60)  # 1 minute window
    
    if count > 100:  # Max 100 calls/minute
        raise HTTPException(
            status_code=429,
            detail="Rate limit exceeded"
        )
    
    return await ticktick_service.get_all_tasks()
```

### Token Expiration
```python
async def api_call_with_token_refresh(user: User):
    try:
        return await ticktick_service.get_all_tasks()
    except httpx.HTTPStatusError as e:
        if e.response.status_code == 401:
            # Token expired, refresh it
            new_token = await refresh_ticktick_token(user)
            ticktick_service.access_token = new_token
            return await ticktick_service.get_all_tasks()
        raise
```

---

## Environment Variables

```bash
# .env
# TickTick
TICKTICK_CLIENT_ID=your_client_id
TICKTICK_CLIENT_SECRET=your_client_secret
TICKTICK_REDIRECT_URI=http://localhost:8000/auth/ticktick/callback

# Google
GOOGLE_CLIENT_ID=your_google_client_id
GOOGLE_CLIENT_SECRET=your_google_client_secret
GOOGLE_REDIRECT_URI=http://localhost:8000/auth/google/callback

# Azure DevOps
AZURE_DEVOPS_ORG_URL=https://dev.azure.com/your-org
AZURE_DEVOPS_PAT=your_personal_access_token
AZURE_DEVOPS_PROJECT=YourProjectName

# App
BACKEND_URL=http://localhost:8000
FRONTEND_URL=http://localhost:3000
```

---

**Last Updated:** 2024-12-09
