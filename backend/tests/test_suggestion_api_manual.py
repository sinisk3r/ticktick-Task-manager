"""
Manual test script for Suggestion API endpoints.
Run with PostgreSQL database to test endpoints.

Usage:
    python tests/test_suggestion_api_manual.py
"""
import asyncio
import httpx
from datetime import datetime, timedelta


BASE_URL = "http://localhost:8000"
USER_ID = 1  # Adjust based on your test user


async def test_suggestion_workflow():
    """Test the complete suggestion workflow."""
    print("\n" + "="*60)
    print("TESTING SUGGESTION API ENDPOINTS")
    print("="*60)

    async with httpx.AsyncClient() as client:
        # Step 1: Create a test task
        print("\n1. Creating test task...")
        task_response = await client.post(
            f"{BASE_URL}/api/tasks",
            json={
                "title": "Complete quarterly financial report",
                "description": "Finish Q4 financial report and submit to management. Due end of week. High priority.",
                "due_date": (datetime.now() + timedelta(days=3)).isoformat(),
                "user_id": USER_ID
            }
        )

        if task_response.status_code != 201:
            print(f"❌ Failed to create task: {task_response.status_code}")
            print(task_response.text)
            return

        task_data = task_response.json()
        task_id = task_data["id"]
        print(f"✓ Created task ID: {task_id}")

        # Step 2: Analyze task to generate suggestions
        print("\n2. Analyzing task to generate suggestions...")
        analyze_response = await client.post(
            f"{BASE_URL}/api/tasks/{task_id}/analyze?user_id={USER_ID}"
        )

        if analyze_response.status_code != 200:
            print(f"❌ Failed to analyze task: {analyze_response.status_code}")
            print(analyze_response.text)
            return

        analyze_data = analyze_response.json()
        print(f"✓ Generated {len(analyze_data['suggestions'])} suggestions")
        print(f"  Analysis: {analyze_data['analysis']}")

        for suggestion in analyze_data['suggestions']:
            print(f"  - {suggestion['type']}: {suggestion['suggested']} (confidence: {suggestion['confidence']:.2f})")
            print(f"    Reason: {suggestion['reason']}")

        # Step 3: Get suggestions
        print("\n3. Retrieving pending suggestions...")
        get_response = await client.get(
            f"{BASE_URL}/api/tasks/{task_id}/suggestions?user_id={USER_ID}"
        )

        if get_response.status_code != 200:
            print(f"❌ Failed to get suggestions: {get_response.status_code}")
            print(get_response.text)
            return

        suggestions_data = get_response.json()
        print(f"✓ Found {len(suggestions_data['suggestions'])} pending suggestions")

        # Step 4: Approve some suggestions
        if len(suggestions_data['suggestions']) > 0:
            print("\n4. Approving priority and tags suggestions...")
            approve_response = await client.post(
                f"{BASE_URL}/api/tasks/{task_id}/suggestions/approve?user_id={USER_ID}",
                json={"suggestion_types": ["priority", "tags"]}
            )

            if approve_response.status_code == 200:
                approve_data = approve_response.json()
                print(f"✓ Approved {approve_data['approved_count']} suggestions")
                print(f"  Types: {approve_data['approved_types']}")
                print(f"  Synced to TickTick: {approve_data['synced_to_ticktick']}")
            else:
                print(f"⚠ Approval returned: {approve_response.json()}")

        # Step 5: Reject remaining suggestions
        print("\n5. Rejecting remaining suggestions...")
        reject_response = await client.post(
            f"{BASE_URL}/api/tasks/{task_id}/suggestions/reject?user_id={USER_ID}",
            json={"suggestion_types": ["all"]}
        )

        if reject_response.status_code == 200:
            reject_data = reject_response.json()
            print(f"✓ Rejected {reject_data.get('rejected_count', 0)} suggestions")
        else:
            print(f"⚠ Rejection returned: {reject_response.json()}")

        # Step 6: Verify no pending suggestions remain
        print("\n6. Verifying all suggestions resolved...")
        final_response = await client.get(
            f"{BASE_URL}/api/tasks/{task_id}/suggestions?user_id={USER_ID}"
        )

        if final_response.status_code == 200:
            final_data = final_response.json()
            if len(final_data['suggestions']) == 0:
                print("✓ All suggestions resolved")
            else:
                print(f"⚠ {len(final_data['suggestions'])} suggestions still pending")

        # Step 7: Test batch analysis
        print("\n7. Testing batch analysis...")

        # Create a few more tasks
        task_ids = [task_id]
        for i in range(2):
            task_response = await client.post(
                f"{BASE_URL}/api/tasks",
                json={
                    "title": f"Test task {i+2}",
                    "description": f"Test description {i+2}",
                    "user_id": USER_ID
                }
            )
            if task_response.status_code == 201:
                task_ids.append(task_response.json()["id"])

        batch_response = await client.post(
            f"{BASE_URL}/api/tasks/analyze/batch?user_id={USER_ID}",
            json={"task_ids": task_ids}
        )

        if batch_response.status_code == 200:
            batch_data = batch_response.json()
            print(f"✓ Batch analysis complete:")
            print(f"  Total: {batch_data['total']}")
            print(f"  Successful: {batch_data['successful']}")
            print(f"  Failed: {batch_data['failed']}")
        else:
            print(f"❌ Batch analysis failed: {batch_response.status_code}")

    print("\n" + "="*60)
    print("TESTING COMPLETE")
    print("="*60 + "\n")


async def test_error_cases():
    """Test error handling."""
    print("\n" + "="*60)
    print("TESTING ERROR CASES")
    print("="*60)

    async with httpx.AsyncClient() as client:
        # Test 1: Analyze non-existent task
        print("\n1. Testing analysis of non-existent task...")
        response = await client.post(
            f"{BASE_URL}/api/tasks/99999/analyze?user_id={USER_ID}"
        )
        if response.status_code == 404:
            print("✓ Correctly returns 404 for non-existent task")
        else:
            print(f"❌ Expected 404, got {response.status_code}")

        # Test 2: Get suggestions for non-existent task
        print("\n2. Testing get suggestions for non-existent task...")
        response = await client.get(
            f"{BASE_URL}/api/tasks/99999/suggestions?user_id={USER_ID}"
        )
        if response.status_code == 404:
            print("✓ Correctly returns 404 for non-existent task")
        else:
            print(f"❌ Expected 404, got {response.status_code}")

        # Test 3: Approve non-existent suggestions
        print("\n3. Testing approval with no pending suggestions...")
        # Create a task without suggestions
        task_response = await client.post(
            f"{BASE_URL}/api/tasks",
            json={
                "title": "Test task",
                "user_id": USER_ID
            }
        )
        if task_response.status_code == 201:
            task_id = task_response.json()["id"]
            response = await client.post(
                f"{BASE_URL}/api/tasks/{task_id}/suggestions/approve?user_id={USER_ID}",
                json={"suggestion_types": ["priority"]}
            )
            if response.status_code == 200 and "No pending suggestions" in response.json().get("message", ""):
                print("✓ Correctly handles no pending suggestions")
            else:
                print(f"❌ Unexpected response: {response.json()}")

    print("\n" + "="*60)
    print("ERROR TESTING COMPLETE")
    print("="*60 + "\n")


if __name__ == "__main__":
    print("\n🧪 Suggestion API Manual Tests")
    print("Make sure the backend server is running on http://localhost:8000")
    print("and you have a user with ID 1 in the database.\n")

    try:
        asyncio.run(test_suggestion_workflow())
        asyncio.run(test_error_cases())
    except Exception as e:
        print(f"\n❌ Test failed with error: {e}")
        import traceback
        traceback.print_exc()
