# SPDX-FileCopyrightText: 2023-present David C Wang <dcwangmit01@gmail.com>
#
# SPDX-License-Identifier: MIT

"""
Schwab Downloader

Usage:
  schwab-downloader.py \
    [--all | --checks --docs --transactions] \
    [--year=<YYYY> | --date-range=<YYYYMMDD-YYYYMMDD>]
    [--id=<id> --password=<password>]
  schwab-downloader.py (-h | --help)
  schwab-downloader.py (-v | --version)

Login Options:
  --id=<id>              Schwab login id  [default: $SCHWAB_ID].
  --password=<password>  Schwab login password  [default: $SCHWAB_PASSWORD].

Date Range Options:
  --date-range=<YYYYMMDD-YYYYMMDD>  Start and end date range
  --year=<YYYY>                     Year, formatted as YYYY  [default: <CUR_YEAR>].

Options:
  -h --help                Show this screen.
  -v --version             Show version.

Examples:
  schwab-downloader.py --year=2022
  schwab-downloader.py --date-range=20220101-20221231
"""

from schwab_downloader.__about__ import __version__

from playwright.sync_api import sync_playwright
from datetime import datetime
import random
import time
import os
import sys
from docopt import docopt
import json
import ipdb


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
        self.DEFAULT_PRINT_FILENAME = "mozilla.pdf"

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
        self.browser = self.playwright.firefox.launch(
            headless=False,
            firefox_user_prefs={
                "print.always_print_silent": True,
                "print.printer_Mozilla_Save_to_PDF.print_to_file": True,
                "print_printer": "Mozilla Save to PDF",
            },
        )
        self.context = self.browser.new_context()

    def login(self):
        self.page = self.context.new_page()
        self.page.goto("https://www.schwab.com/")
        self.sleep()
        self.page.get_by_role("link", name="Log In").click()
        self.sleep()
        self.page.get_by_role("link", name="Schwab.com").click()
        self.sleep()

        if self.id:
            self.page.frame_locator("#lmsSecondaryLogin").get_by_placeholder("Login ID").click()
            self.page.frame_locator("#lmsSecondaryLogin").get_by_placeholder("Login ID").fill(self.id)
            self.sleep()

        if self.password:
            self.page.frame_locator("#lmsSecondaryLogin").get_by_placeholder("Password").click()
            self.page.frame_locator("#lmsSecondaryLogin").get_by_placeholder("Password").fill(self.password)
            self.sleep()

        self.page.frame_locator("#lmsSecondaryLogin").get_by_label("Remember Login ID").check()
        self.sleep()

        if self.id and self.password:
            self.page.frame_locator("#lmsSecondaryLogin").get_by_role("button", name="Log In").click()
            self.sleep()

    def navigate_to_history(self):
        self.page.wait_for_url('*client.schwab.com/clientapps/*', timeout=0)
        self.page.get_by_label("secondary level").get_by_role("link", name="History").click()
        self.page.get_by_role("tab", name="Transactions").click()
        self.sleep()

    def process_accounts(self):
        accounts = self.get_all_accounts()
        print(json.dumps(accounts, indent=2))

        for _, account in accounts.items():
            if account['type'] in ["other", "brokerage"]:
                continue
            print("Processing account", json.dumps(account, indent=2))

            self.select_account(account)
            self.process_account_data(account)

    def get_all_accounts(self):
        accounts = {}
        for i, account_type in enumerate(["brokerage", "other", "bank"]):
            accounts_list = self.page.query_selector(f"xpath=//ul[@aria-labelledby='header-{i}']")
            for a in accounts_list.query_selector_all("a"):
                account_nickname, account_number = [span.inner_text() for span in a.query_selector_all("span")]
                if account_number == "":
                    account_number = "EAC"
                accounts[account_number] = {
                    "number": account_number,
                    "nickname": account_nickname,
                    "type": account_type,
                }
        return accounts

    def select_account(self, account):
        if account['number'] not in self.page.query_selector("button.account-selector-button").inner_text():
            self.page.click('.sdps-account-selector')
            self.page.query_selector(f"xpath=//span[contains(text(), '{account['number']}')]").click()
            self.sleep()

    def process_data_row(self, data_row, tds, account) -> (str, str, datetime):
        tds_strs = [td.inner_text().strip() for td in tds]
        tds_strs = ["" if td == "blank" else td for td in tds_strs]

        account_type = account["type"]
        account_nickname = account["nickname"].title().replace(" ", "").replace("/", "")
        account_number = account["number"][-4:]

        if account_type == "brokerage":
            date = datetime.strptime(tds_strs[0].split(" ")[0], "%m/%d/%Y")
            _type = tds_strs[2].title().replace(" ", "")
            description = tds_strs[4].title().replace(" ", "")
            total = tds_strs[8].replace("$", "").replace(",", "").replace("-", "")
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
        else:  # EAC Row
            return None, None, None

        date_str = date.strftime("%Y%m%d")

        if _type == "Check":
            file_name = (
                f"{TARGET_DIR}/{date_str}_{total}_schwab"
                f"_{account_type}_{account_number}_{account_nickname}"
                f"_{_type}_{check_number}.pdf"
            )
        else:
            file_name = (
                f"{TARGET_DIR}/{date_str}_{total}_schwab"
                f"_{account_type}_{account_number}_{account_nickname}"
                f"_{_type}_{description}.pdf"
            )

        details_link = data_row.query_selector("a")

        return file_name, details_link, date

    def process_account_data(self, account):
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

            data_rows = self.page.query_selector_all("tr.data-row")
            for data_row in data_rows:
                tds = data_row.query_selector_all(":scope > td")
                file_name, details_link, date = self.process_data_row(data_row, tds, account)
                if date > self.end_date:
                    continue
                elif date < self.start_date:
                    done = True
                    break
                if not details_link:
                    continue
                self.click_modal_and_save(file_name, details_link)

    def click_modal_and_save(self, file_name, details_link):
        if os.path.isfile(file_name):
            print(f"File Exists [{file_name}]")
        else:
            print(f"File Saving [{file_name}]")

            details_link.click()
            time.sleep(5)

            # remove the file mozilla.pdf if it exists
            if os.path.isfile(self.DEFAULT_PRINT_FILENAME):
                os.remove(self.DEFAULT_PRINT_FILENAME)

            print_link = self.page.query_selector("a#customModalPrint")  # Wire Details
            if not print_link:
                print_link = self.page.query_selector("a.linkPrint")  # Check Details
            if not print_link:
                ipdb.set_trace()

            try:
                print_link.click()
                self.sleep()
            except Exception as e:
                print("Print link click failed", e)
                ipdb.set_trace()

            # Ensure the printed file exists.
            if not os.path.isfile(self.DEFAULT_PRINT_FILENAME):
                print("File [mozilla.pdf] does not exist")
                ipdb.set_trace()
            else:
                # move the file to file_name
                os.rename(self.DEFAULT_PRINT_FILENAME, file_name)
                print(f"File [{file_name}] saved")

            self.page.query_selector("button#modalClose").click()

    def close(self):
        self.context.close()
        self.browser.close()

    def sleep(self):
        # Add human latency
        # Generate a random self.sleep time between 3 and 5 seconds
        self.sleep_time = random.uniform(2, 5)
        # self.sleep for the generated time
        time.sleep(self.sleep_time)

    def run(self):
        print(self.args)
        self.parse_credentials()
        self.parse_date_range()
        self.ensure_target_dir("YOUR_TARGET_DIR")  # Replace with the actual directory
        self.launch_browser()
        self.login()
        self.navigate_to_history()
        self.process_accounts()
        self.close()


def schwab_downloader():
    args = docopt(__doc__)
    print(args)
    if args['--version']:
        print(__version__)
        sys.exit(0)

    with sync_playwright() as playwright:
        downloader = SchwabDownloader(playwright, args)
        downloader.run()
