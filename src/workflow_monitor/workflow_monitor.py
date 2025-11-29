"""
Main monitoring logic to detect failed GitHub Actions workflows.
"""

import logging
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Optional

from github import Github
from github.Repository import Repository
from github.WorkflowRun import WorkflowRun

from .config import config

logger = logging.getLogger(__name__)


@dataclass
class FailedWorkflow:
    """Represents a failed workflow run with relevant details."""

    repo_full_name: str
    workflow_name: str
    workflow_id: int
    run_id: int
    run_url: str
    branch: str
    commit_sha: str
    conclusion: str
    created_at: datetime
    updated_at: datetime
    logs_url: str
    head_commit_message: Optional[str] = None
    error_message: Optional[str] = None


class WorkflowMonitor:
    """Monitors GitHub repositories for failed workflow runs."""

    def __init__(self, github_token: Optional[str] = None):
        """Initialize the workflow monitor.

        Args:
            github_token: GitHub personal access token. If not provided,
                         uses the token from configuration.
        """
        self.token = github_token or config.github_token
        if not self.token:
            raise ValueError("GitHub token is required")
        self.github = Github(self.token)

    def get_repositories(self) -> list[Repository]:
        """Get the list of repositories to monitor.

        Returns:
            List of Repository objects.
        """
        repos = []

        # Check for specific repos first
        repo_list = config.get_repos_list()
        if repo_list:
            for repo_name in repo_list:
                try:
                    repos.append(self.github.get_repo(repo_name))
                    logger.info(f"Added repository: {repo_name}")
                except Exception as e:
                    logger.error(f"Failed to get repository {repo_name}: {e}")
        # Then check for organization
        elif config.github_org:
            try:
                org = self.github.get_organization(config.github_org)
                for repo in org.get_repos():
                    repos.append(repo)
                    logger.info(f"Added repository from org: {repo.full_name}")
            except Exception as e:
                logger.error(f"Failed to get organization {config.github_org}: {e}")
        # Fall back to user's repos
        else:
            try:
                user = self.github.get_user()
                for repo in user.get_repos():
                    repos.append(repo)
                    logger.info(f"Added user repository: {repo.full_name}")
            except Exception as e:
                logger.error(f"Failed to get user repositories: {e}")

        return repos

    def get_failed_workflows(
        self,
        repo: Repository,
        since: Optional[datetime] = None
    ) -> list[FailedWorkflow]:
        """Get failed workflow runs for a repository.

        Args:
            repo: The repository to check.
            since: Only return failures after this time.
                   Defaults to lookback_hours from configuration.

        Returns:
            List of FailedWorkflow objects.
        """
        if since is None:
            since = datetime.now(timezone.utc) - timedelta(hours=config.lookback_hours)

        failed_runs = []

        try:
            # Get all workflow runs
            runs = repo.get_workflow_runs(status="completed")

            for run in runs:
                # Stop if we've gone past our lookback period
                if run.created_at.replace(tzinfo=timezone.utc) < since:
                    break

                # Check for failures
                if run.conclusion in ("failure", "timed_out", "cancelled"):
                    failed_workflow = self._create_failed_workflow(repo, run)
                    failed_runs.append(failed_workflow)
                    logger.info(
                        f"Found failed workflow: {run.name} in {repo.full_name} "
                        f"(run_id: {run.id})"
                    )

        except Exception as e:
            logger.error(f"Error getting workflow runs for {repo.full_name}: {e}")

        return failed_runs

    def _create_failed_workflow(
        self,
        repo: Repository,
        run: WorkflowRun
    ) -> FailedWorkflow:
        """Create a FailedWorkflow object from a WorkflowRun.

        Args:
            repo: The repository containing the workflow.
            run: The failed workflow run.

        Returns:
            FailedWorkflow object.
        """
        head_commit_message = None
        if run.head_commit:
            head_commit_message = run.head_commit.message

        return FailedWorkflow(
            repo_full_name=repo.full_name,
            workflow_name=run.name or "Unknown",
            workflow_id=run.workflow_id,
            run_id=run.id,
            run_url=run.html_url,
            branch=run.head_branch or "unknown",
            commit_sha=run.head_sha,
            conclusion=run.conclusion or "unknown",
            created_at=run.created_at,
            updated_at=run.updated_at,
            logs_url=run.logs_url,
            head_commit_message=head_commit_message,
        )

    def get_workflow_logs(self, repo: Repository, run_id: int) -> Optional[str]:
        """Get the logs for a workflow run.

        Args:
            repo: The repository containing the workflow.
            run_id: The ID of the workflow run.

        Returns:
            The workflow logs as a string, or None if unavailable.
        """
        try:
            run = repo.get_workflow_run(run_id)
            # Get the logs URL and download
            # Note: This requires the appropriate permissions
            logs = run.get_logs()
            if logs:
                return logs.decode("utf-8") if isinstance(logs, bytes) else str(logs)
        except Exception as e:
            logger.error(f"Error getting logs for run {run_id}: {e}")
        return None

    def scan_all_repositories(self) -> list[FailedWorkflow]:
        """Scan all configured repositories for failed workflows.

        Returns:
            List of all FailedWorkflow objects found.
        """
        all_failures = []
        repos = self.get_repositories()

        logger.info(f"Scanning {len(repos)} repositories for failed workflows")

        for repo in repos:
            failures = self.get_failed_workflows(repo)
            all_failures.extend(failures)

        logger.info(f"Found {len(all_failures)} failed workflows total")
        return all_failures
