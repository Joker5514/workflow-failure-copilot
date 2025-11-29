"""
Flask-based dashboard for monitoring workflow failures.
"""

import logging
from datetime import datetime, timezone
from typing import Optional

from flask import Flask, jsonify, render_template

from .config import config
from .workflow_monitor import FailedWorkflow, WorkflowMonitor

logger = logging.getLogger(__name__)


class Dashboard:
    """Web dashboard for monitoring workflow failures."""

    def __init__(
        self,
        host: Optional[str] = None,
        port: Optional[int] = None,
        secret_key: Optional[str] = None,
    ):
        """Initialize the dashboard.

        Args:
            host: Host to bind to.
            port: Port to bind to.
            secret_key: Flask secret key.
        """
        self.host = host or config.dashboard_host
        self.port = port or config.dashboard_port
        self.secret_key = secret_key or config.dashboard_secret_key

        # Use absolute paths for templates and static files
        import os
        base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        template_dir = os.path.join(base_dir, "templates")
        static_dir = os.path.join(base_dir, "static")

        self.app = Flask(
            __name__,
            template_folder=template_dir,
            static_folder=static_dir,
        )
        self.app.secret_key = self.secret_key

        # Store for failures (in production, use a database)
        self.failures: list[dict] = []
        self.last_scan: Optional[datetime] = None

        self._setup_routes()

    def _setup_routes(self):
        """Set up Flask routes."""

        @self.app.route("/")
        def index():
            """Dashboard home page."""
            return render_template(
                "dashboard.html",
                failures=self.failures,
                last_scan=self.last_scan,
            )

        @self.app.route("/api/failures")
        def api_failures():
            """API endpoint for failures."""
            return jsonify({
                "failures": self.failures,
                "last_scan": self.last_scan.isoformat() if self.last_scan else None,
                "count": len(self.failures),
            })

        @self.app.route("/api/scan", methods=["POST"])
        def api_scan():
            """Trigger a scan for failed workflows."""
            try:
                self.scan_workflows()
                return jsonify({
                    "success": True,
                    "failures_found": len(self.failures),
                })
            except Exception as e:
                return jsonify({
                    "success": False,
                    "error": str(e),
                }), 500

        @self.app.route("/api/status")
        def api_status():
            """API endpoint for system status."""
            return jsonify({
                "status": "running",
                "last_scan": self.last_scan.isoformat() if self.last_scan else None,
                "active_failures": len(self.failures),
                "config": {
                    "ai_provider": config.ai_provider,
                    "create_issues": config.create_issues,
                    "max_retries": config.max_retries,
                    "lookback_hours": config.lookback_hours,
                },
            })

        @self.app.route("/health")
        def health():
            """Health check endpoint."""
            return jsonify({"status": "healthy"})

    def scan_workflows(self):
        """Scan for failed workflows and update the store."""
        try:
            monitor = WorkflowMonitor()
            failures = monitor.scan_all_repositories()

            self.failures = [
                self._failure_to_dict(f) for f in failures
            ]
            self.last_scan = datetime.now(timezone.utc)

            logger.info(f"Scan completed: {len(self.failures)} failures found")

        except Exception as e:
            logger.error(f"Scan failed: {e}")
            raise

    def _failure_to_dict(self, failure: FailedWorkflow) -> dict:
        """Convert a FailedWorkflow to a dictionary.

        Args:
            failure: The FailedWorkflow object.

        Returns:
            Dictionary representation.
        """
        return {
            "repo_full_name": failure.repo_full_name,
            "workflow_name": failure.workflow_name,
            "workflow_id": failure.workflow_id,
            "run_id": failure.run_id,
            "run_url": failure.run_url,
            "branch": failure.branch,
            "commit_sha": failure.commit_sha,
            "conclusion": failure.conclusion,
            "created_at": failure.created_at.isoformat(),
            "updated_at": failure.updated_at.isoformat(),
            "logs_url": failure.logs_url,
            "head_commit_message": failure.head_commit_message,
        }

    def add_failure(self, failure: FailedWorkflow):
        """Add a failure to the store.

        Args:
            failure: The FailedWorkflow to add.
        """
        self.failures.append(self._failure_to_dict(failure))

    def remove_failure(self, run_id: int):
        """Remove a failure from the store.

        Args:
            run_id: The run ID to remove.
        """
        self.failures = [f for f in self.failures if f["run_id"] != run_id]

    def run(self, debug: bool = False):
        """Run the dashboard server.

        Args:
            debug: Whether to run in debug mode.
        """
        logger.info(f"Starting dashboard on {self.host}:{self.port}")
        self.app.run(
            host=self.host,
            port=self.port,
            debug=debug,
        )


def create_app() -> Flask:
    """Create the Flask application for production deployment.

    Returns:
        The Flask application.
    """
    dashboard = Dashboard()
    return dashboard.app
