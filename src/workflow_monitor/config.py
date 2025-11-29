"""
Configuration management for the workflow monitoring system.
"""

import os
from dataclasses import dataclass, field
from typing import Optional

from dotenv import load_dotenv

load_dotenv()


def _get_env(key: str, default: str = "") -> str:
    """Get environment variable with default."""
    return os.getenv(key, default)


def _get_env_optional(key: str) -> Optional[str]:
    """Get optional environment variable."""
    return os.getenv(key)


def _get_env_int(key: str, default: int) -> int:
    """Get integer environment variable with default."""
    return int(os.getenv(key, str(default)))


def _get_env_bool(key: str, default: bool = True) -> bool:
    """Get boolean environment variable with default."""
    return os.getenv(key, str(default).lower()).lower() == "true"


@dataclass
class Config:
    """Configuration settings for the workflow monitor."""

    # GitHub settings
    github_token: str = field(default_factory=lambda: _get_env("GITHUB_TOKEN", ""))
    github_org: Optional[str] = field(default_factory=lambda: _get_env_optional("GITHUB_ORG"))
    github_repos: Optional[str] = field(default_factory=lambda: _get_env_optional("GITHUB_REPOS"))

    # AI settings
    openai_api_key: str = field(default_factory=lambda: _get_env("OPENAI_API_KEY", ""))
    anthropic_api_key: str = field(default_factory=lambda: _get_env("ANTHROPIC_API_KEY", ""))
    ai_provider: str = field(default_factory=lambda: _get_env("AI_PROVIDER", "openai"))
    ai_model: str = field(default_factory=lambda: _get_env("AI_MODEL", "gpt-4"))

    # Dashboard settings
    dashboard_host: str = field(default_factory=lambda: _get_env("DASHBOARD_HOST", "0.0.0.0"))
    dashboard_port: int = field(default_factory=lambda: _get_env_int("DASHBOARD_PORT", 5000))
    dashboard_secret_key: str = field(
        default_factory=lambda: _get_env("DASHBOARD_SECRET_KEY", "change-me-in-production")
    )

    # Notification settings
    create_issues: bool = field(default_factory=lambda: _get_env_bool("CREATE_ISSUES", True))
    issue_assignees: Optional[str] = field(
        default_factory=lambda: _get_env_optional("ISSUE_ASSIGNEES")
    )

    # Retry settings
    max_retries: int = field(default_factory=lambda: _get_env_int("MAX_RETRIES", 3))
    retry_delay_seconds: int = field(
        default_factory=lambda: _get_env_int("RETRY_DELAY_SECONDS", 60)
    )

    # Monitoring settings
    check_interval_hours: int = field(
        default_factory=lambda: _get_env_int("CHECK_INTERVAL_HOURS", 1)
    )
    lookback_hours: int = field(default_factory=lambda: _get_env_int("LOOKBACK_HOURS", 24))

    def validate(self) -> list[str]:
        """Validate the configuration and return a list of errors."""
        errors = []

        if not self.github_token:
            errors.append("GITHUB_TOKEN is required")

        if self.ai_provider not in ("openai", "anthropic"):
            errors.append(f"Invalid AI_PROVIDER: {self.ai_provider}")

        if self.ai_provider == "openai" and not self.openai_api_key:
            errors.append("OPENAI_API_KEY is required when AI_PROVIDER is 'openai'")

        if self.ai_provider == "anthropic" and not self.anthropic_api_key:
            errors.append("ANTHROPIC_API_KEY is required when AI_PROVIDER is 'anthropic'")

        return errors

    def get_repos_list(self) -> list[str]:
        """Get the list of repositories to monitor."""
        if self.github_repos:
            return [r.strip() for r in self.github_repos.split(",") if r.strip()]
        return []

    def get_assignees_list(self) -> list[str]:
        """Get the list of issue assignees."""
        if self.issue_assignees:
            return [a.strip() for a in self.issue_assignees.split(",") if a.strip()]
        return []


# Global configuration instance
config = Config()
