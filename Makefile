.DEFAULT_GOAL := help
SHELL := /usr/bin/env bash

UNAME_S := $(shell uname -s)
PYENV_NAME := $(notdir $(CURDIR))
PYTHON_VERSION := 3.11.4

BREW_PACKAGES := pre-commit
BREW_CASKS :=

PYTHON_PACKAGES := playwright

PYTHON_FILES = $(shell find * -type f -name *.py)

.PHONY: format
format: check  ## Auto-format and check pep8

.PHONY: deps
deps: deps-os deps-dev deps-pyenv  ## Ensure OS Dependencies (Only works for MacOS)

.PHONY: deps-os
deps-os:  ## Ensure OSX Dependencies
ifeq ($(UNAME_S),Darwin)
	@# Check only for MacOS

	@# Check brew-install dependencies
	@for package in $(BREW_PACKAGES); do \
	  if brew list --versions $$package > /dev/null; then \
	    echo "$$package is already installed."; \
	  else \
	    echo "$$package is not installed.  Installing via brew."; \
	    brew install $$package; \
	  fi; \
	done
	@for cask in $(BREW_CASKS); do \
	  if brew list --cask --versions $$cask > /dev/null; then \
	    echo "$$cask is already installed."; \
	  else \
	    echo "$$cask is not installed. Installing via brew cask."; \
	    brew install --cask $$cask; \
	  fi; \
	done

	@# Check if pyenv is activated in the user shell
	@# If not, use the message from pyenv init and pyenv virtualenv-init to
	@# provide instructions for the user
	@if [ -z "$$PYENV_SHELL" ]; then \
	  pyenv init; \
	  exit 1; \
	fi
	@if [ -z "$$PYENV_VIRTUALENV_INIT" ]; then \
	  pyenv virtualenv-init; \
	  exit 1; \
	fi
endif

.PHONY: deps-dev
deps-dev:  ## Ensure development dependencies
	pre-commit install
	pre-commit install-hooks

.PHONY: deps-pyenv
deps-pyenv:  ## Create the pyenv for Python development
	@if ! pyenv versions | grep $(PYTHON_VERSION) 2>&1 > /dev/null; then \
	  pyenv install $(PYTHON_VERSION); \
	fi
	@if ! pyenv virtualenvs | grep $(PYENV_NAME) 2>&1 > /dev/null; then \
	  pyenv virtualenv $(PYTHON_VERSION) $(PYENV_NAME); \
	fi
	@if ! pyenv local 2>&1 > /dev/null; then \
	  pyenv local $(PYENV_NAME); \
	fi
	@PIP_FREEZE_OUT=$$(pip freeze) && \
	for dep in $(PYTHON_PACKAGES); do \
	  if ! echo "$$PIP_FREEZE_OUT" | grep $$dep 2>&1 > /dev/null; then pip install $$dep; fi; \
	done
	python -m pip install --upgrade pip

.PHONY: check
check:  ## Auto-check and format via pre-commit
	pre-commit run --all-files

.PHONY: install-local
install-local:  ## Install the program in the currently active python env
	pip install --editable .

.PHONY: run-local
run-local:  ## Run the program for this year
	schwab-downloader --year 2024

.PHONY: run
run:  ## Run a few examples
	hatch run schwab-downloader --year 2024
	hatch run schwab-downloader --date-range 20230131-20221201
	hatch run schwab-downloader --email=user@domain.com --password=mypassword

.PHONY: build
build:  ## Build the project
	hatch build

.PHONY: clean
clean:  ## Clean the project
	hatch clean
	find * -type d -name __pycache__ | xargs rm -rf

.PHONY: mrclean
mrclean: clean  ## Really clean the project (except downloads)
	pyenv virtualenv-delete --force $(PYENV_NAME)
	rm -f .python-version

.PHONY: help
help:  ## Print list of Makefile targets
	@# Taken from https://github.com/spf13/hugo/blob/master/Makefile
	@grep --with-filename -E '^[a-zA-Z0-9_-]+:.*?## .*$$' $(MAKEFILE_LIST) | \
	  cut -d ":" -f2- | \
	  awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-30s\033[0m %s\n", $$1, $$2}' | sort
