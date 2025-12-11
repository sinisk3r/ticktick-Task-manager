import pytest

from app.services.llm_ollama import OllamaService


@pytest.mark.asyncio
async def test_chat_stream_sends_events(client, monkeypatch):
    async def fake_health_check(self):
        return True

    async def fake_stream_chat(self, messages, context=None, user_id=None):
        assert messages[0]["content"] == "hello"
        yield {"type": "thinking", "delta": "thinking..."}
        yield {"type": "content", "delta": "hi there"}

    monkeypatch.setattr(OllamaService, "health_check", fake_health_check)
    monkeypatch.setattr(OllamaService, "stream_chat", fake_stream_chat)

    response = await client.post(
        "/api/chat/stream",
        json={
            "messages": [{"role": "user", "content": "hello"}],
            "context": {"source": "test"},
        },
    )

    assert response.status_code == 200
    assert response.headers.get("content-type", "").startswith("text/event-stream")
    body = response.text
    assert "event: thinking" in body
    assert "event: message" in body
    assert '"delta": "hi there"' in body

