"""Tests for the notification module."""

from datetime import datetime, timezone
from unittest.mock import MagicMock, patch

import pytest

from workflow_monitor.notification import NotificationManager, NotificationResult
from workflow_monitor.workflow_monitor import FailedWorkflow
from workflow_monitor.error_analyzer import ErrorAnalysis


class TestNotificationManager:
    """Tests for the NotificationManager class."""

    def test_init_without_token_raises(self):
        """Test that initialization without token raises error."""
        with patch("workflow_monitor.notification.config") as mock_config:
            mock_config.github_token = ""
            with pytest.raises(ValueError, match="GitHub token is required"):
                NotificationManager()

    @patch("workflow_monitor.notification.Github")
    def test_create_failure_issue_disabled(self, mock_github):
        """Test that issue creation can be disabled."""
        with patch("workflow_monitor.notification.config") as mock_config:
            mock_config.github_token = "test-token"
            mock_config.create_issues = False
            mock_config.get_assignees_list.return_value = []

            manager = NotificationManager()
            failure = _create_test_failure()

            result = manager.create_failure_issue(failure)

            assert not result.success
            assert "disabled" in result.error_message

    @patch("workflow_monitor.notification.Github")
    def test_generate_issue_title(self, mock_github):
        """Test issue title generation."""
        with patch("workflow_monitor.notification.config") as mock_config:
            mock_config.github_token = "test-token"
            mock_config.create_issues = True
            mock_config.get_assignees_list.return_value = []

            manager = NotificationManager()
            failure = _create_test_failure()

            title = manager._generate_issue_title(failure)

            assert "CI" in title
            assert "main" in title
            assert "🚨" in title

    @patch("workflow_monitor.notification.Github")
    def test_generate_issue_body_without_analysis(self, mock_github):
        """Test issue body generation without AI analysis."""
        with patch("workflow_monitor.notification.config") as mock_config:
            mock_config.github_token = "test-token"
            mock_config.create_issues = True
            mock_config.get_assignees_list.return_value = []

            manager = NotificationManager()
            failure = _create_test_failure()

            body = manager._generate_issue_body(failure, None)

            assert "CI" in body
            assert "owner/repo" in body
            assert "main" in body
            assert "failure" in body
            assert "Workflow Failure Copilot" in body

    @patch("workflow_monitor.notification.Github")
    def test_generate_issue_body_with_analysis(self, mock_github):
        """Test issue body generation with AI analysis."""
        with patch("workflow_monitor.notification.config") as mock_config:
            mock_config.github_token = "test-token"
            mock_config.create_issues = True
            mock_config.get_assignees_list.return_value = []

            manager = NotificationManager()
            failure = _create_test_failure()
            analysis = ErrorAnalysis(
                error_type="test_failure",
                error_summary="Tests failed due to assertion error",
                root_cause="The expected value doesn't match actual",
                suggested_fix="Update the test assertion",
                fix_confidence=0.75,
                requires_manual_intervention=True,
                relevant_files=["tests/test_main.py"],
                additional_context="Check line 42",
            )

            body = manager._generate_issue_body(failure, analysis)

            assert "AI Analysis" in body
            assert "test_failure" in body
            assert "75%" in body
            assert "Yes" in body  # Manual intervention required
            assert "tests/test_main.py" in body

    @patch("workflow_monitor.notification.Github")
    def test_create_failure_issue_existing(self, mock_github):
        """Test that existing issues are not duplicated."""
        mock_gh = MagicMock()
        mock_github.return_value = mock_gh

        mock_issue = MagicMock()
        mock_issue.number = 42
        mock_issue.html_url = "https://github.com/owner/repo/issues/42"
        mock_issue.title = "🚨 Workflow Failure: CI on main"

        mock_repo = MagicMock()
        mock_repo.get_issues.return_value = [mock_issue]
        mock_gh.get_repo.return_value = mock_repo

        with patch("workflow_monitor.notification.config") as mock_config:
            mock_config.github_token = "test-token"
            mock_config.create_issues = True
            mock_config.get_assignees_list.return_value = []

            manager = NotificationManager()
            failure = _create_test_failure()

            result = manager.create_failure_issue(failure)

            assert result.success
            assert result.issue_number == 42
            # Should not create a new issue
            mock_repo.create_issue.assert_not_called()


class TestNotificationResult:
    """Tests for the NotificationResult dataclass."""

    def test_successful_result(self):
        """Test creating a successful notification result."""
        result = NotificationResult(
            success=True,
            issue_number=123,
            issue_url="https://github.com/owner/repo/issues/123",
        )

        assert result.success
        assert result.issue_number == 123
        assert result.error_message is None

    def test_failed_result(self):
        """Test creating a failed notification result."""
        result = NotificationResult(
            success=False,
            error_message="Permission denied",
        )

        assert not result.success
        assert result.issue_number is None
        assert result.error_message == "Permission denied"


def _create_test_failure() -> FailedWorkflow:
    """Create a test FailedWorkflow instance."""
    return FailedWorkflow(
        repo_full_name="owner/repo",
        workflow_name="CI",
        workflow_id=1,
        run_id=123,
        run_url="https://github.com/owner/repo/actions/runs/123",
        branch="main",
        commit_sha="abc123def456",
        conclusion="failure",
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
        logs_url="https://github.com/owner/repo/actions/runs/123/logs",
        head_commit_message="Test commit",
    )
