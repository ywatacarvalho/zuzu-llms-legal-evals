"""Unit tests for app.services.github_copilot_client."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.services.github_copilot_client import chat_completion


def _mock_response(content: str, status_code: int = 200):
    response = MagicMock()
    response.status_code = status_code
    response.json.return_value = {"choices": [{"message": {"content": content}}]}
    if status_code >= 400:
        from httpx import HTTPStatusError, Request, Response

        response.raise_for_status.side_effect = HTTPStatusError(
            "error", request=MagicMock(spec=Request), response=MagicMock(spec=Response)
        )
    else:
        response.raise_for_status = MagicMock()
    return response


class TestChatCompletion:
    @pytest.mark.asyncio
    async def test_returns_content_from_response(self):
        mock_response = _mock_response("Legal analysis result.")

        with patch("app.services.github_copilot_client.settings") as mock_settings:
            mock_settings.TOGETHER_API_KEY = "test-token"

            mock_client = AsyncMock()
            mock_client.post = AsyncMock(return_value=mock_response)
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=False)

            _target = "app.services.github_copilot_client.httpx.AsyncClient"
            with patch(_target, return_value=mock_client):
                result = await chat_completion(
                    messages=[{"role": "user", "content": "What is res judicata?"}]
                )

        assert result == "Legal analysis result."

    @pytest.mark.asyncio
    async def test_includes_response_format_when_provided(self):
        captured_payload: list[dict] = []
        mock_response = _mock_response("result")

        async def _post(url, json, headers):
            captured_payload.append(json)
            return mock_response

        with patch("app.services.github_copilot_client.settings") as mock_settings:
            mock_settings.TOGETHER_API_KEY = "test-token"

            mock_client = AsyncMock()
            mock_client.post = _post
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=False)

            _target = "app.services.github_copilot_client.httpx.AsyncClient"
            with patch(_target, return_value=mock_client):
                await chat_completion(
                    messages=[{"role": "user", "content": "q"}],
                    response_format={"type": "json_object"},
                )

        assert captured_payload[0].get("response_format") == {"type": "json_object"}

    @pytest.mark.asyncio
    async def test_omits_response_format_when_not_provided(self):
        captured_payload: list[dict] = []
        mock_response = _mock_response("result")

        async def _post(url, json, headers):
            captured_payload.append(json)
            return mock_response

        with patch("app.services.github_copilot_client.settings") as mock_settings:
            mock_settings.TOGETHER_API_KEY = "test-token"

            mock_client = AsyncMock()
            mock_client.post = _post
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=False)

            _target = "app.services.github_copilot_client.httpx.AsyncClient"
            with patch(_target, return_value=mock_client):
                await chat_completion(messages=[{"role": "user", "content": "q"}])

        assert "response_format" not in captured_payload[0]

    @pytest.mark.asyncio
    async def test_uses_bearer_token_in_header(self):
        captured_headers: list[dict] = []
        mock_response = _mock_response("result")

        async def _post(url, json, headers):
            captured_headers.append(headers)
            return mock_response

        with patch("app.services.github_copilot_client.settings") as mock_settings:
            mock_settings.TOGETHER_API_KEY = "my-secret-token"

            mock_client = AsyncMock()
            mock_client.post = _post
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=False)

            _target = "app.services.github_copilot_client.httpx.AsyncClient"
            with patch(_target, return_value=mock_client):
                await chat_completion(messages=[{"role": "user", "content": "q"}])

        assert captured_headers[0]["Authorization"] == "Bearer my-secret-token"

    @pytest.mark.asyncio
    async def test_omits_temperature_for_reasoning_models(self):
        captured_payload: list[dict] = []
        mock_response = _mock_response("result")

        async def _post(url, json, headers):
            captured_payload.append(json)
            return mock_response

        with patch("app.services.github_copilot_client.settings") as mock_settings:
            mock_settings.TOGETHER_API_KEY = "test-token"

            mock_client = AsyncMock()
            mock_client.post = _post
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=False)

            _target = "app.services.github_copilot_client.httpx.AsyncClient"
            with patch(_target, return_value=mock_client):
                await chat_completion(
                    messages=[{"role": "user", "content": "q"}],
                    model="deepseek-ai/DeepSeek-R1",
                )

        assert "temperature" not in captured_payload[0]
