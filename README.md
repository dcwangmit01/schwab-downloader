# Schwab Downloader

[![PyPI - Version](https://img.shields.io/pypi/v/schwab-downloader.svg)](https://pypi.org/project/schwab-downloader)
[![PyPI - Python Version](https://img.shields.io/pypi/pyversions/schwab-downloader.svg)](https://pypi.org/project/schwab-downloader)

-----

**Table of Contents**

- [Installation](#installation)
- [Configuration](#configuration)
- [Usage](#usage)
- [Development](#development)
- [License](#license)

## What it does

Logs into a schwab.com account and downloads data (statements, checks, etc) as PDF files. Supports 2FA authentication and AI assistant debugging.

## Installation

### Prerequisites

1. Install [uv](https://docs.astral.sh/uv/):
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
git clone <repository-url>
cd schwab-downloader
make deps
cp .env.example .env
# Edit .env with your Schwab credentials
make run-local
```

## Configuration

### Credentials

Configure your Schwab credentials using one of these methods:

**Option 1: .env file (Recommended)**
```bash
cp .env.example .env
# Edit .env with your credentials
```

**Option 2: Environment variables**
```bash
export SCHWAB_ID=your_username
export SCHWAB_PASSWORD=your_password
```

**Option 3: Command line**
```bash
uv run schwab-downloader --id=user@domain.com --password=mypassword --year 2024
```

### AI Assistant Integration

The project includes MCP configuration for AI assistant browser control:
- `.cursor/mcp.json`: Configures Playwright MCP server
- Remote debugging enables AI assistants to control the same browser instance
- CDP endpoint provides Chrome DevTools Protocol access on port 9222

## Usage

```bash
# Show help
uv run schwab-downloader --help

# Download data for a specific year
uv run schwab-downloader --year 2024

# Download data for a date range
uv run schwab-downloader --date-range 20240101-20241231

# Enable remote debugging (for AI assistant control)
uv run schwab-downloader --remote-debug --year 2024
```

### 2FA Support

The downloader automatically detects Schwab's 2FA requirements and pauses for verification:

```
2FA REQUIRED: Enter your security code and click Continue
Waiting for verification...
```

Complete the verification in the browser window, and the downloader continues automatically.

### Remote Debugging

Enable enhanced debugging with AI assistants:

```bash
uv run schwab-downloader --remote-debug --year 2024
```

**Features:**
- Chrome DevTools Protocol on port 9222
- AI assistants can control the same browser instance
- Real-time debugging and collaboration
- Access Chrome DevTools at http://localhost:9222

**Example AI assistant workflow:**
```bash
# Start debugging session
uv run schwab-downloader --remote-debug --year 2024

# Ask AI assistant while running:
# "Take a screenshot of the current page"
# "What's the current URL?"
# "Help me debug this error"
```

## Development

This project uses `uv` for dependency management and `make` for common tasks.

```bash
# Install dependencies
make deps

# Run tests
make test

# Format and lint code
make format

# Build package
make build

# Clean up
make clean
```

## License

`schwab-downloader` is distributed under the terms of the [MIT](https://spdx.org/licenses/MIT.html) license.
