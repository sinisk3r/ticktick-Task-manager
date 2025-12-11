"""
Test script for the new LLM suggestion engine.
Run with: python -m test_suggestion_engine
"""
import asyncio
import json
from datetime import datetime, timedelta
from app.services.llm_ollama import OllamaService


async def test_suggestion_engine():
    """Test the generate_suggestions method with sample data."""

    # Initialize service
    service = OllamaService()

    # Check if Ollama is running
    is_healthy = await service.health_check()
    if not is_healthy:
        print("❌ Ollama service is not available. Please start Ollama first.")
        print("   Run: ollama serve")
        return

    print("✅ Ollama service is healthy")
    print(f"   Using model: {service.model}")
    print()

    # Test Case 1: High priority task with tight deadline
    print("=" * 80)
    print("TEST CASE 1: High-impact leadership task with tight deadline")
    print("=" * 80)

    task_data_1 = {
        "title": "Complete Q4 OKR Review",
        "description": "Review all team Q4 objectives and prepare presentation for leadership",
        "due_date": datetime.now() + timedelta(days=9),  # Due in 9 days
        "ticktick_priority": 1,  # Low priority (should suggest High)
        "ticktick_tags": ["work"],
        "start_date": None
    }

    project_context_1 = {
        "name": "Work - Q4 Planning",
        "total_tasks": 12,
        "completed_tasks": 8,
        "active_tasks": 4
    }

    related_tasks_1 = [
        {"title": "Gather Q4 metrics", "status": "completed", "due_date": None},
        {"title": "Schedule leadership meeting", "status": "active", "due_date": (datetime.now() + timedelta(days=7)).isoformat()}
    ]

    user_workload_1 = {
        "total_q1_tasks": 8,
        "total_q2_tasks": 15,
        "total_q3_tasks": 3,
        "total_q4_tasks": 2,
        "estimated_hours_q1": 24.0,
        "estimated_hours_q2": 30.0,
        "available_hours_this_week": 16.0
    }

    try:
        print("Calling generate_suggestions...")
        result_1 = await service.generate_suggestions(
            task_data=task_data_1,
            project_context=project_context_1,
            related_tasks=related_tasks_1,
            user_workload=user_workload_1
        )

        print("\n📊 ANALYSIS:")
        print(json.dumps(result_1.get("analysis", {}), indent=2))

        print("\n💡 SUGGESTIONS:")
        suggestions = result_1.get("suggestions", [])
        if suggestions:
            for i, suggestion in enumerate(suggestions, 1):
                print(f"\n  Suggestion {i}:")
                print(f"    Type: {suggestion.get('type')}")
                print(f"    Current: {suggestion.get('current_display')}")
                print(f"    Suggested: {suggestion.get('suggested_display')}")
                print(f"    Reason: {suggestion.get('reason')}")
                print(f"    Confidence: {suggestion.get('confidence'):.2f}")
        else:
            print("  No suggestions generated")

    except Exception as e:
        print(f"❌ Error: {str(e)}")
        import traceback
        traceback.print_exc()

    print()

    # Test Case 2: Low priority task with no deadline
    print("=" * 80)
    print("TEST CASE 2: Maintenance task with no deadline")
    print("=" * 80)

    task_data_2 = {
        "title": "Clean up old project files",
        "description": "Archive completed projects and clean up workspace",
        "due_date": None,
        "ticktick_priority": 0,  # No priority
        "ticktick_tags": ["maintenance", "cleanup"],
        "start_date": None
    }

    project_context_2 = {
        "name": "Personal - Home",
        "total_tasks": 5,
        "completed_tasks": 2,
        "active_tasks": 3
    }

    related_tasks_2 = [
        {"title": "Organize desk", "status": "completed", "due_date": None}
    ]

    user_workload_2 = {
        "total_q1_tasks": 2,
        "total_q2_tasks": 5,
        "total_q3_tasks": 1,
        "total_q4_tasks": 3,
        "estimated_hours_q1": 6.0,
        "estimated_hours_q2": 10.0,
        "available_hours_this_week": 34.0
    }

    try:
        print("Calling generate_suggestions...")
        result_2 = await service.generate_suggestions(
            task_data=task_data_2,
            project_context=project_context_2,
            related_tasks=related_tasks_2,
            user_workload=user_workload_2
        )

        print("\n📊 ANALYSIS:")
        print(json.dumps(result_2.get("analysis", {}), indent=2))

        print("\n💡 SUGGESTIONS:")
        suggestions = result_2.get("suggestions", [])
        if suggestions:
            for i, suggestion in enumerate(suggestions, 1):
                print(f"\n  Suggestion {i}:")
                print(f"    Type: {suggestion.get('type')}")
                print(f"    Current: {suggestion.get('current_display')}")
                print(f"    Suggested: {suggestion.get('suggested_display')}")
                print(f"    Reason: {suggestion.get('reason')}")
                print(f"    Confidence: {suggestion.get('confidence'):.2f}")
        else:
            print("  No suggestions generated (task may be optimal as-is)")

    except Exception as e:
        print(f"❌ Error: {str(e)}")
        import traceback
        traceback.print_exc()

    print()
    print("=" * 80)
    print("✅ Test completed!")
    print("=" * 80)


if __name__ == "__main__":
    asyncio.run(test_suggestion_engine())
