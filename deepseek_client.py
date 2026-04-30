#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""DeepSeek OpenAI-compatible API client."""

from __future__ import annotations

from typing import Any, Dict, Iterator, List, Literal, Optional

from openai import OpenAI

from config_store import CONFIG_PATH, load_config


Message = Dict[str, Any]
ThinkingType = Literal["enabled", "disabled"]
ReasoningEffort = Literal["high", "max"]


class DeepSeekClient:
    """Small client for DeepSeek's OpenAI-compatible Chat API."""

    DEFAULT_BASE_URL = "https://api.deepseek.com"
    DEFAULT_MODEL = "deepseek-v4-pro"
    FLASH_MODEL = "deepseek-v4-flash"

    def __init__(
        self,
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
    ) -> None:
        config = load_config()
        self.api_key = api_key or str(config.get("DEEPSEEK_API_KEY") or "").strip()
        if not self.api_key:
            raise ValueError(
                f"Missing DeepSeek API key. Open API Settings or fill {CONFIG_PATH.name}."
            )

        self.base_url = (
            base_url
            or str(config.get("DEEPSEEK_BASE_URL") or "").strip()
            or self.DEFAULT_BASE_URL
        )
        self.client = OpenAI(api_key=self.api_key, base_url=self.base_url)

    def chat(
        self,
        messages: List[Message],
        model: str = DEFAULT_MODEL,
        thinking: Optional[ThinkingType] = None,
        reasoning_effort: ReasoningEffort = "high",
        temperature: Optional[float] = None,
        top_p: Optional[float] = None,
        max_tokens: Optional[int] = None,
        stream: bool = False,
        **kwargs: Any,
    ) -> Any:
        """Create a chat completion."""
        if not messages:
            raise ValueError("messages must contain at least one message.")

        params: Dict[str, Any] = {
            "model": model,
            "messages": messages,
            "stream": stream,
            **kwargs,
        }

        if temperature is not None:
            params["temperature"] = temperature
        if top_p is not None:
            params["top_p"] = top_p
        if max_tokens is not None:
            params["max_tokens"] = max_tokens

        if thinking is not None:
            if thinking not in ("enabled", "disabled"):
                raise ValueError('thinking must be "enabled", "disabled", or None.')
            if reasoning_effort not in ("high", "max"):
                raise ValueError('reasoning_effort must be "high" or "max".')

            extra_body = dict(params.pop("extra_body", {}) or {})
            extra_body["thinking"] = {"type": thinking}
            params["extra_body"] = extra_body

            if thinking == "enabled":
                params["reasoning_effort"] = reasoning_effort

        return self.client.chat.completions.create(**params)

    def simple_chat(
        self,
        user_message: str,
        system_message: str = "You are a helpful assistant.",
        **kwargs: Any,
    ) -> str:
        """Send one user message and return assistant text."""
        response = self.chat(
            messages=[
                {"role": "system", "content": system_message},
                {"role": "user", "content": user_message},
            ],
            **kwargs,
        )
        return response.choices[0].message.content or ""

    def stream_chat(
        self,
        messages: List[Message],
        include_reasoning: bool = False,
        **kwargs: Any,
    ) -> Iterator[str]:
        """Stream assistant text chunks."""
        response = self.chat(messages=messages, stream=True, **kwargs)
        for chunk in response:
            if not chunk.choices:
                continue

            delta = chunk.choices[0].delta
            reasoning = getattr(delta, "reasoning_content", None)
            content = getattr(delta, "content", None)

            if include_reasoning and reasoning:
                yield reasoning
            if content:
                yield content


DeepSeekV4Client = DeepSeekClient
