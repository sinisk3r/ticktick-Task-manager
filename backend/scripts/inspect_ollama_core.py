#!/usr/bin/env python3
"""
Direct Ollama API inspector for debugging model behavior.

Tests different configurations of think/format/temperature to understand
how Qwen3 and other models handle JSON generation and thinking.

Usage:
    # Test basic completion
    python scripts/inspect_ollama.py --prompt "Hello, how are you?"

    # Test JSON generation with thinking disabled
    python scripts/inspect_ollama.py --prompt "Generate a task plan" --format json --think false

    # Test with thinking enabled
    python scripts/inspect_ollama.py --prompt "Analyze this task" --think true

    # Test different models
    python scripts/inspect_ollama.py --model qwen3:7b --prompt "Test"

    # Test token limits
    python scripts/inspect_ollama.py --prompt "Long response test" --tokens 100
"""

import asyncio
import json
import sys
import time
from pathlib import Path
from typing import Optional, Literal
import argparse

import httpx
from rich.console import Console
from rich.panel import Panel
from rich.syntax import Syntax
from rich.table import Table

console = Console()


class OllamaInspector:
    """Direct Ollama API tester."""

    def __init__(self, base_url: str = "http://127.0.0.1:11434"):
        self.base_url = base_url

    async def test_completion(
        self,
        prompt: str,
        model: str = "qwen3:4b",
        stream: bool = False,
        format_json: bool = False,
        think: Optional[bool] = None,
        temperature: float = 0.3,
        num_predict: int = 500,
        system_prompt: Optional[str] = None
    ):
        """
        Test Ollama completion with various configurations.

        Args:
            prompt: User prompt
            model: Model name
            stream: Whether to stream response
            format_json: Set format to "json"
            think: Enable/disable thinking (None = not set)
            temperature: Sampling temperature
            num_predict: Max tokens to generate
            system_prompt: Optional system message
        """
        console.print(f"\n[bold blue]Testing Ollama API[/bold blue]")
        console.print("="*80)

        # Display config
        config_table = Table(title="Configuration", show_header=False)
        config_table.add_column("Parameter", style="cyan")
        config_table.add_column("Value", style="yellow")

        config_table.add_row("Model", model)
        config_table.add_row("Prompt", prompt[:60] + ("..." if len(prompt) > 60 else ""))
        config_table.add_row("Stream", str(stream))
        config_table.add_row("Format", "json" if format_json else "text")
        config_table.add_row("Think", str(think) if think is not None else "not set")
        config_table.add_row("Temperature", str(temperature))
        config_table.add_row("Max Tokens", str(num_predict))

        console.print(config_table)
        console.print()

        # Build request
        url = f"{self.base_url}/api/chat"
        messages = []

        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})

        messages.append({"role": "user", "content": prompt})

        payload = {
            "model": model,
            "messages": messages,
            "stream": stream,
            "options": {
                "temperature": temperature,
                "num_predict": num_predict
            }
        }

        if format_json:
            payload["format"] = "json"

        if think is not None:
            payload["think"] = think

        # Make request
        start_time = time.time()

        try:
            async with httpx.AsyncClient(timeout=120.0) as client:
                if stream:
                    await self._handle_streaming(client, url, payload)
                else:
                    await self._handle_non_streaming(client, url, payload)

        except Exception as e:
            console.print(f"\n[bold red]Error:[/bold red] {str(e)}")
            return

        duration = time.time() - start_time
        console.print(f"\n[dim]Request completed in {duration:.2f}s[/dim]")

    async def _handle_non_streaming(
        self,
        client: httpx.AsyncClient,
        url: str,
        payload: dict
    ):
        """Handle non-streaming request and display response."""
        console.print("[bold yellow]Sending request...[/bold yellow]")

        response = await client.post(url, json=payload, timeout=120.0)
        response.raise_for_status()

        data = response.json()

        # Display full response
        console.print("\n[bold green]Raw Response:[/bold green]")
        console.print(Syntax(json.dumps(data, indent=2), "json", theme="monokai"))

        # Parse message
        message = data.get("message", {})

        # Display thinking (if present)
        thinking = message.get("thinking", "")
        if thinking:
            console.print(f"\n[bold cyan]Thinking Field:[/bold cyan]")
            console.print(Panel(thinking, border_style="cyan"))

        # Display content
        content = message.get("content", "")
        if content:
            console.print(f"\n[bold white]Content Field:[/bold white]")

            # Try to parse as JSON if format was json
            if payload.get("format") == "json":
                try:
                    parsed = json.loads(content)
                    console.print(Syntax(json.dumps(parsed, indent=2), "json", theme="monokai"))
                except json.JSONDecodeError:
                    console.print(Panel(content, border_style="white"))
            else:
                console.print(Panel(content, border_style="white"))

        # Token usage
        console.print(f"\n[bold blue]Token Usage:[/bold blue]")
        console.print(f"  Prompt tokens: {data.get('prompt_eval_count', 'N/A')}")
        console.print(f"  Completion tokens: {data.get('eval_count', 'N/A')}")
        console.print(f"  Total duration: {data.get('total_duration', 0) / 1e9:.2f}s")

        # Analysis
        console.print(f"\n[bold magenta]Analysis:[/bold magenta]")
        console.print(f"  Content length: {len(content)} chars")
        console.print(f"  Thinking length: {len(thinking)} chars")

        if payload.get("format") == "json":
            if content and not thinking:
                console.print("  ✓ JSON in content field (expected behavior with think:false)")
            elif thinking and not content:
                console.print("  ✗ JSON in thinking field (Qwen3 quirk - need think:false)")
            elif content and thinking:
                console.print("  ⚠ JSON in both fields (unusual)")

    async def _handle_streaming(
        self,
        client: httpx.AsyncClient,
        url: str,
        payload: dict
    ):
        """Handle streaming request and display chunks."""
        console.print("[bold yellow]Streaming response...[/bold yellow]\n")

        thinking_chunks = []
        content_chunks = []

        async with client.stream("POST", url, json=payload, timeout=120.0) as response:
            response.raise_for_status()

            async for line in response.aiter_lines():
                if not line.strip():
                    continue

                try:
                    chunk = json.loads(line)
                except json.JSONDecodeError:
                    continue

                message = chunk.get("message", {})

                # Thinking delta
                thinking_delta = message.get("thinking", "")
                if thinking_delta:
                    thinking_chunks.append(thinking_delta)
                    console.print(f"[dim cyan]{thinking_delta}[/dim cyan]", end="")

                # Content delta
                content_delta = message.get("content", "")
                if content_delta:
                    content_chunks.append(content_delta)
                    console.print(f"[white]{content_delta}[/white]", end="")

                # Check if done
                if chunk.get("done", False):
                    console.print("\n\n[dim green]✓ Stream complete[/dim green]")

                    # Final stats
                    console.print(f"\n[bold blue]Final Stats:[/bold blue]")
                    console.print(f"  Thinking chunks: {len(thinking_chunks)} ({sum(len(c) for c in thinking_chunks)} chars)")
                    console.print(f"  Content chunks: {len(content_chunks)} ({sum(len(c) for c in content_chunks)} chars)")
                    console.print(f"  Prompt tokens: {chunk.get('prompt_eval_count', 'N/A')}")
                    console.print(f"  Completion tokens: {chunk.get('eval_count', 'N/A')}")

    async def compare_configs(self, prompt: str, model: str = "qwen3:4b"):
        """
        Run the same prompt with different think/format configurations
        to compare behavior.
        """
        console.print(f"\n[bold blue]Comparing Configurations[/bold blue]")
        console.print(f"Prompt: {prompt}")
        console.print("="*80)

        configs = [
            {"name": "Default (no think/format)", "think": None, "format_json": False},
            {"name": "think: false", "think": False, "format_json": False},
            {"name": "think: true", "think": True, "format_json": False},
            {"name": "format: json (no think)", "think": None, "format_json": True},
            {"name": "format: json + think: false", "think": False, "format_json": True},
            {"name": "format: json + think: true", "think": True, "format_json": True},
        ]

        for config in configs:
            console.print(f"\n[bold yellow]→ Testing: {config['name']}[/bold yellow]")
            await self.test_completion(
                prompt=prompt,
                model=model,
                format_json=config["format_json"],
                think=config["think"],
                num_predict=300  # Keep it short for comparison
            )
            console.print("\n" + "-"*80)
            await asyncio.sleep(0.5)  # Rate limiting


async def main():
    parser = argparse.ArgumentParser(description="Inspect Ollama API behavior")
    parser.add_argument("--prompt", "-p", default="Hello, how are you?",
                       help="Prompt to test")
    parser.add_argument("--model", "-m", default="qwen3:4b",
                       help="Model name")
    parser.add_argument("--stream", "-s", action="store_true",
                       help="Use streaming")
    parser.add_argument("--format", choices=["text", "json"], default="text",
                       help="Response format")
    parser.add_argument("--think", choices=["true", "false"],
                       help="Enable/disable thinking")
    parser.add_argument("--temperature", "-t", type=float, default=0.3,
                       help="Temperature")
    parser.add_argument("--tokens", "-n", type=int, default=500,
                       help="Max tokens")
    parser.add_argument("--system", help="System prompt")
    parser.add_argument("--compare", "-c", action="store_true",
                       help="Compare different think/format configs")
    parser.add_argument("--url", default="http://127.0.0.1:11434",
                       help="Ollama base URL")

    args = parser.parse_args()

    inspector = OllamaInspector(base_url=args.url)

    if args.compare:
        # Run comparison test
        await inspector.compare_configs(prompt=args.prompt, model=args.model)
    else:
        # Single test
        think_val = None
        if args.think == "true":
            think_val = True
        elif args.think == "false":
            think_val = False

        await inspector.test_completion(
            prompt=args.prompt,
            model=args.model,
            stream=args.stream,
            format_json=(args.format == "json"),
            think=think_val,
            temperature=args.temperature,
            num_predict=args.tokens,
            system_prompt=args.system
        )


if __name__ == "__main__":
    asyncio.run(main())
