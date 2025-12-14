# Treasury Term Structure Grid Search - Follow-up Analysis

## Overview

This follow-up grid search addresses a limitation identified in the original Grid_019 optimization: **all portfolios tested only used Intermediate Term Treasuries**.

We now test variations across the full treasury yield curve to determine if splitting the 25% treasury allocation across different maturities can improve the Sharpe ratio beyond 0.7045.

## Grid_019 Baseline (Original Optimal)

**Allocation:**
- US Equities: 31.5%
- Foreign Developed: 9.0%
- Emerging Markets: 4.5%
- **Intermediate Treasury: 25.0%** ← To be split across maturities
- TIPS: 20.0%
- Corporate Bonds: 5.0%
- REITs: 5.0%

**Performance:**
- Sharpe Ratio: 0.7045
- CAGR: 7.43%
- Volatility: 8.34%
- Max Drawdown: -27.28%

## Treasury Term Structure Options

Testing allocation splits across four treasury maturity buckets:

1. **ShortTreasury** - Short Term Treasury
2. **IntermediateTreasury** - Intermediate Term Treasury
3. **TreasuryNotes** - 10-year Treasury
4. **LongTreasury** - Long Term Treasury

**Total Treasury Allocation:** 25% (fixed)

## Grid Search Design

### Methodology
- **Total Portfolios:** 56 configurations
- **Increment Size:** 5% steps (0%, 5%, 10%, 15%, 20%, 25%)
- **Constraint:** All four treasury allocations must sum to exactly 25%
- **Non-Treasury Assets:** Held constant at Grid_019 values

### Sample Configurations

| Portfolio | Short | Intermediate | 10-Year | Long |
|-----------|-------|--------------|---------|------|
| TreasuryGrid_001 | 0% | 0% | 0% | 25% |
| TreasuryGrid_002 | 0% | 0% | 5% | 20% |
| TreasuryGrid_019 | 0% | 25% | 0% | 0% | ← Baseline (Grid_019)
| TreasuryGrid_028 | 5% | 5% | 10% | 5% | ← Diversified example
| TreasuryGrid_056 | 25% | 0% | 0% | 0% | ← All short-term

## Expected Insights

### Potential Outcomes

1. **Barbell Strategy** (Short + Long)
   - May capture yield curve premium
   - Higher duration risk
   - Potentially higher volatility

2. **Ladder Strategy** (Equal weights)
   - Interest rate risk diversification
   - Moderate duration
   - Stable performance

3. **Intermediate Concentration** (Baseline)
   - Grid_019 may already be optimal
   - Moderate duration
   - Proven Sharpe of 0.7045

4. **Short-Term Tilt**
   - Lower volatility
   - Lower returns
   - Better drawdown protection?

### Questions to Answer

1. Can we beat Sharpe 0.7045 by optimizing treasury term structure?
2. Does duration exposure matter for risk-adjusted returns?
3. Is there a "sweet spot" on the yield curve for this portfolio?
4. How sensitive is Sharpe ratio to treasury maturity mix?

## Files Generated

### Portfolio Configuration Files
Located in `data/source_tables/`:

1. **treasury_term_portfolio_grid.csv**
   - 56 rows × 11 columns
   - Format: Grid_ID as rows, asset classes as columns
   - Each row sums to 100%

2. **treasury_term_allocations.csv**
   - 10 rows × 57 columns
   - Format: Asset_Number as rows, TreasuryGrid_XXX as columns
   - Ready for backtest automation

### Distribution Statistics

```
Short Term Treasury:
  Min: 0.0%, Max: 25.0%, Mean: 6.2%
  Portfolios with >0%: 35

Intermediate Term Treasury:
  Min: 0.0%, Max: 25.0%, Mean: 6.2%
  Portfolios with >0%: 35

10-year Treasury:
  Min: 0.0%, Max: 25.0%, Mean: 6.2%
  Portfolios with >0%: 35

Long Term Treasury:
  Min: 0.0%, Max: 25.0%, Mean: 6.2%
  Portfolios with >0%: 35
```

## Next Steps

### 1. Create Batch Files
Generate batch configuration files for parallel processing:
```bash
python consolidate_batch_results.py --create-batches treasury_term
```

### 2. Run Backtest
Execute the treasury term structure grid search:
```bash
python run_batch_backtest_optimized.py --grid treasury_term --batches 1-20
```

### 3. Analyze Results
Compare Sharpe ratios across treasury configurations:
- Identify top performers
- Analyze term structure patterns
- Compare to Grid_019 baseline

### 4. Validate Findings
If a superior allocation is found:
- Verify statistical significance
- Test on out-of-sample period
- Document rationale for changes

## Expected Timeline

- **Batch Creation:** ~2 minutes
- **Backtest Execution:** ~20 minutes (56 portfolios ÷ 3 per batch × 22 seconds)
- **Analysis:** ~5 minutes
- **Total:** ~30 minutes end-to-end

## Success Criteria

**Goal:** Find a treasury term structure that achieves Sharpe > 0.7045

**Minimum Success:**
- Sharpe ≥ 0.7045 (match Grid_019)
- Max drawdown ≤ -27.28%
- Volatility ≤ 8.50%

**Stretch Goal:**
- Sharpe ≥ 0.7200 (+2.2% improvement)
- Similar or better risk metrics
- Clear term structure pattern

## Risk Considerations

1. **Over-fitting Risk:** More parameters = higher risk of curve-fitting
2. **Data Mining:** Testing 56 variations increases false discovery risk
3. **Transaction Costs:** More complex allocations may have higher turnover
4. **Liquidity:** Long-term treasuries may have different liquidity profiles

## Related Files

- `generate_treasury_term_grid.py` - Grid generation script
- `portfolio_optimization.ipynb` - Updated with Grid_019 results only
- `GRID_SEARCH_RESULTS.md` - Original grid search summary
- `optimal_portfolio_weights.csv` - Current Grid_019 allocation

---

**Generated:** December 14, 2025
**Baseline Portfolio:** Grid_019
**Objective:** Optimize treasury term structure for maximum Sharpe ratio
