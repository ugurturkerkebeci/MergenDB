"""
MergenDB CLI and Server Executable Entry Point.

Enables running directly via Python module execution:
    python -m mergendb
    python -m mergendb serve 8765
    python -m mergendb query "SELECT * FROM users.mgdb"
    python -m mergendb test
    python -m mergendb benchmark
"""
import sys
from mergendb.cli.repl import main

if __name__ == "__main__":
    main()
