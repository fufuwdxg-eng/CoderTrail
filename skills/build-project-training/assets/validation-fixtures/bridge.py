"""Actual Python/JavaScript process boundary used by integration checks only."""
import subprocess
import sys

result = subprocess.run(['node', 'javascript/sum.mjs'], input=sys.stdin.read(),
                        text=True, capture_output=True, timeout=5, check=False)
sys.stdout.write(result.stdout)
sys.stderr.write(result.stderr)
raise SystemExit(result.returncode)
