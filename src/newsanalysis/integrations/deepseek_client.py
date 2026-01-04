"""DeepSeek API client - OpenAI-compatible wrapper with cost tracking."""

from datetime import datetime
from typing import Any, Dict, List, Optional

from openai import AsyncOpenAI
from pydantic import BaseModel

from newsanalysis.database.connection import DatabaseConnection
from newsanalysis.utils.exceptions import AIServiceError
from newsanalysis.utils.logging import get_logger

logger = get_logger(__name__)

# DeepSeek Pricing (January 2025)
# https://api-docs.deepseek.com/quick_start/pricing
DEEPSEEK_PRICING = {
    "deepseek-chat": {
        "input": 0.28 / 1_000_000,      # $0.28 per 1M input tokens
        "output": 0.42 / 1_000_000,     # $0.42 per 1M output tokens
        "cache_hit": 0.028 / 1_000_000, # 90% discount on cache hits
    },
}


class DeepSeekClient:
    """DeepSeek API client using OpenAI-compatible interface."""

    def __init__(
        self,
        api_key: str,
        db: DatabaseConnection,
        run_id: str,
        base_url: str = "https://api.deepseek.com",
        default_model: str = "deepseek-chat",
    ):
        """Initialize DeepSeek client.

        Args:
            api_key: DeepSeek API key.
            db: Database connection for cost tracking.
            run_id: Current pipeline run ID.
            base_url: DeepSeek API base URL.
            default_model: Default model to use.
        """
        # Key insight: DeepSeek uses OpenAI's client library!
        self.client = AsyncOpenAI(
            api_key=api_key,
            base_url=base_url,
        )
        self.db = db
        self.run_id = run_id
        self.default_model = default_model

        logger.info(
            "deepseek_client_initialized",
            base_url=base_url,
            model=default_model,
        )

    async def create_completion(
        self,
        messages: List[Dict[str, str]],
        module: str,
        request_type: str,
        model: Optional[str] = None,
        response_format: Optional[type[BaseModel]] = None,
        temperature: float = 0.0,
        max_tokens: Optional[int] = None,
    ) -> Dict[str, Any]:
        """Create chat completion with cost tracking.

        Interface mirrors OpenAIClient for easy swapping.

        Args:
            messages: List of message dicts with 'role' and 'content'.
            module: Module name for tracking (e.g., "filter", "summarizer").
            request_type: Type of request (e.g., "classification", "summarization").
            model: Model to use (defaults to default_model).
            response_format: Pydantic model for structured outputs (uses JSON mode).
            temperature: Sampling temperature (0.0-2.0).
            max_tokens: Maximum tokens in response.

        Returns:
            Dict with 'content' and 'usage' keys.

        Raises:
            AIServiceError: If API call fails.
        """
        model = model or self.default_model
        started_at = datetime.now()

        logger.info(
            "deepseek_request",
            model=model,
            module=module,
            request_type=request_type,
        )

        try:
            params: Dict[str, Any] = {
                "model": model,
                "messages": messages,
                "temperature": temperature,
            }

            if max_tokens:
                params["max_tokens"] = max_tokens

            # DeepSeek supports JSON mode but not Pydantic structured outputs
            # Use JSON mode and parse manually
            if response_format:
                params["response_format"] = {"type": "json_object"}
                response = await self.client.chat.completions.create(**params)

                # Parse JSON response
                import json
                content_text = response.choices[0].message.content
                if content_text:
                    content_dict = json.loads(content_text)
                else:
                    raise AIServiceError("Empty response from DeepSeek API")
            else:
                response = await self.client.chat.completions.create(**params)
                content_dict = {"text": response.choices[0].message.content}

            usage = response.usage
            if not usage:
                raise AIServiceError("No usage information in response")

            input_tokens = usage.prompt_tokens
            output_tokens = usage.completion_tokens
            total_tokens = usage.total_tokens

            # Check for cache hit (DeepSeek reports this in usage)
            cache_hit_tokens = getattr(usage, 'prompt_cache_hit_tokens', 0) or 0

            cost = self._calculate_cost(model, input_tokens, output_tokens, cache_hit_tokens)

            self._track_api_call(
                module=module,
                model=model,
                request_type=request_type,
                input_tokens=input_tokens,
                output_tokens=output_tokens,
                total_tokens=total_tokens,
                cost=cost,
                success=True,
                started_at=started_at,
                cache_hit_tokens=cache_hit_tokens,
            )

            logger.info(
                "deepseek_response_success",
                model=model,
                input_tokens=input_tokens,
                output_tokens=output_tokens,
                cache_hit_tokens=cache_hit_tokens,
                cost=cost,
            )

            return {
                "content": content_dict,
                "usage": {
                    "input_tokens": input_tokens,
                    "output_tokens": output_tokens,
                    "total_tokens": total_tokens,
                    "cache_hit_tokens": cache_hit_tokens,
                    "cost": cost,
                },
            }

        except Exception as e:
            logger.error("deepseek_request_failed", model=model, error=str(e))
            self._track_api_call(
                module=module,
                model=model,
                request_type=request_type,
                input_tokens=0,
                output_tokens=0,
                total_tokens=0,
                cost=0.0,
                success=False,
                error_message=str(e),
                started_at=started_at,
            )
            raise AIServiceError(f"DeepSeek API call failed: {e}") from e

    def _calculate_cost(
        self,
        model: str,
        input_tokens: int,
        output_tokens: int,
        cache_hit_tokens: int = 0,
    ) -> float:
        """Calculate cost with cache hit discount.

        Args:
            model: Model name.
            input_tokens: Total input tokens.
            output_tokens: Output tokens generated.
            cache_hit_tokens: Tokens served from cache.

        Returns:
            Cost in USD.
        """
        pricing = DEEPSEEK_PRICING.get(model, DEEPSEEK_PRICING["deepseek-chat"])

        # Cache hits get 90% discount
        regular_input = input_tokens - cache_hit_tokens
        cache_cost = cache_hit_tokens * pricing["cache_hit"]
        regular_cost = regular_input * pricing["input"]
        output_cost = output_tokens * pricing["output"]

        return round(cache_cost + regular_cost + output_cost, 8)

    def _track_api_call(
        self,
        module: str,
        model: str,
        request_type: str,
        input_tokens: int,
        output_tokens: int,
        total_tokens: int,
        cost: float,
        success: bool,
        started_at: datetime,
        error_message: Optional[str] = None,
        cache_hit_tokens: int = 0,
    ) -> None:
        """Track API call in database.

        Args:
            module: Module making the call.
            model: Model used.
            request_type: Type of request.
            input_tokens: Input tokens used.
            output_tokens: Output tokens generated.
            total_tokens: Total tokens.
            cost: Cost in USD.
            success: Whether call succeeded.
            started_at: Start timestamp.
            error_message: Error message if failed.
            cache_hit_tokens: Tokens served from cache.
        """
        try:
            query = """
                INSERT INTO api_calls (
                    run_id, module, model, request_type, batch_id,
                    input_tokens, output_tokens, total_tokens, cost,
                    success, error_message, created_at, completed_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """
            params = (
                self.run_id,
                module,
                f"deepseek:{model}",  # Prefix to identify provider
                request_type,
                None,
                input_tokens,
                output_tokens,
                total_tokens,
                cost,
                success,
                error_message,
                started_at,
                datetime.now(),
            )
            self.db.execute(query, params)
            self.db.commit()
        except Exception as e:
            logger.error("failed_to_track_api_call", error=str(e))

    async def check_daily_cost_limit(self, daily_limit: float) -> bool:
        """Check if daily cost limit exceeded.

        Args:
            daily_limit: Daily cost limit in USD.

        Returns:
            True if under limit, False if exceeded.
        """
        try:
            query = """
                SELECT SUM(cost) as total_cost
                FROM api_calls
                WHERE DATE(created_at) = DATE('now')
            """
            cursor = self.db.execute(query)
            row = cursor.fetchone()
            total_cost = row["total_cost"] or 0.0
            return total_cost < daily_limit
        except Exception as e:
            logger.error("cost_check_failed", error=str(e))
            return True  # Fail open
