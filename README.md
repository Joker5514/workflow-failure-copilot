# Workflow Failure Copilot 🤖

Automated copilot that monitors all GitHub repositories for workflow failures, analyzes errors with AI (OpenAI/Claude), auto-generates fixes, creates commits, retries workflows, and sends GitHub Issue notifications when manual help is needed.

## Features

- 🔍 **Automated Monitoring**: Scans all your GitHub repositories for failed workflow runs
- 🧠 **AI-Powered Analysis**: Uses OpenAI GPT-4 or Claude to analyze error logs and identify root causes
- 🔧 **Auto-Fix Generation**: Automatically generates fixes for common issues (outdated actions, Node.js versions, etc.)
- 📝 **Commit Management**: Creates commits with fixes directly to your repositories
- 🔄 **Workflow Retry**: Automatically retries failed workflows with exponential backoff
- 📢 **GitHub Issue Notifications**: Creates detailed issues when manual intervention is required
- 📊 **Web Dashboard**: Real-time monitoring dashboard for workflow failures
- ⏰ **Scheduled Runs**: Runs hourly via GitHub Actions workflow

## Quick Start

### 1. Clone and Install

```bash
git clone https://github.com/your-org/workflow-failure-copilot.git
cd workflow-failure-copilot
pip install -r requirements.txt
```

### 2. Configure Environment

Create a `.env` file or set environment variables:

```bash
# Required
GITHUB_TOKEN=your_github_personal_access_token

# AI Configuration (at least one is required)
OPENAI_API_KEY=your_openai_api_key
# OR
ANTHROPIC_API_KEY=your_anthropic_api_key

# Optional: AI Provider selection (default: openai)
AI_PROVIDER=openai  # or 'anthropic'
AI_MODEL=gpt-4      # or 'claude-3-opus-20240229'

# Optional: Repository filtering
GITHUB_ORG=your-organization          # Monitor all repos in an org
GITHUB_REPOS=owner/repo1,owner/repo2  # Or specific repos

# Optional: Notification settings
CREATE_ISSUES=true
ISSUE_ASSIGNEES=user1,user2

# Optional: Retry settings
MAX_RETRIES=3
LOOKBACK_HOURS=24
```

### 3. Run

```bash
# Run the monitor (scans for failures and processes them)
cd src
python main.py monitor

# Quick scan without processing
python main.py scan

# Start the dashboard
python main.py dashboard
```

## GitHub Actions Integration

The included workflow runs hourly to monitor your repositories:

1. Fork or clone this repository
2. Add the following secrets to your repository:
   - `OPENAI_API_KEY` or `ANTHROPIC_API_KEY`
3. Configure the following repository variables (optional):
   - `AI_PROVIDER`: `openai` or `anthropic`
   - `GITHUB_ORG`: Organization to monitor
   - `GITHUB_REPOS`: Comma-separated list of repos
   - `CREATE_ISSUES`: `true` or `false`
   - `ISSUE_ASSIGNEES`: Comma-separated usernames

The workflow will automatically:
- Run every hour
- Scan configured repositories
- Analyze failures with AI
- Attempt auto-fixes
- Retry transient failures
- Create issues for manual intervention

## Architecture

```
src/
├── main.py                    # Entry point
└── workflow_monitor/
    ├── config.py              # Configuration management
    ├── workflow_monitor.py    # Core monitoring logic
    ├── error_analyzer.py      # AI-powered error analysis
    ├── fix_generator.py       # Auto-fix generation
    ├── commit_manager.py      # Git commit management
    ├── workflow_retry.py      # Workflow retry logic
    ├── notification.py        # GitHub Issue notifications
    └── dashboard.py           # Flask web dashboard
```

## Auto-Fix Patterns

The system can automatically fix common issues:

| Pattern | Fix Applied |
|---------|-------------|
| Outdated Node.js versions | Upgrade to Node.js 20 LTS |
| `actions/checkout@v2` | Upgrade to `@v4` |
| `actions/setup-node@v2` | Upgrade to `@v4` |
| `actions/setup-python@v2` | Upgrade to `@v5` |

## Dashboard

The web dashboard provides:
- Real-time view of all workflow failures
- One-click manual scan trigger
- Failure details with links to GitHub
- Auto-refresh every 5 minutes

Access at `http://localhost:5000` when running `python main.py dashboard`.

## API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/` | GET | Dashboard home page |
| `/api/failures` | GET | List all failures |
| `/api/scan` | POST | Trigger a scan |
| `/api/status` | GET | System status |
| `/health` | GET | Health check |

## Configuration Options

| Variable | Default | Description |
|----------|---------|-------------|
| `GITHUB_TOKEN` | Required | GitHub personal access token |
| `OPENAI_API_KEY` | - | OpenAI API key |
| `ANTHROPIC_API_KEY` | - | Anthropic API key |
| `AI_PROVIDER` | `openai` | AI provider (`openai` or `anthropic`) |
| `AI_MODEL` | `gpt-4` | AI model to use |
| `GITHUB_ORG` | - | Organization to monitor |
| `GITHUB_REPOS` | - | Comma-separated repo list |
| `CREATE_ISSUES` | `true` | Create issues for manual intervention |
| `ISSUE_ASSIGNEES` | - | Comma-separated assignees |
| `MAX_RETRIES` | `3` | Maximum retry attempts |
| `RETRY_DELAY_SECONDS` | `60` | Initial retry delay |
| `LOOKBACK_HOURS` | `24` | Hours to look back for failures |
| `DASHBOARD_HOST` | `0.0.0.0` | Dashboard host |
| `DASHBOARD_PORT` | `5000` | Dashboard port |

## Required Permissions

The GitHub token needs the following permissions:
- `repo`: Full control of repositories (for commits and workflow reruns)
- `workflow`: Update GitHub Action workflows
- `issues:write`: Create and update issues

## Development

### Running Tests

```bash
pytest tests/ -v
```

### Linting

```bash
flake8 src/ tests/
mypy src/
```

### Code Formatting

```bash
black src/ tests/
isort src/ tests/
```

## License

MIT License - See LICENSE file for details.
