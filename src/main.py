"""
Main entry point for the Workflow Failure Copilot.
"""

import argparse
import logging
import sys

from workflow_monitor.config import config
from workflow_monitor.workflow_monitor import WorkflowMonitor, FailedWorkflow
from workflow_monitor.error_analyzer import ErrorAnalyzer
from workflow_monitor.fix_generator import FixGenerator
from workflow_monitor.commit_manager import CommitManager
from workflow_monitor.workflow_retry import WorkflowRetry
from workflow_monitor.notification import NotificationManager
from workflow_monitor.dashboard import Dashboard

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


def process_failure(
    failed_workflow: FailedWorkflow,
    monitor: WorkflowMonitor,
    analyzer: ErrorAnalyzer | None,
    fix_generator: FixGenerator,
    commit_manager: CommitManager,
    retry_handler: WorkflowRetry,
    notification_manager: NotificationManager,
) -> bool:
    """Process a single workflow failure.

    Args:
        failed_workflow: The failed workflow to process.
        monitor: The workflow monitor instance.
        analyzer: The error analyzer instance (may be None if AI not configured).
        fix_generator: The fix generator instance.
        commit_manager: The commit manager instance.
        retry_handler: The workflow retry handler.
        notification_manager: The notification manager.

    Returns:
        True if the failure was resolved, False otherwise.
    """
    logger.info(f"Processing failure: {failed_workflow.workflow_name} in {failed_workflow.repo_full_name}")

    # Get workflow logs
    repo = monitor.github.get_repo(failed_workflow.repo_full_name)
    logs = monitor.get_workflow_logs(repo, failed_workflow.run_id)

    error_analysis = None
    if logs and analyzer:
        try:
            # Analyze the error with AI
            logger.info("Analyzing error with AI...")
            error_analysis = analyzer.analyze_error(
                workflow_name=failed_workflow.workflow_name,
                error_logs=logs,
                commit_message=failed_workflow.head_commit_message,
            )
            logger.info(f"Error type: {error_analysis.error_type}")
            logger.info(f"Confidence: {error_analysis.fix_confidence}")
        except Exception as e:
            logger.warning(f"AI analysis failed: {e}")

    # Check if we can auto-fix
    can_fix = False
    if logs:
        can_fix = fix_generator.can_auto_fix(error_analysis, logs) if error_analysis else False

    if can_fix and error_analysis:
        logger.info("Attempting auto-fix...")

        # Get the workflow file content
        try:
            workflow_content = repo.get_contents(
                f".github/workflows/{failed_workflow.workflow_name}.yml"
            )
            if not isinstance(workflow_content, list):
                workflow_yaml = workflow_content.decoded_content.decode("utf-8")

                # Generate fixes
                fixes = fix_generator.generate_fix(error_analysis, workflow_yaml, logs)

                if fixes:
                    # Create commits with fixes
                    results = commit_manager.create_multiple_fix_commits(
                        repo_name=failed_workflow.repo_full_name,
                        fixes=fixes,
                        branch=failed_workflow.branch,
                        base_commit_message=f"fix: Auto-fix for {failed_workflow.workflow_name}",
                    )

                    if results and results[0].success:
                        logger.info(f"Fix committed: {results[0].commit_url}")

                        # Retry the workflow
                        retry_result = retry_handler.retry_workflow(failed_workflow)
                        if retry_result.success:
                            logger.info(f"Workflow retry triggered: {retry_result.new_run_url}")
                            return True

        except Exception as e:
            logger.error(f"Auto-fix failed: {e}")

    # Try simple retry if it might be a transient failure
    if failed_workflow.conclusion == "timed_out" or (
        error_analysis and error_analysis.error_type in ("timeout", "network", "transient")
    ):
        logger.info("Attempting retry for transient failure...")
        retry_result = retry_handler.retry_workflow(failed_workflow)
        if retry_result.success:
            logger.info(f"Retry triggered: {retry_result.new_run_url}")
            # Note: We don't know if it succeeded yet
            return False

    # If we can't auto-fix, create an issue
    if not can_fix or (error_analysis and error_analysis.requires_manual_intervention):
        logger.info("Creating issue for manual intervention...")
        notification_manager.create_failure_issue(
            failed_workflow=failed_workflow,
            error_analysis=error_analysis,
        )

    return False


def run_monitor():
    """Run the workflow monitor."""
    logger.info("Starting Workflow Failure Copilot...")

    # Validate configuration
    errors = config.validate()
    if errors:
        for error in errors:
            logger.error(f"Configuration error: {error}")
        sys.exit(1)

    # Initialize components
    monitor = WorkflowMonitor()

    # Initialize analyzer if AI is configured
    analyzer = None
    try:
        analyzer = ErrorAnalyzer()
    except ValueError as e:
        logger.warning(f"AI analyzer not available: {e}")

    fix_generator = FixGenerator()
    commit_manager = CommitManager()
    retry_handler = WorkflowRetry()
    notification_manager = NotificationManager()

    # Scan for failures
    logger.info("Scanning for failed workflows...")
    failures = monitor.scan_all_repositories()

    if not failures:
        logger.info("No failed workflows found!")
        return

    logger.info(f"Found {len(failures)} failed workflow(s)")

    # Process each failure
    resolved = 0
    for failure in failures:
        try:
            if process_failure(
                failure,
                monitor,
                analyzer,
                fix_generator,
                commit_manager,
                retry_handler,
                notification_manager,
            ):
                resolved += 1
        except Exception as e:
            logger.error(f"Error processing failure: {e}")

    logger.info(f"Processing complete. Resolved: {resolved}/{len(failures)}")


def run_dashboard():
    """Run the dashboard server."""
    logger.info("Starting dashboard...")
    dashboard = Dashboard()
    dashboard.run(debug=False)


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Workflow Failure Copilot - Monitor and fix GitHub Actions failures"
    )
    parser.add_argument(
        "command",
        choices=["monitor", "dashboard", "scan"],
        help="Command to run",
    )
    parser.add_argument(
        "--debug",
        action="store_true",
        help="Enable debug mode",
    )

    args = parser.parse_args()

    if args.debug:
        logging.getLogger().setLevel(logging.DEBUG)

    if args.command == "monitor":
        run_monitor()
    elif args.command == "dashboard":
        run_dashboard()
    elif args.command == "scan":
        # Quick scan without processing
        monitor = WorkflowMonitor()
        failures = monitor.scan_all_repositories()
        print(f"Found {len(failures)} failed workflow(s):")
        for failure in failures:
            print(f"  - {failure.repo_full_name}: {failure.workflow_name} ({failure.conclusion})")


if __name__ == "__main__":
    main()
