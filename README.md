# Workflow Failure Copilot

Automated copilot that monitors all GitHub repositories for workflow failures, analyzes errors with AI, and automatically debugs and retries failed tasks.

## Overview

This system provides intelligent, automated monitoring and recovery for GitHub Actions workflows across all your repositories. When a workflow fails, the copilot:

1. **Detects** - Continuously monitors all repos for failed workflow runs
2. **Analyzes** - Uses AI (OpenAI/Claude) to analyze error logs and identify root causes  
3. **Fixes** - Automatically generates and applies fixes for common issues
4. **Retries** - Re-runs workflows after applying fixes
5. **Notifies** - Creates GitHub Issues when manual intervention is needed
6. **Tracks** - Maintains a dashboard of all failures and fixes

## Features

### Cross-Repository Monitoring
- Monitors ALL repositories in your GitHub account
- Runs automatically every hour via GitHub Actions
- Manual trigger available via workflow_dispatch

### AI-Powered Debugging
- OpenAI GPT-4 integration for error analysis
- Claude API support for complex debugging scenarios
- Pattern recognition for common failure types
- Contextual analysis of error logs and stack traces

### Automatic Fix Generation
- Dependency version conflicts
- Missing environment variables
- Configuration errors
- Build/test failures
- Timeout issues

### Smart Retry Logic
- Exponential backoff for transient failures
- Conditional retries based on error type
- Maximum retry limits to prevent infinite loops

### Notification System
- Creates GitHub Issues for failures requiring manual fix
- Detailed error reports with AI analysis
- Links to failed workflow runs
- Suggested remediation steps

## Setup

### 1. Repository Secrets

Add these secrets to your repository settings:

```
GITHUB_TOKEN - Already available (GitHub provides this)
OPENAI_API_KEY - Your OpenAI API key
ANTHROPIC_API_KEY - Your Anthropic/Claude API key (optional)
```

### 2. Installation

```bash
pip install -r requirements.txt
```

### 3. Configuration

Create a `config.yaml` in the root directory:

```yaml
monitoring:
  # Which repos to monitor (leave empty for all)
  repositories: []
  # Exclude specific repos
  exclude_repositories: []
  # How far back to check for failures (hours)
  lookback_hours: 24
  
ai:
  # Primary AI provider: 'openai' or 'claude'
  provider: 'openai'
  model: 'gpt-4-turbo-preview'
  
retry:
  # Maximum retry attempts
  max_attempts: 3
  # Base delay between retries (seconds)
  base_delay: 60
  # Enable exponential backoff
  exponential_backoff: true
  
notifications:
  # Create issues for failures
  create_issues: true
  # Label for created issues
  issue_label: 'workflow-failure'
```

### 4. Enable Workflow

The monitoring workflow is already set up in `.github/workflows/monitor-failures.yml`
- Runs automatically every hour
- Can be triggered manually from Actions tab

## Architecture

### Core Modules

**workflow_monitor.py** - Main entry point that orchestrates the monitoring process

**error_analyzer.py** - AI-powered error analysis engine
- Extracts relevant error information from logs
- Categorizes failure types
- Identifies root causes using LLMs

**fix_generator.py** - Automatic fix generation
- Pattern-based fixes for common issues
- AI-generated fixes for complex problems
- Code modification and commit creation

**workflow_retry.py** - Intelligent retry logic
- Determines if failure is retryable
- Manages retry attempts with backoff
- Monitors retry success/failure

**commit_manager.py** - Git operations
- Creates branches for fixes
- Commits changes
- Manages pull requests

**notification.py** - Alert system
- Creates GitHub Issues
- Formats error reports
- Tracks notification history

**dashboard.py** - Flask-based monitoring dashboard
- Real-time failure tracking
- Historical analysis
- Success/failure metrics

**config.py** - Configuration management

## Usage

### Manual Run

```bash
python workflow_monitor.py
```

### View Dashboard

```bash
python dashboard.py
```

Access at `http://localhost:5000`

### Check Specific Repository

```bash
python workflow_monitor.py --repo owner/repo-name
```

### Dry Run (No Fixes Applied)

```bash
python workflow_monitor.py --dry-run
```

## How It Works

### 1. Discovery Phase
```python
- Fetch all repositories using GitHub API
- For each repo, get recent workflow runs
- Filter for failed runs in the lookback period
```

### 2. Analysis Phase
```python
- Download workflow logs
- Extract error messages and stack traces
- Send to AI for analysis
- Categorize failure type
```

### 3. Fix Generation
```python
- Check if failure type has known fix pattern
- If yes: Apply pattern-based fix
- If no: Request AI to generate fix
- Validate fix is safe to apply
```

### 4. Application Phase
```python
- Create new branch
- Apply code changes
- Commit with detailed message
- Trigger workflow re-run
```

### 5. Monitoring Phase
```python
- Watch re-run status
- If successful: Log success
- If failed: Retry or escalate
```

## Common Fix Patterns

### Dependency Conflicts
```python
- Parse error for package names and versions
- Update requirements.txt or package.json
- Re-run install step
```

### Environment Variables
```python
- Identify missing variables from error
- Check if available in repo secrets
- Update workflow YAML if needed
```

### Test Failures
```python
- Analyze test output
- Identify flaky tests
- Apply appropriate fix or mark as known issue
```

## Development

### Project Structure
```
workflow-failure-copilot/
├── .github/
│   └── workflows/
│       └── monitor-failures.yml
├── workflow_monitor.py
├── error_analyzer.py
├── fix_generator.py
├── workflow_retry.py
├── commit_manager.py
├── notification.py
├── dashboard.py
├── config.py
├── requirements.txt
├── config.yaml
└── README.md
```

### Adding New Fix Patterns

Edit `fix_generator.py` and add to the patterns dictionary:

```python
FIX_PATTERNS = {
    'your_pattern_name': {
        'match': lambda error: 'specific text' in error,
        'fix': lambda context: generate_fix(context)
    }
}
```

## Troubleshooting

### Copilot Not Running
- Check GitHub Actions tab for workflow status
- Verify secrets are configured correctly
- Check workflow logs for errors

### Fixes Not Being Applied
- Ensure GitHub token has write permissions
- Check repository branch protection rules
- Verify AI API keys are valid

### Dashboard Not Loading
- Ensure Flask is installed
- Check port 5000 is not in use
- Verify logs directory exists

## Roadmap

- [ ] Multi-language support for error messages
- [ ] Slack/Discord notification integration
- [ ] Machine learning for failure prediction
- [ ] Cost optimization recommendations
- [ ] Performance metrics tracking
- [ ] Integration with monitoring tools (Datadog, New Relic)

## Contributing

Contributions welcome! Please:
1. Fork the repository
2. Create a feature branch
3. Submit a pull request

## License

MIT License

## Support

For issues or questions, please create a GitHub Issue in this repository.
