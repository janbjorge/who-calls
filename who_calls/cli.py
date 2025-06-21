"""Command line interface for ``who-calls``."""

from __future__ import annotations

import argparse
import re
import pathlib

from who_calls import build_call_graph, print_caller_tree

DEFAULT_EXCLUDE = re.compile(r"\.git|\.venv|\.cache|tests")


# ─────────────────────────────────────────────────────────────
#  Main
# ─────────────────────────────────────────────────────────────


def main() -> None:
    """Entry point for the ``who-calls`` command line interface."""

    ap = argparse.ArgumentParser(
        description="Static caller tree explorer",
    )
    ap.add_argument(
        "function",
        help="target function name (or fully‑qualified)",
    )
    ap.add_argument(
        "--root",
        default=".",
        help="source root directory",
    )
    ap.add_argument(
        "--exclude",
        default=DEFAULT_EXCLUDE.pattern,
        help="regex of paths to ignore (default: %(default)s)",
    )
    ap.add_argument(
        "--only",
        default=None,
        help="regex of dotted names to include in the graph",
    )
    args = ap.parse_args()

    rx = re.compile(args.exclude)
    graph = build_call_graph(pathlib.Path(args.root), rx)
    if args.only:
        graph = graph.filtered(re.compile(args.only))
    print_caller_tree(graph, args.function)


if __name__ == "__main__":
    main()
