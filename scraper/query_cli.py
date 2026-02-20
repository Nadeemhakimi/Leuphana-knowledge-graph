#!/usr/bin/env python3
"""
Leuphana Knowledge Graph - Query CLI

Simple command-line interface for querying the knowledge graph.

Usage:
    python query_cli.py                          # Interactive mode
    python query_cli.py "What are the schools?"  # Direct question
    python query_cli.py --list                   # List available queries

Author: Bachelor's Thesis Project
"""

import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent))

from query_interface import PredefinedQueryHandler, interactive_mode


def main():
    """Main entry point for query CLI."""
    # Initialize handler
    try:
        handler = PredefinedQueryHandler()
    except Exception as e:
        print(f"Error: Could not initialize query handler: {e}")
        print("\nMake sure GraphDB is running and credentials are set in .env file")
        return 1

    try:
        # Check command line args
        if len(sys.argv) > 1:
            arg = sys.argv[1]

            if arg in ("--list", "-l", "list"):
                print("\nAvailable queries:")
                print("-" * 50)
                for q in handler.list_queries():
                    print(f"  {q['id']:25} {q['description']}")
                print()
                return 0

            elif arg in ("--help", "-h", "help"):
                print(__doc__)
                print("\nExamples:")
                print('  python query_cli.py "What are all the schools?"')
                print('  python query_cli.py "Find professors in sustainability"')
                print('  python query_cli.py "Show statistics"')
                print()
                return 0

            else:
                # Treat as a question
                question = " ".join(sys.argv[1:])
                try:
                    result = handler.answer(question)
                    print(f"\n{result.description}")
                    print(f"Found {result.count} results\n")
                    print(result.format_table())
                except ValueError as e:
                    print(f"\n{e}")
                    return 1

        else:
            # Interactive mode
            interactive_mode(handler)

    finally:
        handler.close()

    return 0


if __name__ == "__main__":
    sys.exit(main())