from unittest.mock import Mock, patch

import pytest

from app.providers.portkey_provider import PortkeyProvider


class ProviderSettings:
    base_url = "https://portkey.example"
    portkey_api_key = "test-key"
    portkey_model = "main-model"


class FakeAsyncResponse:
    def __init__(self, payload):
        self.payload = payload

    def raise_for_status(self):
        return None

    def json(self):
        return self.payload


class FakeAsyncClient:
    response = FakeAsyncResponse({"client_secret": {"value": "ephemeral"}})
    request = None

    def __init__(self, **kwargs):
        self.kwargs = kwargs

    async def __aenter__(self):
        return self

    async def __aexit__(self, *args):
        return None

    async def post(self, url, **kwargs):
        self.request = (url, kwargs)
        return self.response


@pytest.mark.asyncio
async def test_guardrail_uses_completion_token_parameter() -> None:
    provider = PortkeyProvider(ProviderSettings())
    response = Mock()
    response.choices = [Mock(message=Mock(content='{"intent":"IN_SCOPE"}'))]

    with patch.object(provider._client.chat.completions, "create", return_value=response) as create:
        await provider.complete(
            [{"role": "user", "content": "test"}],
            model="guardrail-model",
            max_completion_tokens=20,
            temperature=None,
        )

    kwargs = create.call_args.kwargs
    assert kwargs["max_completion_tokens"] == 20
    assert "max_tokens" not in kwargs
    assert "temperature" not in kwargs


@pytest.mark.asyncio
async def test_main_agent_keeps_max_tokens_parameter() -> None:
    provider = PortkeyProvider(ProviderSettings())
    response = Mock()
    response.choices = [Mock(message=Mock(content="{}"))]

    with patch.object(provider._client.chat.completions, "create", return_value=response) as create:
        await provider.complete(
            [{"role": "user", "content": "test"}],
            max_tokens=1200,
        )

    kwargs = create.call_args.kwargs
    assert kwargs["max_tokens"] == 1200
    assert "max_completion_tokens" not in kwargs


@pytest.mark.asyncio
async def test_realtime_session_uses_configured_model_and_tools() -> None:
    provider = PortkeyProvider(ProviderSettings())

    result = await provider.create_realtime_session(
        model="@azure-openai-eus2/gpt-realtime-2.1-mini",
        instructions="voice instructions",
        tools=[{"type": "function", "name": "FIND_PET"}],
    )

    assert result["model"] == "@azure-openai-eus2/gpt-realtime-2.1-mini"
    assert result["ws_url"] == "ws://portkey.example/realtime?model=@azure-openai-eus2/gpt-realtime-2.1-mini"
    assert result["tools"][0]["name"] == "FIND_PET"
    assert result["instructions"] == "voice instructions"
