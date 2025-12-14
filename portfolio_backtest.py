#!/usr/bin/env python3
"""
Portfolio Backtesting Automation Script

This script automates portfolio backtesting using Portfolio Visualizer
with Selenium.

Goal: Test portfolio allocations starting from 1998, removing Private Equity,
Hedge Funds, and Venture Capital, and reallocating those weights to REITs.
Compare against VFINX (Vanguard 500 Index Investor) benchmark.
"""

import pandas as pd
import time
import os
import shutil
import glob
from datetime import datetime
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import Select
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.keys import Keys
from webdriver_manager.chrome import ChromeDriverManager
from dotenv import load_dotenv
import warnings

warnings.filterwarnings("ignore")

# Load environment variables from .env file
load_dotenv()


# ============================================================================
# Helper Functions
# ============================================================================


def select_dropdown_value(
    driver, selector, value, by_value=True, wait_time=10, scroll=True
):
    """
    Select a value from a dropdown/select element. Handles various
    dropdown types and uses multiple fallback methods to ensure the
    selection works.

    Args:
        driver: Selenium WebDriver instance
        selector: CSS selector or ID of the dropdown element
            (e.g., "#startYear" or "#asset1")
        value: Value to select (can be the option value or visible text)
        by_value: If True, selects by option value; if False, selects
            by visible text
        wait_time: Maximum time to wait for element (default: 10 seconds)
        scroll: Whether to scroll element into view (default: True)

    Returns:
        bool: True if selection was successful, False otherwise
    """
    try:
        # Wait for element to be present
        element = WebDriverWait(driver, wait_time).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, selector))
        )

        # Scroll into view if requested
        if scroll:
            driver.execute_script(
                "arguments[0].scrollIntoView({block: 'center'});", element
            )
            time.sleep(0.5)

        # Try multiple approaches to select the value
        success = False

        # Approach 1: Try as Select dropdown using Selenium's Select class
        try:
            select = Select(element)
            if by_value:
                select.select_by_value(str(value))
            else:
                select.select_by_visible_text(str(value))
            print(
                f"Selected '{value}' in {selector} "
                "(using Select dropdown)"
            )
            success = True
        except Exception as e1:
            # Approach 2: Use JavaScript to set the value directly
            try:
                driver.execute_script(f"arguments[0].value = '{value}';", element)
                # Trigger change event to ensure the page recognizes
                # the change
                driver.execute_script(
                    "arguments[0].dispatchEvent(new Event('change', "
                    "{ bubbles: true }));",
                    element,
                )
                # Also try input event
                driver.execute_script(
                    "arguments[0].dispatchEvent(new Event('input', "
                    "{ bubbles: true }));",
                    element,
                )
                print(f"Selected '{value}' in {selector} (using JavaScript)")
                success = True
            except Exception as e2:
                # Approach 3: Try clicking and using keyboard navigation
                try:
                    element.click()
                    time.sleep(0.3)
                    # If it's a dropdown that opens, we might need to
                    # select the option. For now, try sending the value
                    # directly
                    element.send_keys(str(value))
                    element.send_keys(Keys.RETURN)
                    print(f"Selected '{value}' in {selector} " "(using click and keys)")
                    success = True
                except Exception as e3:
                    print(f"All approaches failed for {selector}")
                    print(f"  Select approach: {e1}")
                    print(f"  JavaScript approach: {e2}")
                    print(f"  Click/keys approach: {e3}")

        if success:
            time.sleep(0.5)  # Brief pause after selection
        return success

    except Exception as e:
        print(f"Error selecting '{value}' in {selector}: {e}")
        return False


def set_asset_class(driver, asset_num, option_value):
    """
    Set the asset class dropdown for a given asset.

    Args:
        driver: Selenium WebDriver instance
        asset_num: Asset number (1, 2, 3, etc.)
        option_value: Option value to select
            (e.g., 'TotalStockMarket', 'IntlDeveloped')

    Returns:
        bool: True if successful, False otherwise
    """
    asset_selector = f"#asset{asset_num}"
    try:
        success = select_dropdown_value(
            driver, asset_selector, option_value, by_value=True
        )
        if success:
            print(f"Set Asset {asset_num} class to {option_value}")
        return success
    except Exception as e:
        print(f"Error setting asset class for Asset {asset_num}: {e}")
        return False


def enter_portfolio_allocation(driver, asset_num, portfolio_num, allocation):
    """
    Enter a single portfolio allocation percentage.

    Args:
        driver: Selenium WebDriver instance
        asset_num: Asset number (1, 2, 3, etc.)
        portfolio_num: Portfolio number (1, 2, or 3)
        allocation: Allocation percentage as a number (e.g., 30 for 30%)

    Returns:
        bool: True if successful, False otherwise
    """
    field_id = f"allocation{asset_num}_{portfolio_num}"
    try:
        field = WebDriverWait(driver, 5).until(
            EC.presence_of_element_located((By.ID, field_id))
        )

        # Scroll into view
        driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", field)
        time.sleep(0.2)

        # Clear and set the value using JavaScript (more reliable)
        driver.execute_script(f"arguments[0].value = '{allocation}';", field)
        # Trigger input event to ensure the page recognizes the change
        driver.execute_script(
            "arguments[0].dispatchEvent(new Event('input', " "{ bubbles: true }));",
            field,
        )
        driver.execute_script(
            "arguments[0].dispatchEvent(new Event('change', " "{ bubbles: true }));",
            field,
        )

        print(f"Set Asset {asset_num}, Portfolio {portfolio_num} " f"to {allocation}%")
        return True
    except Exception as e:
        print(f"Error setting {field_id} to {allocation}%: {e}")
        return False


def validate_portfolio_weights(allocations_dict):
    """
    Validate that portfolio weights sum to 100% for each portfolio.

    Args:
        allocations_dict: Dictionary mapping (asset_num, portfolio_num)
            to allocation percentage

    Returns:
        dict: Validation results for each portfolio
    """
    portfolio_totals = {1: 0, 2: 0, 3: 0}

    for (asset_num, portfolio_num), allocation in allocations_dict.items():
        if portfolio_num in portfolio_totals:
            portfolio_totals[portfolio_num] += allocation

    validation_results = {}
    for portfolio_num, total in portfolio_totals.items():
        # Allow small floating point differences
        is_valid = abs(total - 100.0) < 0.01
        validation_results[portfolio_num] = {
            "total": total,
            "valid": is_valid,
        }
        if not is_valid:
            print(f"Warning: Portfolio {portfolio_num} totals {total}%, " "not 100%")
        else:
            print(
                f"Portfolio {portfolio_num} totals {total}% ✓"
            )

    return validation_results


def handle_login_from_modal(driver):
    """
    Handle login when the "Login Required" modal appears.
    Uses credentials from .env file.
    """
    try:
        # Get credentials from environment variables
        username = os.getenv("LOGIN_USERNAME")
        password = os.getenv("LOGIN_PWD")

        if not username or not password:
            print("Error: Login credentials not found in .env file")
            return False

        # Find and click the Login button in the modal
        try:
            login_modal_button = WebDriverWait(driver, 5).until(
                EC.element_to_be_clickable((By.ID, "confirmButton"))
            )
            print("Found Login button in modal - clicking...")

            try:
                login_modal_button.click()
            except Exception:
                driver.execute_script("arguments[0].click();", login_modal_button)
            time.sleep(2)

            # Now find and fill the login form
            # Find and fill username field
            username_field = None
            try:
                username_field = WebDriverWait(driver, 10).until(
                    EC.presence_of_element_located((By.ID, "email"))
                )
            except Exception:
                try:
                    username_field = driver.find_element(By.NAME, "email")
                except Exception:
                    username_field = driver.find_element(
                        By.XPATH, "//input[@type='email']"
                    )

            if username_field:
                username_field.clear()
                username_field.send_keys(username)
                print(f"Entered username: {username}")
                time.sleep(0.5)
            else:
                print("Warning: Could not find username field")
                return False

            # Find and fill password field
            password_field = None
            try:
                password_field = driver.find_element(By.ID, "password")
            except Exception:
                try:
                    password_field = driver.find_element(By.NAME, "password")
                except Exception:
                    password_field = driver.find_element(
                        By.XPATH, "//input[@type='password']"
                    )

            if password_field:
                password_field.clear()
                password_field.send_keys(password)
                print("Entered password")
                time.sleep(0.5)
            else:
                print("Warning: Could not find password field")
                return False

            # Find and click submit button
            submit_button = None
            try:
                submit_button = driver.find_element(
                    By.XPATH, "//button[@type='submit']"
                )
            except Exception:
                try:
                    submit_button = driver.find_element(
                        By.XPATH, "//input[@type='submit']"
                    )
                except Exception:
                    submit_button = driver.find_element(
                        By.XPATH,
                        "//button[contains(text(), 'Login') or "
                        "contains(text(), 'Sign In')]",
                    )

            if submit_button:
                try:
                    submit_button.click()
                except Exception:
                    driver.execute_script(
                        "arguments[0].click();", submit_button
                    )
                print("Clicked login submit button")
                time.sleep(3)

                # Check if login was successful
                try:
                    WebDriverWait(driver, 10).until(
                        EC.presence_of_element_located(
                            (By.ID, "accountDropdown")
                        )
                    )
                    print("Login successful - account dropdown found")
                    return True
                except Exception:
                    print(
                        "Login may have failed - account dropdown not found "
                        "after login"
                    )
                    return False
            else:
                print("Warning: Could not find submit button")
                return False

        except Exception as e:
            print(f"Error handling login modal: {e}")
            return False

    except Exception as e:
        print(f"Error during login from modal: {e}")
        import traceback

        traceback.print_exc()
        return False


def download_excel_results(driver, download_dir, output_filename=None):
    """
    Click the Excel download button and save the file.
    Handles login modal if it appears.

    Args:
        driver: Selenium WebDriver instance
        download_dir: Directory where downloads are saved
        output_filename: Optional custom filename (with .xlsx extension)

    Returns:
        str: Path to downloaded file, or None if failed
    """
    try:
        # Find the Excel download link
        excel_link = WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable(
                (
                    By.XPATH,
                    "//a[@class='downloadLink' and contains(., 'Excel')]",
                )
            )
        )

        # Get list of files before download
        files_before = set(glob.glob(os.path.join(download_dir, "*")))

        # Scroll into view
        driver.execute_script(
            "arguments[0].scrollIntoView({block: 'center'});", excel_link
        )
        time.sleep(0.5)

        # Click the Excel download link
        try:
            excel_link.click()
            print("Clicked Excel download link")
        except Exception:
            # Try JavaScript click if regular click fails
            driver.execute_script("arguments[0].click();", excel_link)
            print("Clicked Excel download link (JavaScript)")

        time.sleep(1)  # Wait a moment for modal to appear if needed

        # Check if login modal appeared
        try:
            WebDriverWait(driver, 3).until(
                EC.presence_of_element_located(
                    (By.ID, "confirmDialogTitle")
                )
            )
            modal_text = driver.find_element(By.ID, "confirmText").text
            dialog_title = driver.find_element(
                By.ID, "confirmDialogTitle"
            ).text
            if (
                "Login Required" in dialog_title
                or "login" in modal_text.lower()
            ):
                print("Login Required modal appeared - handling login...")
                login_success = handle_login_from_modal(driver)

                if login_success:
                    # Wait a moment for page to update
                    time.sleep(2)
                    # Navigate back to results page if needed, or retry
                    # download. For now, try clicking the Excel link again
                    try:
                        excel_link = WebDriverWait(driver, 10).until(
                            EC.element_to_be_clickable(
                                (
                                    By.XPATH,
                                    "//a[@class='downloadLink' and "
                                    "contains(., 'Excel')]",
                                )
                            )
                        )
                        driver.execute_script(
                            "arguments[0].scrollIntoView({block: 'center'});",
                            excel_link,
                        )
                        time.sleep(0.5)
                        try:
                            excel_link.click()
                            print(
                                "Clicked Excel download link again after login"
                            )
                        except Exception:
                            driver.execute_script(
                                "arguments[0].click();", excel_link
                            )
                            print(
                                "Clicked Excel download link again after login "
                                "(JavaScript)"
                            )
                        time.sleep(1)
                    except Exception:
                        print("Warning: Could not find Excel link after login")
                else:
                    print("Login failed - cannot download")
                    return None
        except Exception:
            # No modal appeared, download should proceed
            pass

        # Wait for download to complete (check for new file)
        print("Waiting for download to complete...")
        max_wait = 30
        wait_time = 0
        downloaded_file = None

        while wait_time < max_wait:
            time.sleep(1)
            wait_time += 1
            files_after = set(glob.glob(os.path.join(download_dir, "*")))
            new_files = files_after - files_before

            # Look for .xlsx files
            for file_path in new_files:
                if file_path.endswith(".xlsx") or file_path.endswith(".xls"):
                    # Check if file is still being downloaded
                    # (Chrome adds .crdownload extension)
                    if not file_path.endswith(".crdownload"):
                        downloaded_file = file_path
                        break

            if downloaded_file:
                break

        if downloaded_file:
            print(f"Downloaded file: {downloaded_file}")

            # Rename file if custom filename provided
            if output_filename:
                if not output_filename.endswith(".xlsx"):
                    output_filename += ".xlsx"
                # Add timestamp to preserve historical results
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                # Extract base name and extension
                base_name = os.path.splitext(output_filename)[0]
                final_path = os.path.join(download_dir, f"{base_name}_{timestamp}.xlsx")
                # Don't remove existing files - preserve historical data
                shutil.move(downloaded_file, final_path)
                downloaded_file = final_path
                print(f"Renamed to: {final_path}")
            else:
                # Use timestamp-based filename
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                final_path = os.path.join(
                    download_dir,
                    f"backtest_results_{timestamp}.xlsx",
                )
                # Don't remove existing files - preserve historical data
                shutil.move(downloaded_file, final_path)
                downloaded_file = final_path
                print(f"Saved as: {final_path}")

            return downloaded_file
        else:
            print("Warning: Download file not found after waiting")
            return None

    except Exception as e:
        print(f"Error downloading Excel file: {e}")
        import traceback

        traceback.print_exc()
        return None


# ============================================================================
# Main Script
# ============================================================================


def main(allocations_file=None, output_alias=None):
    """Main execution function

    Args:
        allocations_file: Path to CSV file with portfolio allocations.
                         If None, uses default portfolio_allocations.csv
        output_alias: Alias for the output file (e.g., 'coarse_grid').
                     If None, uses timestamp-based naming

    Returns:
        Path to results file
    """

    # Get project directory
    project_dir = os.path.dirname(os.path.abspath(__file__))

    # Initialize Chrome driver
    print("Initializing Chrome WebDriver...")
    options = webdriver.ChromeOptions()
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")

    # Configure download preferences
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
        service=Service(ChromeDriverManager().install()), options=options
    )
    driver.maximize_window()
    print("Chrome WebDriver initialized successfully")

    try:
        # ========================================================================
        # Step 1: Login to Portfolio Visualizer
        # ========================================================================
        print("\n=== Step 1: Logging in ===")
        try:
            # Get credentials from environment variables
            username = os.getenv("LOGIN_USERNAME")
            password = os.getenv("LOGIN_PWD")

            if not username or not password:
                print("Error: Login credentials not found in .env file")
                print("Please create a .env file with LOGIN_USERNAME and " "LOGIN_PWD")
                raise Exception("Login credentials not found")

            # Navigate to login page
            login_url = "https://www.portfoliovisualizer.com/login"
            print(f"Navigating to login page: {login_url}")
            driver.get(login_url)
            time.sleep(2)

            # Find and fill username field
            username_field = None
            try:
                username_field = WebDriverWait(driver, 10).until(
                    EC.presence_of_element_located((By.ID, "email"))
                )
            except Exception:
                try:
                    username_field = driver.find_element(By.NAME, "email")
                except Exception:
                    username_field = driver.find_element(
                        By.XPATH, "//input[@type='email']"
                    )

            if username_field:
                username_field.clear()
                username_field.send_keys(username)
                print(f"Entered username: {username}")
                time.sleep(0.5)
            else:
                raise Exception("Could not find username field")

            # Find and fill password field
            password_field = None
            try:
                password_field = driver.find_element(By.ID, "password")
            except Exception:
                try:
                    password_field = driver.find_element(By.NAME, "password")
                except Exception:
                    password_field = driver.find_element(
                        By.XPATH, "//input[@type='password']"
                    )

            if password_field:
                password_field.clear()
                password_field.send_keys(password)
                print("Entered password")
                time.sleep(0.5)
            else:
                raise Exception("Could not find password field")

            # Find and click submit button
            submit_button = None
            try:
                submit_button = driver.find_element(
                    By.XPATH, "//button[@type='submit']"
                )
            except Exception:
                try:
                    submit_button = driver.find_element(
                        By.XPATH, "//input[@type='submit']"
                    )
                except Exception:
                    submit_button = driver.find_element(
                        By.XPATH,
                        "//button[contains(text(), 'Login') or "
                        "contains(text(), 'Sign In')]",
                    )

            if submit_button:
                try:
                    submit_button.click()
                except Exception:
                    driver.execute_script(
                        "arguments[0].click();", submit_button
                    )
                print("Clicked login submit button")
                time.sleep(3)

                # Check if login was successful
                try:
                    WebDriverWait(driver, 10).until(
                        EC.presence_of_element_located(
                            (By.ID, "accountDropdown")
                        )
                    )
                    print("✓ Login successful - account dropdown found")
                except Exception:
                    print(
                        "Warning: Login may have failed - account dropdown "
                        "not found after login"
                    )
                    print("Continuing anyway...")
            else:
                raise Exception("Could not find submit button")

        except Exception as e:
            print(f"Error during login: {e}")
            import traceback

            traceback.print_exc()
            raise

        # ========================================================================
        # Step 2: Navigate to Backtest Page
        # ========================================================================
        print("\n=== Step 2: Navigating to backtest page ===")
        url = "https://www.portfoliovisualizer.com/" "backtest-asset-class-allocation"
        driver.get(url)
        print(f"Navigated to: {url}")
        time.sleep(3)

        # ========================================================================
        # Step 3: Set Start Year to 1998
        # ========================================================================
        print("\n=== Step 3: Setting start year to 1998 ===")
        try:
            # Step 1: Click the button to open the modal
            modal_button = WebDriverWait(driver, 10).until(
                EC.presence_of_element_located(
                    (
                        By.CSS_SELECTOR,
                        "#overview > div:nth-child(1) > div > div > "
                        "div:nth-child(1) > table > tfoot > tr > td > "
                        "button.btn.btn-outline-primary.me-3",
                    )
                )
            )

            # Scroll the button into view
            driver.execute_script(
                "arguments[0].scrollIntoView({block: 'center'});", modal_button
            )
            time.sleep(1)

            # Try regular click first
            try:
                modal_button.click()
                print("Clicked button to open modal (regular click)")
            except Exception:
                # If regular click fails, use JavaScript click
                driver.execute_script("arguments[0].click();", modal_button)
                print("Clicked button to open modal (JavaScript click)")

            time.sleep(2)

            # Step 2: Wait for modal to appear
            WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, "#custom-data-body"))
            )
            print("Modal appeared")
            time.sleep(1)

            # Step 3: Click the Settings tab
            settings_tab = None
            try:
                settings_tab = WebDriverWait(driver, 5).until(
                    EC.element_to_be_clickable(
                        (
                            By.CSS_SELECTOR,
                            "#inputSettings_btn[aria-selected='false']",
                        )
                    )
                )
                print("Found Settings tab (aria-selected=false)")
            except Exception:
                try:
                    settings_tab = WebDriverWait(driver, 5).until(
                        EC.element_to_be_clickable(
                            (By.CSS_SELECTOR, "#inputSettings_btn")
                        )
                    )
                    print(
                        "Found Settings tab (any aria-selected value)"
                    )
                except Exception:
                    try:
                        settings_tab = driver.find_element(
                            By.XPATH, "//button[@id='inputSettings_btn']"
                        )
                        print("Found Settings tab (by XPath)")
                    except Exception as e:
                        print(f"Could not find Settings tab. Error: {e}")
                        raise

            # Click the Settings tab
            if settings_tab:
                try:
                    settings_tab.click()
                except Exception:
                    driver.execute_script("arguments[0].click();", settings_tab)
                print("Clicked Settings tab")
                time.sleep(1)

            # Step 4: Modify the StartYear field to 1998
            start_year_set = select_dropdown_value(
                driver, "#startYear", "1998", by_value=True
            )

            if not start_year_set:
                raise Exception("Could not set start year using any method")

            time.sleep(1)

            # Step 5: Navigate back to Portfolio Assets tab
            portfolio_assets_tab = None
            try:
                portfolio_assets_tab = WebDriverWait(driver, 5).until(
                    EC.element_to_be_clickable(
                        (
                            By.CSS_SELECTOR,
                            "#inputAssets_btn[aria-selected='false']",
                        )
                    )
                )
                print("Found Portfolio Assets tab (aria-selected=false)")
            except Exception:
                try:
                    portfolio_assets_tab = WebDriverWait(driver, 5).until(
                        EC.element_to_be_clickable(
                            (By.CSS_SELECTOR, "#inputAssets_btn")
                        )
                    )
                    print("Found Portfolio Assets tab (any aria-selected value)")
                except Exception:
                    try:
                        portfolio_assets_tab = driver.find_element(
                            By.XPATH, "//button[@id='inputAssets_btn']"
                        )
                        print("Found Portfolio Assets tab (by XPath)")
                    except Exception as e:
                        print(f"Could not find Portfolio Assets tab. Error: {e}")
                        raise

            # Click the Portfolio Assets tab
            if portfolio_assets_tab:
                try:
                    portfolio_assets_tab.click()
                except Exception:
                    driver.execute_script("arguments[0].click();", portfolio_assets_tab)
                print("Navigated back to Portfolio Assets tab")
                time.sleep(1)

        except Exception as e:
            print(f"Error setting start year via modal: {e}")
            import traceback

            traceback.print_exc()

        # ========================================================================
        # Step 4: Configure Benchmark
        # ========================================================================
        print("\n=== Step 4: Configuring benchmark ===")
        try:
            # Use the reusable function to select VFINX from the benchmark
            # dropdown
            benchmark_set = select_dropdown_value(
                driver,
                "#benchmark",
                "Vanguard 500 Index Investor (VFINX)",
                by_value=False,
            )

            if benchmark_set:
                print(
                    "Successfully configured benchmark: "
                    "Vanguard 500 Index Investor (VFINX)"
                )
            else:
                print("Warning: Could not set benchmark to VFINX")

        except Exception as e:
            print(f"Error setting benchmark: {e}")
            import traceback

            traceback.print_exc()

        # ========================================================================
        # Step 5: Add More Rows
        # ========================================================================
        print("\n=== Step 5: Adding more rows ===")
        try:
            # Find the "More" link by its onclick attribute
            more_button = WebDriverWait(driver, 10).until(
                EC.element_to_be_clickable(
                    (
                        By.XPATH,
                        "//a[contains(@onclick, 'addAssetRows') and "
                        "contains(text(), 'More')]",
                    )
                )
            )

            # Scroll into view
            driver.execute_script(
                "arguments[0].scrollIntoView({block: 'center'});", more_button
            )
            time.sleep(0.5)

            # Click the More button
            try:
                more_button.click()
                print("Clicked 'More' button to add rows")
            except Exception:
                # Try JavaScript click if regular click fails
                driver.execute_script("arguments[0].click();", more_button)
                print("Clicked 'More' button (JavaScript)")

            time.sleep(1)  # Wait for rows to be added

        except Exception as e:
            print(f"Warning: Could not click 'More' button: {e}")
            print("Continuing with existing rows...")

        # ========================================================================
        # Step 6: Load and Enter Portfolio Allocations
        # ========================================================================
        print("\n=== Step 6: Loading and entering portfolio allocations ===")

        # Use provided allocations file or default
        if allocations_file:
            csv_path = allocations_file
        else:
            csv_path = os.path.join(project_dir, "portfolio_allocations.csv")

        try:
            df_portfolio = pd.read_csv(csv_path)
            print(f"Loaded portfolio allocations from: {csv_path}")

            # Detect file format: check if columns start with Grid_ or Portfolio_
            portfolio_cols = [col for col in df_portfolio.columns
                            if col.startswith('Grid_') or col.startswith('Portfolio_')]

            num_portfolios = len(portfolio_cols)
            print(f"Detected {num_portfolios} portfolios in CSV")

            # Check Portfolio Visualizer limits (max 3 portfolios at a time)
            if num_portfolios > 3:
                print(f"\nWarning: Portfolio Visualizer supports max 3 portfolios per backtest")
                print(f"This file has {num_portfolios} portfolios.")
                print(f"Processing first 3 portfolios only.")
                print(f"To backtest all portfolios, upload the CSV directly to Portfolio Visualizer")
                print(f"and download the results manually.")
                portfolio_cols = portfolio_cols[:3]
                num_portfolios = 3

            # Show sample of data
            if num_portfolios <= 10:
                print("\nPortfolio Allocations CSV (first few columns):")
                cols_to_show = ['Asset_Description'] + portfolio_cols[:min(5, len(portfolio_cols))]
                print(df_portfolio[cols_to_show].to_string(index=False))

            # For grid format, we need to determine asset class mappings
            # Check if Asset_Class_Option_Value column exists
            if 'Asset_Class_Option_Value' in df_portfolio.columns:
                # Old format with explicit option values
                asset_class_mappings = {}
                for _, row in df_portfolio.iterrows():
                    asset_num = int(row["Asset_Number"])
                    option_value = row["Asset_Class_Option_Value"]
                    asset_class_mappings[asset_num] = option_value
            else:
                # New grid format - infer from Asset_Description
                asset_description_to_option = {
                    'US Equities - US Stock Market': 'TotalStockMarket',
                    'Foreign Developed Equities - Intl Developed ex-US Market': 'IntlDeveloped',
                    'Emerging Market Equities - Emerging Markets': 'EmergingMarket',
                    'US Treasuries - Intermediate Term Treasury': 'IntermediateTreasury',
                    'TIPS - Inflation-Protected Bonds': 'TIPS',
                    'Corporate Bonds - Investment Grade Corporate Bonds': 'CorpBond',
                    'Real Estate/REITs - US REIT': 'REIT',
                }

                asset_class_mappings = {}
                for idx, row in df_portfolio.iterrows():
                    asset_num = idx + 1  # Asset numbers are 1-indexed
                    asset_desc = row['Asset_Description']
                    if asset_desc in asset_description_to_option:
                        asset_class_mappings[asset_num] = asset_description_to_option[asset_desc]
                    else:
                        print(f"Warning: Unknown asset description: {asset_desc}")

            # Extract portfolio allocations from CSV
            portfolio_allocations = {}
            for idx, row in df_portfolio.iterrows():
                asset_num = idx + 1  # Asset numbers are 1-indexed
                # Read allocations for each portfolio column
                for portfolio_idx, col_name in enumerate(portfolio_cols, start=1):
                    if col_name in row and pd.notna(row[col_name]):
                        allocation = float(row[col_name])
                        if allocation > 0:  # Only include non-zero allocations
                            portfolio_allocations[(asset_num, portfolio_idx)] = allocation

            print(f"\nLoaded {len(asset_class_mappings)} asset classes")
            print(f"Loaded {len(portfolio_allocations)} allocation entries")
            print(f"Processing {num_portfolios} portfolios")

        except FileNotFoundError:
            print(f"Warning: CSV file not found at {csv_path}")
            print("Creating default CSV file...")

            # Create default CSV with current allocations
            default_data = {
                "Asset_Number": [1, 2, 3, 4, 5, 6, 7],
                "Asset_Class_Option_Value": [
                    "TotalStockMarket",
                    "IntlDeveloped",
                    "EmergingMarket",
                    "IntermediateTreasury",
                    "TIPS",
                    "CorpBond",
                    "REIT",
                ],
                "Asset_Description": [
                    "US Equities - US Stock Market",
                    "Foreign Developed Equities - Intl Developed ex-US Market",
                    "Emerging Market Equities - Emerging Markets",
                    "US Treasuries - Intermediate Term Treasury",
                    "TIPS - Inflation-Protected Bonds",
                    "Corporate Bonds - Investment Grade Corporate Bonds",
                    "Real Estate/REITs - US REIT",
                ],
                "Portfolio_1": [30.0, 15.0, 8.0, 10.0, 15.0, 7.5, 14.5],
                "Portfolio_2": [20.0, 15.0, 8.0, 20.0, 15.0, 7.5, 14.5],
                "Portfolio_3": [40.0, 15.0, 8.0, 0.0, 15.0, 7.5, 14.5],
            }
            df_default = pd.DataFrame(default_data)
            df_default.to_csv(csv_path, index=False)
            print(f"Created default CSV file at: {csv_path}")
            print("Please edit this file and re-run the script.")
            raise Exception("CSV file not found - created default file")

        except Exception as e:
            print(f"Error loading CSV file: {e}")
            import traceback

            traceback.print_exc()
            raise

        # Validate portfolio weights
        print("\n=== Validating Portfolio Weights ===")
        validate_portfolio_weights(portfolio_allocations)

        # Set asset classes first (before entering allocations)
        print("\n=== Setting Asset Classes ===")
        for asset_num, option_value in asset_class_mappings.items():
            set_asset_class(driver, asset_num, option_value)
            time.sleep(0.3)  # Brief pause between selections

        # Enter portfolio allocations
        print("\n=== Entering Portfolio Allocations ===")
        for (asset_num, portfolio_num), allocation in (
            portfolio_allocations.items()
        ):
            enter_portfolio_allocation(
                driver, asset_num, portfolio_num, allocation
            )
            time.sleep(0.2)  # Brief pause between entries

        print("\nPortfolio setup completed successfully")

        # ========================================================================
        # Step 7: Run Backtest
        # ========================================================================
        print("\n=== Step 7: Running backtest ===")
        try:
            # Find the submit button by ID
            analyze_button = WebDriverWait(driver, 10).until(
                EC.element_to_be_clickable((By.ID, "submitButton"))
            )

            # Scroll into view
            driver.execute_script(
                "arguments[0].scrollIntoView({block: 'center'});",
                analyze_button,
            )
            time.sleep(0.5)

            # Click the button
            try:
                analyze_button.click()
                print("Clicked 'Analyze Portfolios' button")
            except Exception:
                # Try JavaScript click if regular click fails
                driver.execute_script("arguments[0].click();", analyze_button)
                print("Clicked 'Analyze Portfolios' button (JavaScript)")

            # Wait for results to load
            print("Waiting for results to load...")
            time.sleep(5)

            # Wait for results table to appear
            WebDriverWait(driver, 30).until(
                EC.presence_of_element_located((By.CLASS_NAME, "table"))
            )
            print("Results loaded successfully")

        except Exception as e:
            print(f"Error running analysis: {e}")
            import traceback

            traceback.print_exc()

        # ========================================================================
        # Step 8: Download Excel Results
        # ========================================================================
        print("\n=== Step 8: Downloading Excel results ===")
        # Chrome downloads to this directory
        chrome_download_dir = os.path.join(project_dir, "downloads")
        # Save to data/source_tables for processing
        excel_output_dir = os.path.join(project_dir, "data", "source_tables")
        os.makedirs(excel_output_dir, exist_ok=True)

        # Determine output filename based on alias
        if output_alias:
            output_filename = f"portfolio_backtest_results_{output_alias}.xlsx"
        else:
            output_filename = "portfolio_backtest_results.xlsx"

        # Download with aliased filename
        excel_file = download_excel_results(
            driver,
            chrome_download_dir,
            output_filename,
        )

        if excel_file:
            # Move file from downloads directory to data/source_tables
            try:
                filename = os.path.basename(excel_file)
                final_path = os.path.join(excel_output_dir, filename)
                # Don't remove existing files - preserve historical data
                # If file exists, add a counter to make it unique
                if os.path.exists(final_path):
                    base_name, ext = os.path.splitext(filename)
                    counter = 1
                    while os.path.exists(final_path):
                        final_path = os.path.join(
                            excel_output_dir, f"{base_name}_{counter}{ext}"
                        )
                        counter += 1
                shutil.move(excel_file, final_path)
                print(f"\n✓ Excel file saved to: {final_path}")

                # Return the final path for the orchestrator to use
                return final_path
            except Exception as e:
                print(f"\n✓ Excel file downloaded to: {excel_file}")
                print(f"Warning: Could not move to custom directory: {e}")
                return excel_file
        else:
            print("\n✗ Failed to download Excel file")
            return None

        print("\n=== Script completed successfully ===")

    finally:
        # Close the browser
        print("\nClosing browser...")
        driver.quit()
        print("Browser closed")


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(
        description='Automate portfolio backtesting using Portfolio Visualizer'
    )
    parser.add_argument(
        '--allocations',
        type=str,
        default=None,
        help='Path to portfolio allocations CSV file'
    )
    parser.add_argument(
        '--alias',
        type=str,
        default=None,
        help='Alias for output file (e.g., "coarse_grid", "fine_grid")'
    )

    args = parser.parse_args()

    result_file = main(allocations_file=args.allocations, output_alias=args.alias)
    if result_file:
        print(f"\n{'='*80}")
        print(f"BACKTEST RESULTS FILE:")
        print(f"  {result_file}")
        print(f"{'='*80}")
