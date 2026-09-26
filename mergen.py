#!/usr/bin/env python3
"""Direct entrypoint to launch MergenDB interactive CLI."""
import sys
import os

# Add local package to sys.path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from mergendb.cli.repl import main

if __name__ == "__main__":
    main()
