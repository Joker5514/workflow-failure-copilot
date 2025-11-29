"""Tests for the error_analyzer module."""

import json
from unittest.mock import MagicMock, patch

import pytest

from workflow_monitor.error_analyzer import ErrorAnalysis, ErrorAnalyzer


class TestErrorAnalysis:
    """Tests for the ErrorAnalysis dataclass."""

    def test_create_error_analysis(self):
        """Test creating an ErrorAnalysis instance."""
        analysis = ErrorAnalysis(
            error_type="dependency",
            error_summary="Missing package",
            root_cause="Package not found in requirements",
            suggested_fix="Add package to requirements.txt",
            fix_confidence=0.85,
            requires_manual_intervention=False,
            relevant_files=["requirements.txt"],
            additional_context="Check pip install",
        )

        assert analysis.error_type == "dependency"
        assert analysis.fix_confidence == 0.85
        assert not analysis.requires_manual_intervention
        assert len(analysis.relevant_files) == 1


class TestErrorAnalyzer:
    """Tests for the ErrorAnalyzer class."""

    def test_init_invalid_provider(self):
        """Test that invalid provider raises error."""
        with pytest.raises(ValueError, match="Unsupported AI provider"):
            ErrorAnalyzer(provider="invalid", api_key="test")

    @patch("workflow_monitor.error_analyzer.config")
    def test_init_openai_without_key_raises(self, mock_config):
        """Test that OpenAI without key raises error."""
        mock_config.ai_provider = "openai"
        mock_config.openai_api_key = ""
        mock_config.ai_model = "gpt-4"

        with pytest.raises(ValueError, match="OpenAI API key is required"):
            ErrorAnalyzer(provider="openai")

    @patch("workflow_monitor.error_analyzer.config")
    def test_init_anthropic_without_key_raises(self, mock_config):
        """Test that Anthropic without key raises error."""
        mock_config.ai_provider = "anthropic"
        mock_config.anthropic_api_key = ""
        mock_config.ai_model = "claude-3"

        with pytest.raises(ValueError, match="Anthropic API key is required"):
            ErrorAnalyzer(provider="anthropic")

    def test_build_analysis_prompt(self):
        """Test prompt building."""
        with patch("workflow_monitor.error_analyzer.config"):
            with patch("openai.OpenAI"):
                analyzer = ErrorAnalyzer(provider="openai", api_key="test-key")
                prompt = analyzer._build_analysis_prompt(
                    workflow_name="CI",
                    error_logs="Error: test failed",
                    workflow_file="name: CI",
                    commit_message="Test commit",
                )

                assert "CI" in prompt
                assert "Error: test failed" in prompt
                assert "Test commit" in prompt
                assert "name: CI" in prompt

    def test_parse_valid_response(self):
        """Test parsing a valid JSON response."""
        with patch("workflow_monitor.error_analyzer.config"):
            with patch("openai.OpenAI"):
                analyzer = ErrorAnalyzer(provider="openai", api_key="test-key")

                response = json.dumps({
                    "error_type": "test_failure",
                    "error_summary": "Tests failed",
                    "root_cause": "Assertion error",
                    "suggested_fix": "Fix the test",
                    "fix_confidence": 0.7,
                    "requires_manual_intervention": False,
                    "relevant_files": ["test_file.py"],
                })

                analysis = analyzer._parse_response(response)

                assert analysis.error_type == "test_failure"
                assert analysis.fix_confidence == 0.7
                assert not analysis.requires_manual_intervention

    def test_parse_invalid_response(self):
        """Test parsing an invalid response returns default analysis."""
        with patch("workflow_monitor.error_analyzer.config"):
            with patch("openai.OpenAI"):
                analyzer = ErrorAnalyzer(provider="openai", api_key="test-key")

                analysis = analyzer._parse_response("not valid json")

                assert analysis.error_type == "Parse Error"
                assert analysis.requires_manual_intervention is True

    def test_parse_response_with_markdown(self):
        """Test parsing response wrapped in markdown code blocks."""
        with patch("workflow_monitor.error_analyzer.config"):
            with patch("openai.OpenAI"):
                analyzer = ErrorAnalyzer(provider="openai", api_key="test-key")

                response = """```json
{
    "error_type": "syntax",
    "error_summary": "Syntax error",
    "root_cause": "Missing bracket",
    "suggested_fix": "Add bracket",
    "fix_confidence": 0.9,
    "requires_manual_intervention": false,
    "relevant_files": []
}
```"""

                analysis = analyzer._parse_response(response)

                assert analysis.error_type == "syntax"
                assert analysis.fix_confidence == 0.9

    @patch("openai.OpenAI")
    def test_analyze_error_with_openai(self, mock_openai):
        """Test error analysis with OpenAI."""
        mock_client = MagicMock()
        mock_openai.return_value = mock_client

        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = json.dumps({
            "error_type": "dependency",
            "error_summary": "Missing dependency",
            "root_cause": "Package not installed",
            "suggested_fix": "Install package",
            "fix_confidence": 0.8,
            "requires_manual_intervention": False,
            "relevant_files": ["requirements.txt"],
        })
        mock_client.chat.completions.create.return_value = mock_response

        with patch("workflow_monitor.error_analyzer.config"):
            analyzer = ErrorAnalyzer(provider="openai", api_key="test-key")
            analysis = analyzer.analyze_error(
                workflow_name="CI",
                error_logs="ModuleNotFoundError: No module named 'requests'",
            )

            assert analysis.error_type == "dependency"
            assert analysis.fix_confidence == 0.8
