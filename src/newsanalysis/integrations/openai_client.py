"""OpenAI API client with cost tracking."""

import json
from datetime import datetime
from typing import Any, Dict, List, Optional

from openai import AsyncOpenAI
from pydantic import BaseModel

from newsanalysis.database.connection import DatabaseConnection
from newsanalysis.utils.exceptions import AIServiceError
from newsanalysis.utils.logging import get_logger

logger = get_logger(__name__)


# OpenAI Pricing (as of 2026-01-04)
# https://openai.com/api/pricing/
PRICING = {
    "gpt-4o-mini": {
        "input": 0.150 / 1_000_000,  # $0.150 per 1M input tokens
        "output": 0.600 / 1_000_000,  # $0.600 per 1M output tokens
    },
    "gpt-4o": {
        "input": 2.50 / 1_000_000,  # $2.50 per 1M input tokens
        "output": 10.00 / 1_000_000,  # $10.00 per 1M output tokens
    },
}


class OpenAIClient:
    """Wrapper for OpenAI API with cost tracking and structured outputs."""

    def __init__(
        self,
        api_key: str,
        db: DatabaseConnection,
        run_id: str,
        default_model: str = "gpt-4o-mini",
    ):
        """Initialize OpenAI client.

        Args:
            api_key: OpenAI API key.
            db: Database connection for cost tracking.
            run_id: Current pipeline run ID.
            default_model: Default model to use.
        """
        self.client = AsyncOpenAI(api_key=api_key)
        self.db = db
        self.run_id = run_id
        self.default_model = default_model

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
        """Create a chat completion with cost tracking.

        Args:
            messages: List of message dicts with 'role' and 'content'.
            module: Module name for tracking (e.g., "filter", "summarizer").
            request_type: Type of request (e.g., "classification", "summarization").
            model: Model to use (defaults to default_model).
            response_format: Pydantic model for structured outputs.
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
            "openai_request",
            model=model,
            module=module,
            request_type=request_type,
        )

        try:
            # Prepare request parameters
            params: Dict[str, Any] = {
                "model": model,
                "messages": messages,
                "temperature": temperature,
            }

            if max_tokens:
                params["max_tokens"] = max_tokens

            if response_format:
                # Use structured outputs with Pydantic model
                params["response_format"] = response_format

            # Make API call
            response = await self.client.chat.completions.create(**params)

            # Extract response content
            if response_format:
                # Parse structured output
                content = response.choices[0].message.parsed
                content_dict = content.model_dump() if content else {}
            else:
                # Plain text response
                content_dict = {"text": response.choices[0].message.content}

            # Extract usage information
            usage = response.usage
            if not usage:
                raise AIServiceError("No usage information in response")

            input_tokens = usage.prompt_tokens
            output_tokens = usage.completion_tokens
            total_tokens = usage.total_tokens

            # Calculate cost
            cost = self._calculate_cost(model, input_tokens, output_tokens)

            # Track API call in database
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
            )

            logger.info(
                "openai_response_success",
                model=model,
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
            logger.error(
                "openai_request_failed",
                model=model,
                module=module,
                error=str(e),
            )

            # Track failed API call
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

            raise AIServiceError(f"OpenAI API call failed: {e}") from e

    async def create_batch_completion(
        self,
        batch_requests: List[Dict[str, Any]],
        module: str,
        request_type: str,
    ) -> str:
        """Create a batch API request (for cost optimization).

        Note: Batch API is 50% cheaper but has 24h latency.
        Use for non-urgent summarization tasks.

        Args:
            batch_requests: List of request objects.
            module: Module name for tracking.
            request_type: Type of request.

        Returns:
            Batch ID for status checking.

        Raises:
            AIServiceError: If batch creation fails.
        """
        logger.info(
            "openai_batch_request",
            module=module,
            request_type=request_type,
            num_requests=len(batch_requests),
        )

        try:
            # Create batch file
            batch_file = await self.client.files.create(
                file=json.dumps(batch_requests).encode(),
                purpose="batch",
            )

            # Create batch job
            batch = await self.client.batches.create(
                input_file_id=batch_file.id,
                endpoint="/v1/chat/completions",
                completion_window="24h",
            )

            logger.info("batch_created", batch_id=batch.id)

            return batch.id

        except Exception as e:
            logger.error("batch_creation_failed", error=str(e))
            raise AIServiceError(f"Failed to create batch: {e}") from e

    async def check_batch_status(self, batch_id: str) -> Dict[str, Any]:
        """Check status of a batch job.

        Args:
            batch_id: Batch ID to check.

        Returns:
            Dict with batch status information.

        Raises:
            AIServiceError: If status check fails.
        """
        try:
            batch = await self.client.batches.retrieve(batch_id)

            status_info = {
                "id": batch.id,
                "status": batch.status,
                "created_at": batch.created_at,
                "completed_at": batch.completed_at,
                "failed_at": batch.failed_at,
                "request_counts": {
                    "total": batch.request_counts.total,
                    "completed": batch.request_counts.completed,
                    "failed": batch.request_counts.failed,
                },
            }

            if batch.status == "completed":
                status_info["output_file_id"] = batch.output_file_id
            elif batch.status == "failed":
                status_info["error_file_id"] = batch.error_file_id

            logger.info(
                "batch_status_check",
                batch_id=batch_id,
                status=batch.status,
            )

            return status_info

        except Exception as e:
            logger.error("batch_status_check_failed", batch_id=batch_id, error=str(e))
            raise AIServiceError(f"Failed to check batch status: {e}") from e

    async def retrieve_batch_results(
        self,
        batch_id: str,
    ) -> List[Dict[str, Any]]:
        """Retrieve results from a completed batch job.

        Args:
            batch_id: Batch ID to retrieve results from.

        Returns:
            List of result dictionaries.

        Raises:
            AIServiceError: If retrieval fails or batch is not completed.
        """
        try:
            # Check batch status
            status = await self.check_batch_status(batch_id)

            if status["status"] != "completed":
                raise AIServiceError(
                    f"Batch {batch_id} is not completed (status: {status['status']})"
                )

            # Get output file
            output_file_id = status.get("output_file_id")
            if not output_file_id:
                raise AIServiceError(f"No output file for batch {batch_id}")

            # Retrieve file content
            file_response = await self.client.files.content(output_file_id)
            content = file_response.read().decode("utf-8")

            # Parse JSONL results
            results = []
            for line in content.strip().split("\n"):
                if line:
                    result = json.loads(line)
                    results.append(result)

            logger.info(
                "batch_results_retrieved",
                batch_id=batch_id,
                num_results=len(results),
            )

            return results

        except Exception as e:
            logger.error(
                "batch_retrieval_failed",
                batch_id=batch_id,
                error=str(e),
            )
            raise AIServiceError(f"Failed to retrieve batch results: {e}") from e

    def _calculate_cost(self, model: str, input_tokens: int, output_tokens: int) -> float:
        """Calculate cost of API call.

        Args:
            model: Model name.
            input_tokens: Number of input tokens.
            output_tokens: Number of output tokens.

        Returns:
            Cost in USD.
        """
        if model not in PRICING:
            logger.warning("unknown_model_pricing", model=model)
            # Default to gpt-4o-mini pricing
            model = "gpt-4o-mini"

        pricing = PRICING[model]
        cost = (input_tokens * pricing["input"]) + (output_tokens * pricing["output"])

        return round(cost, 6)

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
        batch_id: Optional[str] = None,
    ) -> None:
        """Track API call in database.

        Args:
            module: Module name.
            model: Model name.
            request_type: Request type.
            input_tokens: Input tokens used.
            output_tokens: Output tokens used.
            total_tokens: Total tokens used.
            cost: Cost in USD.
            success: Whether call succeeded.
            started_at: When call started.
            error_message: Error message if failed.
            batch_id: Batch ID if batch request.
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
                model,
                request_type,
                batch_id,
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
            # Don't raise - tracking failure shouldn't break the pipeline

    async def check_daily_cost_limit(self, daily_limit: float) -> bool:
        """Check if daily cost limit has been exceeded.

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

            if total_cost >= daily_limit:
                logger.warning(
                    "daily_cost_limit_exceeded",
                    total_cost=total_cost,
                    limit=daily_limit,
                )
                return False

            logger.info(
                "daily_cost_check",
                total_cost=total_cost,
                limit=daily_limit,
                remaining=daily_limit - total_cost,
            )

            return True

        except Exception as e:
            logger.error("cost_check_failed", error=str(e))
            # Fail open - allow requests even if check fails
            return True
