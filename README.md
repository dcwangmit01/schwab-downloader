# Schwab Downloader

[![PyPI - Version](https://img.shields.io/pypi/v/schwab-downloader.svg)](https://pypi.org/project/schwab-downloader)
[![PyPI - Python Version](https://img.shields.io/pypi/pyversions/schwab-downloader.svg)](https://pypi.org/project/schwab-downloader)

> **⚠️ Important Note**: This program was last tested and verified to work in August 2025. Schwab.com occasionally updates their website interface, which may require code updates to maintain compatibility. If you encounter issues, please consider submitting a pull request with fixes.

-----

**Table of Contents**

- [Installation](#installation)
- [Configuration](#configuration)
- [Usage](#usage)
- [Development](#development)
- [License](#license)

## What it does

This tool automates the process of downloading statements and transaction history data from Schwab.com accounts. It uses Playwright to control a web browser, logs into a Schwab account, navigates to both the statements and transaction history pages, and downloads individual documents as PDF files. It supports multiple account types including brokerage, IRA, DAF (Donor Advised Fund), EAC (Equity Award Center), and bank accounts. It can process data within specified date ranges and saves files with descriptive names that include account information, document dates, types, and amounts. The tool also includes support for two-factor authentication and can cache account information to avoid repeated web scraping.

## Installation

### Prerequisites

1. **Python 3.13+**: This project requires Python 3.13 or later.

2. **Install [uv](https://docs.astral.sh/uv/)** for dependency management:
   ```bash
   # macOS
   brew install uv
   ```

3. **Install Playwright browsers**:
   ```bash
   uv run playwright install
   ```

### Quick Start

```bash
git clone <repository-url>
cd schwab-downloader
make deps
# Configure your Schwab credentials (see Configuration section below)
make run-local
```

## Configuration

### Credentials

Configure your Schwab credentials using one of these methods:

**Option 1: .env file (Recommended)**
```bash
# Create a .env file in the project root with your credentials
echo "SCHWAB_ID=your_username" > .env
echo "SCHWAB_PASSWORD=your_password" >> .env
```

**Option 2: Environment variables**
```bash
export SCHWAB_ID=your_username
export SCHWAB_PASSWORD=your_password
```

**Option 3: Command line**
```bash
uv run schwab-downloader --id=your_username --password=your_password --year 2024
```

### AI Assistant Development

The project includes remote debugging capabilities for development workflows:
- Remote debugging enables AI assistants to control the same browser instance during development
- CDP endpoint provides Chrome DevTools Protocol access on port 9222
- AI MCP assistants can interact with the browser for debugging and development purposes
- This feature is for development only and not used in normal operation

## Usage

```bash
# Show help
uv run schwab-downloader --help

# Download transaction history for a specific year
uv run schwab-downloader --year 2024

# Download transaction history for a date range
uv run schwab-downloader --date-range 20240101-20241231

# Enable remote debugging (for AI assistant control)
uv run schwab-downloader --remote-debug --year 2024

# Use custom cache file location
uv run schwab-downloader --cache-accounts=my_accounts.json --year 2024

# Force refresh of account cache from web
uv run schwab-downloader --refresh-cache --year 2024
```

### 2FA Support

The downloader automatically detects Schwab's identity confirmation requirements and pauses for verification:

```
2FA REQUIRED: Enter your security code and click Continue
Waiting for verification...
```

Complete the verification in the browser window, and the downloader continues automatically.

### File Naming

Downloaded files are saved with descriptive names that include:
- Account type (brokerage, IRA, DAF, EAC, bank)
- Account number (last 4 digits for most accounts)
- Account nickname
- Document/transaction date
- Document/transaction type
- Amount (for financial transactions)
- Description/document name

**Transaction Examples:**
- `schwab_brokerage_1234_MyAccount_20241201_Dividend_150.00_StockDividend.pdf`
- `schwab_bank_5678_Checking_20241201_Check_250.00_1234.pdf`

**Statement Examples:**
- `schwab_brokerage_1234_MyAccount_20241201_Statement_MonthlyStatement.pdf`
- `schwab_IRA_9876_Retirement_20241201_1099_TaxDocument.pdf`

### Remote Debugging

Enable enhanced debugging for development workflows:

```bash
uv run schwab-downloader --remote-debug --year 2024
```

**Features:**
- Chrome DevTools Protocol on port 9222
- AI assistants can control the same browser instance for development
- Real-time debugging and development collaboration
- Access Chrome DevTools at http://localhost:9222

**Example development workflow:**
```bash
# Start debugging session
uv run schwab-downloader --remote-debug --year 2024

# During development, AI assistants can help with:
# "Take a screenshot of the current page"
# "What's the current URL?"
# "Help me debug this error"
# "Click on the next page button"
```

## Development

This project uses `uv` for dependency management and `make` for common tasks.

### Available Make Targets

```bash
# Install all dependencies (OS, development, and Python packages)
make deps

# Install just Python dependencies
make deps-uv

# Run tests
make test

# Auto-format and check code style via pre-commit
make format

# Run local instance with current year
make run-local

# Build the package
make build

# Clean build artifacts
make clean

# Complete cleanup (removes .venv and uv.lock)
make mrclean

# Show all available targets
make help
```

### Dependencies

The project dependencies are managed through:
- **Runtime**: `pyproject.toml` (docopt, playwright, playwright-stealth, ipdb, python-dotenv)
- **Development**: `dependency-groups.dev` in `pyproject.toml` (black, coverage, mypy, pytest)
- **OS**: Managed via Homebrew on macOS (uv)

## License

`schwab-downloader` is distributed under the terms of the [MIT](https://spdx.org/licenses/MIT.html) license.
