"""
GitHub Issue notifications for workflow failures requiring manual help.
"""

import logging
from dataclasses import dataclass
from typing import Optional

from github import Github

from .config import config
from .error_analyzer import ErrorAnalysis
from .workflow_monitor import FailedWorkflow

logger = logging.getLogger(__name__)


@dataclass
class NotificationResult:
    """Result of a notification attempt."""

    success: bool
    issue_number: Optional[int] = None
    issue_url: Optional[str] = None
    error_message: Optional[str] = None


class NotificationManager:
    """Manages GitHub Issue notifications for workflow failures."""

    ISSUE_LABEL = "workflow-failure"

    def __init__(self, github_token: Optional[str] = None):
        """Initialize the notification manager.

        Args:
            github_token: GitHub token for authentication.
        """
        self.token = github_token or config.github_token
        if not self.token:
            raise ValueError("GitHub token is required")
        self.github = Github(self.token)
        self.create_issues = config.create_issues
        self.assignees = config.get_assignees_list()

    def create_failure_issue(
        self,
        failed_workflow: FailedWorkflow,
        error_analysis: Optional[ErrorAnalysis] = None,
    ) -> NotificationResult:
        """Create a GitHub issue for a workflow failure.

        Args:
            failed_workflow: The failed workflow.
            error_analysis: Optional AI analysis of the error.

        Returns:
            NotificationResult with the outcome.
        """
        if not self.create_issues:
            logger.info("Issue creation disabled")
            return NotificationResult(
                success=False,
                error_message="Issue creation disabled in configuration",
            )

        try:
            repo = self.github.get_repo(failed_workflow.repo_full_name)

            # Check if an issue already exists for this failure
            existing_issue = self._find_existing_issue(repo, failed_workflow)
            if existing_issue:
                logger.info(f"Issue already exists: {existing_issue.html_url}")
                return NotificationResult(
                    success=True,
                    issue_number=existing_issue.number,
                    issue_url=existing_issue.html_url,
                )

            # Create the issue
            title = self._generate_issue_title(failed_workflow)
            body = self._generate_issue_body(failed_workflow, error_analysis)

            # Ensure the label exists
            self._ensure_label_exists(repo)

            issue = repo.create_issue(
                title=title,
                body=body,
                labels=[self.ISSUE_LABEL],
                assignees=self.assignees if self.assignees else None,
            )

            logger.info(f"Created issue: {issue.html_url}")
            return NotificationResult(
                success=True,
                issue_number=issue.number,
                issue_url=issue.html_url,
            )

        except Exception as e:
            logger.error(f"Failed to create issue: {e}")
            return NotificationResult(
                success=False,
                error_message=str(e),
            )

    def update_existing_issue(
        self,
        failed_workflow: FailedWorkflow,
        status_update: str,
    ) -> NotificationResult:
        """Update an existing issue with a status update.

        Args:
            failed_workflow: The failed workflow.
            status_update: The status update message.

        Returns:
            NotificationResult with the outcome.
        """
        try:
            repo = self.github.get_repo(failed_workflow.repo_full_name)
            existing_issue = self._find_existing_issue(repo, failed_workflow)

            if not existing_issue:
                return NotificationResult(
                    success=False,
                    error_message="No existing issue found",
                )

            # Add a comment to the issue
            existing_issue.create_comment(status_update)
            logger.info(f"Updated issue {existing_issue.number} with status")

            return NotificationResult(
                success=True,
                issue_number=existing_issue.number,
                issue_url=existing_issue.html_url,
            )

        except Exception as e:
            logger.error(f"Failed to update issue: {e}")
            return NotificationResult(
                success=False,
                error_message=str(e),
            )

    def close_issue(
        self,
        failed_workflow: FailedWorkflow,
        resolution_message: str,
    ) -> NotificationResult:
        """Close an issue when the workflow is fixed.

        Args:
            failed_workflow: The failed workflow.
            resolution_message: Message explaining the resolution.

        Returns:
            NotificationResult with the outcome.
        """
        try:
            repo = self.github.get_repo(failed_workflow.repo_full_name)
            existing_issue = self._find_existing_issue(repo, failed_workflow)

            if not existing_issue:
                return NotificationResult(
                    success=False,
                    error_message="No existing issue found",
                )

            # Add a comment and close the issue
            existing_issue.create_comment(f"✅ Resolved: {resolution_message}")
            existing_issue.edit(state="closed")

            logger.info(f"Closed issue {existing_issue.number}")
            return NotificationResult(
                success=True,
                issue_number=existing_issue.number,
                issue_url=existing_issue.html_url,
            )

        except Exception as e:
            logger.error(f"Failed to close issue: {e}")
            return NotificationResult(
                success=False,
                error_message=str(e),
            )

    def _find_existing_issue(self, repo, failed_workflow: FailedWorkflow):
        """Find an existing issue for a workflow failure.

        Args:
            repo: The repository.
            failed_workflow: The failed workflow.

        Returns:
            The existing Issue, or None if not found.
        """
        try:
            # Search for open issues with our label and workflow name
            issues = repo.get_issues(
                state="open",
                labels=[self.ISSUE_LABEL],
            )

            for issue in issues:
                if failed_workflow.workflow_name in issue.title:
                    return issue

        except Exception as e:
            logger.error(f"Error searching for existing issues: {e}")
        return None

    def _generate_issue_title(self, failed_workflow: FailedWorkflow) -> str:
        """Generate a title for the issue.

        Args:
            failed_workflow: The failed workflow.

        Returns:
            The issue title.
        """
        return (
            f"🚨 Workflow Failure: {failed_workflow.workflow_name} "
            f"on {failed_workflow.branch}"
        )

    def _generate_issue_body(
        self,
        failed_workflow: FailedWorkflow,
        error_analysis: Optional[ErrorAnalysis],
    ) -> str:
        """Generate the body content for the issue.

        Args:
            failed_workflow: The failed workflow.
            error_analysis: Optional AI analysis.

        Returns:
            The issue body in markdown format.
        """
        body = f"""## Workflow Failure Details

| Field | Value |
|-------|-------|
| **Workflow** | `{failed_workflow.workflow_name}` |
| **Repository** | `{failed_workflow.repo_full_name}` |
| **Branch** | `{failed_workflow.branch}` |
| **Conclusion** | `{failed_workflow.conclusion}` |
| **Run ID** | `{failed_workflow.run_id}` |
| **Commit** | `{failed_workflow.commit_sha[:8]}` |
| **Time** | {failed_workflow.created_at.strftime('%Y-%m-%d %H:%M:%S UTC')} |

### Links
- [View Workflow Run]({failed_workflow.run_url})
- [View Logs]({failed_workflow.logs_url})
"""

        if failed_workflow.head_commit_message:
            body += f"""
### Commit Message
```
{failed_workflow.head_commit_message}
```
"""

        if error_analysis:
            body += f"""
## AI Analysis

### Error Type
`{error_analysis.error_type}`

### Summary
{error_analysis.error_summary}

### Root Cause
{error_analysis.root_cause}

### Suggested Fix
{error_analysis.suggested_fix}

### Confidence Level
{error_analysis.fix_confidence * 100:.0f}%

### Manual Intervention Required
{'Yes' if error_analysis.requires_manual_intervention else 'No'}
"""

            if error_analysis.relevant_files:
                body += "\n### Relevant Files\n"
                for f in error_analysis.relevant_files:
                    body += f"- `{f}`\n"

            if error_analysis.additional_context:
                body += f"""
### Additional Context
{error_analysis.additional_context}
"""

        body += """
---
*This issue was automatically created by the Workflow Failure Copilot.*
"""
        return body

    def _ensure_label_exists(self, repo) -> None:
        """Ensure the workflow-failure label exists.

        Args:
            repo: The repository.
        """
        try:
            repo.get_label(self.ISSUE_LABEL)
        except Exception:
            try:
                repo.create_label(
                    name=self.ISSUE_LABEL,
                    color="d73a4a",  # Red color
                    description="Automated workflow failure notification",
                )
                logger.info(f"Created label: {self.ISSUE_LABEL}")
            except Exception as e:
                logger.error(f"Failed to create label: {e}")
