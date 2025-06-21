from __future__ import annotations
import argparse
import re
import pathlib

from who_calls import who_calls

DEFAULT_EXCLUDE = re.compile(r"\.git|\.venv|\.cache|tests")


# ─────────────────────────────────────────────────────────────
#  Main
# ─────────────────────────────────────────────────────────────
#
def main() -> None:
    ap = argparse.ArgumentParser(description="Static caller tree explorer")
    ap.add_argument("function", help="target function name (or fully‑qualified)")
    ap.add_argument("--root", default=".", help="source root directory")
    ap.add_argument(
        "--exclude",
        default=DEFAULT_EXCLUDE.pattern,
        help="regex of paths to ignore (default: %(default)s)",
    )
    args = ap.parse_args()

    rx = re.compile(args.exclude)
    g, srcm, linem = who_calls.build_call_graph(pathlib.Path(args.root), rx)
    who_calls.print_caller_tree(g, srcm, linem, args.function)


if __name__ == "__main__":
    main()
