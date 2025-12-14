#!/usr/bin/env python3
"""
Consolidate Batch Backtest Results

Combines multiple batch backtest Excel files into unified metadata and metrics tables.
"""

import pandas as pd
import os
import sys
import uuid
import glob
from pathlib import Path


def parse_all_tables(file_path, sheet_name="Asset Allocation Report"):
    """Parse all tables from Excel file (imported from backtest_analysis_processor)."""
    # Import the parsing function
    sys.path.insert(0, ".")
    from backtest_analysis_processor_working import parse_all_tables as parse_tables

    return parse_tables(file_path, sheet_name)


def extract_portfolio_names_from_batch(all_tables):
    """
    Extract portfolio column names from parsed tables.

    Args:
        all_tables: Dictionary of parsed tables

    Returns:
        List of portfolio column names
    """
    # Look in the performance table
    for table_name in all_tables:
        if "Portfolio Performance" in table_name:
            df = all_tables[table_name]
            # Portfolio columns are everything except the first (metric name)
            portfolio_cols = [
                col for col in df.columns[1:] if "Portfolio" in col or "Sample" in col
            ]
            return portfolio_cols

    return []


def generate_batch_metadata(batch_results_file, batch_file, portfolio_uuid_map):
    """
    Generate metadata for a batch of portfolios.

    Args:
        batch_results_file: Path to batch backtest results Excel
        batch_file: Path to batch allocations CSV
        portfolio_uuid_map: Existing UUID map to extend

    Returns:
        DataFrame with metadata rows
        Updated UUID map
    """
    # Load batch allocations
    df_batch = pd.read_csv(batch_file)

    # Get portfolio columns from this batch
    portfolio_cols = [
        col
        for col in df_batch.columns
        if col.startswith("Grid_")
        or col.startswith("Portfolio_")
        or col.startswith("TreasuryGrid_")
    ]

    metadata_rows = []

    for i, portfolio_col in enumerate(portfolio_cols, start=1):
        # Check if we already have a UUID for this portfolio
        if portfolio_col not in portfolio_uuid_map:
            portfolio_uuid_map[portfolio_col] = str(uuid.uuid4())

        portfolio_uuid = portfolio_uuid_map[portfolio_col]

        # Extract allocations for this portfolio
        for _, row in df_batch.iterrows():
            asset_name = row["Asset_Description"]
            weight = row[portfolio_col]

            if pd.notna(weight) and weight > 0:
                metadata_rows.append(
                    {
                        "portfolio_uuid": portfolio_uuid,
                        "portfolio_name": portfolio_col,
                        "asset_name": asset_name,
                        "portfolio_weight": weight / 100.0,  # Convert to decimal
                    }
                )

    return pd.DataFrame(metadata_rows), portfolio_uuid_map


def extract_batch_metrics(all_tables, batch_file, portfolio_uuid_map):
    """
    Extract performance metrics from a batch results file.

    Args:
        all_tables: Parsed tables from batch results
        batch_file: Path to batch allocations CSV
        portfolio_uuid_map: UUID mapping for portfolios

    Returns:
        DataFrame with metrics rows
    """
    # Get portfolio column names from batch file
    df_batch = pd.read_csv(batch_file)
    batch_portfolio_cols = [
        col
        for col in df_batch.columns
        if col.startswith("Grid_")
        or col.startswith("Portfolio_")
        or col.startswith("TreasuryGrid_")
    ]

    metrics_rows = []

    # Define target tables
    target_tables = [
        "Portfolio Performance (Jan 2003 - Nov 2025)",
        "Portfolio Performance (Jan 1998 - Dec 2025)",  # Alternative date range
        "Risk and Return Metrics (Jan 2003 - Nov 2025)",
        "Risk and Return Metrics (Jan 1998 - Dec 2025)",  # Alternative date range
    ]

    for table_name in target_tables:
        # Try to find the table (may have slightly different names)
        matching_tables = [t for t in all_tables.keys() if table_name[:30] in t]

        if not matching_tables:
            continue

        actual_table_name = matching_tables[0]
        df_table = all_tables[actual_table_name]

        metric_col = df_table.columns[0]

        # Map Portfolio Visualizer column names to our Grid names
        pv_to_grid_mapping = {}
        for i, grid_name in enumerate(batch_portfolio_cols):
            if i == 0:
                pv_to_grid_mapping["Sample Portfolio"] = grid_name
            else:
                pv_to_grid_mapping[f"Portfolio {i+1}"] = grid_name

        # Extract metrics for each portfolio column
        for pv_col in df_table.columns[1:]:
            # Map PV column name to Grid name
            grid_name = None
            if pv_col in pv_to_grid_mapping:
                grid_name = pv_to_grid_mapping[pv_col]
            elif "sample" in pv_col.lower():
                grid_name = pv_to_grid_mapping.get("Sample Portfolio")
            elif "portfolio 2" in pv_col.lower():
                grid_name = pv_to_grid_mapping.get("Portfolio 2")
            elif "portfolio 3" in pv_col.lower():
                grid_name = pv_to_grid_mapping.get("Portfolio 3")

            if not grid_name or grid_name not in portfolio_uuid_map:
                continue

            portfolio_uuid = portfolio_uuid_map[grid_name]

            # Extract metrics
            for _, row in df_table.iterrows():
                metric_name = row[metric_col]
                metric_value = row[pv_col]

                if pd.notna(metric_value) and isinstance(metric_value, (int, float)):
                    metrics_rows.append(
                        {
                            "portfolio_uuid": portfolio_uuid,
                            "portfolio_name": grid_name,
                            "metric_name": str(metric_name),
                            "metric_value": float(metric_value),
                            "table_source": actual_table_name,
                        }
                    )

    return pd.DataFrame(metrics_rows)


def consolidate_all_batches(manifest_file="data/batch_files/batch_manifest.csv"):
    """
    Consolidate all batch results into unified tables.

    Args:
        manifest_file: Path to batch manifest CSV

    Returns:
        Tuple of (metadata_df, metrics_df, uuid_map)
    """
    print("=" * 80)
    print("CONSOLIDATING BATCH RESULTS")
    print("=" * 80)

    # Load manifest
    df_manifest = pd.read_csv(manifest_file)
    print(f"\nFound {len(df_manifest)} batches to consolidate")

    all_metadata = []
    all_metrics = []
    portfolio_uuid_map = {}

    # Process each batch
    for _, row in df_manifest.iterrows():
        batch_num = row["batch_num"]
        results_file = row["results_file"]

        # Find corresponding batch file
        batch_file = glob.glob(f"data/batch_files/batch_{batch_num:03d}_*.csv")[0]

        print(f"\nProcessing Batch {batch_num}...")
        print(f"  Results: {results_file}")
        print(f"  Allocations: {batch_file}")

        # Parse results
        all_tables = parse_all_tables(results_file)

        # Generate metadata
        batch_metadata, portfolio_uuid_map = generate_batch_metadata(
            results_file, batch_file, portfolio_uuid_map
        )
        all_metadata.append(batch_metadata)

        # Extract metrics
        batch_metrics = extract_batch_metrics(
            all_tables, batch_file, portfolio_uuid_map
        )
        all_metrics.append(batch_metrics)

        print(f"  ✓ Extracted {len(batch_metadata)} metadata rows")
        print(f"  ✓ Extracted {len(batch_metrics)} metric rows")

    # Combine all batches
    df_metadata = pd.concat(all_metadata, ignore_index=True)
    df_metrics = pd.concat(all_metrics, ignore_index=True)

    print("\n" + "=" * 80)
    print("CONSOLIDATION COMPLETE")
    print("=" * 80)
    print(f"Total portfolios: {len(portfolio_uuid_map)}")
    print(f"Total metadata rows: {len(df_metadata)}")
    print(f"Total metric rows: {len(df_metrics)}")

    return df_metadata, df_metrics, portfolio_uuid_map


def save_consolidated_results(df_metadata, df_metrics, uuid_map):
    """Save consolidated results to CSV files."""
    output_dir = "data/generated_tables"
    os.makedirs(output_dir, exist_ok=True)

    # Save metadata
    metadata_file = os.path.join(output_dir, "portfolio_metadata.csv")
    df_metadata.to_csv(metadata_file, index=False)
    print(f"\n✓ Saved metadata: {metadata_file}")
    print(f"  Rows: {len(df_metadata)}")

    # Save metrics
    metrics_file = os.path.join(output_dir, "portfolio_performance_metrics.csv")
    df_metrics.to_csv(metrics_file, index=False)
    print(f"\n✓ Saved metrics: {metrics_file}")
    print(f"  Rows: {len(df_metrics)}")

    # Save UUID mapping
    uuid_file = os.path.join(output_dir, "portfolio_uuid_mapping.csv")
    df_uuid_map = pd.DataFrame(
        [{"portfolio_name": k, "portfolio_uuid": v} for k, v in uuid_map.items()]
    )
    df_uuid_map.to_csv(uuid_file, index=False)
    print(f"\n✓ Saved UUID mapping: {uuid_file}")
    print(f"  Rows: {len(df_uuid_map)}")

    # Display top portfolios by Sharpe Ratio
    df_sharpe = df_metrics[df_metrics["metric_name"] == "Sharpe Ratio"].copy()
    df_sharpe = df_sharpe.sort_values("metric_value", ascending=False)

    print("\n" + "=" * 80)
    print("TOP 10 PORTFOLIOS BY SHARPE RATIO")
    print("=" * 80)
    for i, (_, row) in enumerate(df_sharpe.head(10).iterrows(), 1):
        print(f"{i:2d}. {row['portfolio_name']:15s}: {row['metric_value']:.6f}")

    print("\n" + "=" * 80)


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Consolidate batch backtest results")
    parser.add_argument(
        "--manifest",
        type=str,
        default="data/batch_files/batch_manifest.csv",
        help="Path to batch manifest file",
    )

    args = parser.parse_args()

    # Consolidate results
    df_metadata, df_metrics, uuid_map = consolidate_all_batches(args.manifest)

    # Save consolidated results
    save_consolidated_results(df_metadata, df_metrics, uuid_map)

    print("\n✓ All done! Results ready for optimization analysis.")
