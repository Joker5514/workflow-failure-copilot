"""
AI-powered error analysis using OpenAI or Claude.
"""

import json
import logging
from dataclasses import dataclass
from typing import Optional

from .config import config

logger = logging.getLogger(__name__)


@dataclass
class ErrorAnalysis:
    """Represents the AI analysis of a workflow error."""

    error_type: str
    error_summary: str
    root_cause: str
    suggested_fix: str
    fix_confidence: float  # 0.0 to 1.0
    requires_manual_intervention: bool
    relevant_files: list[str]
    additional_context: Optional[str] = None


class ErrorAnalyzer:
    """Analyzes workflow errors using AI (OpenAI or Claude)."""

    def __init__(
        self,
        provider: Optional[str] = None,
        api_key: Optional[str] = None,
        model: Optional[str] = None,
    ):
        """Initialize the error analyzer.

        Args:
            provider: AI provider ('openai' or 'anthropic'). Uses config if not provided.
            api_key: API key for the provider. Uses config if not provided.
            model: Model to use. Uses config if not provided.
        """
        self.provider = provider or config.ai_provider
        self.model = model or config.ai_model

        if self.provider == "openai":
            self.api_key = api_key or config.openai_api_key
            if not self.api_key:
                raise ValueError("OpenAI API key is required")
            try:
                from openai import OpenAI
                self.client = OpenAI(api_key=self.api_key)
            except ImportError:
                raise ImportError("openai package is required. Install with: pip install openai")
        elif self.provider == "anthropic":
            self.api_key = api_key or config.anthropic_api_key
            if not self.api_key:
                raise ValueError("Anthropic API key is required")
            try:
                from anthropic import Anthropic
                self.client = Anthropic(api_key=self.api_key)
            except ImportError:
                raise ImportError("anthropic package is required. Install with: pip install anthropic")
        else:
            raise ValueError(f"Unsupported AI provider: {self.provider}")

    def analyze_error(
        self,
        workflow_name: str,
        error_logs: str,
        workflow_file: Optional[str] = None,
        commit_message: Optional[str] = None,
    ) -> ErrorAnalysis:
        """Analyze a workflow error using AI.

        Args:
            workflow_name: Name of the failed workflow.
            error_logs: The error logs from the workflow run.
            workflow_file: Optional workflow YAML content.
            commit_message: Optional commit message that triggered the workflow.

        Returns:
            ErrorAnalysis object with the analysis results.
        """
        prompt = self._build_analysis_prompt(
            workflow_name, error_logs, workflow_file, commit_message
        )

        try:
            response = self._call_ai(prompt)
            return self._parse_response(response)
        except Exception as e:
            logger.error(f"Error analyzing workflow failure: {e}")
            # Return a default analysis indicating manual intervention needed
            return ErrorAnalysis(
                error_type="Unknown",
                error_summary="Failed to analyze error",
                root_cause=f"AI analysis failed: {str(e)}",
                suggested_fix="Manual investigation required",
                fix_confidence=0.0,
                requires_manual_intervention=True,
                relevant_files=[],
            )

    def _build_analysis_prompt(
        self,
        workflow_name: str,
        error_logs: str,
        workflow_file: Optional[str],
        commit_message: Optional[str],
    ) -> str:
        """Build the prompt for AI analysis.

        Args:
            workflow_name: Name of the failed workflow.
            error_logs: The error logs from the workflow run.
            workflow_file: Optional workflow YAML content.
            commit_message: Optional commit message.

        Returns:
            The formatted prompt string.
        """
        # Truncate logs if too long
        max_log_length = 8000
        if len(error_logs) > max_log_length:
            error_logs = f"...[truncated]...\n{error_logs[-max_log_length:]}"

        prompt = f"""Analyze the following GitHub Actions workflow failure and provide a structured analysis.

Workflow Name: {workflow_name}

Error Logs:
```
{error_logs}
```
"""

        if workflow_file:
            prompt += f"""
Workflow File Content:
```yaml
{workflow_file}
```
"""

        if commit_message:
            prompt += f"""
Commit Message: {commit_message}
"""

        prompt += """
Please analyze this error and respond with a JSON object containing:
{
    "error_type": "Category of error (e.g., 'dependency', 'syntax', 'test_failure', 'configuration', 'timeout', 'permission')",
    "error_summary": "Brief one-line summary of the error",
    "root_cause": "Detailed explanation of the root cause",
    "suggested_fix": "Step-by-step instructions to fix the issue",
    "fix_confidence": 0.0-1.0 confidence level that the suggested fix will work,
    "requires_manual_intervention": true/false whether a human needs to intervene,
    "relevant_files": ["list", "of", "files", "to", "modify"],
    "additional_context": "Any additional helpful context or warnings"
}

Respond ONLY with the JSON object, no additional text.
"""
        return prompt

    def _call_ai(self, prompt: str) -> str:
        """Call the AI API with the given prompt.

        Args:
            prompt: The prompt to send to the AI.

        Returns:
            The AI's response text.
        """
        if self.provider == "openai":
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {
                        "role": "system",
                        "content": "You are an expert DevOps engineer who specializes in debugging GitHub Actions workflows. You provide accurate, actionable analysis of workflow failures.",
                    },
                    {"role": "user", "content": prompt},
                ],
                temperature=0.3,
                max_tokens=2000,
            )
            return response.choices[0].message.content or ""
        else:  # anthropic
            response = self.client.messages.create(
                model=self.model,
                max_tokens=2000,
                messages=[{"role": "user", "content": prompt}],
                system="You are an expert DevOps engineer who specializes in debugging GitHub Actions workflows. You provide accurate, actionable analysis of workflow failures.",
            )
            return response.content[0].text

    def _parse_response(self, response: str) -> ErrorAnalysis:
        """Parse the AI response into an ErrorAnalysis object.

        Args:
            response: The AI's response text.

        Returns:
            ErrorAnalysis object.
        """
        try:
            # Try to extract JSON from the response
            response = response.strip()
            if response.startswith("```json"):
                response = response[7:]
            if response.startswith("```"):
                response = response[3:]
            if response.endswith("```"):
                response = response[:-3]

            data = json.loads(response.strip())

            return ErrorAnalysis(
                error_type=data.get("error_type", "Unknown"),
                error_summary=data.get("error_summary", ""),
                root_cause=data.get("root_cause", ""),
                suggested_fix=data.get("suggested_fix", ""),
                fix_confidence=float(data.get("fix_confidence", 0.0)),
                requires_manual_intervention=data.get("requires_manual_intervention", True),
                relevant_files=data.get("relevant_files", []),
                additional_context=data.get("additional_context"),
            )
        except (json.JSONDecodeError, KeyError, ValueError) as e:
            logger.error(f"Failed to parse AI response: {e}")
            return ErrorAnalysis(
                error_type="Parse Error",
                error_summary="Failed to parse AI response",
                root_cause=str(e),
                suggested_fix="Manual investigation required",
                fix_confidence=0.0,
                requires_manual_intervention=True,
                relevant_files=[],
                additional_context=response,
            )
