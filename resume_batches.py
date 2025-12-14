#!/usr/bin/env python3
"""Simple script to resume batch processing from 118-192"""
import subprocess
import sys

python_path = "/opt/anaconda3/envs/berkeley_240/bin/python"
script = "run_batch_backtest_optimized.py"

# Run without headless mode
cmd = [python_path, script, "--start-batch", "118", "--no-headless"]

print("Starting batch processing from batch 118...")
print(f"Command: {' '.join(cmd)}")

result = subprocess.run(cmd)
sys.exit(result.returncode)
