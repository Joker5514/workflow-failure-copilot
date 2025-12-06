#!/usr/bin/env python3
"""
Workflow Monitor - Scans GitHub repos for failed workflows and logs issues.
"""
import os
import json
import subprocess
from datetime import datetime

def get_failed_workflows():
    """Get list of failed workflow runs."""
    result = subprocess.run(
        ['gh', 'run', 'list', '--status', 'failure', '--limit', '20', '--json', 
         'databaseId,name,conclusion,createdAt,headBranch'],
        capture_output=True, text=True
    )
    if result.returncode == 0:
        return json.loads(result.stdout)
    return []

def log_failures(failures):
    """Log failures to file."""
    os.makedirs('logs', exist_ok=True)
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    log_file = f'logs/failures_{timestamp}.json'
    
    with open(log_file, 'w') as f:
        json.dump({
            'timestamp': timestamp,
            'failure_count': len(failures),
            'failures': failures
        }, f, indent=2)
    
    print(f"Logged {len(failures)} failures to {log_file}")
    return log_file

def main():
    print("🔍 Scanning for workflow failures...")
    failures = get_failed_workflows()
    
    if failures:
        print(f"⚠️  Found {len(failures)} failed workflows")
        for f in failures[:5]:
            print(f"  - {f['name']} ({f['headBranch']}): {f['conclusion']}")
        log_failures(failures)
    else:
        print("✅ No workflow failures found")
        # Create empty log to satisfy artifact upload
        os.makedirs('logs', exist_ok=True)
        with open('logs/no_failures.txt', 'w') as f:
            f.write(f"No failures detected at {datetime.now().isoformat()}\n")  # Fixed

if __name__ == '__main__':
    main()
