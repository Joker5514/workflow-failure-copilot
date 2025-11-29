"""
Manage commits with auto-generated fixes.
"""

import logging
from dataclasses import dataclass
from typing import Optional

from github import Github
from github.Repository import Repository

from .config import config
from .fix_generator import GeneratedFix

logger = logging.getLogger(__name__)


@dataclass
class CommitResult:
    """Result of a commit operation."""

    success: bool
    commit_sha: Optional[str] = None
    commit_url: Optional[str] = None
    error_message: Optional[str] = None
    branch_name: Optional[str] = None


class CommitManager:
    """Manages creating commits with fixes for failed workflows."""

    def __init__(self, github_token: Optional[str] = None):
        """Initialize the commit manager.

        Args:
            github_token: GitHub token for authentication.
        """
        self.token = github_token or config.github_token
        if not self.token:
            raise ValueError("GitHub token is required")
        self.github = Github(self.token)

    def create_fix_commit(
        self,
        repo_name: str,
        fix: GeneratedFix,
        branch: str,
        commit_message: str,
        create_branch: bool = True,
    ) -> CommitResult:
        """Create a commit with a fix.

        Args:
            repo_name: Full repository name (owner/repo).
            fix: The generated fix to commit.
            branch: The branch to commit to.
            commit_message: The commit message.
            create_branch: Whether to create a new branch for the fix.

        Returns:
            CommitResult with the outcome.
        """
        try:
            repo = self.github.get_repo(repo_name)

            # Get the default branch
            default_branch = repo.default_branch

            # Create a new branch for the fix if requested
            target_branch = branch
            if create_branch:
                target_branch = f"fix/{branch}-{fix.fix_type}"
                self._create_branch(repo, target_branch, default_branch)
                logger.info(f"Created branch: {target_branch}")

            # Get the current file content
            file_path = fix.file_path
            try:
                contents = repo.get_contents(file_path, ref=target_branch)
                sha = contents.sha if not isinstance(contents, list) else None
            except Exception:
                sha = None

            # Create or update the file
            if sha:
                result = repo.update_file(
                    path=file_path,
                    message=commit_message,
                    content=fix.fixed_content,
                    sha=sha,
                    branch=target_branch,
                )
            else:
                result = repo.create_file(
                    path=file_path,
                    message=commit_message,
                    content=fix.fixed_content,
                    branch=target_branch,
                )

            commit = result["commit"]
            return CommitResult(
                success=True,
                commit_sha=commit.sha,
                commit_url=commit.html_url,
                branch_name=target_branch,
            )

        except Exception as e:
            logger.error(f"Failed to create fix commit: {e}")
            return CommitResult(
                success=False,
                error_message=str(e),
            )

    def create_multiple_fix_commits(
        self,
        repo_name: str,
        fixes: list[GeneratedFix],
        branch: str,
        base_commit_message: str,
    ) -> list[CommitResult]:
        """Create commits for multiple fixes.

        Args:
            repo_name: Full repository name.
            fixes: List of fixes to commit.
            branch: The base branch name.
            base_commit_message: Base message for commits.

        Returns:
            List of CommitResult objects.
        """
        results = []
        for i, fix in enumerate(fixes):
            commit_message = f"{base_commit_message} (fix {i + 1}/{len(fixes)}): {fix.description}"
            result = self.create_fix_commit(
                repo_name=repo_name,
                fix=fix,
                branch=branch,
                commit_message=commit_message,
                create_branch=(i == 0),  # Only create branch for first fix
            )
            results.append(result)

            if not result.success:
                logger.error(f"Failed to commit fix {i + 1}: {result.error_message}")
                break

        return results

    def _create_branch(
        self,
        repo: Repository,
        branch_name: str,
        source_branch: str,
    ) -> bool:
        """Create a new branch from source branch.

        Args:
            repo: The repository.
            branch_name: Name of the new branch.
            source_branch: Branch to create from.

        Returns:
            True if successful, False otherwise.
        """
        try:
            # Check if branch already exists
            try:
                repo.get_branch(branch_name)
                logger.info(f"Branch {branch_name} already exists")
                return True
            except Exception:
                pass

            # Get the SHA of the source branch
            source = repo.get_branch(source_branch)
            sha = source.commit.sha

            # Create the new branch
            repo.create_git_ref(f"refs/heads/{branch_name}", sha)
            logger.info(f"Created branch {branch_name} from {source_branch}")
            return True

        except Exception as e:
            logger.error(f"Failed to create branch {branch_name}: {e}")
            return False

    def create_pull_request(
        self,
        repo_name: str,
        head_branch: str,
        base_branch: str,
        title: str,
        body: str,
    ) -> Optional[str]:
        """Create a pull request for a fix.

        Args:
            repo_name: Full repository name.
            head_branch: Branch with the fix.
            base_branch: Target branch for the PR.
            title: PR title.
            body: PR description.

        Returns:
            URL of the created PR, or None if failed.
        """
        try:
            repo = self.github.get_repo(repo_name)
            pr = repo.create_pull(
                title=title,
                body=body,
                head=head_branch,
                base=base_branch,
            )
            logger.info(f"Created PR: {pr.html_url}")
            return pr.html_url
        except Exception as e:
            logger.error(f"Failed to create PR: {e}")
            return None
