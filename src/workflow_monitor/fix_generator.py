"""
Auto-generate fixes for common workflow errors.
"""

import logging
import re
from dataclasses import dataclass
from typing import Optional

from .config import config
from .error_analyzer import ErrorAnalysis

logger = logging.getLogger(__name__)


@dataclass
class GeneratedFix:
    """Represents a generated fix for a workflow error."""

    file_path: str
    original_content: str
    fixed_content: str
    description: str
    fix_type: str


class FixGenerator:
    """Generates fixes for common workflow errors."""

    # Common patterns and their fixes
    COMMON_FIXES = {
        "node_version": {
            "pattern": r"Node\.js version .* is no longer supported|The following actions uses node12",
            "fix_type": "node_upgrade",
            "description": "Upgrade Node.js version in workflow",
        },
        "checkout_version": {
            "pattern": r"actions/checkout@v[12]",
            "fix_type": "action_upgrade",
            "description": "Upgrade actions/checkout to v4",
        },
        "setup_node_version": {
            "pattern": r"actions/setup-node@v[12]",
            "fix_type": "action_upgrade",
            "description": "Upgrade actions/setup-node to v4",
        },
        "python_version": {
            "pattern": r"actions/setup-python@v[12]",
            "fix_type": "action_upgrade",
            "description": "Upgrade actions/setup-python to v5",
        },
        "npm_ci_failure": {
            "pattern": r"npm ERR! code E(NOTFOUND|NOENT|LIFECYCLE)",
            "fix_type": "dependency",
            "description": "Fix npm dependency issue",
        },
        "pip_install_failure": {
            "pattern": r"Could not find a version that satisfies the requirement",
            "fix_type": "dependency",
            "description": "Fix pip dependency issue",
        },
        "permission_denied": {
            "pattern": r"Permission denied|EACCES",
            "fix_type": "permission",
            "description": "Fix file permission issue",
        },
    }

    def __init__(self, ai_provider: Optional[str] = None, api_key: Optional[str] = None):
        """Initialize the fix generator.

        Args:
            ai_provider: AI provider to use for complex fixes.
            api_key: API key for the AI provider.
        """
        self.ai_provider = ai_provider or config.ai_provider
        self.api_key = api_key

    def identify_fix_type(self, error_logs: str) -> Optional[str]:
        """Identify the type of fix needed based on error logs.

        Args:
            error_logs: The workflow error logs.

        Returns:
            The fix type identifier, or None if no common fix found.
        """
        for fix_id, fix_info in self.COMMON_FIXES.items():
            if re.search(fix_info["pattern"], error_logs, re.IGNORECASE):
                logger.info(f"Identified fix type: {fix_id}")
                return fix_id
        return None

    def generate_fix(
        self,
        error_analysis: ErrorAnalysis,
        workflow_content: str,
        error_logs: str,
    ) -> list[GeneratedFix]:
        """Generate fixes based on error analysis.

        Args:
            error_analysis: The AI analysis of the error.
            workflow_content: The workflow YAML content.
            error_logs: The error logs from the workflow.

        Returns:
            List of GeneratedFix objects.
        """
        fixes = []

        # Try to identify common fixes first
        fix_type = self.identify_fix_type(error_logs)

        if fix_type:
            common_fix = self._generate_common_fix(fix_type, workflow_content)
            if common_fix:
                fixes.append(common_fix)

        # If no common fix or low confidence, try AI-generated fix
        if not fixes and error_analysis.fix_confidence >= 0.7:
            ai_fix = self._generate_ai_fix(error_analysis, workflow_content)
            if ai_fix:
                fixes.append(ai_fix)

        return fixes

    def _generate_common_fix(
        self,
        fix_type: str,
        workflow_content: str
    ) -> Optional[GeneratedFix]:
        """Generate a fix for a common issue.

        Args:
            fix_type: The type of fix to generate.
            workflow_content: The workflow YAML content.

        Returns:
            GeneratedFix object, or None if fix couldn't be generated.
        """
        if fix_type == "node_version":
            return self._fix_node_version(workflow_content)
        elif fix_type == "checkout_version":
            return self._fix_action_version(
                workflow_content,
                "actions/checkout",
                "v4",
                "Upgrade actions/checkout to v4",
            )
        elif fix_type == "setup_node_version":
            return self._fix_action_version(
                workflow_content,
                "actions/setup-node",
                "v4",
                "Upgrade actions/setup-node to v4",
            )
        elif fix_type == "python_version":
            return self._fix_action_version(
                workflow_content,
                "actions/setup-python",
                "v5",
                "Upgrade actions/setup-python to v5",
            )
        return None

    def _fix_node_version(self, workflow_content: str) -> Optional[GeneratedFix]:
        """Fix Node.js version issues in workflow.

        Args:
            workflow_content: The workflow YAML content.

        Returns:
            GeneratedFix object, or None if no fix needed.
        """
        # Look for node-version: X and upgrade to 20
        pattern = r"(node-version:\s*['\"]?)(\d+)(['\"]?)"

        def replace_version(match):
            prefix = match.group(1)
            version = int(match.group(2))
            suffix = match.group(3)
            if version < 18:
                return f"{prefix}20{suffix}"
            return match.group(0)

        fixed_content = re.sub(pattern, replace_version, workflow_content)

        if fixed_content != workflow_content:
            return GeneratedFix(
                file_path=".github/workflows/",  # To be filled in by caller
                original_content=workflow_content,
                fixed_content=fixed_content,
                description="Upgrade Node.js version to 20 (LTS)",
                fix_type="node_upgrade",
            )
        return None

    def _fix_action_version(
        self,
        workflow_content: str,
        action_name: str,
        new_version: str,
        description: str,
    ) -> Optional[GeneratedFix]:
        """Fix action version in workflow.

        Args:
            workflow_content: The workflow YAML content.
            action_name: Name of the action to upgrade.
            new_version: New version to use.
            description: Description of the fix.

        Returns:
            GeneratedFix object, or None if no fix needed.
        """
        pattern = rf"({re.escape(action_name)}@)v?\d+"
        fixed_content = re.sub(pattern, rf"\g<1>{new_version}", workflow_content)

        if fixed_content != workflow_content:
            return GeneratedFix(
                file_path=".github/workflows/",
                original_content=workflow_content,
                fixed_content=fixed_content,
                description=description,
                fix_type="action_upgrade",
            )
        return None

    def _generate_ai_fix(
        self,
        error_analysis: ErrorAnalysis,
        workflow_content: str,
    ) -> Optional[GeneratedFix]:
        """Generate a fix using AI.

        Args:
            error_analysis: The error analysis from AI.
            workflow_content: The workflow YAML content.

        Returns:
            GeneratedFix object, or None if AI fix not possible.
        """
        # For now, we only apply AI suggestions for specific fix types
        # that we're confident about
        if error_analysis.requires_manual_intervention:
            return None

        if not error_analysis.suggested_fix:
            return None

        # Return a placeholder - actual implementation would use AI
        # to generate the specific code changes
        logger.info(
            f"AI suggested fix available: {error_analysis.suggested_fix[:100]}..."
        )
        return None

    def can_auto_fix(self, error_analysis: ErrorAnalysis, error_logs: str) -> bool:
        """Check if an error can be automatically fixed.

        Args:
            error_analysis: The error analysis.
            error_logs: The workflow error logs.

        Returns:
            True if the error can be auto-fixed, False otherwise.
        """
        # Check for common fix patterns
        if self.identify_fix_type(error_logs):
            return True

        # Check AI analysis confidence
        if (
            error_analysis.fix_confidence >= 0.8
            and not error_analysis.requires_manual_intervention
        ):
            return True

        return False
