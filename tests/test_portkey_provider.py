from unittest.mock import Mock, patch

import pytest

from app.providers.portkey_provider import PortkeyProvider


class ProviderSettings:
    base_url = "https://portkey.example"
    portkey_api_key = "test-key"
    portkey_model = "main-model"


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
