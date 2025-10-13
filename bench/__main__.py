"""Entry point for running bench as a module.

Usage:
    python -m bench list --split basic
    python -m bench run --split basic
    python -m bench run --split basic --filter "lang:zh"
    python -m bench run --split basic --verbose
"""
import sys
from bench.core.cli import main

if __name__ == "__main__":
    sys.exit(main())
