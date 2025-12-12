"""
Service for testing LLM configuration connections.

⚠️ SECURITY WARNING: SSL verification is disabled for cloud LLM APIs due to macOS SSL certificate issues.
This is a development-only workaround. Never deploy to production with SSL verification disabled.
"""
import time
from typing import Optional, Dict, Any
import httpx
from pydantic import BaseModel

from app.models.llm_configuration import LLMConfiguration, LLMProvider

# SSL verification setting for cloud LLM APIs
# NOTE: Temporarily disabled due to macOS SSL certificate issues
# TODO: Re-enable once proper certificate configuration is resolved
_SSL_VERIFY = False  # Set to False to disable SSL verification (development only)


class ConnectionTestResult(BaseModel):
    """Result of testing an LLM configuration connection."""
    success: bool
    error: Optional[str] = None
    response_time_ms: Optional[int] = None
    model_info: Optional[Dict[str, Any]] = None


async def test_llm_connection(config: LLMConfiguration) -> ConnectionTestResult:
    """
    Test connection to an LLM configuration.
    
    Sends a simple test request to verify the configuration works.
    """
    start_time = time.time()
    
    try:
        if config.provider == LLMProvider.OLLAMA:
            return await _test_ollama_connection(config, start_time)
        elif config.provider == LLMProvider.OPENROUTER:
            return await _test_openrouter_connection(config, start_time)
        elif config.provider == LLMProvider.ANTHROPIC:
            return await _test_anthropic_connection(config, start_time)
        elif config.provider == LLMProvider.OPENAI:
            return await _test_openai_connection(config, start_time)
        else:
            return ConnectionTestResult(
                success=False,
                error=f"Testing not implemented for provider: {config.provider}"
            )
    
    except Exception as e:
        response_time = int((time.time() - start_time) * 1000)
        return ConnectionTestResult(
            success=False,
            error=f"Connection test failed: {str(e)}",
            response_time_ms=response_time
        )


async def _test_ollama_connection(config: LLMConfiguration, start_time: float) -> ConnectionTestResult:
    """Test Ollama connection."""
    base_url = config.base_url or "http://localhost:11434"
    
    async with httpx.AsyncClient(timeout=30.0) as client:
        # First, check if Ollama is running
        try:
            health_response = await client.get(f"{base_url}/api/tags")
            health_response.raise_for_status()
        except Exception as e:
            response_time = int((time.time() - start_time) * 1000)
            return ConnectionTestResult(
                success=False,
                error=f"Ollama server not accessible: {str(e)}",
                response_time_ms=response_time
            )
        
        # Check if the specific model is available
        try:
            models_data = health_response.json()
            available_models = [model["name"] for model in models_data.get("models", [])]
            
            if config.model not in available_models:
                response_time = int((time.time() - start_time) * 1000)
                return ConnectionTestResult(
                    success=False,
                    error=f"Model '{config.model}' not found. Available models: {', '.join(available_models)}",
                    response_time_ms=response_time
                )
        except Exception as e:
            response_time = int((time.time() - start_time) * 1000)
            return ConnectionTestResult(
                success=False,
                error=f"Failed to check available models: {str(e)}",
                response_time_ms=response_time
            )
        
        # Test a simple generation
        try:
            test_payload = {
                "model": config.model,
                "prompt": "Hello",
                "stream": False,
                "options": {
                    "temperature": config.temperature,
                    "num_predict": 10  # Just a few tokens for testing
                }
            }
            
            generate_response = await client.post(
                f"{base_url}/api/generate",
                json=test_payload
            )
            generate_response.raise_for_status()
            
            response_time = int((time.time() - start_time) * 1000)
            result_data = generate_response.json()
            
            return ConnectionTestResult(
                success=True,
                response_time_ms=response_time,
                model_info={
                    "model": config.model,
                    "response_length": len(result_data.get("response", "")),
                    "total_duration": result_data.get("total_duration"),
                    "load_duration": result_data.get("load_duration")
                }
            )
            
        except Exception as e:
            response_time = int((time.time() - start_time) * 1000)
            return ConnectionTestResult(
                success=False,
                error=f"Model generation test failed: {str(e)}",
                response_time_ms=response_time
            )


async def _test_openrouter_connection(config: LLMConfiguration, start_time: float) -> ConnectionTestResult:
    """Test OpenRouter connection."""
    if not config.api_key:
        return ConnectionTestResult(
            success=False,
            error="API key is required for OpenRouter"
        )
    
    async with httpx.AsyncClient(timeout=30.0, verify=_SSL_VERIFY) as client:
        try:
            test_payload = {
                "model": config.model,
                "messages": [{"role": "user", "content": "Hello"}],
                "max_tokens": 10,
                "temperature": config.temperature
            }
            
            headers = {
                "Authorization": f"Bearer {config.api_key}",
                "Content-Type": "application/json"
            }
            
            response = await client.post(
                "https://openrouter.ai/api/v1/chat/completions",
                json=test_payload,
                headers=headers
            )
            response.raise_for_status()
            
            response_time = int((time.time() - start_time) * 1000)
            result_data = response.json()
            
            return ConnectionTestResult(
                success=True,
                response_time_ms=response_time,
                model_info={
                    "model": result_data.get("model", config.model),
                    "usage": result_data.get("usage", {}),
                    "response_length": len(result_data.get("choices", [{}])[0].get("message", {}).get("content", ""))
                }
            )
            
        except httpx.HTTPStatusError as e:
            response_time = int((time.time() - start_time) * 1000)
            error_detail = "Unknown error"
            
            try:
                error_data = e.response.json()
                error_detail = error_data.get("error", {}).get("message", str(e))
            except:
                error_detail = str(e)
            
            return ConnectionTestResult(
                success=False,
                error=f"OpenRouter API error: {error_detail}",
                response_time_ms=response_time
            )
        
        except Exception as e:
            response_time = int((time.time() - start_time) * 1000)
            return ConnectionTestResult(
                success=False,
                error=f"Connection failed: {str(e)}",
                response_time_ms=response_time
            )


async def _test_anthropic_connection(config: LLMConfiguration, start_time: float) -> ConnectionTestResult:
    """Test Anthropic Claude connection."""
    if not config.api_key:
        return ConnectionTestResult(
            success=False,
            error="API key is required for Anthropic Claude"
        )
    
    async with httpx.AsyncClient(timeout=30.0, verify=_SSL_VERIFY) as client:
        try:
            test_payload = {
                "model": config.model,
                "max_tokens": 10,
                "temperature": config.temperature,
                "messages": [{"role": "user", "content": "Hello"}]
            }
            
            headers = {
                "x-api-key": config.api_key,
                "Content-Type": "application/json",
                "anthropic-version": "2023-06-01"
            }
            
            response = await client.post(
                "https://api.anthropic.com/v1/messages",
                json=test_payload,
                headers=headers
            )
            response.raise_for_status()
            
            response_time = int((time.time() - start_time) * 1000)
            result_data = response.json()
            
            return ConnectionTestResult(
                success=True,
                response_time_ms=response_time,
                model_info={
                    "model": result_data.get("model", config.model),
                    "usage": result_data.get("usage", {}),
                    "response_length": len(result_data.get("content", [{}])[0].get("text", ""))
                }
            )
            
        except httpx.HTTPStatusError as e:
            response_time = int((time.time() - start_time) * 1000)
            error_detail = "Unknown error"
            
            try:
                error_data = e.response.json()
                error_detail = error_data.get("error", {}).get("message", str(e))
            except:
                error_detail = str(e)
            
            return ConnectionTestResult(
                success=False,
                error=f"Anthropic API error: {error_detail}",
                response_time_ms=response_time
            )
        
        except Exception as e:
            response_time = int((time.time() - start_time) * 1000)
            return ConnectionTestResult(
                success=False,
                error=f"Connection failed: {str(e)}",
                response_time_ms=response_time
            )


async def _test_openai_connection(config: LLMConfiguration, start_time: float) -> ConnectionTestResult:
    """Test OpenAI connection."""
    if not config.api_key:
        return ConnectionTestResult(
            success=False,
            error="API key is required for OpenAI"
        )
    
    async with httpx.AsyncClient(timeout=30.0, verify=_SSL_VERIFY) as client:
        try:
            test_payload = {
                "model": config.model,
                "messages": [{"role": "user", "content": "Hello"}],
                "max_tokens": 10,
                "temperature": config.temperature
            }
            
            headers = {
                "Authorization": f"Bearer {config.api_key}",
                "Content-Type": "application/json"
            }
            
            response = await client.post(
                "https://api.openai.com/v1/chat/completions",
                json=test_payload,
                headers=headers
            )
            response.raise_for_status()
            
            response_time = int((time.time() - start_time) * 1000)
            result_data = response.json()
            
            return ConnectionTestResult(
                success=True,
                response_time_ms=response_time,
                model_info={
                    "model": result_data.get("model", config.model),
                    "usage": result_data.get("usage", {}),
                    "response_length": len(result_data.get("choices", [{}])[0].get("message", {}).get("content", ""))
                }
            )
            
        except httpx.HTTPStatusError as e:
            response_time = int((time.time() - start_time) * 1000)
            error_detail = "Unknown error"
            
            try:
                error_data = e.response.json()
                error_detail = error_data.get("error", {}).get("message", str(e))
            except:
                error_detail = str(e)
            
            return ConnectionTestResult(
                success=False,
                error=f"OpenAI API error: {error_detail}",
                response_time_ms=response_time
            )
        
        except Exception as e:
            response_time = int((time.time() - start_time) * 1000)
            return ConnectionTestResult(
                success=False,
                error=f"Connection failed: {str(e)}",
                response_time_ms=response_time
            )
