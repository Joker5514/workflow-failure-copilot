"""Tests for the fix_generator module."""

from workflow_monitor.fix_generator import FixGenerator


class TestFixGenerator:
    """Tests for the FixGenerator class."""

    def setup_method(self):
        """Set up test fixtures."""
        self.generator = FixGenerator()

    def test_identify_node_version_fix(self):
        """Test identification of Node.js version issues."""
        logs = "The following actions uses node12 which is deprecated"
        fix_type = self.generator.identify_fix_type(logs)
        assert fix_type == "node_version"

    def test_identify_checkout_version_fix(self):
        """Test identification of actions/checkout version issues."""
        logs = "uses: actions/checkout@v2"
        fix_type = self.generator.identify_fix_type(logs)
        assert fix_type == "checkout_version"

    def test_identify_setup_node_version_fix(self):
        """Test identification of actions/setup-node version issues."""
        logs = "uses: actions/setup-node@v1"
        fix_type = self.generator.identify_fix_type(logs)
        assert fix_type == "setup_node_version"

    def test_identify_python_version_fix(self):
        """Test identification of actions/setup-python version issues."""
        logs = "uses: actions/setup-python@v2"
        fix_type = self.generator.identify_fix_type(logs)
        assert fix_type == "python_version"

    def test_identify_npm_ci_failure(self):
        """Test identification of npm CI failures."""
        logs = "npm ERR! code ENOTFOUND"
        fix_type = self.generator.identify_fix_type(logs)
        assert fix_type == "npm_ci_failure"

    def test_identify_no_fix(self):
        """Test that unknown errors return None."""
        logs = "Some random error that we don't recognize"
        fix_type = self.generator.identify_fix_type(logs)
        assert fix_type is None

    def test_fix_node_version(self):
        """Test Node.js version fix generation."""
        workflow = """
name: CI
on: push
jobs:
  build:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/setup-node@v4
        with:
          node-version: 12
"""
        fix = self.generator._fix_node_version(workflow)
        assert fix is not None
        assert "node-version: 20" in fix.fixed_content
        assert fix.fix_type == "node_upgrade"

    def test_fix_node_version_quoted(self):
        """Test Node.js version fix with quoted version."""
        workflow = """
name: CI
on: push
jobs:
  build:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/setup-node@v4
        with:
          node-version: '14'
"""
        fix = self.generator._fix_node_version(workflow)
        assert fix is not None
        assert "node-version: '20'" in fix.fixed_content

    def test_fix_node_version_no_change_needed(self):
        """Test no fix when Node version is already current."""
        workflow = """
name: CI
on: push
jobs:
  build:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/setup-node@v4
        with:
          node-version: 20
"""
        fix = self.generator._fix_node_version(workflow)
        assert fix is None

    def test_fix_action_version_checkout(self):
        """Test actions/checkout version upgrade."""
        workflow = """
name: CI
on: push
jobs:
  build:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2
"""
        fix = self.generator._fix_action_version(
            workflow,
            "actions/checkout",
            "v4",
            "Upgrade checkout",
        )
        assert fix is not None
        assert "actions/checkout@v4" in fix.fixed_content

    def test_fix_action_version_setup_python(self):
        """Test actions/setup-python version upgrade."""
        workflow = """
name: CI
on: push
jobs:
  build:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/setup-python@v2
"""
        fix = self.generator._fix_action_version(
            workflow,
            "actions/setup-python",
            "v5",
            "Upgrade setup-python",
        )
        assert fix is not None
        assert "actions/setup-python@v5" in fix.fixed_content


class TestCanAutoFix:
    """Tests for the can_auto_fix method."""

    def setup_method(self):
        """Set up test fixtures."""
        self.generator = FixGenerator()

    def test_can_fix_common_pattern(self):
        """Test that common patterns can be auto-fixed."""
        from workflow_monitor.error_analyzer import ErrorAnalysis

        analysis = ErrorAnalysis(
            error_type="dependency",
            error_summary="Test",
            root_cause="Test",
            suggested_fix="Test",
            fix_confidence=0.5,
            requires_manual_intervention=True,
            relevant_files=[],
        )
        logs = "The following actions uses node12"

        assert self.generator.can_auto_fix(analysis, logs) is True

    def test_can_fix_high_confidence(self):
        """Test that high confidence AI fixes can be auto-applied."""
        from workflow_monitor.error_analyzer import ErrorAnalysis

        analysis = ErrorAnalysis(
            error_type="configuration",
            error_summary="Test",
            root_cause="Test",
            suggested_fix="Test",
            fix_confidence=0.9,
            requires_manual_intervention=False,
            relevant_files=[],
        )
        logs = "Unknown error"

        assert self.generator.can_auto_fix(analysis, logs) is True

    def test_cannot_fix_low_confidence(self):
        """Test that low confidence errors require manual intervention."""
        from workflow_monitor.error_analyzer import ErrorAnalysis

        analysis = ErrorAnalysis(
            error_type="unknown",
            error_summary="Test",
            root_cause="Test",
            suggested_fix="Test",
            fix_confidence=0.3,
            requires_manual_intervention=True,
            relevant_files=[],
        )
        logs = "Unknown error"

        assert self.generator.can_auto_fix(analysis, logs) is False
