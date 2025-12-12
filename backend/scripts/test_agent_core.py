#!/usr/bin/env python3
"""
Interactive test runner for Context agent system.

Usage:
    # Single query test
    python scripts/test_agent.py --query "Create task for meeting at 2pm"

    # Batch test from file
    python scripts/test_agent.py --batch

    # Save results
    python scripts/test_agent.py --batch --save results.json

    # Compare with previous run
    python scripts/test_agent.py --batch --diff results_v1.json
"""

import asyncio
import json
import sys
import time
from pathlib import Path
from datetime import datetime
from typing import Optional, Dict, List, Any
import argparse

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent.parent))

import httpx
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.syntax import Syntax
from rich.progress import Progress, SpinnerColumn, TextColumn

console = Console()


class AgentTester:
    """Test harness for agent streaming endpoint."""

    def __init__(self, base_url: str = "http://localhost:5405"):
        self.base_url = base_url
        self.results: List[Dict[str, Any]] = []

    async def test_query(
        self,
        query: str,
        user_id: int = 1,
        verbose: bool = True,
        save_raw: bool = False
    ) -> Dict[str, Any]:
        """
        Test a single agent query and capture full SSE stream.

        Returns:
            Dict with test results including events, timing, tokens
        """
        if verbose:
            console.print(f"\n[bold blue]Testing Query:[/bold blue] {query}")
            console.print(f"[dim]User ID: {user_id}[/dim]")

        # Prepare request
        url = f"{self.base_url}/api/agent/stream"
        payload = {
            "goal": query,
            "user_id": user_id,
            "context": None,
            "dry_run": False
        }

        # Track metrics
        start_time = time.time()
        events: List[Dict[str, Any]] = []
        thinking_chunks: List[str] = []
        message_chunks: List[str] = []
        tool_calls: List[Dict[str, Any]] = []
        errors: List[str] = []

        try:
            async with httpx.AsyncClient(timeout=120.0) as client:
                async with client.stream("POST", url, json=payload) as response:
                    response.raise_for_status()

                    async for line in response.aiter_lines():
                        if not line.strip() or line.startswith(":"):
                            continue

                        # Parse SSE format: "event: <type>" then "data: <json>"
                        if line.startswith("event:"):
                            current_event = line.split(":", 1)[1].strip()
                        elif line.startswith("data:"):
                            data_str = line.split(":", 1)[1].strip()
                            try:
                                data = json.loads(data_str)
                            except json.JSONDecodeError:
                                data = {"raw": data_str}

                            event_obj = {
                                "type": current_event,
                                "data": data,
                                "timestamp": time.time() - start_time
                            }
                            events.append(event_obj)

                            # Display in real-time
                            if verbose:
                                self._display_event(current_event, data)

                            # Categorize events
                            if current_event == "thinking":
                                # Backend sends "delta" for thinking
                                thinking_chunks.append(data.get("delta", ""))
                            elif current_event == "message":
                                # Backend sends "message" field (not "delta")
                                msg = data.get("message") or data.get("delta", "")
                                if msg:
                                    message_chunks.append(msg)
                            elif current_event == "tool_request":
                                tool_calls.append(data)
                            elif current_event == "error":
                                errors.append(data.get("error", str(data)))

        except httpx.HTTPStatusError as e:
            console.print(f"[bold red]HTTP Error:[/bold red] {e.response.status_code}")
            errors.append(f"HTTP {e.response.status_code}: {e.response.text}")
        except Exception as e:
            console.print(f"[bold red]Error:[/bold red] {str(e)}")
            errors.append(str(e))

        end_time = time.time()
        duration = end_time - start_time

        # Compile results
        result = {
            "query": query,
            "user_id": user_id,
            "timestamp": datetime.now().isoformat(),
            "duration_seconds": round(duration, 2),
            "event_count": len(events),
            "thinking": "".join(thinking_chunks),
            "message": "".join(message_chunks),
            "tool_calls": tool_calls,
            "errors": errors,
            "success": len(errors) == 0,
            "events": events if save_raw else []
        }

        # Display summary
        if verbose:
            self._display_summary(result)

        return result

    def _display_event(self, event_type: str, data: Dict[str, Any]):
        """Pretty-print an SSE event in real-time."""
        if event_type == "thinking":
            delta = data.get("delta", "")
            if delta:
                console.print(f"[dim cyan]{delta}[/dim cyan]", end="")

        elif event_type == "step":
            console.print(f"\n[bold yellow]→ Step {data.get('step', '?')}[/bold yellow]")

        elif event_type == "tool_request":
            console.print(f"[bold green]🔧 Tool:[/bold green] {data.get('tool', 'unknown')}")
            args = data.get("args", {})
            console.print(Syntax(json.dumps(args, indent=2), "json", theme="monokai"))

        elif event_type == "tool_result":
            result = data.get("result", {})
            if isinstance(result, dict) and result.get("error"):
                console.print(f"[bold red]✗ Error:[/bold red] {result['error']}")
            else:
                console.print(f"[bold green]✓ Result:[/bold green] {str(result)[:100]}...")

        elif event_type == "message":
            # Backend can send either "delta" or "message" field
            msg = data.get("message") or data.get("delta", "")
            if msg:
                console.print(f"[bold white]{msg}[/bold white]")

        elif event_type == "done":
            console.print(f"\n[dim green]✓ Stream complete[/dim green]")

        elif event_type == "error":
            console.print(f"[bold red]✗ Error:[/bold red] {data.get('error', data)}")

    def _display_summary(self, result: Dict[str, Any]):
        """Display test result summary."""
        console.print("\n" + "="*80)

        # Status
        status = "✓ PASS" if result["success"] else "✗ FAIL"
        color = "green" if result["success"] else "red"
        console.print(f"[bold {color}]{status}[/bold {color}] in {result['duration_seconds']}s")

        # Thinking (if present)
        if result["thinking"]:
            thinking = result["thinking"][:200] + ("..." if len(result["thinking"]) > 200 else "")
            console.print(f"\n[dim cyan]Thinking:[/dim cyan] {thinking}")

        # Tool calls
        if result["tool_calls"]:
            console.print(f"\n[bold yellow]Tool Calls ({len(result['tool_calls'])}):[/bold yellow]")
            for tc in result["tool_calls"]:
                console.print(f"  • {tc.get('tool', 'unknown')}: {tc.get('args', {})}")

        # Final message
        if result["message"]:
            console.print(f"\n[bold white]Message:[/bold white]")
            console.print(Panel(result["message"], border_style="white"))

        # Errors
        if result["errors"]:
            console.print(f"\n[bold red]Errors ({len(result['errors'])}):[/bold red]")
            for err in result["errors"]:
                console.print(f"  • {err}")

        # Metrics
        console.print(f"\n[dim]Events: {result['event_count']} | "
                     f"Thinking chars: {len(result['thinking'])} | "
                     f"Message chars: {len(result['message'])}[/dim]")

    async def batch_test(
        self,
        test_cases_file: Path,
        verbose: bool = False
    ) -> List[Dict[str, Any]]:
        """Run all test cases from JSON file."""

        # Load test cases
        if not test_cases_file.exists():
            console.print(f"[bold red]Test cases file not found:[/bold red] {test_cases_file}")
            return []

        with open(test_cases_file) as f:
            test_cases = json.load(f)

        console.print(f"[bold blue]Running {len(test_cases)} test cases...[/bold blue]\n")

        results = []
        for i, tc in enumerate(test_cases, 1):
            console.print(f"[bold cyan]Test {i}/{len(test_cases)}:[/bold cyan] {tc['name']}")

            result = await self.test_query(
                query=tc["query"],
                user_id=tc.get("user_id", 1),
                verbose=verbose,
                save_raw=True
            )

            # Add test case metadata
            result["test_name"] = tc["name"]
            result["expected"] = tc.get("expected", {})
            result["passed"] = self._check_expectations(result, tc.get("expected", {}))

            results.append(result)

            # Spacing between tests
            if not verbose:
                console.print(f"  {'✓' if result['passed'] else '✗'} "
                            f"{result['duration_seconds']}s")
            console.print()

        return results

    def _check_expectations(
        self,
        result: Dict[str, Any],
        expected: Dict[str, Any]
    ) -> bool:
        """Check if result meets expected criteria."""
        checks = []

        # Should call tools?
        if "should_call_tools" in expected:
            has_tools = len(result["tool_calls"]) > 0
            checks.append(has_tools == expected["should_call_tools"])

        # Specific tool expected?
        if "expected_tool" in expected:
            tools_called = [tc.get("tool") for tc in result["tool_calls"]]
            checks.append(expected["expected_tool"] in tools_called)

        # Should not have errors?
        if expected.get("should_succeed", True):
            checks.append(len(result["errors"]) == 0)

        # Message should not be truncated?
        if expected.get("no_truncation", False):
            msg = result["message"]
            # Check for abrupt cutoffs (ends mid-sentence)
            checks.append(not msg or msg[-1] in ".!?")

        # Thinking should not leak?
        if expected.get("no_thinking_leak", True):
            # Check if thinking appears in message
            thinking_keywords = ["I should", "I will", "Let me", "First I", "Then I"]
            msg = result["message"]
            checks.append(not any(kw in msg for kw in thinking_keywords))

        return all(checks) if checks else result["success"]

    def save_results(self, results: List[Dict[str, Any]], output_file: Path):
        """Save test results to JSON file."""
        output_data = {
            "timestamp": datetime.now().isoformat(),
            "total_tests": len(results),
            "passed": sum(1 for r in results if r.get("passed", r["success"])),
            "failed": sum(1 for r in results if not r.get("passed", r["success"])),
            "results": results
        }

        with open(output_file, "w") as f:
            json.dump(output_data, f, indent=2)

        console.print(f"[bold green]✓ Results saved to {output_file}[/bold green]")

    def compare_results(self, current_file: Path, previous_file: Path):
        """Compare two test result files."""
        with open(current_file) as f:
            current = json.load(f)
        with open(previous_file) as f:
            previous = json.load(f)

        console.print("\n[bold blue]Comparison Report[/bold blue]")
        console.print("="*80)

        # Overall stats
        table = Table(title="Overall Statistics")
        table.add_column("Metric", style="cyan")
        table.add_column("Previous", style="yellow")
        table.add_column("Current", style="green")
        table.add_column("Change", style="magenta")

        prev_passed = previous["passed"]
        curr_passed = current["passed"]
        table.add_row(
            "Passed",
            str(prev_passed),
            str(curr_passed),
            f"{curr_passed - prev_passed:+d}"
        )

        prev_failed = previous["failed"]
        curr_failed = current["failed"]
        table.add_row(
            "Failed",
            str(prev_failed),
            str(curr_failed),
            f"{curr_failed - prev_failed:+d}"
        )

        console.print(table)

        # Per-test changes
        console.print("\n[bold yellow]Test Changes:[/bold yellow]")
        prev_by_name = {r["test_name"]: r for r in previous["results"]}

        for curr_result in current["results"]:
            name = curr_result["test_name"]
            if name in prev_by_name:
                prev_result = prev_by_name[name]
                curr_pass = curr_result.get("passed", curr_result["success"])
                prev_pass = prev_result.get("passed", prev_result["success"])

                if curr_pass != prev_pass:
                    status = "✓ NOW PASSING" if curr_pass else "✗ NOW FAILING"
                    color = "green" if curr_pass else "red"
                    console.print(f"  [bold {color}]{status}:[/bold {color}] {name}")


async def main():
    parser = argparse.ArgumentParser(description="Test Context agent system")
    parser.add_argument("--query", "-q", help="Single query to test")
    parser.add_argument("--batch", "-b", action="store_true", help="Run batch tests")
    parser.add_argument("--cases", default="tests/agent_test_cases.json",
                       help="Path to test cases file")
    parser.add_argument("--save", "-s", help="Save results to file")
    parser.add_argument("--diff", "-d", help="Compare with previous results file")
    parser.add_argument("--verbose", "-v", action="store_true",
                       help="Show detailed output")
    parser.add_argument("--url", default="http://localhost:5405",
                       help="Backend URL")
    parser.add_argument("--user-id", type=int, default=1,
                       help="User ID for tests")

    args = parser.parse_args()

    tester = AgentTester(base_url=args.url)

    if args.query:
        # Single query test
        result = await tester.test_query(
            query=args.query,
            user_id=args.user_id,
            verbose=True
        )

        if args.save:
            tester.save_results([result], Path(args.save))

    elif args.batch:
        # Batch test
        cases_file = Path(__file__).parent.parent / args.cases
        results = await tester.batch_test(cases_file, verbose=args.verbose)

        # Summary
        passed = sum(1 for r in results if r.get("passed", r["success"]))
        console.print(f"\n[bold blue]Summary:[/bold blue] "
                     f"{passed}/{len(results)} tests passed")

        if args.save:
            tester.save_results(results, Path(args.save))

        if args.diff:
            tester.compare_results(Path(args.save or "current.json"), Path(args.diff))

    else:
        parser.print_help()


if __name__ == "__main__":
    asyncio.run(main())
