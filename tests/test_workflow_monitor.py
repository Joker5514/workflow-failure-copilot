"""Tests for the workflow_monitor module."""

from datetime import datetime, timezone
from unittest.mock import MagicMock, patch

import pytest

from workflow_monitor.workflow_monitor import FailedWorkflow, WorkflowMonitor


class TestFailedWorkflow:
    """Tests for the FailedWorkflow dataclass."""

    def test_create_failed_workflow(self):
        """Test creating a FailedWorkflow instance."""
        now = datetime.now(timezone.utc)
        failure = FailedWorkflow(
            repo_full_name="owner/repo",
            workflow_name="CI",
            workflow_id=123,
            run_id=456,
            run_url="https://github.com/owner/repo/actions/runs/456",
            branch="main",
            commit_sha="abc123def",
            conclusion="failure",
            created_at=now,
            updated_at=now,
            logs_url="https://github.com/owner/repo/actions/runs/456/logs",
            head_commit_message="Test commit",
        )

        assert failure.repo_full_name == "owner/repo"
        assert failure.workflow_name == "CI"
        assert failure.conclusion == "failure"
        assert failure.head_commit_message == "Test commit"


class TestWorkflowMonitor:
    """Tests for the WorkflowMonitor class."""

    def test_init_without_token_raises(self):
        """Test that initialization without token raises error."""
        with patch("workflow_monitor.workflow_monitor.config") as mock_config:
            mock_config.github_token = ""
            with pytest.raises(ValueError, match="GitHub token is required"):
                WorkflowMonitor()

    def test_init_with_token(self):
        """Test initialization with token."""
        with patch("workflow_monitor.workflow_monitor.Github") as mock_github:
            monitor = WorkflowMonitor(github_token="test-token")
            assert monitor.token == "test-token"
            mock_github.assert_called_once_with("test-token")

    @patch("workflow_monitor.workflow_monitor.Github")
    def test_get_repositories_from_list(self, mock_github):
        """Test getting repositories from configured list."""
        mock_gh = MagicMock()
        mock_github.return_value = mock_gh

        mock_repo = MagicMock()
        mock_repo.full_name = "owner/repo"
        mock_gh.get_repo.return_value = mock_repo

        with patch("workflow_monitor.workflow_monitor.config") as mock_config:
            mock_config.github_token = "test-token"
            mock_config.get_repos_list.return_value = ["owner/repo"]
            mock_config.github_org = None

            monitor = WorkflowMonitor()
            repos = monitor.get_repositories()

            assert len(repos) == 1
            mock_gh.get_repo.assert_called_once_with("owner/repo")

    @patch("workflow_monitor.workflow_monitor.Github")
    def test_get_failed_workflows(self, mock_github):
        """Test getting failed workflows from a repository."""
        mock_gh = MagicMock()
        mock_github.return_value = mock_gh

        # Create mock workflow run
        mock_run = MagicMock()
        mock_run.conclusion = "failure"
        mock_run.id = 123
        mock_run.name = "CI"
        mock_run.workflow_id = 1
        mock_run.html_url = "https://github.com/owner/repo/actions/runs/123"
        mock_run.head_branch = "main"
        mock_run.head_sha = "abc123"
        mock_run.created_at = datetime.now(timezone.utc)
        mock_run.updated_at = datetime.now(timezone.utc)
        mock_run.logs_url = "https://github.com/owner/repo/actions/runs/123/logs"
        mock_run.head_commit = MagicMock()
        mock_run.head_commit.message = "Test commit"

        mock_repo = MagicMock()
        mock_repo.full_name = "owner/repo"
        mock_repo.get_workflow_runs.return_value = [mock_run]

        with patch("workflow_monitor.workflow_monitor.config") as mock_config:
            mock_config.github_token = "test-token"
            mock_config.lookback_hours = 24

            monitor = WorkflowMonitor()
            failures = monitor.get_failed_workflows(mock_repo)

            assert len(failures) == 1
            assert failures[0].workflow_name == "CI"
            assert failures[0].conclusion == "failure"

    @patch("workflow_monitor.workflow_monitor.Github")
    def test_ignores_successful_runs(self, mock_github):
        """Test that successful runs are ignored."""
        mock_gh = MagicMock()
        mock_github.return_value = mock_gh

        # Create mock successful run
        mock_run = MagicMock()
        mock_run.conclusion = "success"
        mock_run.created_at = datetime.now(timezone.utc)

        mock_repo = MagicMock()
        mock_repo.full_name = "owner/repo"
        mock_repo.get_workflow_runs.return_value = [mock_run]

        with patch("workflow_monitor.workflow_monitor.config") as mock_config:
            mock_config.github_token = "test-token"
            mock_config.lookback_hours = 24

            monitor = WorkflowMonitor()
            failures = monitor.get_failed_workflows(mock_repo)

            assert len(failures) == 0
