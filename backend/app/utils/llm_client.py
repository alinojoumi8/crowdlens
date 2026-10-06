"""
LLM Client Wrapper
Unified OpenAI format API calls
Supports Ollama num_ctx parameter to prevent prompt truncation
"""

from .model_limits import anthropic_output_settings

import json
import os
import re
import time
from typing import Optional, Dict, Any, List
from openai import OpenAI
from openai import APIConnectionError, APITimeoutError, APIStatusError
import requests

from ..config import Config
from ..utils.logger import get_logger
from ..services.workflow_execution import transport_attempt


logger = get_logger('mirofish.llm_client')


class LLMClient:
    """LLM Client"""

    def __init__(
        self,
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
        model: Optional[str] = None,
        timeout: float = 300.0
    ):
        self.api_key = api_key or Config.LLM_API_KEY
        self.base_url = base_url or Config.LLM_BASE_URL
        self.model = model or Config.LLM_MODEL_NAME
        self.timeout = timeout

        if not self.api_key:
            raise ValueError("LLM_API_KEY not configured")

        self.client = OpenAI(
            api_key=self.api_key,
            base_url=self.base_url,
            timeout=timeout,
            max_retries=0,
        )

        # Ollama context window size — prevents prompt truncation.
        # Read from env OLLAMA_NUM_CTX, default 8192 (Ollama default is only 2048).
        self._num_ctx = int(os.environ.get('OLLAMA_NUM_CTX', '8192'))

    def _is_ollama(self) -> bool:
        """Check if we're talking to an Ollama server."""
        return '11434' in (self.base_url or '')

    def _is_anthropic_compatible(self) -> bool:
        """Check if we're talking to an Anthropic Messages compatible endpoint."""
        return 'anthropic' in (self.base_url or '') or (self.base_url or '').rstrip('/').endswith('/coding')

    def _chat_anthropic(
        self,
        messages: List[Dict[str, str]],
        temperature: float = 0.7,
        max_tokens: int = 4096,
        *, request_timeout=None, request_max_retries=None, usage_callback=None,
    ) -> str:
        """Send chat request to an Anthropic Messages compatible endpoint."""
        system_messages = [m.get("content", "") for m in messages if m.get("role") == "system"]
        chat_messages = [
            {"role": m.get("role", "user"), "content": m.get("content", "")}
            for m in messages
            if m.get("role") != "system"
        ]

        body: Dict[str, Any] = {
            "model": self.model,
            **anthropic_output_settings(self.model, max_tokens),
            "messages": chat_messages,
        }
        if system_messages:
            body["system"] = "\n\n".join(system_messages)
        if temperature is not None:
            body["temperature"] = temperature

        url = f"{self.base_url.rstrip('/')}/v1/messages"
        headers = {
            "x-api-key": self.api_key,
            "anthropic-version": "2023-06-01",
            "content-type": "application/json",
        }
        started = time.monotonic()
        try:
            response = self._post_anthropic_with_retry(url, headers, body,
                request_timeout=request_timeout, request_max_retries=request_max_retries)
            data = response.json()
        except Exception:
            if usage_callback:
                usage_callback('anthropic', self.model, {}, (time.monotonic() - started) * 1000)
            raise
        if usage_callback:
            usage_callback('anthropic', data.get('model', self.model), data.get('usage', {}),
                           (time.monotonic() - started) * 1000)

        text_parts = [
            item.get("text", "")
            for item in data.get("content", [])
            if item.get("type") == "text" and item.get("text")
        ]
        content = "\n".join(text_parts).strip()
        if not content:
            raise ValueError("Anthropic-compatible LLM returned no text content")
        return content

    def _post_anthropic_with_retry(
        self,
        url: str,
        headers: Dict[str, str],
        body: Dict[str, Any],
        *, request_timeout=None, request_max_retries=None,
    ) -> requests.Response:
        max_retries = int(os.environ.get("LLM_HTTP_MAX_RETRIES", "4")) if request_max_retries is None else request_max_retries
        base_delay = float(os.environ.get("LLM_HTTP_RETRY_BASE_SECONDS", "2"))
        max_delay = float(os.environ.get("LLM_HTTP_RETRY_MAX_SECONDS", "30"))
        last_error: Optional[Exception] = None

        for attempt in range(max_retries + 1):
            try:
                with transport_attempt(self.model, self.base_url, attempt + 1) as receipt:
                    response = requests.post(
                        url, headers=headers, json=body,
                        timeout=self.timeout if request_timeout is None else request_timeout,
                    )
                    receipt['http_status'] = getattr(response, 'status_code', 200)
                    try:
                        receipt['usage'] = response.json().get('usage')
                    except ValueError:
                        pass
                    response.raise_for_status()
                return response
            except (
                requests.exceptions.ConnectionError,
                requests.exceptions.Timeout,
                requests.exceptions.HTTPError,
            ) as exc:
                if isinstance(exc, requests.exceptions.HTTPError):
                    status_code = exc.response.status_code if exc.response is not None else 0
                    if status_code and status_code < 500 and status_code != 429:
                        raise
                last_error = exc
                if attempt >= max_retries:
                    raise
                logger.warning(
                    "Anthropic-compatible LLM request failed (attempt %s/%s): %s",
                    attempt + 1,
                    max_retries + 1,
                    exc,
                )
                delay = min(max_delay, base_delay * (2 ** attempt))
                time.sleep(delay)

        raise last_error or RuntimeError("Anthropic-compatible LLM request failed")

    def chat(
        self,
        messages: List[Dict[str, str]],
        temperature: float = 0.7,
        max_tokens: int = 4096,
        response_format: Optional[Dict] = None,
        *, request_timeout=None, request_max_retries=None, usage_callback=None,
    ) -> str:
        """
        Send chat request

        Args:
            messages: Message list
            temperature: Temperature parameter
            max_tokens: Max token count
            response_format: Response format (e.g., JSON mode)

        Returns:
            Model response text
        """
        if self._is_anthropic_compatible():
            return self._chat_anthropic(
                messages=messages,
                temperature=temperature,
                max_tokens=max_tokens,
                request_timeout=request_timeout, request_max_retries=request_max_retries, usage_callback=usage_callback,
            )

        kwargs = {
            "model": self.model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
        }

        if response_format:
            kwargs["response_format"] = response_format

        # For Ollama: pass num_ctx via extra_body to prevent prompt truncation
        if self._is_ollama() and self._num_ctx:
            kwargs["extra_body"] = {
                "options": {"num_ctx": self._num_ctx}
            }

        client = self.client
        overrides = {}
        if request_timeout is not None:
            overrides['timeout'] = request_timeout
        overrides['max_retries'] = 0
        if overrides:
            client = client.with_options(**overrides)
        started = time.monotonic()
        try:
            retries = request_max_retries if request_max_retries is not None else 2
            for attempt in range(retries + 1):
                try:
                    with transport_attempt(self.model, self.base_url, attempt + 1) as receipt:
                        response = client.chat.completions.create(**kwargs)
                        receipt['usage'] = response.usage.model_dump() if getattr(response, 'usage', None) else None
                        receipt['http_status'] = 200
                    break
                except (APIConnectionError, APITimeoutError, APIStatusError) as exc:
                    status = getattr(exc, 'status_code', None)
                    if attempt >= retries or (status and status < 500 and status != 429):
                        raise
                    time.sleep(min(30, 2 ** (attempt + 1)))
        except Exception:
            if usage_callback:
                usage_callback('openai_compatible', self.model, {}, (time.monotonic() - started) * 1000)
            raise
        if usage_callback:
            usage = response.usage.model_dump() if getattr(response, 'usage', None) else {}
            usage_callback('openai_compatible', response.model or self.model, usage, (time.monotonic() - started) * 1000)
        content = response.choices[0].message.content
        # Some models (like MiniMax M2.5) include <think>thinking content in response, need to remove
        content = re.sub(r'<think>[\s\S]*?</think>', '', content).strip()
        return content

    def chat_json(
        self,
        messages: List[Dict[str, str]],
        temperature: float = 0.3,
        max_tokens: int = 4096,
        disable_reasoning: bool = False,
        *, request_timeout=None, request_max_retries=None, usage_callback=None, response_callback=None,
    ) -> Dict[str, Any]:
        """
        Send chat request and return JSON

        Args:
            messages: Message list
            temperature: Temperature parameter
            max_tokens: Max token count
            disable_reasoning: Disable model thinking when Ollama JSON is required

        Returns:
            Parsed JSON object
        """
        if disable_reasoning and self._is_ollama():
            base_url = (self.base_url or "").rstrip("/")
            if base_url.endswith("/v1"):
                base_url = base_url[:-3]
            options: Dict[str, Any] = {
                "temperature": temperature,
                "num_predict": max_tokens,
            }
            if self._num_ctx:
                options["num_ctx"] = self._num_ctx
            started = time.monotonic()
            with transport_attempt(self.model, self.base_url) as receipt:
                native_response = requests.post(
                    f"{base_url}/api/chat",
                    json={"model": self.model, "messages": messages, "stream": False,
                          "think": False, "format": "json", "options": options},
                    timeout=self.timeout if request_timeout is None else request_timeout,
                )
                receipt['http_status'] = getattr(native_response, 'status_code', 200)
                native_response.raise_for_status()
                body = native_response.json()
                receipt['usage'] = {key: value for key, value in {
                    'input_tokens': body.get('prompt_eval_count'), 'output_tokens': body.get('eval_count')
                }.items() if value is not None}
            if usage_callback:
                usage_callback('ollama', body.get('model', self.model),
                    {'input_tokens': body.get('prompt_eval_count'), 'output_tokens': body.get('eval_count')},
                    (time.monotonic() - started) * 1000)
            response = (body.get("message") or {}).get("content", "")
            if not isinstance(response, str) or not response.strip():
                raise ValueError("Ollama returned no JSON content")
        else:
            response = self.chat(
                messages=messages,
                temperature=temperature,
                max_tokens=max_tokens,
                response_format={"type": "json_object"},
                **({k: v for k, v in dict(request_timeout=request_timeout,
                     request_max_retries=request_max_retries, usage_callback=usage_callback).items() if v is not None})
            )
        # Preserve completion text before JSON cleanup/parsing, including failures.
        # Opt-in observers own their private storage; nothing is logged globally.
        if response_callback is not None:
            response_callback(response)
        if not isinstance(response, str):
            raise ValueError("invalid_llm_response_text")
        # Clean markdown code block markers
        cleaned_response = response.strip()
        cleaned_response = re.sub(r'^```(?:json)?\s*\n?', '', cleaned_response, flags=re.IGNORECASE)
        cleaned_response = re.sub(r'\n?```\s*$', '', cleaned_response)
        cleaned_response = cleaned_response.strip()

        try:
            return json.loads(cleaned_response)
        except json.JSONDecodeError:
            raise ValueError("invalid_llm_json")
