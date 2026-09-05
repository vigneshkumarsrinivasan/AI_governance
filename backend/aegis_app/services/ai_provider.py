"""
Pluggable AI provider abstraction (spec #87/#88).

The platform must never be locked to one LLM vendor, and must never silently
send tenant compliance data to an external model unless the deployment has
explicitly opted in. Selection is controlled entirely by Settings.AI_PROVIDER:

  - "rules" (default): no external call is made at all. This is the only mode
    that requires zero configuration and is what ships out of the box - it
    is what powers services/copilot.py's canned-but-data-grounded answers.
  - "anthropic" / "openai": real generative calls, only active when
    AI_API_KEY is also configured. Lazily imports the vendor SDK so
    environments that never configure a generative provider don't need it
    installed.

Nothing in this module is wired into copilot.py's default answer path yet
beyond an optional enrichment hook - see CopilotService.answer_query's use of
`generate_response()` below - because no API key is configured in this
deployment. Enabling it is a configuration change (env vars), not a code
change, which is the point of the abstraction.
"""

from abc import ABC, abstractmethod
from typing import Optional

from aegis_app.core.config import settings


class AIProviderError(RuntimeError):
    pass


class AIProvider(ABC):
    @abstractmethod
    def generate(self, system_prompt: str, user_query: str) -> str:
        ...


class AnthropicProvider(AIProvider):
    def __init__(self, api_key: str, model: str):
        try:
            import anthropic  # lazy import - only required when this provider is selected
        except ImportError as exc:
            raise AIProviderError(
                "AI_PROVIDER=anthropic requires the 'anthropic' package. Install it with `pip install anthropic`."
            ) from exc
        self._client = anthropic.Anthropic(api_key=api_key)
        self._model = model

    def generate(self, system_prompt: str, user_query: str) -> str:
        response = self._client.messages.create(
            model=self._model,
            max_tokens=1024,
            system=system_prompt,
            messages=[{"role": "user", "content": user_query}],
        )
        return "".join(block.text for block in response.content if hasattr(block, "text"))


class OpenAIProvider(AIProvider):
    def __init__(self, api_key: str, model: str):
        try:
            import openai  # lazy import - only required when this provider is selected
        except ImportError as exc:
            raise AIProviderError(
                "AI_PROVIDER=openai requires the 'openai' package. Install it with `pip install openai`."
            ) from exc
        self._client = openai.OpenAI(api_key=api_key)
        self._model = model

    def generate(self, system_prompt: str, user_query: str) -> str:
        response = self._client.chat.completions.create(
            model=self._model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_query},
            ],
        )
        return response.choices[0].message.content or ""


def get_configured_provider() -> Optional[AIProvider]:
    """
    Returns an AIProvider instance if a generative provider is explicitly
    configured (AI_PROVIDER + AI_API_KEY both set to something other than the
    default), otherwise None - callers must fall back to rules-based logic.
    """
    if settings.AI_PROVIDER == "rules" or not settings.AI_API_KEY:
        return None
    if settings.AI_PROVIDER == "anthropic":
        return AnthropicProvider(settings.AI_API_KEY, settings.AI_MODEL or "claude-sonnet-4-5")
    if settings.AI_PROVIDER == "openai":
        return OpenAIProvider(settings.AI_API_KEY, settings.AI_MODEL or "gpt-4o")
    raise AIProviderError(f"Unknown AI_PROVIDER '{settings.AI_PROVIDER}'. Expected: rules | anthropic | openai.")
