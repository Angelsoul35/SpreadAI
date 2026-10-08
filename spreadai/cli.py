"""SpreadAI command-line demo."""

from __future__ import annotations

import argparse
import json

from .generate import make_statement, render_text
from .service import SpreadService


def demo(seed: int = 7) -> None:
    """Generate a statement, spread it, and print the result."""
    statement = make_statement(seed)
    text = render_text(statement)
    print("=== Generated statement (text) ===")
    print(text)
    print("\n=== Spread result ===")
    result = SpreadService().spread_text(text)
    print(f"method: {result['method']}")
    print(f"summary: {json.dumps(result['summary'], indent=2)}")
    print(f"ratios: {json.dumps(result['ratios'], indent=2)}")
    print(f"validation: {json.dumps(result['validation'], indent=2)}")
    print(f"needs_human_review: {result['needs_human_review']}")
    print("\n=== Credit memo ===")
    print(result["memo"])


def main() -> None:
    parser = argparse.ArgumentParser(description="SpreadAI CLI")
    sub = parser.add_subparsers(dest="command", required=True)
    demo_parser = sub.add_parser("demo", help="run an end-to-end demo")
    demo_parser.add_argument("--seed", type=int, default=7)
    args = parser.parse_args()
    if args.command == "demo":
        demo(args.seed)


if __name__ == "__main__":
    main()
