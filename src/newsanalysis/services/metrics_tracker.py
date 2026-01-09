"""Metrics tracking service for pipeline monitoring and observability."""

import time
from datetime import datetime
from typing import Dict, Any, Optional
from collections import defaultdict

from newsanalysis.utils.logging import get_logger

logger = get_logger(__name__)


class MetricsTracker:
    """Track and aggregate metrics across pipeline stages."""

    def __init__(self):
        """Initialize MetricsTracker with empty metrics."""
        self.metrics: Dict[str, Any] = defaultdict(int)
        self.timers: Dict[str, float] = {}
        self.stage_metrics: Dict[str, Dict[str, Any]] = {}
        self.start_time: Optional[float] = None

    def start_pipeline(self) -> None:
        """Mark the start of pipeline execution."""
        self.start_time = time.time()
        self.metrics.clear()
        self.timers.clear()
        self.stage_metrics.clear()
        logger.info("pipeline_started", timestamp=datetime.now().isoformat())

    def start_timer(self, timer_name: str) -> None:
        """
        Start a named timer.

        Args:
            timer_name: Name of the timer
        """
        self.timers[timer_name] = time.time()

    def stop_timer(self, timer_name: str) -> float:
        """
        Stop a named timer and return elapsed time.

        Args:
            timer_name: Name of the timer

        Returns:
            Elapsed time in seconds, or 0 if timer not found
        """
        if timer_name in self.timers:
            elapsed = time.time() - self.timers[timer_name]
            del self.timers[timer_name]
            return elapsed
        return 0.0

    def increment(self, metric_name: str, value: int = 1) -> None:
        """
        Increment a metric counter.

        Args:
            metric_name: Name of the metric
            value: Amount to increment (default: 1)
        """
        self.metrics[metric_name] += value

    def set_metric(self, metric_name: str, value: Any) -> None:
        """
        Set a metric to a specific value.

        Args:
            metric_name: Name of the metric
            value: Value to set
        """
        self.metrics[metric_name] = value

    def record_stage_metrics(self, stage_name: str, metrics: Dict[str, Any]) -> None:
        """
        Record metrics for a specific pipeline stage.

        Args:
            stage_name: Name of the pipeline stage
            metrics: Dictionary of metrics for this stage
        """
        self.stage_metrics[stage_name] = {
            **metrics,
            "timestamp": datetime.now().isoformat(),
        }

        logger.info(
            f"stage_metrics_{stage_name}",
            stage=stage_name,
            **metrics
        )

    def get_pipeline_duration(self) -> float:
        """
        Get total pipeline duration in seconds.

        Returns:
            Duration in seconds, or 0 if pipeline not started
        """
        if self.start_time is None:
            return 0.0
        return time.time() - self.start_time

    def get_metrics_summary(self) -> Dict[str, Any]:
        """
        Get comprehensive metrics summary.

        Returns:
            Dictionary with all metrics and statistics
        """
        pipeline_duration = self.get_pipeline_duration()

        summary = {
            "pipeline_duration_seconds": round(pipeline_duration, 2),
            "timestamp": datetime.now().isoformat(),
            "overall_metrics": dict(self.metrics),
            "stage_metrics": dict(self.stage_metrics),
        }

        # Calculate rates if applicable
        if pipeline_duration > 0:
            for metric_name, value in self.metrics.items():
                if isinstance(value, (int, float)) and "count" in metric_name.lower():
                    rate_name = f"{metric_name}_per_second"
                    summary[rate_name] = round(value / pipeline_duration, 2)

        return summary

    def log_metrics_summary(self) -> None:
        """Log comprehensive metrics summary."""
        summary = self.get_metrics_summary()

        logger.info(
            "pipeline_metrics_summary",
            duration_seconds=summary["pipeline_duration_seconds"],
            overall_metrics=summary["overall_metrics"],
            stage_count=len(summary["stage_metrics"]),
        )

        # Log detailed stage metrics
        for stage_name, stage_data in summary["stage_metrics"].items():
            logger.info(
                f"stage_summary_{stage_name}",
                stage=stage_name,
                **{k: v for k, v in stage_data.items() if k != "timestamp"}
            )

    def get_image_pipeline_metrics(self) -> Dict[str, Any]:
        """
        Get image-specific pipeline metrics.

        Returns:
            Dictionary with image extraction and download metrics
        """
        image_metrics = {
            "images_extracted": self.metrics.get("images_extracted_count", 0),
            "images_downloaded": self.metrics.get("images_downloaded_count", 0),
            "images_failed": self.metrics.get("images_failed_count", 0),
            "images_cached": self.metrics.get("images_cached_count", 0),
            "circuit_breaker_trips": self.metrics.get("circuit_breaker_trips", 0),
        }

        # Calculate success rate
        total_attempts = image_metrics["images_downloaded"] + image_metrics["images_failed"]
        if total_attempts > 0:
            image_metrics["download_success_rate"] = round(
                image_metrics["images_downloaded"] / total_attempts * 100, 2
            )
        else:
            image_metrics["download_success_rate"] = 0.0

        # Calculate extraction rate
        if image_metrics["images_extracted"] > 0:
            image_metrics["download_rate"] = round(
                image_metrics["images_downloaded"] / image_metrics["images_extracted"] * 100, 2
            )
        else:
            image_metrics["download_rate"] = 0.0

        return image_metrics

    def check_health(self) -> Dict[str, Any]:
        """
        Perform health check based on metrics.

        Returns:
            Health status dictionary with warnings/errors
        """
        health = {
            "status": "healthy",
            "warnings": [],
            "errors": [],
        }

        # Check image download success rate
        image_metrics = self.get_image_pipeline_metrics()
        success_rate = image_metrics.get("download_success_rate", 100.0)

        if success_rate < 50:
            health["status"] = "unhealthy"
            health["errors"].append(
                f"Image download success rate critically low: {success_rate}%"
            )
        elif success_rate < 80:
            health["status"] = "degraded"
            health["warnings"].append(
                f"Image download success rate below target: {success_rate}%"
            )

        # Check circuit breaker trips
        breaker_trips = image_metrics.get("circuit_breaker_trips", 0)
        if breaker_trips > 0:
            health["warnings"].append(
                f"Circuit breaker tripped {breaker_trips} times"
            )

        # Check for failures
        failures = self.metrics.get("images_failed_count", 0)
        if failures > 10:
            health["warnings"].append(
                f"High number of image failures: {failures}"
            )

        return health
