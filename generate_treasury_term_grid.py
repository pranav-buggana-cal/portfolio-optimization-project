#!/usr/bin/env python3
"""
Generate Treasury Term Structure Grid Search
============================================
Takes the Grid_019 optimal allocation and creates variations by splitting
the 25% Intermediate Treasury allocation across different treasury maturities:
- ShortTreasury (Short Term Treasury)
- IntermediateTreasury (Intermediate Term Treasury)
- TreasuryNotes (10-year Treasury)
- LongTreasury (Long Term Treasury)

Base Grid_019 Allocation:
- US Equities: 31.5%
- Foreign Developed: 9.0%
- Emerging Markets: 4.5%
- Intermediate Treasury: 25.0% <- This will be split
- TIPS: 20.0%
- Corporate Bonds: 5.0%
- REITs: 5.0%
"""

import pandas as pd
import numpy as np
from itertools import product

# Base Grid_019 allocation (non-treasury assets remain constant)
BASE_ALLOCATION = {
    'TotalStockMarket': 31.5,      # US Equities
    'IntlDeveloped': 9.0,          # Foreign Developed
    'EmergingMarket': 4.5,         # Emerging Markets
    'TIPS': 20.0,                  # TIPS (stays constant)
    'CorpBond': 5.0,               # Corporate Bonds
    'REIT': 5.0                    # REITs
}

# Total treasury allocation to split
TOTAL_TREASURY = 25.0

# Define the treasury term options (using the Portfolio Visualizer values)
TREASURY_OPTIONS = {
    'ShortTreasury': 'Short Term Treasury',
    'IntermediateTreasury': 'Intermediate Term Treasury',
    'TreasuryNotes': '10-year Treasury',
    'LongTreasury': 'Long Term Treasury'
}

def generate_treasury_splits():
    """
    Generate combinations of treasury allocations that sum to 25%
    Using increments of 5% with minimum 0% per maturity
    """
    splits = []

    # Generate all combinations that sum to 25%
    # Using 5% increments: 0, 5, 10, 15, 20, 25
    increments = [0, 5, 10, 15, 20, 25]

    for short in increments:
        for intermediate in increments:
            for ten_year in increments:
                for long in increments:
                    if short + intermediate + ten_year + long == TOTAL_TREASURY:
                        # Only include if at least one treasury type is used
                        if max(short, intermediate, ten_year, long) > 0:
                            splits.append({
                                'ShortTreasury': short,
                                'IntermediateTreasury': intermediate,
                                'TreasuryNotes': ten_year,
                                'LongTreasury': long
                            })

    return splits

def create_portfolio_grid():
    """Create the portfolio grid with treasury term structure variations"""

    treasury_splits = generate_treasury_splits()

    print(f"Generated {len(treasury_splits)} treasury term structure combinations")
    print(f"\nSample combinations:")
    for i, split in enumerate(treasury_splits[:5]):
        print(f"  {i+1}. Short: {split['ShortTreasury']}%, Int: {split['IntermediateTreasury']}%, "
              f"10yr: {split['TreasuryNotes']}%, Long: {split['LongTreasury']}%")

    # Create portfolio configurations
    portfolios = []

    for idx, treasury_split in enumerate(treasury_splits, start=1):
        portfolio = {
            'Grid_ID': f'TreasuryGrid_{idx:03d}',
            'TotalStockMarket': BASE_ALLOCATION['TotalStockMarket'],
            'IntlDeveloped': BASE_ALLOCATION['IntlDeveloped'],
            'EmergingMarket': BASE_ALLOCATION['EmergingMarket'],
            'ShortTreasury': treasury_split['ShortTreasury'],
            'IntermediateTreasury': treasury_split['IntermediateTreasury'],
            'TreasuryNotes': treasury_split['TreasuryNotes'],
            'LongTreasury': treasury_split['LongTreasury'],
            'TIPS': BASE_ALLOCATION['TIPS'],
            'CorpBond': BASE_ALLOCATION['CorpBond'],
            'REIT': BASE_ALLOCATION['REIT']
        }

        # Verify sum equals 100%
        total = sum([v for k, v in portfolio.items() if k != 'Grid_ID'])
        assert abs(total - 100.0) < 0.01, f"Portfolio {portfolio['Grid_ID']} sums to {total}%"

        portfolios.append(portfolio)

    return pd.DataFrame(portfolios)

def create_asset_mapping_table(grid_df):
    """Create the asset mapping table for the backtest"""

    # Define asset classes in the order they'll be used
    asset_mapping = [
        {
            'Asset_Number': 1,
            'Asset_Class_Option_Value': 'TotalStockMarket',
            'Asset_Description': 'US Equities - US Stock Market',
            'Category': 'Equity'
        },
        {
            'Asset_Number': 2,
            'Asset_Class_Option_Value': 'IntlDeveloped',
            'Asset_Description': 'Foreign Developed Equities - Intl Developed ex-US Market',
            'Category': 'Equity'
        },
        {
            'Asset_Number': 3,
            'Asset_Class_Option_Value': 'EmergingMarket',
            'Asset_Description': 'Emerging Market Equities - Emerging Markets',
            'Category': 'Equity'
        },
        {
            'Asset_Number': 4,
            'Asset_Class_Option_Value': 'ShortTreasury',
            'Asset_Description': 'US Treasuries - Short Term Treasury',
            'Category': 'Fixed Income'
        },
        {
            'Asset_Number': 5,
            'Asset_Class_Option_Value': 'IntermediateTreasury',
            'Asset_Description': 'US Treasuries - Intermediate Term Treasury',
            'Category': 'Fixed Income'
        },
        {
            'Asset_Number': 6,
            'Asset_Class_Option_Value': 'TreasuryNotes',
            'Asset_Description': 'US Treasuries - 10-year Treasury',
            'Category': 'Fixed Income'
        },
        {
            'Asset_Number': 7,
            'Asset_Class_Option_Value': 'LongTreasury',
            'Asset_Description': 'US Treasuries - Long Term Treasury',
            'Category': 'Fixed Income'
        },
        {
            'Asset_Number': 8,
            'Asset_Class_Option_Value': 'TIPS',
            'Asset_Description': 'TIPS - Inflation-Protected Bonds',
            'Category': 'Fixed Income'
        },
        {
            'Asset_Number': 9,
            'Asset_Class_Option_Value': 'CorpBond',
            'Asset_Description': 'Corporate Bonds - Investment Grade Corporate Bonds',
            'Category': 'Fixed Income'
        },
        {
            'Asset_Number': 10,
            'Asset_Class_Option_Value': 'REIT',
            'Asset_Description': 'Real Estate/REITs - US REIT',
            'Category': 'Alternative'
        }
    ]

    # Create the transposed table (Asset_Number, Asset_Description, Grid_001, Grid_002, ...)
    asset_df = pd.DataFrame(asset_mapping)

    # Add allocation columns for each grid
    for _, portfolio in grid_df.iterrows():
        grid_id = portfolio['Grid_ID']
        allocations = []

        for asset in asset_df['Asset_Class_Option_Value']:
            allocations.append(portfolio[asset])

        asset_df[grid_id] = allocations

    return asset_df[['Asset_Number', 'Asset_Description'] + [col for col in asset_df.columns if col.startswith('TreasuryGrid_')]]

def main():
    print("=" * 80)
    print("Treasury Term Structure Grid Search Generator")
    print("=" * 80)
    print("\nBase Portfolio (Grid_019):")
    for key, value in BASE_ALLOCATION.items():
        print(f"  {key:20s}: {value:5.1f}%")
    print(f"  {'Treasury (to split)':20s}: {TOTAL_TREASURY:5.1f}%")
    print(f"  {'TOTAL':20s}: {sum(BASE_ALLOCATION.values()) + TOTAL_TREASURY:5.1f}%")

    print("\n" + "=" * 80)

    # Generate portfolio grid
    grid_df = create_portfolio_grid()

    print(f"\nGenerated {len(grid_df)} portfolio configurations")
    print(f"\nFirst 5 portfolios:")
    print(grid_df.head().to_string(index=False))

    # Create asset mapping table
    asset_table = create_asset_mapping_table(grid_df)

    # Save outputs
    output_dir = 'data/source_tables'

    # Portfolio grid (Grid_ID as rows, assets as columns)
    grid_file = f'{output_dir}/treasury_term_portfolio_grid.csv'
    grid_df.to_csv(grid_file, index=False)
    print(f"\n✓ Saved portfolio grid: {grid_file}")

    # Asset allocation table (Asset_Number as rows, Grid_IDs as columns)
    asset_file = f'{output_dir}/treasury_term_allocations.csv'
    asset_table.to_csv(asset_file, index=False)
    print(f"✓ Saved asset allocations: {asset_file}")

    # Summary statistics
    print("\n" + "=" * 80)
    print("Treasury Allocation Distribution Across Portfolios:")
    print("=" * 80)

    for treasury_type in ['ShortTreasury', 'IntermediateTreasury', 'TreasuryNotes', 'LongTreasury']:
        allocations = grid_df[treasury_type]
        print(f"\n{TREASURY_OPTIONS[treasury_type]}:")
        print(f"  Min: {allocations.min():.1f}%")
        print(f"  Max: {allocations.max():.1f}%")
        print(f"  Mean: {allocations.mean():.1f}%")
        print(f"  Portfolios with >0%: {(allocations > 0).sum()}")

    print("\n" + "=" * 80)
    print("Summary")
    print("=" * 80)
    print(f"Total portfolios: {len(grid_df)}")
    print(f"Asset classes: {len(asset_table)}")
    print(f"Treasury term splits tested: {len(grid_df)}")
    print(f"\nNext steps:")
    print(f"1. Review generated files in {output_dir}/")
    print(f"2. Create batch files using consolidate_batch_results.py logic")
    print(f"3. Run backtest using run_batch_backtest_optimized.py")
    print("=" * 80)

if __name__ == '__main__':
    main()
