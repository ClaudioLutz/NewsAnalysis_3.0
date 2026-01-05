"""Google Gemini API client with cost tracking."""

import asyncio
import json
from datetime import datetime
from typing import Any, Dict, List, Optional

try:
    from google import genai
    USE_NEW_API = True
except ImportError:
    import google.generativeai as genai
    USE_NEW_API = False

from pydantic import BaseModel

from newsanalysis.database.connection import DatabaseConnection
from newsanalysis.utils.exceptions import AIServiceError
from newsanalysis.utils.logging import get_logger

logger = get_logger(__name__)

# Retry configuration
MAX_RETRIES = 3
RETRY_DELAY_BASE = 1.0  # Base delay in seconds (exponential backoff)

# Gemini Pricing (January 2025)
# https://ai.google.dev/gemini-api/docs/pricing
GEMINI_PRICING = {
    "gemini-2.0-flash": {
        "input": 0.10 / 1_000_000,   # $0.10 per 1M input tokens
        "output": 0.40 / 1_000_000,  # $0.40 per 1M output tokens
    },
    "gemini-2.0-flash-lite": {
        "input": 0.075 / 1_000_000,
        "output": 0.30 / 1_000_000,
    },
    "gemini-1.5-flash": {
        "input": 0.075 / 1_000_000,
        "output": 0.30 / 1_000_000,
    },
}


class GeminiClient:
    """Google Gemini API client with cost tracking."""

    def __init__(
        self,
        api_key: str,
        db: DatabaseConnection,
        run_id: str,
        default_model: str = "gemini-2.0-flash",
    ):
        """Initialize Gemini client.

        Args:
            api_key: Google API key.
            db: Database connection for cost tracking.
            run_id: Current pipeline run ID.
            default_model: Default model to use.
        """
        if USE_NEW_API:
            self.client = genai.Client(api_key=api_key)
        else:
            genai.configure(api_key=api_key)
            self.client = None

        self.api_key = api_key
        self.db = db
        self.run_id = run_id
        self.default_model = default_model

        logger.info("gemini_client_initialized", model=default_model, use_new_api=USE_NEW_API)

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
        """Create completion with Gemini.

        Converts OpenAI-style messages to Gemini format for compatibility.

        Args:
            messages: List of message dicts with 'role' and 'content'.
            module: Module name for tracking.
            request_type: Type of request.
            model: Model to use (defaults to default_model).
            response_format: Pydantic model for structured outputs.
            temperature: Sampling temperature.
            max_tokens: Maximum tokens in response.

        Returns:
            Dict with 'content' and 'usage' keys.

        Raises:
            AIServiceError: If API call fails.
        """
        model_name = model or self.default_model
        started_at = datetime.now()

        logger.info(
            "gemini_request",
            model=model_name,
            module=module,
            request_type=request_type,
        )

        try:
            if USE_NEW_API:
                # New google.genai API
                system_instruction, user_content = self._convert_messages(messages)

                config_dict = {
                    "temperature": temperature,
                    "max_output_tokens": max_tokens or 4096,
                }

                if response_format:
                    config_dict["response_mime_type"] = "application/json"

                # Build contents with proper system instruction handling
                if system_instruction:
                    config_dict["system_instruction"] = system_instruction
                contents = [{"role": "user", "parts": [{"text": user_content}]}]

                # Retry loop with exponential backoff for transient failures
                last_error = None
                for attempt in range(MAX_RETRIES):
                    try:
                        response = await asyncio.to_thread(
                            self.client.models.generate_content,
                            model=model_name,
                            contents=contents,
                            config=config_dict,
                        )
                        break
                    except Exception as e:
                        last_error = e
                        error_str = str(e).lower()
                        # Retry on rate limit or server errors
                        if "429" in error_str or "rate" in error_str or "quota" in error_str or "500" in error_str or "503" in error_str:
                            if attempt < MAX_RETRIES - 1:
                                delay = RETRY_DELAY_BASE * (2 ** attempt)
                                logger.warning(
                                    "gemini_retry",
                                    attempt=attempt + 1,
                                    delay=delay,
                                    error=str(e)[:100],
                                )
                                await asyncio.sleep(delay)
                                continue
                        raise
                else:
                    raise last_error  # type: ignore

                # Extract content with empty response check
                if not response.text:
                    raise AIServiceError("Empty response from Gemini API")

                if response_format:
                    content_dict = json.loads(response.text)
                    # Gemini sometimes wraps response in a list - extract first element
                    if isinstance(content_dict, list) and len(content_dict) > 0:
                        content_dict = content_dict[0]
                else:
                    content_dict = {"text": response.text}

                # Get token counts
                usage = response.usage_metadata
                input_tokens = usage.prompt_token_count
                output_tokens = usage.candidates_token_count
                total_tokens = usage.total_token_count

            else:
                # Old google.generativeai API
                generation_config = genai.GenerationConfig(
                    temperature=temperature,
                    max_output_tokens=max_tokens or 4096,
                )

                # Request JSON output if structured response needed
                if response_format:
                    generation_config.response_mime_type = "application/json"

                # Convert OpenAI messages to Gemini format
                system_instruction, contents = self._convert_messages(messages)

                if system_instruction:
                    gemini_model = genai.GenerativeModel(
                        model_name=model_name,
                        generation_config=generation_config,
                        system_instruction=system_instruction,
                    )
                else:
                    gemini_model = genai.GenerativeModel(
                        model_name=model_name,
                        generation_config=generation_config,
                    )

                # Retry loop with exponential backoff for transient failures
                last_error = None
                for attempt in range(MAX_RETRIES):
                    try:
                        response = await asyncio.to_thread(
                            gemini_model.generate_content,
                            contents,
                        )
                        break
                    except Exception as e:
                        last_error = e
                        error_str = str(e).lower()
                        # Retry on rate limit or server errors
                        if "429" in error_str or "rate" in error_str or "quota" in error_str or "500" in error_str or "503" in error_str:
                            if attempt < MAX_RETRIES - 1:
                                delay = RETRY_DELAY_BASE * (2 ** attempt)
                                logger.warning(
                                    "gemini_retry",
                                    attempt=attempt + 1,
                                    delay=delay,
                                    error=str(e)[:100],
                                )
                                await asyncio.sleep(delay)
                                continue
                        raise
                else:
                    raise last_error  # type: ignore

                # Extract content with empty response check
                if not response.text:
                    raise AIServiceError("Empty response from Gemini API")

                if response_format:
                    content_dict = json.loads(response.text)
                    # Gemini sometimes wraps response in a list - extract first element
                    if isinstance(content_dict, list) and len(content_dict) > 0:
                        content_dict = content_dict[0]
                else:
                    content_dict = {"text": response.text}

                # Get token counts from usage metadata
                usage = response.usage_metadata
                input_tokens = usage.prompt_token_count
                output_tokens = usage.candidates_token_count
                total_tokens = usage.total_token_count

            cost = self._calculate_cost(model_name, input_tokens, output_tokens)

            self._track_api_call(
                module=module,
                model=model_name,
                request_type=request_type,
                input_tokens=input_tokens,
                output_tokens=output_tokens,
                total_tokens=total_tokens,
                cost=cost,
                success=True,
                started_at=started_at,
            )

            logger.info(
                "gemini_response_success",
                model=model_name,
                input_tokens=input_tokens,
                output_tokens=output_tokens,
                cost=cost,
            )

            return {
                "content": content_dict,
                "usage": {
                    "input_tokens": input_tokens,
                    "output_tokens": output_tokens,
                    "total_tokens": total_tokens,
                    "cost": cost,
                },
            }

        except Exception as e:
            logger.error("gemini_request_failed", model=model_name, error=str(e))
            self._track_api_call(
                module=module,
                model=model_name,
                request_type=request_type,
                input_tokens=0,
                output_tokens=0,
                total_tokens=0,
                cost=0.0,
                success=False,
                error_message=str(e),
                started_at=started_at,
            )
            raise AIServiceError(f"Gemini API call failed: {e}") from e

    def _convert_messages(
        self, messages: List[Dict[str, str]]
    ) -> tuple[Optional[str], Any]:
        """Convert OpenAI message format to Gemini format.

        Args:
            messages: OpenAI-style messages.

        Returns:
            Tuple of (system_instruction, user_content or contents).
        """
        system_instruction = None
        user_content = ""

        for msg in messages:
            role = msg["role"]
            content = msg["content"]

            if role == "system":
                system_instruction = content
            elif role == "user":
                user_content = content

        if USE_NEW_API:
            return system_instruction, user_content
        else:
            # Old API format
            contents = []
            for msg in messages:
                role = msg["role"]
                content = msg["content"]

                if role == "system":
                    continue  # Already handled
                elif role == "user":
                    contents.append({"role": "user", "parts": [content]})
                elif role == "assistant":
                    contents.append({"role": "model", "parts": [content]})

            # If only one user message, just return the string
            if len(contents) == 1 and contents[0]["role"] == "user":
                return system_instruction, contents[0]["parts"][0]

            return system_instruction, contents

    def _calculate_cost(self, model: str, input_tokens: int, output_tokens: int) -> float:
        """Calculate cost of API call.

        Args:
            model: Model name.
            input_tokens: Input tokens used.
            output_tokens: Output tokens generated.

        Returns:
            Cost in USD.
        """
        pricing = GEMINI_PRICING.get(model, GEMINI_PRICING["gemini-2.0-flash"])
        cost = (input_tokens * pricing["input"]) + (output_tokens * pricing["output"])
        return round(cost, 8)

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
                f"gemini:{model}",  # Prefix to identify provider
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
            return True
