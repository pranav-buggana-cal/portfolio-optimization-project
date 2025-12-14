#!/bin/bash
#
# Simple wrapper to run backtest analysis
#

PYTHON="/opt/anaconda3/envs/berkeley_240/bin/python"

# Just run the processor - it reads from data/source_tables/ automatically
$PYTHON -c "
import sys
sys.path.insert(0, '.')
exec(open('backtest_analysis_processor_working.py').read())
" 2>&1 | grep -v "UserWarning"
