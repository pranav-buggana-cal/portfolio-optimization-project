#!/bin/bash
#
# Portfolio Optimization Workflow Orchestrator
#
# This script runs the complete portfolio optimization workflow:
# 1. Generate portfolio allocation grid
# 2. Run backtests (via portfolio_backtest.py)
# 3. Parse results and extract performance metrics
#
# Usage:
#   ./run_portfolio_optimization.sh [grid_type]
#
# Arguments:
#   grid_type: coarse, fine, or random (default: coarse)
#

set -e  # Exit on any error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
PYTHON="/opt/anaconda3/envs/berkeley_240/bin/python"
GRID_TYPE="${1:-coarse}"
N_RANDOM="${2:-100}"

# Files
GRID_FILE="data/source_tables/portfolio_allocations_grid.csv"
BACKTEST_RESULTS="data/source_tables/portfolio_backtest_results.xlsx"

echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}Portfolio Optimization Workflow${NC}"
echo -e "${BLUE}========================================${NC}"
echo ""

# Step 1: Generate portfolio grid
echo -e "${YELLOW}[1/3] Generating portfolio grid (type: ${GRID_TYPE})...${NC}"
if [ "$GRID_TYPE" = "random" ]; then
    $PYTHON generate_portfolio_grid.py --type random --n $N_RANDOM --output $GRID_FILE
else
    $PYTHON generate_portfolio_grid.py --type $GRID_TYPE --output $GRID_FILE
fi

if [ $? -ne 0 ]; then
    echo -e "${RED}✗ Failed to generate portfolio grid${NC}"
    exit 1
fi

echo -e "${GREEN}✓ Portfolio grid generated: $GRID_FILE${NC}"
echo ""

# Step 2: Run backtests
echo -e "${YELLOW}[2/3] Running backtests...${NC}"
echo -e "${BLUE}Note: This will use the portfolio_backtest.py script${NC}"

# Check if portfolio_backtest.py exists
if [ -f "portfolio_backtest.py" ]; then
    # Run with grid file and alias
    $PYTHON portfolio_backtest.py --allocations "$GRID_FILE" --alias "$GRID_TYPE"
    BACKTEST_EXIT=$?
elif [ -f "archived/portfolio_backtest.py" ]; then
    $PYTHON archived/portfolio_backtest.py --allocations "$GRID_FILE" --alias "$GRID_TYPE"
    BACKTEST_EXIT=$?
else
    echo -e "${RED}✗ portfolio_backtest.py not found${NC}"
    echo -e "${YELLOW}Manual backtest required:${NC}"
    echo -e "${YELLOW}  1. Upload $GRID_FILE to Portfolio Visualizer${NC}"
    echo -e "${YELLOW}  2. Download results to $BACKTEST_RESULTS${NC}"
    echo -e "${YELLOW}  3. Then run: $PYTHON backtest_analysis_processor_working.py${NC}"
    exit 1
fi

if [ $BACKTEST_EXIT -ne 0 ]; then
    echo -e "${RED}✗ Backtest failed${NC}"
    echo -e "${YELLOW}Manual backtest required:${NC}"
    echo -e "${YELLOW}  1. Upload $GRID_FILE to Portfolio Visualizer${NC}"
    echo -e "${YELLOW}  2. Download results to $BACKTEST_RESULTS${NC}"
    echo -e "${YELLOW}  3. Then run: $PYTHON backtest_analysis_processor_working.py${NC}"
    exit 1
fi

echo -e "${GREEN}✓ Backtests completed${NC}"
echo ""

# Step 3: Parse results and extract metrics
echo -e "${YELLOW}[3/3] Parsing backtest results and extracting metrics...${NC}"

# Look for the results file with alias
RESULTS_WITH_ALIAS="data/source_tables/portfolio_backtest_results_${GRID_TYPE}*.xlsx"
RESULTS_FILES=($(ls $RESULTS_WITH_ALIAS 2>/dev/null | head -1))

if [ ${#RESULTS_FILES[@]} -eq 0 ]; then
    echo -e "${YELLOW}No results file found with alias ${GRID_TYPE}, trying default location...${NC}"
    if [ ! -f "$BACKTEST_RESULTS" ]; then
        echo -e "${RED}✗ Backtest results not found: $BACKTEST_RESULTS${NC}"
        echo -e "${YELLOW}Please ensure backtest results Excel file exists${NC}"
        echo -e "${YELLOW}You may need to manually download from Portfolio Visualizer${NC}"
        exit 1
    fi
fi

# Run the analysis processor (suppressing numpy warnings)
$PYTHON backtest_analysis_processor_working.py 2>&1 | grep -v "UserWarning"
ANALYSIS_EXIT=${PIPESTATUS[0]}

if [ $ANALYSIS_EXIT -ne 0 ]; then
    echo -e "${RED}✗ Failed to parse backtest results${NC}"
    exit 1
fi

echo -e "${GREEN}✓ Results parsed and metrics extracted${NC}"
echo ""

# Summary
echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}Workflow Complete!${NC}"
echo -e "${BLUE}========================================${NC}"
echo ""
echo -e "${GREEN}Generated files:${NC}"
echo -e "  ${YELLOW}Grid:${NC}     $GRID_FILE"
echo -e "  ${YELLOW}Results:${NC}  $BACKTEST_RESULTS"
echo -e "  ${YELLOW}Metadata:${NC} data/generated_tables/portfolio_metadata.csv"
echo -e "  ${YELLOW}Metrics:${NC}  data/generated_tables/portfolio_performance_metrics.csv"
echo -e "  ${YELLOW}UUIDs:${NC}    data/generated_tables/portfolio_uuid_mapping.csv"
echo ""
echo -e "${YELLOW}Next steps:${NC}"
echo -e "  1. Analyze performance metrics"
echo -e "  2. Find optimal portfolio (max Sharpe Ratio)"
echo -e "  3. Visualize results in portfolio_optimization.ipynb"
echo ""

# Display quick stats
if [ -f "data/generated_tables/portfolio_performance_metrics.csv" ]; then
    echo -e "${BLUE}Quick Stats:${NC}"
    PORTFOLIOS=$($PYTHON -c "import pandas as pd; df=pd.read_csv('data/generated_tables/portfolio_uuid_mapping.csv'); print(len(df))")
    echo -e "  ${GREEN}Portfolios analyzed:${NC} $PORTFOLIOS"

    echo -e "\n${BLUE}Top 5 portfolios by Sharpe Ratio:${NC}"
    $PYTHON -c "
import pandas as pd
df = pd.read_csv('data/generated_tables/portfolio_performance_metrics.csv')
sharpe = df[df['metric_name'] == 'Sharpe Ratio'].sort_values('metric_value', ascending=False).head(5)
for i, row in sharpe.iterrows():
    print(f'  {row[\"portfolio_name\"]}: {row[\"metric_value\"]:.4f}')
"
fi

echo ""
echo -e "${GREEN}✓ All done!${NC}"
