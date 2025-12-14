#!/usr/bin/env python3
"""
Portfolio Grid Search Generator

Generates a grid of portfolio allocations for backtesting.
Based on the Midterm Asset Allocations with PE/VC removed.
"""

import pandas as pd
import numpy as np
import itertools
from pathlib import Path


def generate_coarse_grid():
    """
    Generate a coarse grid of portfolio allocations (~54 portfolios).

    Tests major variations across:
    - Equity/FI split
    - US/International equity mix
    - Fixed income composition
    - REIT allocation

    Returns:
        DataFrame with portfolio allocations
    """
    # Grid parameters
    equity_splits = [0.50, 0.675, 0.70]  # Total equity as % of portfolio
    us_equity_ratios = [0.70, 0.55, 0.50]  # US as % of total equity within equity
    intl_dev_ratios = [0.20, 0.22, 0.35]  # Intl Developed as % of total equity
    # Emerging will be the remainder after US and Intl Dev

    fi_treasury_ratios = [0.31, 0.40, 0.50]  # Treasuries as % of total FI
    fi_tips_ratios = [0.46, 0.40, 0.30]  # TIPS as % of total FI
    # Corp bonds will be the remainder

    reit_levels = [0.05, 0.075, 0.10]  # REIT as % of portfolio

    portfolios = []
    portfolio_id = 1

    # Generate all combinations
    for eq_split in equity_splits:
        for us_ratio in us_equity_ratios:
            for intl_ratio in intl_dev_ratios:
                for treas_ratio in fi_treasury_ratios:
                    for tips_ratio in fi_tips_ratios:
                        for reit in reit_levels:
                            # Calculate allocations
                            total_equity = eq_split
                            total_fi = 1.0 - total_equity

                            # Equity breakdown (REIT is separate)
                            non_reit_equity = total_equity - reit

                            us_equities = non_reit_equity * us_ratio
                            intl_dev = non_reit_equity * intl_ratio
                            emerging = non_reit_equity * (1 - us_ratio - intl_ratio)

                            # Skip if any allocation below 3% minimum
                            MIN_ALLOCATION = 0.03
                            if emerging < MIN_ALLOCATION:
                                continue
                            if us_equities < MIN_ALLOCATION or intl_dev < MIN_ALLOCATION:
                                continue

                            # Fixed income breakdown
                            treasuries = total_fi * treas_ratio
                            tips = total_fi * tips_ratio
                            corp_bonds = total_fi * (1 - treas_ratio - tips_ratio)

                            # Skip if any FI allocation below 3% minimum
                            if corp_bonds < MIN_ALLOCATION or treasuries < MIN_ALLOCATION or tips < MIN_ALLOCATION:
                                continue
                            if reit < MIN_ALLOCATION:
                                continue

                            # Create portfolio
                            portfolio = {
                                'portfolio_id': f'Grid_{portfolio_id:03d}',
                                'US Equities': us_equities,
                                'Foreign Developed Equities': intl_dev,
                                'Emerging Market Equities': emerging,
                                'US Treasuries': treasuries,
                                'TIPS': tips,
                                'Corporate Bonds': corp_bonds,
                                'Real Estate/REIT': reit,
                            }

                            # Verify sum is close to 1.0
                            total = sum([v for k, v in portfolio.items() if k != 'portfolio_id'])
                            if abs(total - 1.0) < 0.001:  # Allow small rounding error
                                # Normalize to exactly 1.0
                                for k in portfolio:
                                    if k != 'portfolio_id':
                                        portfolio[k] = portfolio[k] / total

                                portfolios.append(portfolio)
                                portfolio_id += 1

    df = pd.DataFrame(portfolios)
    return df


def generate_fine_grid():
    """
    Generate a fine grid of portfolio allocations (~300 portfolios).

    More granular variations for comprehensive search.

    Returns:
        DataFrame with portfolio allocations
    """
    # Finer grid parameters
    equity_splits = [0.40, 0.50, 0.60, 0.675, 0.70, 0.80]
    us_equity_ratios = [0.70, 0.60, 0.55, 0.50, 0.40]
    intl_dev_ratios = [0.20, 0.22, 0.30, 0.35, 0.40]

    fi_treasury_ratios = [0.20, 0.31, 0.40, 0.50]
    fi_tips_ratios = [0.30, 0.40, 0.46, 0.50]

    reit_levels = [0.05, 0.075, 0.10, 0.15, 0.20]

    portfolios = []
    portfolio_id = 1

    for eq_split in equity_splits:
        for us_ratio in us_equity_ratios:
            for intl_ratio in intl_dev_ratios:
                for treas_ratio in fi_treasury_ratios:
                    for tips_ratio in fi_tips_ratios:
                        for reit in reit_levels:
                            total_equity = eq_split
                            total_fi = 1.0 - total_equity

                            non_reit_equity = total_equity - reit

                            # Skip if REIT allocation is too high for this equity level
                            if non_reit_equity < 0.2:  # Minimum 20% in non-REIT equity
                                continue

                            us_equities = non_reit_equity * us_ratio
                            intl_dev = non_reit_equity * intl_ratio
                            emerging = non_reit_equity * (1 - us_ratio - intl_ratio)

                            # Apply 3% minimum allocation constraint
                            MIN_ALLOCATION = 0.03
                            if emerging < MIN_ALLOCATION or us_equities < MIN_ALLOCATION or intl_dev < MIN_ALLOCATION:
                                continue

                            treasuries = total_fi * treas_ratio
                            tips = total_fi * tips_ratio
                            corp_bonds = total_fi * (1 - treas_ratio - tips_ratio)

                            if corp_bonds < MIN_ALLOCATION or treasuries < MIN_ALLOCATION or tips < MIN_ALLOCATION:
                                continue
                            if reit < MIN_ALLOCATION:
                                continue

                            portfolio = {
                                'portfolio_id': f'FineGrid_{portfolio_id:03d}',
                                'US Equities': us_equities,
                                'Foreign Developed Equities': intl_dev,
                                'Emerging Market Equities': emerging,
                                'US Treasuries': treasuries,
                                'TIPS': tips,
                                'Corporate Bonds': corp_bonds,
                                'Real Estate/REIT': reit,
                            }

                            total = sum([v for k, v in portfolio.items() if k != 'portfolio_id'])
                            if abs(total - 1.0) < 0.001:
                                for k in portfolio:
                                    if k != 'portfolio_id':
                                        portfolio[k] = portfolio[k] / total

                                portfolios.append(portfolio)
                                portfolio_id += 1

    df = pd.DataFrame(portfolios)
    return df


def generate_random_portfolios(n_portfolios=100, seed=42):
    """
    Generate random portfolio allocations with constraints.

    Args:
        n_portfolios: Number of random portfolios to generate
        seed: Random seed for reproducibility

    Returns:
        DataFrame with portfolio allocations
    """
    np.random.seed(seed)
    portfolios = []
    MIN_ALLOCATION = 0.03

    attempts = 0
    max_attempts = n_portfolios * 10  # Avoid infinite loop

    while len(portfolios) < n_portfolios and attempts < max_attempts:
        attempts += 1

        # Random constraints
        total_equity = np.random.uniform(0.40, 0.80)
        reit = np.random.uniform(MIN_ALLOCATION, 0.20)
        non_reit_equity = total_equity - reit

        # Random equity split (using Dirichlet distribution for valid probabilities)
        equity_weights = np.random.dirichlet([2, 1.5, 1])  # Favor US slightly
        us_equities = non_reit_equity * equity_weights[0]
        intl_dev = non_reit_equity * equity_weights[1]
        emerging = non_reit_equity * equity_weights[2]

        # Skip if any below minimum
        if us_equities < MIN_ALLOCATION or intl_dev < MIN_ALLOCATION or emerging < MIN_ALLOCATION:
            continue

        # Random FI split
        total_fi = 1.0 - total_equity
        fi_weights = np.random.dirichlet([1.5, 1.5, 1])  # Equal-ish
        treasuries = total_fi * fi_weights[0]
        tips = total_fi * fi_weights[1]
        corp_bonds = total_fi * fi_weights[2]

        # Skip if any below minimum
        if treasuries < MIN_ALLOCATION or tips < MIN_ALLOCATION or corp_bonds < MIN_ALLOCATION:
            continue

        portfolio = {
            'portfolio_id': f'Random_{len(portfolios)+1:03d}',
            'US Equities': us_equities,
            'Foreign Developed Equities': intl_dev,
            'Emerging Market Equities': emerging,
            'US Treasuries': treasuries,
            'TIPS': tips,
            'Corporate Bonds': corp_bonds,
            'Real Estate/REIT': reit,
        }

        # Normalize
        total = sum([v for k, v in portfolio.items() if k != 'portfolio_id'])
        for k in portfolio:
            if k != 'portfolio_id':
                portfolio[k] = portfolio[k] / total

        # Final check after normalization
        if all(portfolio[k] >= MIN_ALLOCATION for k in portfolio if k != 'portfolio_id'):
            portfolios.append(portfolio)

    if len(portfolios) < n_portfolios:
        print(f"Warning: Only generated {len(portfolios)} valid portfolios out of {n_portfolios} requested")

    df = pd.DataFrame(portfolios)
    return df


def save_grid_for_backtest(df, output_path='data/source_tables/portfolio_allocations_grid.csv'):
    """
    Save portfolio grid in format ready for backtesting.

    Converts from long format to wide format expected by backtest processor.

    Args:
        df: DataFrame with portfolio allocations (from generate functions)
        output_path: Where to save the CSV
    """
    # Prepare data in Portfolio Visualizer format
    asset_mapping = {
        'US Equities': 'US Equities - US Stock Market',
        'Foreign Developed Equities': 'Foreign Developed Equities - Intl Developed ex-US Market',
        'Emerging Market Equities': 'Emerging Market Equities - Emerging Markets',
        'US Treasuries': 'US Treasuries - Intermediate Term Treasury',
        'TIPS': 'TIPS - Inflation-Protected Bonds',
        'Corporate Bonds': 'Corporate Bonds - Investment Grade Corporate Bonds',
        'Real Estate/REIT': 'Real Estate/REITs - US REIT',
    }

    # Create rows for each asset
    rows = []
    for i, (short_name, full_name) in enumerate(asset_mapping.items(), 1):
        row = {
            'Asset_Number': i,
            'Asset_Description': full_name,
        }

        # Add each portfolio's allocation for this asset (as percentage)
        for _, portfolio in df.iterrows():
            portfolio_id = portfolio['portfolio_id']
            row[portfolio_id] = portfolio[short_name] * 100  # Convert to percentage

        rows.append(row)

    df_output = pd.DataFrame(rows)

    # Save
    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
    df_output.to_csv(output_path, index=False)

    print(f"✓ Saved {len(df)} portfolios to: {output_path}")
    print(f"  Asset classes: {len(rows)}")
    print(f"  Format: Ready for backtesting")

    return df_output


def display_grid_summary(df):
    """Display summary statistics of the generated grid."""
    print("\n" + "="*80)
    print("PORTFOLIO GRID SUMMARY")
    print("="*80)
    print(f"Total portfolios: {len(df)}")

    # Calculate summary stats
    asset_cols = [c for c in df.columns if c != 'portfolio_id']

    print("\nAllocation ranges (as %):")
    for col in asset_cols:
        print(f"  {col:30s}: {df[col].min()*100:5.1f}% - {df[col].max()*100:5.1f}%  "
              f"(mean: {df[col].mean()*100:5.1f}%)")

    # Total equity vs FI
    equity_cols = ['US Equities', 'Foreign Developed Equities', 'Emerging Market Equities', 'Real Estate/REIT']
    fi_cols = ['US Treasuries', 'TIPS', 'Corporate Bonds']

    df['Total_Equity'] = df[[c for c in equity_cols if c in df.columns]].sum(axis=1)
    df['Total_FI'] = df[[c for c in fi_cols if c in df.columns]].sum(axis=1)

    print(f"\nTotal Equity range: {df['Total_Equity'].min()*100:.1f}% - {df['Total_Equity'].max()*100:.1f}%")
    print(f"Total FI range: {df['Total_FI'].min()*100:.1f}% - {df['Total_FI'].max()*100:.1f}%")

    print("\nSample portfolios:")
    print(df.head(3).to_string(index=False))

    print("="*80)


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description='Generate portfolio allocation grid')
    parser.add_argument('--type', choices=['coarse', 'fine', 'random'], default='coarse',
                       help='Type of grid to generate')
    parser.add_argument('--n', type=int, default=100,
                       help='Number of portfolios (for random type)')
    parser.add_argument('--output', default='data/source_tables/portfolio_allocations_grid.csv',
                       help='Output file path')

    args = parser.parse_args()

    print(f"Generating {args.type} portfolio grid...")

    if args.type == 'coarse':
        df = generate_coarse_grid()
    elif args.type == 'fine':
        df = generate_fine_grid()
    else:  # random
        df = generate_random_portfolios(n_portfolios=args.n)

    display_grid_summary(df)
    save_grid_for_backtest(df, args.output)

    print(f"\nNext steps:")
    print(f"1. Review the generated file: {args.output}")
    print(f"2. Upload to Portfolio Visualizer for backtesting")
    print(f"3. Download results and save to data/source_tables/")
    print(f"4. Run: python backtest_analysis_processor.py")
    print(f"5. Analyze results to find optimal portfolio")
