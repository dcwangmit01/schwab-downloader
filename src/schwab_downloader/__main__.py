# SPDX-FileCopyrightText: 2023-present David C Wang <dcwangmit01@gmail.com>
#
# SPDX-License-Identifier: MIT
import sys

if __name__ == "__main__":
    from schwab_downloader.cli import schwab_downloader

    sys.exit(schwab_downloader())
