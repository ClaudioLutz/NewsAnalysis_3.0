"""Configuration loading from YAML files."""

from pathlib import Path
from typing import Any, Dict, List

import yaml

from newsanalysis.core.config import FeedConfig, PromptConfig, TopicConfig
from newsanalysis.utils.exceptions import ConfigurationError


class ConfigLoader:
    """Configuration loader for loading YAML configuration files."""

    def __init__(self, config_dir: Path = Path("config")):
        """Initialize config loader.

        Args:
            config_dir: Configuration directory path
        """
        self.config_dir = config_dir

    def load_prompt_config(self, prompt_name: str) -> PromptConfig:
        """Load prompt configuration from YAML.

        Args:
            prompt_name: Name of prompt file (without .yaml extension)

        Returns:
            PromptConfig object
        """
        return load_prompt_config(prompt_name, self.config_dir)

    def load_feeds_config(self) -> List[FeedConfig]:
        """Load news feeds configuration from YAML.

        Returns:
            List of FeedConfig objects
        """
        return load_feeds_config(self.config_dir)

    def load_topics_config(self) -> Dict[str, TopicConfig]:
        """Load topics configuration from YAML.

        Returns:
            Dictionary of topic name to TopicConfig
        """
        return load_topics_config(self.config_dir)


def load_yaml(file_path: Path) -> Dict[str, Any]:
    """Load YAML file.

    Args:
        file_path: Path to YAML file

    Returns:
        Parsed YAML data

    Raises:
        ConfigurationError: If file doesn't exist or is invalid
    """
    if not file_path.exists():
        raise ConfigurationError(f"Configuration file not found: {file_path}")

    try:
        with open(file_path, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f)
            if data is None:
                return {}
            return data
    except yaml.YAMLError as e:
        raise ConfigurationError(f"Invalid YAML in {file_path}: {e}") from e


def load_feeds_config(config_dir: Path = Path("config")) -> List[FeedConfig]:
    """Load news feeds configuration from YAML.

    Args:
        config_dir: Configuration directory path

    Returns:
        List of FeedConfig objects
    """
    feeds_path = config_dir / "feeds.yaml"

    data = load_yaml(feeds_path)
    feeds_data = data.get("feeds", [])

    feeds = []
    for feed_data in feeds_data:
        try:
            feed = FeedConfig(**feed_data)
            feeds.append(feed)
        except Exception as e:
            raise ConfigurationError(
                f"Invalid feed configuration: {feed_data.get('name', 'unknown')}: {e}"
            ) from e

    return feeds


def load_topics_config(config_dir: Path = Path("config")) -> Dict[str, TopicConfig]:
    """Load topics configuration from YAML.

    Args:
        config_dir: Configuration directory path

    Returns:
        Dictionary of topic name to TopicConfig
    """
    topics_path = config_dir / "topics.yaml"

    data = load_yaml(topics_path)

    topics = {}
    for topic_name, topic_data in data.items():
        try:
            topic = TopicConfig(**topic_data)
            topics[topic_name] = topic
        except Exception as e:
            raise ConfigurationError(
                f"Invalid topic configuration: {topic_name}: {e}"
            ) from e

    return topics


def load_prompt_config(
    prompt_name: str, config_dir: Path = Path("config")
) -> PromptConfig:
    """Load prompt configuration from YAML.

    Args:
        prompt_name: Name of prompt file (without .yaml extension)
        config_dir: Configuration directory path

    Returns:
        PromptConfig object
    """
    prompt_path = config_dir / "prompts" / f"{prompt_name}.yaml"

    data = load_yaml(prompt_path)

    try:
        prompt = PromptConfig(**data)
        return prompt
    except Exception as e:
        raise ConfigurationError(
            f"Invalid prompt configuration: {prompt_name}: {e}"
        ) from e


def save_yaml(data: Dict[str, Any], file_path: Path) -> None:
    """Save data to YAML file.

    Args:
        data: Data to save
        file_path: Path to save file

    Raises:
        ConfigurationError: If unable to save file
    """
    try:
        # Ensure parent directory exists
        file_path.parent.mkdir(parents=True, exist_ok=True)

        with open(file_path, "w", encoding="utf-8") as f:
            yaml.safe_dump(data, f, default_flow_style=False, allow_unicode=True)
    except Exception as e:
        raise ConfigurationError(f"Failed to save YAML to {file_path}: {e}") from e
