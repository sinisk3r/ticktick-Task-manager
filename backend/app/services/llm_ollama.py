import os
import json
import httpx
from pathlib import Path
from typing import Optional, List
from pydantic import BaseModel


class TaskAnalysis(BaseModel):
    """Result of analyzing a task"""
    urgency: int  # 1-10
    importance: int  # 1-10
    quadrant: str  # Q1, Q2, Q3, Q4
    reasoning: str


def load_prompt_template(version: str = "v1") -> str:
    """Load versioned prompt template from file"""
    prompt_path = Path(__file__).parent.parent / "prompts" / f"task_analysis_suggestions_{version}.txt"
    if not prompt_path.exists():
        raise FileNotFoundError(f"Prompt file not found: {prompt_path}")
    return prompt_path.read_text()


class OllamaService:
    """Service for interacting with Ollama LLM"""

    def __init__(
        self,
        base_url: str | None = None,
        model: str | None = None,
        timeout: float = 60.0
    ):
        self.base_url = base_url or os.getenv("OLLAMA_URL", "http://localhost:11434")
        self.model = model or os.getenv("OLLAMA_MODEL", "qwen3:4b")
        self.timeout = timeout

    async def health_check(self) -> bool:
        """Check if Ollama is reachable and the model is available"""
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                response = await client.get(f"{self.base_url}/api/tags")
                if response.status_code == 200:
                    data = response.json()
                    models = [m["name"] for m in data.get("models", [])]
                    # Check if our model (or a variant) is available
                    return any(self.model in m or m in self.model for m in models)
                return False
        except Exception:
            return False

    async def list_models(self) -> list[str]:
        """List available models in Ollama"""
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                response = await client.get(f"{self.base_url}/api/tags")
                if response.status_code == 200:
                    data = response.json()
                    return [m["name"] for m in data.get("models", [])]
                return []
        except Exception:
            return []

    async def analyze_task(self, description: str, profile_context: str | None = None) -> TaskAnalysis:
        """
        Analyze a task description and return urgency/importance scores.

        Uses Eisenhower Matrix quadrants:
        - Q1: Urgent & Important (Do First)
        - Q2: Not Urgent & Important (Schedule)
        - Q3: Urgent & Not Important (Delegate)
        - Q4: Not Urgent & Not Important (Eliminate)
        """
        system_message = (
            "You are a task analysis assistant. "
            "Respond ONLY with JSON containing integer fields "
            "urgency (1-10) and importance (1-10), plus a brief reasoning string "
            "under 200 characters. Consider provided user context if present."
        )

        context_block = f"User context: {profile_context}\n\n" if profile_context else ""
        user_message = (
            f"""{context_block}Analyze this task:
{description}

Return strictly valid JSON in this shape:
{{"urgency": <int 1-10>, "importance": <int 1-10>, "reasoning": "<brief explanation>"}}"""
        )

        async with httpx.AsyncClient(timeout=self.timeout) as client:
            payload = {
                "model": self.model,
                "messages": [
                    {"role": "system", "content": system_message},
                    {"role": "user", "content": user_message},
                ],
                "stream": False,
                # Disable Qwen3 thinking mode so JSON lands in 'content', not 'thinking'
                "think": False,
                "format": "json",
                "options": {
                    "temperature": 0.3,
                    "num_predict": 300,
                }
            }
            print(f"[DEBUG] Sending to Ollama: {self.base_url}/api/chat")
            print(f"[DEBUG] Model: {self.model}")

            response = await client.post(
                f"{self.base_url}/api/chat",
                json=payload
            )
            response.raise_for_status()
            result = response.json()

            print(f"[DEBUG] Raw response keys: {result.keys()}")
            print(f"[DEBUG] Full response: {json.dumps(result, indent=2)[:500]}")

            # Extract the message content from chat response. If think:false is
            # ignored by the server, fall back to the thinking field.
            message = result.get("message", {})
            llm_text = message.get("content", "") or message.get("thinking", "")

            # Final check for empty response
            if not llm_text or llm_text.strip() == "":
                raise ValueError(
                    "Received empty response from Ollama. "
                    "This may be due to model loading or a timeout. Try again."
                )

            try:
                llm_output = json.loads(llm_text)
            except json.JSONDecodeError:
                # Try to extract JSON from the response if it has extra text
                import re
                # Try to find JSON object, possibly with think tags
                json_match = re.search(r'\{[^{}]*"urgency"[^{}]*\}', llm_text, re.DOTALL)
                if json_match:
                    llm_output = json.loads(json_match.group())
                else:
                    raise ValueError(f"Could not parse LLM response as JSON: {llm_text}")

            # Extract and validate scores
            urgency = int(llm_output.get("urgency", 5))
            importance = int(llm_output.get("importance", 5))
            reasoning = llm_output.get("reasoning", "No reasoning provided")

            # Clamp to valid range
            urgency = max(1, min(10, urgency))
            importance = max(1, min(10, importance))

            # Calculate Eisenhower quadrant
            quadrant = self._calculate_quadrant(urgency, importance)

            return TaskAnalysis(
                urgency=urgency,
                importance=importance,
                quadrant=quadrant,
                reasoning=reasoning
            )

    def _calculate_quadrant(self, urgency: int, importance: int) -> str:
        """
        Determine Eisenhower Matrix quadrant.

        Threshold is 7 (scores >= 7 are considered high)
        """
        if urgency >= 7 and importance >= 7:
            return "Q1"  # Do First
        elif urgency < 7 and importance >= 7:
            return "Q2"  # Schedule
        elif urgency >= 7 and importance < 7:
            return "Q3"  # Delegate
        else:
            return "Q4"  # Eliminate

    async def generate_suggestions(
        self,
        task_data: dict,
        project_context: Optional[dict] = None,
        related_tasks: Optional[List[dict]] = None,
        user_workload: Optional[dict] = None
    ) -> dict:
        """
        Generate AI suggestions for a task (not direct changes).

        Args:
            task_data: Task details (title, description, due_date, current priority, etc.)
            project_context: Project info (name, other tasks in project)
            related_tasks: Similar or related tasks for context
            user_workload: User's current task load and capacity

        Returns:
            dict with "analysis" and "suggestions" keys
        """
        # Load prompt template
        prompt_template = load_prompt_template("v1")

        # Build context JSON
        task_context = {
            "title": task_data.get("title"),
            "description": task_data.get("description", ""),
            "due_date": task_data.get("due_date").isoformat() if task_data.get("due_date") else None,
            "ticktick_priority": task_data.get("ticktick_priority", 0),
            "project_name": project_context.get("name") if project_context else None,
            "ticktick_tags": task_data.get("ticktick_tags", []),
            "start_date": task_data.get("start_date").isoformat() if task_data.get("start_date") else None,
            "related_tasks_in_project": related_tasks or [],
            "user_workload": user_workload or {}
        }

        # Substitute into prompt
        final_prompt = prompt_template.replace("{task_json}", json.dumps(task_context, indent=2))

        async with httpx.AsyncClient(timeout=self.timeout) as client:
            # Use chat API endpoint for better control
            system_message = (
                "You are a task analysis assistant that generates suggestions for task organization. "
                "Respond ONLY with valid JSON in the exact format requested. "
                "Do NOT echo back the input data."
            )

            payload = {
                "model": self.model,
                "messages": [
                    {"role": "system", "content": system_message},
                    {"role": "user", "content": final_prompt}
                ],
                "format": "json",
                "stream": False,
                # Disable Qwen3 thinking mode so JSON lands in 'content', not 'thinking'
                "think": False,
                "options": {
                    "temperature": 0.3,
                    "num_predict": 1500,
                }
            }
            print(f"[DEBUG] Generating suggestions with Ollama: {self.base_url}/api/chat")
            print(f"[DEBUG] Model: {self.model}")

            response = await client.post(
                f"{self.base_url}/api/chat",
                json=payload
            )
            response.raise_for_status()
            result = response.json()

            print(f"[DEBUG] Raw response keys: {result.keys()}")

            # Extract the message content from chat response
            message = result.get("message", {})
            llm_text = message.get("content", "") or message.get("thinking", "")

            # Final check for empty response
            if not llm_text or llm_text.strip() == "":
                raise ValueError(
                    "Received empty response from Ollama. "
                    "This may be due to model loading or a timeout. Try again."
                )

            print(f"[DEBUG] LLM response (first 500 chars): {llm_text[:500]}")

            try:
                suggestion_data = json.loads(llm_text)
            except json.JSONDecodeError:
                # Try to extract JSON from the response if it has extra text
                import re
                json_match = re.search(r'\{.*"analysis".*\}', llm_text, re.DOTALL)
                if json_match:
                    suggestion_data = json.loads(json_match.group())
                else:
                    raise ValueError(f"Could not parse LLM response as JSON: {llm_text[:500]}")

            # Validate structure
            if "analysis" not in suggestion_data or "suggestions" not in suggestion_data:
                raise ValueError(
                    f"Invalid suggestion format. Expected 'analysis' and 'suggestions' keys. "
                    f"Got: {list(suggestion_data.keys())}"
                )

            return suggestion_data
