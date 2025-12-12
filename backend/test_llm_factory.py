#!/usr/bin/env python3
"""Quick test script for LLM factory"""

import asyncio
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

from app.core.llm_config import get_llm_settings
from app.agent.llm_factory import get_llm_provider


async def test_ollama_provider():
    """Test Ollama provider connection"""
    print("=" * 60)
    print("Testing LLM Factory with Ollama Provider")
    print("=" * 60)

    # Get settings
    settings = get_llm_settings()
    print(f"\nConfiguration:")
    print(f"  Provider: {settings.provider}")
    print(f"  Model: {settings.model}")
    print(f"  Base URL: {settings.base_url or 'default'}")
    print(f"  Temperature: {settings.temperature}")
    print(f"  Max Tokens: {settings.max_tokens}")

    # Create LLM instance
    print(f"\nCreating LLM provider...")
    llm = get_llm_provider(settings)
    print(f"  ✓ Provider created: {llm.__class__.__name__}")

    # Test simple invocation
    print(f"\nTesting LLM invocation...")
    test_prompt = "Say 'Hello from LangChain!' and nothing else."

    try:
        response = await llm.ainvoke(test_prompt)
        print(f"  ✓ Response received:")
        print(f"    {response.content}")
        print("\n" + "=" * 60)
        print("✓ ALL TESTS PASSED")
        print("=" * 60)
        return True

    except Exception as e:
        print(f"  ✗ Error: {e}")
        print("\n" + "=" * 60)
        print("✗ TEST FAILED")
        print("=" * 60)
        return False


if __name__ == "__main__":
    success = asyncio.run(test_ollama_provider())
    sys.exit(0 if success else 1)
