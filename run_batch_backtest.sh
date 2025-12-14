#!/bin/bash
#
# Wrapper script to run batch backtesting with system sleep prevention
# Uses macOS caffeinate to keep the system awake during execution
#

# Default Python path (can be overridden)
PYTHON="${PYTHON:-/opt/anaconda3/envs/berkeley_240/bin/python}"

# Get the directory where this script is located
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Prevent system from sleeping while this script runs
# -i: Prevent idle sleep (keeps system awake)
# -w: Wait for the process to exit
# -d: Prevent display from sleeping
# -m: Prevent disk from sleeping
exec caffeinate -i -w -d -m "$PYTHON" "$SCRIPT_DIR/run_batch_backtest.py" "$@"

