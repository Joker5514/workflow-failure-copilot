"""
Retry failed GitHub Actions workflows.
"""

import logging
import time
from dataclasses import dataclass
from typing import Optional

from github import Github

from .config import config
from .workflow_monitor import FailedWorkflow

logger = logging.getLogger(__name__)


@dataclass
class RetryResult:
    """Result of a workflow retry attempt."""

    success: bool
    new_run_id: Optional[int] = None
    new_run_url: Optional[str] = None
    error_message: Optional[str] = None
    retry_count: int = 0


class WorkflowRetry:
    """Handles retrying failed workflows."""

    def __init__(self, github_token: Optional[str] = None):
        """Initialize the workflow retry handler.

        Args:
            github_token: GitHub token for authentication.
        """
        self.token = github_token or config.github_token
        if not self.token:
            raise ValueError("GitHub token is required")
        self.github = Github(self.token)
        self.max_retries = config.max_retries
        self.retry_delay = config.retry_delay_seconds

    def retry_workflow(
        self,
        failed_workflow: FailedWorkflow,
        wait_for_completion: bool = False,
    ) -> RetryResult:
        """Retry a failed workflow.

        Args:
            failed_workflow: The failed workflow to retry.
            wait_for_completion: Whether to wait for the retry to complete.

        Returns:
            RetryResult with the outcome.
        """
        try:
            repo = self.github.get_repo(failed_workflow.repo_full_name)
            run = repo.get_workflow_run(failed_workflow.run_id)

            # Trigger a re-run
            success = run.rerun()

            if not success:
                return RetryResult(
                    success=False,
                    error_message="Failed to trigger workflow re-run",
                )

            # Get the new run info
            # Note: The rerun creates a new run, but we need to find it
            time.sleep(2)  # Brief wait for the new run to appear

            new_run = self._find_new_run(repo, failed_workflow.workflow_id, run.id)

            if new_run:
                result = RetryResult(
                    success=True,
                    new_run_id=new_run.id,
                    new_run_url=new_run.html_url,
                    retry_count=1,
                )

                if wait_for_completion:
                    self._wait_for_completion(repo, new_run.id)

                return result
            else:
                return RetryResult(
                    success=True,
                    retry_count=1,
                    error_message="Retry triggered but couldn't find new run ID",
                )

        except Exception as e:
            logger.error(f"Failed to retry workflow: {e}")
            return RetryResult(
                success=False,
                error_message=str(e),
            )

    def retry_with_backoff(
        self,
        failed_workflow: FailedWorkflow,
        max_retries: Optional[int] = None,
    ) -> RetryResult:
        """Retry a workflow with exponential backoff.

        Args:
            failed_workflow: The failed workflow to retry.
            max_retries: Maximum number of retry attempts.

        Returns:
            RetryResult with the final outcome.
        """
        max_attempts = max_retries or self.max_retries
        delay = self.retry_delay

        for attempt in range(max_attempts):
            logger.info(
                f"Retry attempt {attempt + 1}/{max_attempts} for "
                f"{failed_workflow.repo_full_name}/{failed_workflow.workflow_name}"
            )

            result = self.retry_workflow(failed_workflow, wait_for_completion=True)

            if result.success:
                # Check if the new run succeeded
                if result.new_run_id:
                    repo = self.github.get_repo(failed_workflow.repo_full_name)
                    new_run = repo.get_workflow_run(result.new_run_id)
                    if new_run.conclusion == "success":
                        result.retry_count = attempt + 1
                        return result

            # Exponential backoff
            if attempt < max_attempts - 1:
                logger.info(f"Waiting {delay} seconds before next retry")
                time.sleep(delay)
                delay *= 2

        return RetryResult(
            success=False,
            retry_count=max_attempts,
            error_message=f"Failed after {max_attempts} retry attempts",
        )

    def rerun_failed_jobs_only(
        self,
        failed_workflow: FailedWorkflow,
    ) -> RetryResult:
        """Rerun only the failed jobs in a workflow.

        Args:
            failed_workflow: The failed workflow.

        Returns:
            RetryResult with the outcome.
        """
        try:
            repo = self.github.get_repo(failed_workflow.repo_full_name)
            run = repo.get_workflow_run(failed_workflow.run_id)

            # Trigger re-run of failed jobs only
            success = run.rerun_failed_jobs()

            if not success:
                return RetryResult(
                    success=False,
                    error_message="Failed to trigger re-run of failed jobs",
                )

            return RetryResult(
                success=True,
                retry_count=1,
            )

        except Exception as e:
            logger.error(f"Failed to rerun failed jobs: {e}")
            return RetryResult(
                success=False,
                error_message=str(e),
            )

    def _find_new_run(self, repo, workflow_id: int, old_run_id: int):
        """Find a newly created workflow run.

        Args:
            repo: The repository.
            workflow_id: The workflow ID.
            old_run_id: The old run ID to exclude.

        Returns:
            The new WorkflowRun, or None if not found.
        """
        try:
            workflow = repo.get_workflow(workflow_id)
            runs = workflow.get_runs()

            for run in runs:
                if run.id != old_run_id:
                    return run
                break  # Only check the most recent runs

        except Exception as e:
            logger.error(f"Failed to find new run: {e}")
        return None

    def _wait_for_completion(
        self,
        repo,
        run_id: int,
        timeout_seconds: int = 3600,
        poll_interval: int = 30,
    ) -> Optional[str]:
        """Wait for a workflow run to complete.

        Args:
            repo: The repository.
            run_id: The run ID to wait for.
            timeout_seconds: Maximum time to wait.
            poll_interval: Seconds between status checks.

        Returns:
            The conclusion of the run, or None if timeout.
        """
        elapsed = 0

        while elapsed < timeout_seconds:
            try:
                run = repo.get_workflow_run(run_id)

                if run.status == "completed":
                    logger.info(f"Run {run_id} completed with conclusion: {run.conclusion}")
                    return run.conclusion

                logger.debug(f"Run {run_id} status: {run.status}")
                time.sleep(poll_interval)
                elapsed += poll_interval

            except Exception as e:
                logger.error(f"Error checking run status: {e}")
                time.sleep(poll_interval)
                elapsed += poll_interval

        logger.warning(f"Timeout waiting for run {run_id} to complete")
        return None

    def can_retry(self, failed_workflow: FailedWorkflow) -> bool:
        """Check if a workflow can be retried.

        Args:
            failed_workflow: The failed workflow to check.

        Returns:
            True if the workflow can be retried, False otherwise.
        """
        # Some conclusions can't be retried
        if failed_workflow.conclusion in ("cancelled",):
            return True

        if failed_workflow.conclusion in ("failure", "timed_out"):
            return True

        return False
