import os
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from dotenv import load_dotenv

from app.services import OllamaService
from app.api import tasks, settings

# Load environment variables
load_dotenv()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan handler"""
    # Startup
    print(f"Starting Context API...")
    print(f"Ollama URL: {os.getenv('OLLAMA_URL', 'http://localhost:11434')}")
    print(f"Ollama Model: {os.getenv('OLLAMA_MODEL', 'qwen3:4b')}")
    yield
    # Shutdown
    print("Shutting down Context API...")


app = FastAPI(
    title="Context - Task Management API",
    description="LLM-powered task analysis and prioritization",
    version="0.1.0",
    lifespan=lifespan
)

# CORS configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        os.getenv("FRONTEND_URL", "http://localhost:3000"),
        "http://localhost:3000",
        "http://127.0.0.1:3000",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include API routers
app.include_router(tasks.router)
app.include_router(settings.router)


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
    urgency: int
    importance: int
    quadrant: str
    reasoning: str

    class Config:
        json_schema_extra = {
            "example": {
                "urgency": 8,
                "importance": 7,
                "quadrant": "Q1",
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
            urgency=analysis.urgency,
            importance=analysis.importance,
            quadrant=analysis.quadrant,
            reasoning=analysis.reasoning
        )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Analysis failed: {str(e)}"
        )
