import asyncio
import json
import logging
import time
from typing import Any, AsyncGenerator, Dict, List, Optional

import aiohttp

from ..domain.entities import MessageType
from ..domain.exceptions import AgentProcessingError
from ..domain.value_objects import AgentRequest, AgentResponse
from ..ports.agent_port import AgentPort

logger = logging.getLogger(__name__)


class OpenRouterAdapter(AgentPort):
    def __init__(self, api_key: str, base_url: str = "https://openrouter.ai/api/v1", default_model: str = "google/gemma-3-27b-it:free", timeout: Optional[int] = 30, max_retries: int = 3,):
        self._api_key = api_key
        self._base_url = base_url
        self._default_model = default_model
        self._timeout = timeout
        self._max_retries = max_retries
        self._session: Optional[aiohttp.ClientSession] = None

    async def generate_response(self, request: AgentRequest) -> AgentResponse:
        session = await self._get_session()
        payload = self._to_api_payload(request, stream=False)

        start = time.time()
        last_error: Optional[Exception] = None

        for attempt in range(self._max_retries):
            try:
                async with session.post(f"{self._base_url}/chat/completions",json=payload) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        return self._parse_response(data, payload["model"], start, attempt)

                    if resp.status == 429:
                        # Rate-limited → exponential back-off
                        await asyncio.sleep(2**attempt)
                        continue

                    error_text = await resp.text()
                    raise AgentProcessingError(
                        f"OpenRouter API error {resp.status}: {error_text}",
                        details={"status": resp.status, "attempt": attempt + 1},
                    )

            except aiohttp.ClientError as exc:
                last_error = exc
                if attempt < self._max_retries - 1:
                    await asyncio.sleep(2**attempt)
                    continue

        raise AgentProcessingError(
            f"Max retries ({self._max_retries}) exceeded",
            cause=last_error,
        )

    async def stream_response(self, request: AgentRequest) -> AsyncGenerator[str, None]:
        session = await self._get_session()
        payload = self._to_api_payload(request, stream=True)

        try:
            async with session.post(f"{self._base_url}/chat/completions", json=payload) as resp:
                if resp.status != 200:
                    error_text = await resp.text()
                    raise AgentProcessingError(
                        f"OpenRouter streaming error {resp.status}: {error_text}",
                    )

                async for raw_line in resp.content:
                    line = raw_line.decode("utf-8").strip()
                    if not line.startswith("data: "):
                        continue

                    data_str = line[6:]
                    if data_str == "[DONE]":
                        break

                    try:
                        data = json.loads(data_str)
                        choices = data.get("choices", [])
                        if choices:
                            token = choices[0].get("delta", {}).get("content")
                            if token:
                                yield token
                    except json.JSONDecodeError:
                        continue

        except aiohttp.ClientError as exc:
            raise AgentProcessingError(f"Streaming error: {exc}", cause=exc)

    async def close(self) -> None:
        if self._session and not self._session.closed:
            await self._session.close()

    async def _get_session(self) -> aiohttp.ClientSession:
        if self._session is None or self._session.closed:
            kwargs: Dict[str, Any] = {
                "headers": {
                    "Authorization": f"Bearer {self._api_key}",
                    "Content-Type": "application/json",
                    "HTTP-Referer": "https://localhost:3000",
                    "X-Title": "Chatbot-UIT",
                },
            }
            if self._timeout is not None:
                kwargs["timeout"] = aiohttp.ClientTimeout(total=self._timeout)
            self._session = aiohttp.ClientSession(**kwargs)
        return self._session

    def _to_api_payload(self, request: AgentRequest, *, stream: bool) -> Dict[str, Any]:
        messages: List[Dict[str, str]] = []

        if request.context:
            if request.context.system_prompt:
                messages.append(
                    {"role": "system", "content": request.context.system_prompt}
                )
            for msg in request.context.messages:
                if msg.message_type == MessageType.TEXT:
                    messages.append(
                        {"role": msg.role.value, "content": msg.content}
                    )
        messages.append({"role": "user", "content": request.prompt})

        payload: Dict[str, Any] = {
            "model": request.model or self._default_model,
            "messages": messages,
            "stream": stream,
        }

        if request.max_tokens:
            payload["max_tokens"] = request.max_tokens
        if request.temperature is not None:
            payload["temperature"] = request.temperature

        if request.metadata:
            for key in ("top_p", "frequency_penalty", "presence_penalty"):
                if key in request.metadata:
                    payload[key] = request.metadata[key]

        return payload

    @staticmethod
    def _parse_response(data: Dict[str, Any], model_fallback: str, start_time: float, attempt: int) -> AgentResponse:
        choice = data["choices"][0]
        usage = data.get("usage", {})

        return AgentResponse(
            content=choice["message"]["content"],
            model_used=data.get("model", model_fallback),
            tokens_used=usage.get("total_tokens"),
            finish_reason=choice.get("finish_reason"),
            processing_time=time.time() - start_time,
            metadata={
                "provider": "openrouter",
                "attempt": attempt + 1,
            },
        )
