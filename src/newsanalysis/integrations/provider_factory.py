"""LLM Provider factory with fallback support."""

from enum import Enum
from typing import Any, Dict, List, Optional, Protocol

from pydantic import BaseModel

from newsanalysis.core.config import Config
from newsanalysis.database.connection import DatabaseConnection
from newsanalysis.utils.logging import get_logger

logger = get_logger(__name__)


class LLMProvider(str, Enum):
    """Available LLM providers."""

    OPENAI = "openai"
    DEEPSEEK = "deepseek"
    GEMINI = "gemini"


class LLMClient(Protocol):
    """Protocol for LLM clients - ensures consistent interface."""

    async def create_completion(
        self,
        messages: List[Dict[str, str]],
        module: str,
        request_type: str,
        model: Optional[str] = None,
        response_format: Optional[type[BaseModel]] = None,
        temperature: float = 0.0,
        max_tokens: Optional[int] = None,
    ) -> Dict[str, Any]: ...

    async def check_daily_cost_limit(self, daily_limit: float) -> bool: ...


class ProviderFactory:
    """Factory for creating LLM clients with fallback support."""

    def __init__(self, config: Config, db: DatabaseConnection, run_id: str):
        """Initialize factory.

        Args:
            config: Application configuration.
            db: Database connection.
            run_id: Pipeline run ID.
        """
        self.config = config
        self.db = db
        self.run_id = run_id
        self._clients: Dict[LLMProvider, LLMClient] = {}

        logger.info("provider_factory_initialized", run_id=run_id)

    def get_classification_client(self) -> LLMClient:
        """Get client for classification tasks.

        Uses DeepSeek by default (cheapest for high-volume classification).
        Falls back to OpenAI if DeepSeek unavailable.

        Returns:
            LLM client instance.
        """
        provider = LLMProvider(self.config.classification_provider)
        return self._get_or_create_client(provider, fallback=LLMProvider.OPENAI)

    def get_summarization_client(self) -> LLMClient:
        """Get client for summarization tasks.

        Uses Gemini by default (good quality, reasonable cost).
        Falls back to OpenAI if Gemini unavailable.

        Returns:
            LLM client instance.
        """
        provider = LLMProvider(self.config.summarization_provider)
        return self._get_or_create_client(provider, fallback=LLMProvider.OPENAI)

    def get_digest_client(self) -> LLMClient:
        """Get client for digest generation.

        Uses Gemini by default.
        Falls back to OpenAI if Gemini unavailable.

        Returns:
            LLM client instance.
        """
        provider = LLMProvider(self.config.digest_provider)
        return self._get_or_create_client(provider, fallback=LLMProvider.OPENAI)

    def _get_or_create_client(
        self,
        provider: LLMProvider,
        fallback: Optional[LLMProvider] = None,
    ) -> LLMClient:
        """Get or create client for provider with optional fallback.

        Args:
            provider: Requested provider.
            fallback: Fallback provider if requested one unavailable.

        Returns:
            LLM client instance.

        Raises:
            ValueError: If no client available for provider.
        """
        # Return cached client if available
        if provider in self._clients:
            return self._clients[provider]

        # Try to create client for requested provider
        client = self._create_client(provider)

        if client is None and fallback:
            logger.warning(
                "provider_unavailable_using_fallback",
                requested=provider.value,
                fallback=fallback.value,
            )
            client = self._create_client(fallback)

        if client is None:
            raise ValueError(f"No LLM client available for {provider.value}")

        self._clients[provider] = client
        return client

    def _create_client(self, provider: LLMProvider) -> Optional[LLMClient]:
        """Create client for specific provider.

        Args:
            provider: Provider to create client for.

        Returns:
            LLM client instance or None if unavailable.
        """
        if provider == LLMProvider.DEEPSEEK:
            if not self.config.deepseek_api_key:
                logger.warning("deepseek_api_key_not_configured")
                return None

            from newsanalysis.integrations.deepseek_client import DeepSeekClient

            return DeepSeekClient(
                api_key=self.config.deepseek_api_key,
                db=self.db,
                run_id=self.run_id,
                base_url=self.config.deepseek_base_url,
                default_model=self.config.deepseek_model,
            )

        elif provider == LLMProvider.GEMINI:
            if not self.config.google_api_key:
                logger.warning("google_api_key_not_configured")
                return None

            from newsanalysis.integrations.gemini_client import GeminiClient

            return GeminiClient(
                api_key=self.config.google_api_key,
                db=self.db,
                run_id=self.run_id,
                default_model=self.config.gemini_model,
            )

        elif provider == LLMProvider.OPENAI:
            if not self.config.openai_api_key:
                logger.warning("openai_api_key_not_configured")
                return None

            from newsanalysis.integrations.openai_client import OpenAIClient

            return OpenAIClient(
                api_key=self.config.openai_api_key,
                db=self.db,
                run_id=self.run_id,
                default_model=self.config.model_mini,
            )

        return None
