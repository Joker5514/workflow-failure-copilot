"""Tests for the configuration module."""

import os
from unittest.mock import patch

from workflow_monitor.config import Config


class TestConfig:
    """Tests for the Config class."""

    def test_default_values(self):
        """Test that default values are set correctly."""
        with patch.dict(os.environ, {}, clear=True):
            config = Config()
            assert config.ai_provider == "openai"
            assert config.dashboard_port == 5000
            assert config.max_retries == 3
            assert config.lookback_hours == 24

    def test_from_environment(self):
        """Test that config reads from environment variables."""
        env = {
            "GITHUB_TOKEN": "test-token",
            "AI_PROVIDER": "anthropic",
            "AI_MODEL": "claude-3-opus-20240229",
            "DASHBOARD_PORT": "8080",
            "MAX_RETRIES": "5",
        }
        with patch.dict(os.environ, env, clear=True):
            config = Config()
            assert config.github_token == "test-token"
            assert config.ai_provider == "anthropic"
            assert config.ai_model == "claude-3-opus-20240229"
            assert config.dashboard_port == 8080
            assert config.max_retries == 5

    def test_validate_missing_github_token(self):
        """Test validation fails when GitHub token is missing."""
        with patch.dict(os.environ, {}, clear=True):
            config = Config()
            errors = config.validate()
            assert "GITHUB_TOKEN is required" in errors

    def test_validate_invalid_ai_provider(self):
        """Test validation fails for invalid AI provider."""
        env = {
            "GITHUB_TOKEN": "test-token",
            "AI_PROVIDER": "invalid",
        }
        with patch.dict(os.environ, env, clear=True):
            config = Config()
            errors = config.validate()
            assert any("Invalid AI_PROVIDER" in e for e in errors)

    def test_validate_missing_openai_key(self):
        """Test validation fails when OpenAI key is missing."""
        env = {
            "GITHUB_TOKEN": "test-token",
            "AI_PROVIDER": "openai",
        }
        with patch.dict(os.environ, env, clear=True):
            config = Config()
            errors = config.validate()
            assert any("OPENAI_API_KEY is required" in e for e in errors)

    def test_validate_missing_anthropic_key(self):
        """Test validation fails when Anthropic key is missing."""
        env = {
            "GITHUB_TOKEN": "test-token",
            "AI_PROVIDER": "anthropic",
        }
        with patch.dict(os.environ, env, clear=True):
            config = Config()
            errors = config.validate()
            assert any("ANTHROPIC_API_KEY is required" in e for e in errors)

    def test_get_repos_list(self):
        """Test parsing of comma-separated repos list."""
        env = {
            "GITHUB_REPOS": "owner/repo1, owner/repo2 , owner/repo3",
        }
        with patch.dict(os.environ, env, clear=True):
            config = Config()
            repos = config.get_repos_list()
            assert repos == ["owner/repo1", "owner/repo2", "owner/repo3"]

    def test_get_repos_list_empty(self):
        """Test empty repos list returns empty list."""
        with patch.dict(os.environ, {}, clear=True):
            config = Config()
            repos = config.get_repos_list()
            assert repos == []

    def test_get_assignees_list(self):
        """Test parsing of comma-separated assignees list."""
        env = {
            "ISSUE_ASSIGNEES": "user1, user2",
        }
        with patch.dict(os.environ, env, clear=True):
            config = Config()
            assignees = config.get_assignees_list()
            assert assignees == ["user1", "user2"]
