# SPDX-FileCopyrightText: 2023-present David C Wang <dcwangmit01@gmail.com>
#
# SPDX-License-Identifier: MIT

"""
Schwab Downloader

Usage:
  schwab-downloader.py \
    [--all | --checks --docs --transactions] \
    [--year=<YYYY> | --date-range=<YYYYMMDD-YYYYMMDD>]
    [--id=<id> --password=<password>] [--remote-debug]
  schwab-downloader.py (-h | --help)
  schwab-downloader.py (-v | --version)

Login Options:
  --id=<id>              Schwab login id  [default: $SCHWAB_ID].
  --password=<password>  Schwab login password  [default: $SCHWAB_PASSWORD].

Date Range Options:
  --date-range=<YYYYMMDD-YYYYMMDD>  Start and end date range
  --year=<YYYY>                     Year, formatted as YYYY  [default: <CUR_YEAR>].

Debug Options:
  --remote-debug          Enable remote debugging on port 9222

Options:
  -h --help                Show this screen.
  -v --version             Show version.

Examples:
  schwab-downloader.py --year=2022
  schwab-downloader.py --date-range=20220101-20221231
  schwab-downloader.py --remote-debug --year=2022
"""

import json
import os
import sys
import time
from datetime import datetime
from pathlib import Path

import ipdb
from docopt import docopt
from dotenv import load_dotenv
from playwright.sync_api import sync_playwright
from playwright_stealth import Stealth

from schwab_downloader.__about__ import __version__


def load_env_if_needed():
    """Load environment variables from .env file if it exists and variables aren't set."""
    # Check if Schwab credentials are already set in environment
    schwab_id = os.environ.get('SCHWAB_ID')
    schwab_password = os.environ.get('SCHWAB_PASSWORD')

    # If both are already set, no need to load .env
    if schwab_id and schwab_password:
        return

    # Look for .env file in current directory and parent directories
    current_dir = Path.cwd()
    env_file = None

    # Check current directory and up to 3 parent directories
    for i in range(4):
        check_path = current_dir / '.env'
        if check_path.exists():
            env_file = check_path
            break
        current_dir = current_dir.parent

    if env_file:
        print(f"Loading environment variables from {env_file}")
        load_dotenv(env_file)
    else:
        print("No .env file found in current directory or parent directories")


TARGET_DIR = os.getcwd() + "/" + "downloads"


class SchwabDownloader:
    def __init__(self, playwright, args):
        self.playwright = playwright
        self.args = args
        self.id = None
        self.password = None
        self.start_date = None
        self.end_date = None
        self.browser = None
        self.context = None
        self.page = None
        self.accounts = None

    def parse_credentials(self):
        self.id = self.args.get('--id')
        if self.id == '$SCHWAB_ID':
            self.id = os.environ.get('SCHWAB_ID')

        self.password = self.args.get('--password')
        if self.password == '$SCHWAB_PASSWORD':
            self.password = os.environ.get('SCHWAB_PASSWORD')

    def parse_date_range(self):
        if self.args['--date-range']:
            self.start_date, self.end_date = self.args['--date-range'].split('-')
        elif self.args['--year'] != "<CUR_YEAR>":
            self.start_date, self.end_date = self.args['--year'] + "0101", self.args['--year'] + "1231"
        else:
            year = str(datetime.now().year)
            self.start_date, self.end_date = "2000101", year + "1231"

        self.start_date = datetime.strptime(self.start_date, "%Y%m%d")
        self.end_date = datetime.strptime(self.end_date, "%Y%m%d")

    def ensure_target_dir(self, TARGET_DIR):
        os.makedirs(TARGET_DIR, exist_ok=True)

    def launch_browser(self):
        # Check if remote debugging is enabled
        remote_debug = self.args.get('--remote-debug', False)

        if remote_debug:
            print("🚀 Launching Chromium with CDP debugging on port 9222")
            print("📱 You can connect to this browser at: http://localhost:9222")
            print("🔗 AI assistant can control this browser instance via CDP")

            # Launch browser with CDP endpoint
            self.browser = self.playwright.chromium.launch(
                headless=False,
                args=[
                    '--remote-debugging-port=9222',
                    '--remote-debugging-address=0.0.0.0',
                    '--disable-web-security',
                    '--disable-features=VizDisplayCompositor',
                ],
            )

            # Connect to the browser using CDP
            self.browser = self.playwright.chromium.connect_over_cdp("http://localhost:9222")
        else:
            self.browser = self.playwright.chromium.launch(
                headless=False,
            )

        self.context = self.browser.new_context()

    def login(self):
        self.page = self.context.new_page()
        Stealth().apply_stealth_sync(self.page)
        self.page.goto("https://www.schwab.com/")

        # Store frame locator once for efficiency
        frame = self.page.frame_locator("iframe[title=\"log in form\"]")

        if self.id:
            frame.get_by_role("textbox", name="Login ID").fill(self.id)

        if self.password:
            frame.get_by_role("textbox", name="Password").fill(self.password)

        frame.get_by_label("Remember Login ID").check()

        self.sleep()

        if self.id and self.password:
            frame.get_by_role("button", name="Log in").click()
            self.sleep()

            # Check if we're on the identity confirmation page
            if "Confirm Your Identity" in self.page.title():
                print("\n2FA REQUIRED: Enter your security code and click Continue")
        else:
            print("No credentials provided, waiting for user to enter credentials")

        print("Waiting for verification...")

        # Wait for navigation to the account summary page
        self.page.wait_for_url('https://client.schwab.com/clientapps/accounts/summary/', timeout=0)

        print("Verification completed! Continuing...")
        self.sleep()

    def navigate_to_statements(self):
        self.page.wait_for_url('*client.schwab.com/*', timeout=0)
        self.page.get_by_label("secondary level").get_by_role("link", name="Statements").click()
        self.sleep()

    def load_accounts(self):

        self.accounts = {}

        # Find all "More" buttons for accounts
        more_buttons = self.page.query_selector_all(
            "xpath=//button[contains(@aria-label, 'More account details overlay')]"
        )

        for more_button in more_buttons:
            # Click the "More" button to open the dialog
            more_button.click()
            self.sleep()

            # Wait for the dialog to appear and extract account information
            dialog = self.page.query_selector("#accountdetailsoverlay-modal-body")

            # Extract account name from the label-value item with "Name" label
            #   For EAC this will be the company name
            #   For other accounts this will be the account name (alias that the user has set)
            name_item = dialog.query_selector(
                "xpath=.//sdps-list-label-value-item[.//span[contains(text(), 'Name')]]//div[@slot='value']"
            )
            account_name = name_item.inner_text().strip() if name_item else "Unknown"

            # Extract account number from the label-value item with "Account Number" label
            account_number_item = dialog.query_selector(
                "xpath=.//sdps-list-label-value-item[.//span[contains(text(), 'Account Number')]]//div[@slot='value']"
            )
            account_number_text = account_number_item.inner_text().strip() if account_number_item else "Unknown"

            # Extract account number - handle all formats:
            # 1. "440044196739 Schwab Bank" -> extract "440044196739"
            # 2. "6206-8621" -> extract "6206-8621"
            # 3. "1952-1651 DAFgiving360" -> extract "1952-1651"
            import re

            account_match = re.search(r'[\d-]+', account_number_text)
            account_number = account_match.group(0) if account_match else "Unknown"

            # Extract account type from the label-value item with "Type" label
            type_item = dialog.query_selector(
                "xpath=.//sdps-list-label-value-item[.//span[contains(text(), 'Type')]]//div[@slot='value']"
            )
            account_type_text = type_item.inner_text().strip() if type_item else "Unknown"

            # Extract "Companies" from the label-value item with "Companies" label, if present
            companies_item = dialog.query_selector(
                "xpath=.//sdps-list-label-value-item[.//span[contains(text(), 'Companies')]]//div[@slot='value']"
            )
            companies_text = companies_item.inner_text().strip() if companies_item else None
            if companies_text:
                account_type = "EAC"
                account_name = "EAC " + companies_text
                account_number = "EAC" + companies_text
            elif 'DAF' in account_type_text:
                account_type = "DAF"
            else:
                account_type = account_type_text

            # Store the account information
            self.accounts[account_number] = {
                "number": account_number,
                "nickname": account_name,
                "type": account_type,
            }

            # Close the dialog
            self.page.keyboard.press("Escape")

        print(json.dumps(self.accounts, indent=2))

    def process_accounts(self, fn_account_selector: callable, fn_process_row: callable, fn_click_save: callable):
        for _, account in self.accounts.items():
            print("Processing account", json.dumps(account, indent=2))

            fn_account_selector(account)
            self.process_page(account, fn_process_row, fn_click_save)

    def select_account(self, account):
        if account['number'] not in self.page.query_selector("button.account-selector-button").inner_text():
            self.page.click('.sdps-account-selector')
            self.page.query_selector(f"xpath=//span[contains(text(), '{account['number']}')]").click()
            self.sleep()

    def select_history_account(self, account):
        self.select_account(account)
        self.page.select_option('#date-range-select-id', 'All')
        search_button = self.page.query_selector('xpath=//button[contains(., "Search")]')
        search_button.click()
        self.sleep()

    def select_statements_account(self, account):
        self.select_account(account)
        self.page.query_selector("#date-range-select-id").click()
        self.page.select_option('#date-range-select-id', 'Last 10 Years')
        select_all_button = self.page.query_selector('xpath=//button[contains(., "Select All")]')
        if select_all_button:
            select_all_button.click()
        search_button = self.page.query_selector('xpath=//button[contains(., "Search")]')
        search_button.click()
        self.sleep()

    def process_history_row(self, data_row, tds, account) -> (str, str, datetime):
        tds_strs = [td.inner_text().strip() for td in tds]
        tds_strs = ["" if td == "blank" else td for td in tds_strs]
        tds_strs = [td.replace("\n", "") for td in tds_strs]  # remove all newlines from tds_strs

        account_type = account["type"]
        account_nickname = account["nickname"].title().replace(" ", "").replace("/", "")
        account_number = account["number"][-4:]

        if account_type == "other":  # EAC Row
            # EAC doesn't have details to save.  Set date to be super old and details_link = None
            return None, None, datetime(2000, 1, 1)
        elif account_type == "brokerage":
            if len(tds_strs) != 7:
                import ipdb

                ipdb.set_trace()
            date = datetime.strptime(tds_strs[0].split(" ")[0], "%m/%d/%Y")
            _type = tds_strs[1].title().replace(" ", "")
            description = tds_strs[2].title().replace(" ", "")
            total = tds_strs[6].replace("$", "").replace(",", "").replace("-", "")
        elif account_type == "bank":
            date = datetime.strptime(tds_strs[0], "%m/%d/%Y")
            _type = tds_strs[1].title().replace(" ", "")
            check_number = tds_strs[2]
            description = tds_strs[3].title().replace(" ", "")

            withdrawal = tds_strs[4].replace("$", "").replace(",", "").replace("-", "")
            deposit = tds_strs[5].replace("$", "").replace(",", "").replace("-", "")
            total = "0.00"
            if withdrawal == "":
                total = deposit
            elif deposit == "":
                total = withdrawal

        date_str = date.strftime("%Y%m%d")

        if _type == "Check":
            file_name = (
                f"{TARGET_DIR}/schwab"
                f"_{account_type}_{account_number}_{account_nickname}_{date_str}"
                f"_{total}_{_type}_{check_number}.pdf"
            )
        else:
            file_name = (
                f"{TARGET_DIR}/schwab"
                f"_{account_type}_{account_number}_{account_nickname}_{date_str}"
                f"_{total}_{_type}_{description}.pdf"
            )

        details_link = data_row.query_selector("button")

        return file_name, details_link, date

    def process_statements_row(self, data_row, tds, account) -> (str, str, datetime):
        tds_strs = [td.inner_text().strip() for td in tds]
        tds_strs = ["" if td == "blank" else td for td in tds_strs]

        # Skip the records of the 1099 dashboard, which is the annual summary
        if len(tds_strs) == 3:
            return None, None, datetime(2000, 1, 1)

        account_type = account["type"]
        account_nickname = account["nickname"].title().replace(" ", "").replace("/", "")
        if account_type == "other":
            account_number = "EAC"
        else:
            account_number = account["number"][-4:]

        date = datetime.strptime(tds_strs[0].split(" ")[0], "%m/%d/%Y")
        _type = tds_strs[1].title().replace(" ", "")
        doc_name = (
            tds_strs[3].title().replace(" ", "").split("\n")[0].replace("/", "")
        )  # Split off regulatory inserts, then replace slashes

        date_str = date.strftime("%Y%m%d")

        file_name = (
            f"{TARGET_DIR}/schwab_{account_type}_{account_number}_{account_nickname}_{date_str}_{_type}_{doc_name}.pdf"
        )

        details_link = data_row.query_selector("button:text('PDF')")
        return file_name, details_link, date

    def process_page(self, account, fn_process_row: callable, fn_click_save: callable):
        first_page = True
        done = False
        while not done:
            if first_page:
                first_page = False
            else:
                next_link = self.page.query_selector("xpath=//a[contains(text(), 'Next')]")
                if not next_link:
                    break
                next_link.click()
                self.sleep()

            data_rows = self.page.query_selector_all("tbody > tr")
            for data_row in data_rows:
                tds = data_row.query_selector_all(":scope > td")
                file_name, details_link, date = fn_process_row(data_row, tds, account)
                if not details_link:
                    continue
                if date > self.end_date:
                    continue
                elif date < self.start_date:
                    done = True
                    break
                fn_click_save(file_name, details_link)

    def click_and_save(self, file_name, details_link):
        if os.path.isfile(file_name):
            print(f"File Exists [{file_name}]")
        else:
            print(f"File Saving [{file_name}]")

            with self.page.expect_download() as download_info:
                details_link.click()
            download = download_info.value
            download.save_as(file_name)

    def click_modal_and_save(self, file_name, details_link):
        if os.path.isfile(file_name):
            print(f"File Exists [{file_name}]")
        else:
            print(f"File Saving [{file_name}]")

            details_link.click()
            time.sleep(5)

            print_link = self.page.query_selector("a.print-link")  # Wire Details
            if not print_link:
                print_link = self.page.query_selector("a.linkPrint")  # Check Details
            if not print_link:
                ipdb.set_trace()

            try:
                self.page.pdf(
                    path=file_name,
                    format="Letter",
                    margin={"top": ".5in", "right": ".5in", "bottom": ".5in", "left": ".5in"},
                    page_ranges="1",  # page.pdf is generating 5 pages instead of 1... work around it
                )
                self.sleep()
            except Exception as e:
                print("Save Page failed", e)
                ipdb.set_trace()

            # Close the Modal
            self.page.keyboard.press('Escape')

    def close(self):
        self.context.close()
        self.browser.close()

    def sleep(self):
        # Add human latency
        # Generate a random self.sleep time between 3 and 5 seconds
        # self.sleep_time = random.uniform(1, 2)
        # # self.sleep for the generated time
        # time.sleep(self.sleep_time)
        time.sleep(2)

    def run(self):
        print(self.args)
        self.parse_credentials()
        self.parse_date_range()
        self.ensure_target_dir(TARGET_DIR)  # Replace with the actual directory
        self.launch_browser()
        self.login()
        self.load_accounts()
        self.process_accounts(self.select_history_account, self.process_history_row, self.click_modal_and_save)
        self.navigate_to_statements()
        self.process_accounts(self.select_statements_account, self.process_statements_row, self.click_and_save)
        self.close()


def schwab_downloader():
    # Load environment variables from .env file if needed
    load_env_if_needed()

    args = docopt(__doc__)
    print(args)
    if args['--version']:
        print(__version__)
        sys.exit(0)

    with sync_playwright() as playwright:
        downloader = SchwabDownloader(playwright, args)
        downloader.run()
