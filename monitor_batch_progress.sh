#!/bin/bash
# Monitor batch processing progress

echo "==================================="
echo "BATCH PROCESSING PROGRESS MONITOR"
echo "==================================="
echo ""

# Count completed batches
COMPLETED=$(ls data/source_tables/portfolio_backtest_results_batch_*.xlsx 2>/dev/null | wc -l | tr -d ' ')
TOTAL=192
PERCENT=$((COMPLETED * 100 / TOTAL))

echo "Completed Batches: $COMPLETED / $TOTAL ($PERCENT%)"
echo ""

# Check if process is running
if ps aux | grep -v grep | grep "run_batch_backtest_optimized.py" > /dev/null; then
    echo "Status: RUNNING ✓"

    # Show current batch from log
    CURRENT_BATCH=$(tail -20 batch_run.log | grep "PROCESSING BATCH" | tail -1 | grep -oE '[0-9]+')
    if [ ! -z "$CURRENT_BATCH" ]; then
        echo "Current Batch: $CURRENT_BATCH"
    fi
else
    echo "Status: NOT RUNNING ✗"
fi

echo ""
echo "Latest completions:"
ls -lt data/source_tables/portfolio_backtest_results_batch_*.xlsx 2>/dev/null | head -5 | awk '{print "  " $9 " (" $6 " " $7 " " $8 ")"}'

echo ""
echo "Estimated time remaining:"
if [ $COMPLETED -gt 0 ] && ps aux | grep -v grep | grep "run_batch_backtest_optimized.py" > /dev/null; then
    # Calculate average time per batch (rough estimate)
    FIRST_FILE=$(ls -t data/source_tables/portfolio_backtest_results_batch_*.xlsx 2>/dev/null | tail -1)
    LAST_FILE=$(ls -t data/source_tables/portfolio_backtest_results_batch_*.xlsx 2>/dev/null | head -1)

    if [ ! -z "$FIRST_FILE" ] && [ ! -z "$LAST_FILE" ]; then
        START_TIME=$(stat -f %m "$FIRST_FILE")
        END_TIME=$(stat -f %m "$LAST_FILE")
        ELAPSED=$((END_TIME - START_TIME))

        if [ $ELAPSED -gt 0 ] && [ $COMPLETED -gt 0 ]; then
            AVG_PER_BATCH=$((ELAPSED / COMPLETED))
            REMAINING=$((TOTAL - COMPLETED))
            ETA_SECONDS=$((REMAINING * AVG_PER_BATCH))
            ETA_MINUTES=$((ETA_SECONDS / 60))
            ETA_HOURS=$((ETA_MINUTES / 60))
            ETA_MINS_REMAINDER=$((ETA_MINUTES % 60))

            echo "  ~${ETA_HOURS}h ${ETA_MINS_REMAINDER}m (based on ~${AVG_PER_BATCH}s/batch average)"
        fi
    fi
fi

echo ""
echo "==================================="
