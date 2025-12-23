import os
from contextlib import asynccontextmanager
from pathlib import Path

# Set SSL certificate paths BEFORE any other imports that use SSL.
# Prefer repo-level combined bundle (for corp roots like Zscaler); fall back to certifi.
import certifi
_repo_root = Path(__file__).resolve().parents[1]
_combined_ca = _repo_root / "certs" / "combined.pem"
_ca_path = _combined_ca if _combined_ca.exists() else Path(certifi.where())
os.environ["SSL_CERT_FILE"] = str(_ca_path)
os.environ["REQUESTS_CA_BUNDLE"] = str(_ca_path)

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from dotenv import load_dotenv

from app.services import OllamaService
from app.api import tasks, settings, auth, profile, projects, chat, agent, llm_configurations, strategy_config, notifications

# Load environment variables
load_dotenv()

# Also load runtime config if available (created by init.sh)
runtime_env_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "..", ".env.runtime")
if os.path.exists(runtime_env_path):
    load_dotenv(runtime_env_path, override=True)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan handler"""
    # Startup
    backend_port = os.getenv('BACKEND_PORT', '8000')
    print(f"Starting Context API on port {backend_port}...")
    print(f"Ollama URL: {os.getenv('OLLAMA_URL', 'http://localhost:11434')}")
    print(f"Ollama Model: {os.getenv('OLLAMA_MODEL', 'qwen3:4b')}")
    print(f"Frontend URL: {os.getenv('FRONTEND_URL', 'http://localhost:3000')}")
    yield
    # Shutdown
    print("Shutting down Context API...")

    # Clean up Chat UX v2 persistent memory connections
    from app.api.agent import _checkpointer, _store
    if _checkpointer:
        try:
            print("Closing AsyncPostgresSaver connection...")
            await _checkpointer.__aexit__(None, None, None)
        except Exception as e:
            print(f"Error closing checkpointer: {e}")
    if _store:
        try:
            print("Closing AsyncPostgresStore connection...")
            await _store.__aexit__(None, None, None)
        except Exception as e:
            print(f"Error closing store: {e}")


app = FastAPI(
    title="Context - Task Management API",
    description="LLM-powered task analysis and prioritization",
    version="0.1.0",
    lifespan=lifespan
)

# CORS configuration - dynamically allow configured ports
frontend_port = os.getenv("FRONTEND_PORT", "3000")
backend_port = os.getenv("BACKEND_PORT", "8000")

allowed_origins = [
    os.getenv("FRONTEND_URL", f"http://localhost:{frontend_port}"),
    f"http://localhost:{frontend_port}",
    f"http://127.0.0.1:{frontend_port}",
    f"http://localhost:{backend_port}",
    f"http://127.0.0.1:{backend_port}",
    # Also allow default ports for development
    "http://localhost:3000",
    "http://127.0.0.1:3000",
    "http://localhost:8000",
    "http://127.0.0.1:8000",
    # Allow file:// protocol for local HTML files
    "null",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include API routers
app.include_router(tasks.router)
app.include_router(settings.router)
app.include_router(auth.router)
app.include_router(profile.router)
app.include_router(projects.router)
app.include_router(chat.router)
app.include_router(agent.router)
app.include_router(llm_configurations.router)
app.include_router(strategy_config.router)
app.include_router(notifications.router)


# Request/Response models
class AnalyzeRequest(BaseModel):
    description: str

    class Config:
        json_schema_extra = {
            "example": {
                "description": "Finish quarterly report by Friday EOD"
            }
        }


class AnalyzeResponse(BaseModel):
    urgency_score: int
    importance_score: int
    eisenhower_quadrant: str
    reasoning: str

    class Config:
        json_schema_extra = {
            "example": {
                "urgency_score": 8,
                "importance_score": 7,
                "eisenhower_quadrant": "Q1",
                "reasoning": "High urgency due to Friday deadline, important for quarterly goals"
            }
        }


class HealthResponse(BaseModel):
    status: str
    ollama_connected: bool
    ollama_model: str


class ModelsResponse(BaseModel):
    models: list[str]


# Endpoints
@app.get("/health", response_model=HealthResponse)
async def health_check():
    """Check API and Ollama health"""
    ollama = OllamaService()
    ollama_ok = await ollama.health_check()

    return HealthResponse(
        status="ok",
        ollama_connected=ollama_ok,
        ollama_model=ollama.model
    )


@app.get("/api/llm/health")
async def llm_health():
    """Check if Ollama is reachable"""
    ollama = OllamaService()
    is_healthy = await ollama.health_check()

    if not is_healthy:
        raise HTTPException(
            status_code=503,
            detail=f"Ollama not available at {ollama.base_url} or model {ollama.model} not found"
        )

    return {
        "status": "ok",
        "url": ollama.base_url,
        "model": ollama.model
    }


@app.get("/api/llm/models", response_model=ModelsResponse)
async def list_models():
    """List available Ollama models"""
    ollama = OllamaService()
    models = await ollama.list_models()
    return ModelsResponse(models=models)


@app.post("/api/analyze", response_model=AnalyzeResponse)
async def analyze_task(request: AnalyzeRequest):
    """
    Analyze a task description and return Eisenhower Matrix classification.

    - **Q1**: Urgent & Important (Do First)
    - **Q2**: Not Urgent & Important (Schedule)
    - **Q3**: Urgent & Not Important (Delegate)
    - **Q4**: Not Urgent & Not Important (Eliminate)
    """
    if not request.description.strip():
        raise HTTPException(status_code=400, detail="Task description cannot be empty")

    ollama = OllamaService()

    # Check if Ollama is available
    if not await ollama.health_check():
        raise HTTPException(
            status_code=503,
            detail=f"Ollama not available. Ensure it's running at {ollama.base_url}"
        )

    try:
        analysis = await ollama.analyze_task(request.description)
        return AnalyzeResponse(
            urgency_score=analysis.urgency,
            importance_score=analysis.importance,
            eisenhower_quadrant=analysis.quadrant,
            reasoning=analysis.reasoning
        )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Analysis failed: {str(e)}"
        )
