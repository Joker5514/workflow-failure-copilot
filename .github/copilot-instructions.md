# Copilot Instructions for workflow-failure-copilot

## Project Overview
This repository contains a Python-based workflow monitoring system that:
- Monitors GitHub Actions workflows for failures
- Analyzes errors using AI (OpenAI/Claude)
- Auto-generates fixes for common issues
- Creates GitHub Issues when manual intervention needed

## Code Style
- Python 3.11+
- Use type hints for all functions
- Follow PEP 8 guidelines
- Use Black for formatting
- Use Ruff for linting

## Architecture
- `workflow_monitor.py` - Main monitoring script
- `.github/workflows/` - GitHub Actions workflows
- `requirements.txt` - Python dependencies

## When Making Changes
- Ensure all workflow files use actions v4+ (checkout, setup-python, upload-artifact)
- Add error handling with try/except blocks
- Log important events using print() or logging module
- Create logs/ directory for artifact uploads

## Testing
- Run `python workflow_monitor.py` locally to test
- Check GitHub Actions tab for workflow status

## Common Fixes
- Upgrade deprecated actions (v3 → v4)
- Add missing permissions to workflows
- Fix YAML indentation issues
