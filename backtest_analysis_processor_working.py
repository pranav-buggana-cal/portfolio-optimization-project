#!/usr/bin/env python
# coding: utf-8

# # Portfolio Backtest Results Analysis
# 
# This notebook analyzes and interprets the results from the portfolio backtest.
# 
# **Objective**: Compare portfolio performance across different allocations, focusing on:
# - Performance metrics (CAGR, Sharpe Ratio, Max Drawdown, etc.)
# - Risk-adjusted returns
# - Comparison against VFINX benchmark
# - Portfolio allocation impact on performance
# a

# In[32]:


# Import required libraries
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
from pathlib import Path
import warnings
warnings.filterwarnings('ignore')

# Set plotting style
plt.style.use('seaborn-v0_8-darkgrid')
sns.set_palette("husl")

# Set display options
pd.set_option('display.max_columns', None)
pd.set_option('display.width', None)
pd.set_option('display.max_colwidth', None)

print("Libraries imported successfully")


# ## 1. Load and Explore Backtest Results
# 

# In[33]:


# ============================================================================
# EXCEL TABLE PARSING FUNCTIONS
# ============================================================================

def identify_table_boundaries(df):
    """
    Identify boundaries of all tables in the Excel sheet.
    
    Tables are separated by empty rows. This function identifies the start
    and end row indices for each table.
    
    Args:
        df: DataFrame loaded from Excel with header=None
        
    Returns:
        List of tuples (start_row, end_row, table_name) for each table
    """
    tables = []
    current_table_start = None
    current_table_name = None
    
    for idx in range(len(df)):
        row = df.iloc[idx]
        # Check if row is completely empty (all NaN)
        is_empty = row.isna().all()
        
        if not is_empty:
            if current_table_start is None:
                # Start of a new table
                current_table_start = idx
                # Try to get table name from first non-NaN value
                first_val = row.dropna().iloc[0] if not row.dropna().empty else f"Table_{len(tables)+1}"
                current_table_name = str(first_val)
        else:
            if current_table_start is not None:
                # End of current table
                tables.append((current_table_start, idx - 1, current_table_name))
                current_table_start = None
                current_table_name = None
    
    # Don't forget the last table if file doesn't end with empty row
    if current_table_start is not None:
        tables.append((current_table_start, len(df) - 1, current_table_name))
    
    return tables


def detect_table_structure(df_subset):
    """
    Detect the structure of a table subset (header row, data rows).
    
    Args:
        df_subset: DataFrame slice containing a single table
        
    Returns:
        Dictionary with 'header_row', 'data_start_row', 'num_columns'
    """
    structure = {
        'header_row': None,
        'data_start_row': None,
        'num_columns': 0,
        'table_type': 'unknown'
    }
    
    # Look for a row that looks like a header
    # Headers typically have multiple non-NaN values and text content
    for idx in range(len(df_subset)):
        row = df_subset.iloc[idx]
        non_nan_count = row.notna().sum()
        
        if non_nan_count >= 2:  # Potential header with at least 2 columns
            # Check if this looks like a header row
            # Headers often contain strings like "Metric", "Name", "Portfolio", etc.
            row_values = [str(v).lower() for v in row.dropna() if pd.notna(v)]
            header_keywords = ['metric', 'name', 'portfolio', 'asset', 'year', 'allocation', 'month']
            
            if any(keyword in ' '.join(row_values) for keyword in header_keywords):
                structure['header_row'] = idx
                structure['data_start_row'] = idx + 1
                structure['num_columns'] = non_nan_count
                break
    
    # If no explicit header found, assume first row is header
    if structure['header_row'] is None and len(df_subset) > 0:
        first_row = df_subset.iloc[0]
        structure['header_row'] = 0
        structure['data_start_row'] = 1
        structure['num_columns'] = first_row.notna().sum()
    
    # Detect table type based on content
    if structure['header_row'] is not None:
        header_text = ' '.join([str(v).lower() for v in df_subset.iloc[structure['header_row']].dropna()])
        
        if 'allocation' in header_text:
            structure['table_type'] = 'allocation'
        elif 'metric' in header_text or 'performance' in header_text:
            structure['table_type'] = 'metrics'
        elif 'return' in header_text or 'year' in header_text:
            structure['table_type'] = 'returns'
        elif 'correlation' in header_text:
            structure['table_type'] = 'correlation'
    
    return structure


def parse_key_value_table(df_subset, table_name):
    """
    Parse a simple key-value table (e.g., metadata like "Start Date", "End Date").
    
    Args:
        df_subset: DataFrame slice containing the table
        table_name: Name of the table
        
    Returns:
        DataFrame with cleaned key-value pairs
    """
    data_rows = []
    
    for idx in range(len(df_subset)):
        row = df_subset.iloc[idx]
        non_nan = row.dropna()
        
        if len(non_nan) >= 2:
            # Key-value pair
            key = non_nan.iloc[0]
            value = non_nan.iloc[1]
            data_rows.append({'Key': key, 'Value': value})
        elif len(non_nan) == 1:
            # Single value (could be section header)
            data_rows.append({'Key': non_nan.iloc[0], 'Value': None})
    
    if data_rows:
        return pd.DataFrame(data_rows)
    return pd.DataFrame()


def parse_tabular_data(df_subset, structure):
    """
    Parse a structured table with headers and data rows.
    
    Args:
        df_subset: DataFrame slice containing the table
        structure: Structure dictionary from detect_table_structure
        
    Returns:
        DataFrame with cleaned tabular data
    """
    if structure['header_row'] is None:
        return pd.DataFrame()
    
    # Extract header
    header_row = df_subset.iloc[structure['header_row']]
    columns = []
    
    for i, val in enumerate(header_row):
        if pd.notna(val):
            columns.append(str(val))
        else:
            # For NaN columns, use generic name
            columns.append(f'Column_{i}')
    
    # Extract data rows
    data_start = structure['data_start_row']
    data_rows = []
    
    for idx in range(data_start, len(df_subset)):
        row = df_subset.iloc[idx]
        # Only include rows with at least one non-NaN value
        if row.notna().any():
            # Take only as many values as we have columns
            row_data = row.iloc[:len(columns)].tolist()
            data_rows.append(row_data)
    
    if data_rows:
        df_result = pd.DataFrame(data_rows, columns=columns)
        # Remove columns that are entirely NaN
        df_result = df_result.dropna(axis=1, how='all')
        # Remove rows that are entirely NaN
        df_result = df_result.dropna(axis=0, how='all')
        return df_result
    
    return pd.DataFrame()


def parse_all_tables(file_path, sheet_name='Asset Allocation Report'):
    """
    Parse all tables from an Excel file and return them as a dictionary of DataFrames.
    
    This is the main function that orchestrates the entire parsing process.
    
    Args:
        file_path: Path to the Excel file
        sheet_name: Name of the sheet to parse (default: 'Asset Allocation Report')
        
    Returns:
        Dictionary where keys are table names and values are parsed DataFrames
    """
    # Load the raw Excel data without headers
    df_raw = pd.read_excel(file_path, sheet_name=sheet_name, header=None)
    
    # Identify all table boundaries
    table_boundaries = identify_table_boundaries(df_raw)
    
    print(f"Found {len(table_boundaries)} tables in the Excel file")
    print("-" * 80)
    
    # Parse each table
    parsed_tables = {}
    
    for table_num, (start_row, end_row, raw_table_name) in enumerate(table_boundaries, 1):
        # Extract the table subset
        df_subset = df_raw.iloc[start_row:end_row+1].reset_index(drop=True)
        
        # Detect table structure
        structure = detect_table_structure(df_subset)
        
        # Clean up table name
        table_name = raw_table_name.strip()
        
        # Avoid duplicate keys
        if table_name in parsed_tables:
            table_name = f"{table_name}_{table_num}"
        
        print(f"\nTable {table_num}: {table_name}")
        print(f"  Rows: {start_row} to {end_row} ({end_row - start_row + 1} rows)")
        print(f"  Type: {structure['table_type']}")
        print(f"  Columns: {structure['num_columns']}")
        
        # Parse based on structure
        if structure['num_columns'] <= 2 and structure['table_type'] == 'unknown':
            # Likely a key-value table
            parsed_df = parse_key_value_table(df_subset, table_name)
            if not parsed_df.empty:
                parsed_tables[table_name] = parsed_df
                print(f"  Parsed as: Key-Value table ({len(parsed_df)} entries)")
        else:
            # Structured tabular data
            parsed_df = parse_tabular_data(df_subset, structure)
            if not parsed_df.empty:
                parsed_tables[table_name] = parsed_df
                print(f"  Parsed as: Tabular data ({len(parsed_df)} rows x {len(parsed_df.columns)} cols)")
    
    print("\n" + "=" * 80)
    print(f"Successfully parsed {len(parsed_tables)} tables")
    print("=" * 80)
    
    return parsed_tables


def display_parsed_tables(tables_dict, max_rows=10):
    """
    Display a summary of all parsed tables.
    
    Args:
        tables_dict: Dictionary of parsed tables from parse_all_tables
        max_rows: Maximum number of rows to display per table
    """
    print("\n" + "=" * 80)
    print("PARSED TABLES SUMMARY")
    print("=" * 80)
    
    for table_name, df in tables_dict.items():
        print(f"\n{'='*80}")
        print(f"TABLE: {table_name}")
        print(f"{'='*80}")
        print(f"Shape: {df.shape[0]} rows × {df.shape[1]} columns")
        print(f"Columns: {list(df.columns)}")
        print(f"\nFirst {min(max_rows, len(df))} rows:")
        print(df.head(max_rows).to_string(index=False))
        
        if len(df) > max_rows:
            print(f"\n... ({len(df) - max_rows} more rows)")
    
    print("\n" + "=" * 80)


# ============================================================================
# LOAD AND PARSE THE EXCEL FILE
# ============================================================================

def main(results_file=None, allocations_file=None):
    """
    Main processing function for backtest analysis.

    Args:
        results_file: Path to Excel file with backtest results
        allocations_file: Path to CSV file with portfolio allocations

    Returns:
        Tuple of (metadata_df, metrics_df, uuid_map)
    """
    # Use provided file paths or defaults
    if results_file is None:
        results_file = 'data/source_tables/portfolio_backtest_results.xlsx'
    if allocations_file is None:
        allocations_file = 'data/source_tables/portfolio_allocations.csv'

    print(f"Processing backtest results from: {results_file}")
    print(f"Using allocations from: {allocations_file}")
    print("="*80)

    print("\nStarting Excel table parsing...")
    print("=" * 80)

    # Parse all tables
    all_tables = parse_all_tables(results_file)

    # Display summary of parsed tables (commented out to reduce output)
    # display_parsed_tables(all_tables, max_rows=15)

    # Load portfolio allocations from CSV
    try:
        df_allocations = pd.read_csv(allocations_file)
        print("✓ Loaded portfolio allocations")
        print(f"\nPortfolio Allocations:")
        print(df_allocations.to_string(index=False))

        # Detect portfolio columns (Grid_* or Portfolio_*)
        portfolio_cols = [col for col in df_allocations.columns
                         if col.startswith('Grid_') or col.startswith('Portfolio_')]

        # Create a summary of allocations by portfolio
        portfolio_summary = {}
        for col in portfolio_cols[:min(10, len(portfolio_cols))]:  # Show first 10 max
            portfolio_summary[col] = dict(zip(
                df_allocations['Asset_Description'],
                df_allocations[col]
            ))

        print("\n=== Portfolio Allocation Summary ===")
        for portfolio, allocations in portfolio_summary.items():
            print(f"\n{portfolio}:")
            total = 0
            for asset, weight in allocations.items():
                if pd.notna(weight) and weight > 0:
                    print(f"  {asset}: {weight}%")
                    total += weight
            print(f"  Total: {total}%")

    except FileNotFoundError:
        print(f"Warning: Could not find {allocations_file}")
        df_allocations = None
        portfolio_summary = {}


# urrent 

# ## 3. Helper Functions for Analysis
# 
# Additional utility functions to work with the parsed tables:

# ## 4. Export Parsed Tables
# 
# Save all parsed tables to a new Excel file for easy access:

# In[ ]:


import uuid
from datetime import datetime

def generate_portfolio_metadata(allocations_csv_path, portfolio_names=None):
    """
    Generate portfolio metadata table from allocations CSV.
    
    Args:
        allocations_csv_path: Path to portfolio_allocations.csv
        portfolio_names: List of portfolio column names (e.g., ['Portfolio_1', 'Portfolio_2'])
                        If None, will auto-detect all Portfolio_* columns
    
    Returns:
        DataFrame with columns: portfolio_uuid | asset_name | portfolio_weight
        Dictionary mapping portfolio names to UUIDs
    """
    # Load allocations
    df_alloc = pd.read_csv(allocations_csv_path)
    
    # Auto-detect portfolio columns if not provided
    if portfolio_names is None:
        portfolio_names = [col for col in df_alloc.columns if col.startswith('Portfolio_')]
    
    metadata_rows = []
    portfolio_uuid_map = {}  # Map portfolio names to UUIDs
    
    for portfolio_col in portfolio_names:
        # Generate UUID for this portfolio
        portfolio_uuid = str(uuid.uuid4())
        portfolio_uuid_map[portfolio_col] = portfolio_uuid
        
        # Extract weights for this portfolio
        for idx, row in df_alloc.iterrows():
            asset_name = row['Asset_Description']
            weight = row[portfolio_col]
            
            # Only include assets with non-zero weights
            if pd.notna(weight) and weight > 0:
                metadata_rows.append({
                    'portfolio_uuid': portfolio_uuid,
                    'portfolio_name': portfolio_col,  # Keep for reference
                    'asset_name': asset_name,
                    'portfolio_weight': weight / 100.0  # Convert to decimal
                })
    
    df_metadata = pd.DataFrame(metadata_rows)
    
    print(f"Generated metadata for {len(portfolio_names)} portfolios")
    print(f"Total rows: {len(df_metadata)}")
    print(f"\nPortfolio UUID mapping:")
    for name, uid in portfolio_uuid_map.items():
        print(f"  {name}: {uid}")
    
    return df_metadata, portfolio_uuid_map


def extract_performance_metrics_long(all_tables, portfolio_uuid_map):
    """
    Extract performance metrics and convert to long format.
    
    Args:
        all_tables: Dictionary of parsed tables from parse_all_tables()
        portfolio_uuid_map: Dictionary mapping portfolio names to UUIDs
        
    Returns:
        DataFrame with columns: portfolio_uuid | metric_name | metric_value
    """
    metrics_rows = []
    
    # Define which tables to extract metrics from
    target_tables = [
        'Portfolio Performance (Jan 2003 - Nov 2025)',
        'Risk and Return Metrics (Jan 2003 - Nov 2025)'
    ]
    
    for table_name in target_tables:
        if table_name not in all_tables:
            print(f"Warning: Table '{table_name}' not found in parsed tables")
            continue
        
        df_table = all_tables[table_name]
        
        # The first column should be the metric name
        metric_col = df_table.columns[0]
        
        # Iterate through each portfolio column
        for col in df_table.columns[1:]:
            # Map column name to UUID
            # Try to match 'Sample Portfolio' -> 'Portfolio_1', 'Portfolio 2' -> 'Portfolio_2', etc.
            portfolio_key = None
            
            if 'sample' in col.lower() or col == 'Sample Portfolio':
                portfolio_key = 'Portfolio_1'
            elif 'portfolio 2' in col.lower() or col == 'Portfolio 2':
                portfolio_key = 'Portfolio_2'
            elif 'portfolio 3' in col.lower() or col == 'Portfolio 3':
                portfolio_key = 'Portfolio_3'
            
            if portfolio_key not in portfolio_uuid_map:
                print(f"Warning: Could not map column '{col}' to a portfolio UUID")
                continue
            
            portfolio_uuid = portfolio_uuid_map[portfolio_key]
            
            # Extract metrics for this portfolio
            for idx, row in df_table.iterrows():
                metric_name = row[metric_col]
                metric_value = row[col]
                
                # Only include valid numeric metrics
                if pd.notna(metric_value) and isinstance(metric_value, (int, float)):
                    metrics_rows.append({
                        'portfolio_uuid': portfolio_uuid,
                        'portfolio_name': portfolio_key,  # Keep for reference
                        'metric_name': str(metric_name),
                        'metric_value': float(metric_value),
                        'table_source': table_name
                    })
    
    df_metrics = pd.DataFrame(metrics_rows)
    
    print(f"\nExtracted {len(df_metrics)} metric values")
    print(f"Unique metrics: {df_metrics['metric_name'].nunique()}")
    print(f"Portfolios: {df_metrics['portfolio_uuid'].nunique()}")
    
    return df_metrics


    # Generate metadata and metrics
    print("="*80)
    print("GENERATING PORTFOLIO METADATA AND METRICS")
    print("="*80)

    # Generate metadata
    df_portfolio_metadata, uuid_map = generate_portfolio_metadata(allocations_file)

    print("\n" + "="*80)
    print("Portfolio Metadata Sample:")
    print("="*80)
    print(df_portfolio_metadata.head(10))

    # Extract performance metrics in long format
    df_performance_metrics = extract_performance_metrics_long(all_tables, uuid_map)

    print("\n" + "="*80)
    print("Performance Metrics Sample:")
    print("="*80)
    print(df_performance_metrics.head(20))

    return df_portfolio_metadata, df_performance_metrics, uuid_map


# ## 5. Generate Portfolio Metadata and Performance Metrics
#
# Create structured tables for optimization:
# - Portfolio metadata table (portfolio_uuid | asset_name | portfolio_weight)
# - Long-format performance metrics (portfolio_uuid | metric_name | metric_value)

# NOTE: The code below is commented out as it's module-level code that would execute on import.
# These functions are meant to be called from consolidate_batch_results.py

# # In[ ]:
#
#
# # Extract Sharpe Ratio specifically (our optimization target)
# df_sharpe = df_performance_metrics[df_performance_metrics['metric_name'] == 'Sharpe Ratio'].copy()
#
# print("="*80)
# print("SHARPE RATIO BY PORTFOLIO")
# print("="*80)
# print(df_sharpe[['portfolio_name', 'portfolio_uuid', 'metric_value']].to_string(index=False))
#
# # Display all unique metrics available
# print("\n" + "="*80)
# print("ALL AVAILABLE METRICS")
# print("="*80)
# unique_metrics = df_performance_metrics['metric_name'].unique()
# print(f"Total metrics: {len(unique_metrics)}\n")
# for i, metric in enumerate(sorted(unique_metrics), 1):
#     print(f"{i:2d}. {metric}")
#
#
# # ## 6. Extract Key Metrics (Sharpe Ratio) for Optimization
#
# # In[ ]:
#
#
# # Save metadata and metrics to CSV files for use in optimization
# metadata_output = 'data/generated_tables/portfolio_metadata.csv'
# metrics_output = 'data/generated_tables/portfolio_performance_metrics.csv'
# uuid_mapping_output = 'data/generated_tables/portfolio_uuid_mapping.csv'
#
# # Save portfolio metadata
# df_portfolio_metadata.to_csv(metadata_output, index=False)
# print(f"✓ Saved portfolio metadata to: {metadata_output}")
# print(f"  Columns: {list(df_portfolio_metadata.columns)}")
# print(f"  Rows: {len(df_portfolio_metadata)}")
#
# # Save performance metrics
# df_performance_metrics.to_csv(metrics_output, index=False)
# print(f"\n✓ Saved performance metrics to: {metrics_output}")
# print(f"  Columns: {list(df_performance_metrics.columns)}")
# print(f"  Rows: {len(df_performance_metrics)}")
#
# # Also save UUID mapping for reference
# df_uuid_map = pd.DataFrame([
#     {'portfolio_name': k, 'portfolio_uuid': v}
#     for k, v in uuid_map.items()
# ])
# df_uuid_map.to_csv(uuid_mapping_output, index=False)
# print(f"\n✓ Saved UUID mapping to: {uuid_mapping_output}")
#
# print("\n" + "="*80)
# print("FILES READY FOR OPTIMIZATION")
# print("="*80)
# print(f"1. {metadata_output} - Portfolio allocations with UUIDs")
# print(f"2. {metrics_output} - Performance metrics in long format")
# print(f"3. {uuid_mapping_output} - UUID to portfolio name mapping")


# ## 7. Functions are ready to be imported by consolidate_batch_results.py
