#!/usr/bin/env python3
"""
Optimized Batch Portfolio Backtesting Script

Uses a single persistent browser session to process all batches without
re-authentication. Runs in headless mode for efficiency.
"""

import pandas as pd
import os
import sys
import time
import argparse
from pathlib import Path
from datetime import datetime
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from dotenv import load_dotenv

# Load environment
load_dotenv()

# Import the backtest functions
from portfolio_backtest import (
    select_dropdown_value,
    set_asset_class,
    enter_portfolio_allocation,
    validate_portfolio_weights,
    download_excel_results
)


def initialize_persistent_driver(headless=True):
    """Initialize a persistent Chrome WebDriver with authentication."""
    print("="*80)
    print("INITIALIZING PERSISTENT BROWSER SESSION")
    print("="*80)

    options = webdriver.ChromeOptions()

    if headless:
        options.add_argument('--headless=new')  # Use new headless mode
        options.add_argument('--disable-gpu')
        print("✓ Running in headless mode")

    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-blink-features=AutomationControlled")

    # Configure download preferences
    project_dir = os.path.dirname(os.path.abspath(__file__))
    download_dir = os.path.join(project_dir, "downloads")
    os.makedirs(download_dir, exist_ok=True)

    prefs = {
        "download.default_directory": download_dir,
        "download.prompt_for_download": False,
        "download.directory_upgrade": True,
        "safebrowsing.enabled": True,
    }
    options.add_experimental_option("prefs", prefs)

    # Create driver
    driver = webdriver.Chrome(
        service=Service(ChromeDriverManager().install()),
        options=options
    )

    print("✓ Chrome WebDriver initialized")

    # Login once
    print("\n=== Authenticating to Portfolio Visualizer ===")
    username = os.getenv("LOGIN_USERNAME")
    password = os.getenv("LOGIN_PWD")

    if not username or not password:
        raise Exception("Login credentials not found in .env file")

    driver.get("https://www.portfoliovisualizer.com/login")
    print("Waiting for login page to load...")
    time.sleep(1)  # Reduced from 3s - WebDriverWait handles the rest

    # Login
    try:
        print("Looking for username field...")
        # Try multiple selectors for email field
        username_field = None
        try:
            username_field = WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.ID, "email"))
            )
        except:
            try:
                username_field = driver.find_element(By.NAME, "email")
            except:
                try:
                    username_field = driver.find_element(By.XPATH, "//input[@type='email']")
                except:
                    username_field = driver.find_element(By.XPATH, "//input[@placeholder='Email address']")

        print("Found username field")
        username_field.clear()
        username_field.send_keys(username)
        print(f"Entered username: {username}")

        print("Looking for password field...")
        # Try multiple selectors for password field
        password_field = None
        try:
            password_field = driver.find_element(By.ID, "password")
        except:
            try:
                password_field = driver.find_element(By.NAME, "password")
            except:
                try:
                    password_field = driver.find_element(By.XPATH, "//input[@type='password']")
                except:
                    password_field = driver.find_element(By.XPATH, "//input[@placeholder='Password']")

        print("Found password field")
        password_field.clear()
        password_field.send_keys(password)
        print("Entered password")

        print("Looking for submit button...")
        # Try multiple selectors for submit button
        submit_button = None
        try:
            submit_button = driver.find_element(By.XPATH, "//button[@type='submit']")
        except:
            try:
                submit_button = driver.find_element(By.XPATH, "//button[contains(text(), 'Login')]")
            except:
                submit_button = driver.find_element(By.XPATH, "//input[@type='submit']")

        print("Found submit button - clicking...")
        submit_button.click()

        # Wait for login success
        print("Waiting for login to complete...")
        WebDriverWait(driver, 20).until(
            EC.presence_of_element_located((By.ID, "accountDropdown"))
        )
        print("✓ Authentication successful\n")

    except Exception as e:
        print(f"✗ Authentication failed: {e}")
        print(f"Current URL: {driver.current_url}")
        print("Taking screenshot for debugging...")
        try:
            driver.save_screenshot(os.path.join(project_dir, "downloads", "login_failure.png"))
            print("Screenshot saved to downloads/login_failure.png")
        except:
            pass
        driver.quit()
        raise

    return driver


def run_batch_with_persistent_session(driver, batch_file, batch_num, project_dir):
    """Run a single batch using existing authenticated driver."""

    print(f"{'='*80}")
    print(f"PROCESSING BATCH {batch_num}")
    print(f"{'='*80}")

    try:
        # Navigate to backtest page
        driver.get("https://www.portfoliovisualizer.com/backtest-asset-class-allocation")
        time.sleep(0.5)  # Reduced from 2s - WebDriverWait handles the rest

        # Configure start year (1998)
        modal_button = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((
                By.CSS_SELECTOR,
                "#overview > div:nth-child(1) > div > div > div:nth-child(1) > table > tfoot > tr > td > button.btn.btn-outline-primary.me-3"
            ))
        )
        driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", modal_button)
        time.sleep(0.2)  # Reduced from 0.5s
        driver.execute_script("arguments[0].click();", modal_button)
        time.sleep(0.3)  # Reduced from 1s

        # Click Settings tab
        WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "#custom-data-body"))
        )
        settings_tab = driver.find_element(By.ID, "inputSettings_btn")
        driver.execute_script("arguments[0].click();", settings_tab)
        time.sleep(0.2)  # Reduced from 0.5s

        # Set start year
        select_dropdown_value(driver, "#startYear", "1998", by_value=True)
        time.sleep(0.2)  # Reduced from 0.5s

        # Go back to Portfolio Assets tab
        assets_tab = driver.find_element(By.ID, "inputAssets_btn")
        driver.execute_script("arguments[0].click();", assets_tab)
        time.sleep(0.2)  # Reduced from 0.5s

        # Configure benchmark
        select_dropdown_value(driver, "#benchmark", "Vanguard 500 Index Investor (VFINX)", by_value=False)

        # Add more rows
        try:
            more_button = WebDriverWait(driver, 5).until(
                EC.element_to_be_clickable((
                    By.XPATH,
                    "//a[contains(@onclick, 'addAssetRows') and contains(text(), 'More')]"
                ))
            )
            driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", more_button)
            time.sleep(0.1)  # Reduced from 0.3s
            driver.execute_script("arguments[0].click();", more_button)
            time.sleep(0.2)  # Reduced from 0.5s
        except:
            pass

        # Load batch allocations
        df_batch = pd.read_csv(batch_file)
        portfolio_cols = [col for col in df_batch.columns
                         if col.startswith('Grid_') or col.startswith('Portfolio_') or col.startswith('TreasuryGrid_')][:3]

        # Asset mapping
        asset_description_to_option = {
            'US Equities - US Stock Market': 'TotalStockMarket',
            'Foreign Developed Equities - Intl Developed ex-US Market': 'IntlDeveloped',
            'Emerging Market Equities - Emerging Markets': 'EmergingMarket',
            'US Treasuries - Short Term Treasury': 'ShortTreasury',
            'US Treasuries - Intermediate Term Treasury': 'IntermediateTreasury',
            'US Treasuries - 10-year Treasury': 'TreasuryNotes',
            'US Treasuries - Long Term Treasury': 'LongTreasury',
            'TIPS - Inflation-Protected Bonds': 'TIPS',
            'Corporate Bonds - Investment Grade Corporate Bonds': 'CorpBond',
            'Real Estate/REITs - US REIT': 'REIT',
        }

        # Set asset classes
        asset_class_mappings = {}
        for idx, row in df_batch.iterrows():
            asset_num = idx + 1
            asset_desc = row['Asset_Description']
            if asset_desc in asset_description_to_option:
                asset_class_mappings[asset_num] = asset_description_to_option[asset_desc]

        for asset_num, option_value in asset_class_mappings.items():
            set_asset_class(driver, asset_num, option_value)
            time.sleep(0.05)  # Reduced from 0.2s - just enough for DOM update

        # Enter allocations
        portfolio_allocations = {}
        for idx, row in df_batch.iterrows():
            asset_num = idx + 1
            for portfolio_idx, col_name in enumerate(portfolio_cols, start=1):
                if col_name in row and pd.notna(row[col_name]):
                    allocation = float(row[col_name])
                    if allocation > 0:
                        portfolio_allocations[(asset_num, portfolio_idx)] = allocation

        for (asset_num, portfolio_num), allocation in portfolio_allocations.items():
            enter_portfolio_allocation(driver, asset_num, portfolio_num, allocation)
            time.sleep(0.05)  # Reduced from 0.15s - just enough for DOM update

        # Run backtest
        analyze_button = WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable((By.ID, "submitButton"))
        )
        driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", analyze_button)
        time.sleep(0.1)  # Reduced from 0.3s
        driver.execute_script("arguments[0].click();", analyze_button)

        # Wait for results
        WebDriverWait(driver, 60).until(
            EC.presence_of_element_located((By.CLASS_NAME, "table"))
        )
        print("✓ Backtest completed")

        # Download results
        download_dir = os.path.join(project_dir, "downloads")
        output_alias = f"batch_{batch_num:03d}"
        excel_file = download_excel_results(driver, download_dir, f"portfolio_backtest_results_{output_alias}.xlsx")

        if excel_file:
            # Move to data/source_tables
            excel_output_dir = os.path.join(project_dir, "data", "source_tables")
            os.makedirs(excel_output_dir, exist_ok=True)

            filename = os.path.basename(excel_file)
            final_path = os.path.join(excel_output_dir, filename)

            # Handle existing files
            if os.path.exists(final_path):
                base_name, ext = os.path.splitext(filename)
                counter = 1
                while os.path.exists(final_path):
                    final_path = os.path.join(excel_output_dir, f"{base_name}_{counter}{ext}")
                    counter += 1

            import shutil
            shutil.move(excel_file, final_path)
            print(f"✓ Results saved: {final_path}\n")
            return final_path

        return None

    except Exception as e:
        print(f"✗ Batch {batch_num} failed: {e}\n")
        import traceback
        traceback.print_exc()
        return None


def main():
    parser = argparse.ArgumentParser(description='Optimized batch backtesting with persistent session')
    parser.add_argument('--grid-file', type=str, default='data/source_tables/portfolio_allocations_grid.csv')
    parser.add_argument('--start-batch', type=int, default=1)
    parser.add_argument('--end-batch', type=int, default=None)
    parser.add_argument('--wait-time', type=int, default=0, help='Seconds between batches (default: 0 for max speed)')
    parser.add_argument('--headless', action='store_true', default=False, help='Run in headless mode')
    parser.add_argument('--no-headless', dest='headless', action='store_false', help='Disable headless mode')
    parser.add_argument('--manifest-file', type=str, default='data/batch_files/batch_manifest.csv',
                       help='Path to manifest file (default: data/batch_files/batch_manifest.csv)')

    args = parser.parse_args()

    project_dir = os.path.dirname(os.path.abspath(__file__))

    # Split grid into batches
    df_grid = pd.read_csv(args.grid_file)
    portfolio_cols = [col for col in df_grid.columns
                     if col.startswith('Grid_') or col.startswith('Portfolio_') or col.startswith('TreasuryGrid_')]
    num_portfolios = len(portfolio_cols)
    num_batches = (num_portfolios + 2) // 3  # 3 per batch

    print(f"Total portfolios: {num_portfolios}")
    print(f"Total batches: {num_batches}")

    # Determine batch range
    start_idx = args.start_batch - 1
    end_idx = args.end_batch if args.end_batch else num_batches

    # Initialize persistent browser session
    driver = initialize_persistent_driver(headless=args.headless)

    results_files = []
    failed_batches = []

    try:
        # Process each batch
        for batch_idx in range(start_idx, end_idx):
            batch_num = batch_idx + 1
            start_col = batch_idx * 3
            end_col = min(start_col + 3, num_portfolios)
            batch_cols = portfolio_cols[start_col:end_col]

            # Create batch file
            batch_dir = os.path.join(project_dir, 'data', 'batch_files')
            os.makedirs(batch_dir, exist_ok=True)
            batch_file = os.path.join(batch_dir, f'batch_{batch_num:03d}_{batch_cols[0]}_to_{batch_cols[-1]}.csv')

            batch_df = df_grid[['Asset_Number', 'Asset_Description'] + batch_cols].copy()
            batch_df.to_csv(batch_file, index=False)

            # Run batch
            result_file = run_batch_with_persistent_session(driver, batch_file, batch_num, project_dir)

            if result_file:
                results_files.append({
                    'batch_num': batch_num,
                    'portfolios': batch_cols,
                    'results_file': result_file
                })
            else:
                failed_batches.append(batch_num)

            # Wait between batches
            if args.wait_time > 0 and batch_idx < end_idx - 1:
                print(f"Waiting {args.wait_time}s before next batch...\n")
                time.sleep(args.wait_time)

    finally:
        # Close browser
        print("\n" + "="*80)
        print("CLOSING BROWSER SESSION")
        print("="*80)
        driver.quit()
        print("✓ Browser closed")

    # Save manifest
    print("\n" + "="*80)
    print("BATCH PROCESSING COMPLETE")
    print("="*80)
    print(f"Successful: {len(results_files)}/{end_idx - start_idx}")
    print(f"Failed: {len(failed_batches)}")

    if failed_batches:
        print(f"\nFailed batches: {failed_batches}")

    # Save manifest
    manifest_file = args.manifest_file
    df_manifest = pd.DataFrame(results_files)
    if not df_manifest.empty:
        # Append to existing manifest if it exists
        if os.path.exists(manifest_file):
            df_existing = pd.read_csv(manifest_file)
            df_manifest = pd.concat([df_existing, df_manifest], ignore_index=True)
            df_manifest = df_manifest.drop_duplicates(subset=['batch_num'], keep='last')

        df_manifest.to_csv(manifest_file, index=False)
        print(f"\n✓ Manifest saved: {manifest_file}")

    print("\n" + "="*80)
    print("NEXT STEPS:")
    print(f"  python consolidate_batch_results.py --manifest {manifest_file}")
    print("="*80)


if __name__ == "__main__":
    main()
