# Schwab Downloader

[![PyPI - Version](https://img.shields.io/pypi/v/schwab-downloader.svg)](https://pypi.org/project/schwab-downloader)
[![PyPI - Python Version](https://img.shields.io/pypi/pyversions/schwab-downloader.svg)](https://pypi.org/project/schwab-downloader)

-----

**Table of Contents**

- [Installation](#installation)
- [Development Setup](#development-setup)
- [Usage](#usage)
- [License](#license)

## What it does

Logs into a schwab.com account and downloads data (statements, checks, etc) as PDF files.

## Installation

### Prerequisites

1. Install [uv](https://docs.astral.sh/uv/) (Python package manager):
   ```bash
   # macOS
   brew install uv

   # Linux
   curl -LsSf https://astral.sh/uv/install.sh | sh
   ```

2. Install Playwright browsers:
   ```bash
   uv run playwright install
   ```

### Quick Start

```bash
# Clone the repository
git clone <repository-url>
cd schwab-downloader

# Install dependencies and setup development environment
make deps

# Run the application
make run-local
```

## Development Setup

This project uses `uv` for dependency management and `make` for common development tasks.

### Initial Setup

```bash
# Install all dependencies (OS packages, Python packages, development tools)
make deps

# This will:
# - Install uv and other system dependencies
# - Create a Python virtual environment
# - Install Python packages
# - Setup pre-commit hooks
```

### Common Development Tasks

```bash
# Run tests
make test

# Format and lint code
make format

# Check code quality
make lint

# Build the package
make build

# Clean up
make clean

# Full cleanup (removes virtual environment)
make mrclean
```

### Environment Variables

Create a `.envrc` file (not tracked in git) with your Schwab credentials:

```bash
export SCHWAB_ID=your_username
export SCHWAB_PASSWORD=your_password
```

## Usage

```bash
# Show help
uv run schwab-downloader --help

# Download data for a specific year
uv run schwab-downloader --year 2024

# Download data for a date range
uv run schwab-downloader --date-range 20240101-20241231

# Use specific credentials
uv run schwab-downloader --id=user@domain.com --password=mypassword
```

## License

`schwab-downloader` is distributed under the terms of the [MIT](https://spdx.org/licenses/MIT.html) license.
