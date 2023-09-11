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

from playwright.sync_api import sync_playwright, TimeoutError
from datetime import datetime
import random
import time
import os
import sys
from docopt import docopt
import json
import ipdb


TARGET_DIR = os.getcwd() + "/" + "downloads"
DEFAULT_PRINT_FILENAME = "mozilla.pdf"


def sleep():
    # Add human latency
    # Generate a random sleep time between 3 and 5 seconds
    sleep_time = random.uniform(2, 5)
    # Sleep for the generated time
    time.sleep(sleep_time)


def process_brokerage_row(data_row, tds, account) -> (str, str, datetime):
    assert account['type'] == "brokerage"

    tds_strs = [td.inner_text().strip() for td in tds]
    tds_strs = ["" if td == "blank" else td for td in tds_strs]  # replace all 'blank' in tds_strs with ""

    date = datetime.strptime(tds_strs[0].split(" ")[0], "%m/%d/%Y")  # strip of "as of mm/dd/yyyy"
    _type = tds_strs[2].title().replace(" ", "")
    details_link = data_row.query_selector("a")
    description = tds_strs[4].title().replace(" ", "")
    total = tds_strs[8].replace("$", "").replace(",", "").replace("-", "")  # Remove dollar, commas, negative

    date_str = date.strftime("%Y%m%d")
    account_type = account["type"]
    account_nickname = account["nickname"].title().replace(" ", "").replace("/", "")
    account_number = account["number"][-4:]

    file_name = (
        f"{TARGET_DIR}/{date_str}_{total}_schwab_{account_type}_{account_number}_{account_nickname}"
        f"_{_type}_{description}.pdf"
    )

    return file_name, details_link, date


def process_bank_row(data_row, tds, account) -> (str, str, datetime):
    assert account['type'] == "bank"

    tds_strs = [td.inner_text().strip() for td in tds]
    tds_strs = ["" if td == "blank" else td for td in tds_strs]  # replace all 'blank' in tds_strs with ""

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
    account_type = account["type"]
    account_nickname = account["nickname"].title().replace(" ", "").replace("/", "")
    account_number = account["number"][-4:]  # last 4 digits
    details_link = data_row.query_selector("a")

    if _type == "Check":
        file_name = (
            f"{TARGET_DIR}/{date_str}_{total}_schwab_{account_type}_{account_number}_{account_nickname}"
            f"_{_type}_{check_number}.pdf"
        )
    else:
        file_name = (
            f"{TARGET_DIR}/{date_str}_{total}_schwab_{account_type}_{account_number}_{account_nickname}"
            f"_{_type}_{description}.pdf"
        )
    return file_name, details_link, date


def process_eac_row(data_row, tds, account) -> (str, str, datetime):
    assert account['type'] == "EAC"

    # date = datetime.strptime(
    #     tds[0].inner_text().strip().split(" ")[0], "%m/%d/%Y"
    # )  # split off the second part "08/16/2023 as of 08/15/2023"
    return None, None, None


def click_modal_and_save(page, file_name, details_link):
    if os.path.isfile(file_name):
        print(f"File Exists [{file_name}]")
    else:
        print(f"File Saving [{file_name}]")

        details_link.click()
        time.sleep(5)

        # remove the file mozilla.pdf if it exists
        if os.path.isfile(DEFAULT_PRINT_FILENAME):
            os.remove(DEFAULT_PRINT_FILENAME)

        print_link = page.query_selector("a#customModalPrint")  # Wire Details
        if not print_link:
            print_link = page.query_selector("a.linkPrint")  # Check Details
        if not print_link:
            ipdb.set_trace()

        try:
            print_link.click()
            sleep()
        except Exception as e:
            print("Print link click failed", e)
            ipdb.set_trace()

        # Ensure the printed file exists.
        if not os.path.isfile(DEFAULT_PRINT_FILENAME):
            print("File [mozilla.pdf] does not exist")
            ipdb.set_trace()
        else:
            # move the file to file_name
            os.rename(DEFAULT_PRINT_FILENAME, file_name)
            print(f"File [{file_name}] saved")

        page.query_selector("button#modalClose").click()


def run(playwright, args):
    print(args)

    id = args.get('--id')
    if id == '$SCHWAB_ID':
        id = os.environ.get('SCHWAB_ID')

    password = args.get('--password')
    if password == '$SCHWAB_PASSWORD':
        password = os.environ.get('SCHWAB_PASSWORD')

    # Parse date ranges int start_date and end_date
    if args['--date-range']:
        start_date, end_date = args['--date-range'].split('-')
    elif args['--year'] != "<CUR_YEAR>":
        start_date, end_date = args['--year'] + "0101", args['--year'] + "1231"
    else:
        year = str(datetime.now().year)
        start_date, end_date = year + "0101", year + "1231"
    start_date = datetime.strptime(start_date, "%Y%m%d")
    end_date = datetime.strptime(end_date, "%Y%m%d")

    # Debug
    print(start_date, end_date)

    # Ensure the location exists for where we will save our downloads
    os.makedirs(TARGET_DIR, exist_ok=True)

    # Create Playwright context with Firefox
    browser = playwright.firefox.launch(
        headless=False,
        firefox_user_prefs={
            "print.always_print_silent": True,
            "print.printer_Mozilla_Save_to_PDF.print_to_file": True,
            "print_printer": "Mozilla Save to PDF",
        },
    )
    context = browser.new_context()

    page = context.new_page()
    page.goto("https://www.schwab.com/")
    sleep()
    page.get_by_role("link", name="Log In").click()
    sleep()
    page.get_by_role("link", name="Schwab.com").click()
    sleep()

    if id:
        page.frame_locator("#lmsSecondaryLogin").get_by_placeholder("Login ID").click()
        page.frame_locator("#lmsSecondaryLogin").get_by_placeholder("Login ID").fill(id)
        sleep()

    if password:
        page.frame_locator("#lmsSecondaryLogin").get_by_placeholder("Password").click()
        page.frame_locator("#lmsSecondaryLogin").get_by_placeholder("Password").fill(password)
        sleep()

    page.frame_locator("#lmsSecondaryLogin").get_by_label("Remember Login ID").check()
    sleep()

    if id and password:
        page.frame_locator("#lmsSecondaryLogin").get_by_role("button", name="Log In").click()
        sleep()

    # Wait until user to clicks through the login and 2fa pages and successfully login
    page.wait_for_url('*client.schwab.com/clientapps/*', timeout=0)

    # Click on history
    page.get_by_label("secondary level").get_by_role("link", name="History").click()
    page.get_by_role("tab", name="Transactions").click()
    sleep()

    # parse all accounts and their links
    accounts = {}
    for i, account_type in enumerate(["brokerage", "other", "bank"]):
        accounts_list = page.query_selector(f"xpath=//ul[@aria-labelledby='header-{i}']")
        for a in accounts_list.query_selector_all("a"):
            account_nickname, account_number = [span.inner_text() for span in a.query_selector_all("span")]

            # for EAC accounts
            if account_number == "":
                account_number = "EAC"

            accounts[account_number] = {
                "number": account_number,
                "nickname": account_nickname,
                "type": account_type,
            }

    print(json.dumps(accounts, indent=2))

    for _, account in accounts.items():
        # TODO: Only do brokerage
        if account['type'] in ["other", "brokerage"]:
            continue

        print("processing account", json.dumps(account, indent=2))

        # Click to select the account if it's not already selected
        if account['number'] not in page.query_selector("button.account-selector-button").inner_text():
            # Click on the account selector box
            page.click('.sdps-account-selector')
            page.query_selector(f"xpath=//span[contains(text(), '{account['number']}')]").click()
            sleep()

        # Page Loop
        first_page = True
        done = False
        while not done:
            # Go to the next page pagination, and continue downloading
            #   if there is not a next page then break
            if first_page:
                first_page = False
            else:
                next_link = page.query_selector("xpath=//a[contains(text(), 'Next')]")
                if not next_link:
                    break
                next_link.click()
                sleep()

            # Row Loop
            data_rows = page.query_selector_all("tr.data-row")
            for data_row in data_rows:
                # Get all immediate <td> children of the parent tr element.
                tds = data_row.query_selector_all(":scope > td")

                file_name, details_link, date = None, None, None
                if account['type'] == "brokerage":
                    file_name, details_link, date = process_brokerage_row(data_row, tds, account)
                elif account['type'] == "bank":
                    file_name, details_link, date = process_bank_row(data_row, tds, account)
                else:
                    file_name, details_link, date = process_eac_row(data_row, tds, account)

                # if date > end_date:
                #     continue
                # elif date < start_date:
                #     done = True
                #     break
                if not details_link:
                    continue
                click_modal_and_save(page, file_name, details_link)
            pass

    # Close the browser
    context.close()
    browser.close()


def schwab_downloader():
    args = docopt(__doc__)
    print(args)
    if args['--version']:
        print(__version__)
        sys.exit(0)

    with sync_playwright() as playwright:
        run(playwright, args)
