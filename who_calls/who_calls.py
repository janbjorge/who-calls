#!/usr/bin/env python3
# requirements: networkx
"""
calltree_ast.py — static caller‑tree explorer (AST + NetworkX)
==============================================================

    python calltree_ast.py <function> [--root SRC] [--exclude REGEX]

The script prints every *static* call‑path that can reach the requested
function.  Paths are filtered with a user‑supplied regular expression
(default skips `.git`, `.venv`, `.cache`, `tests`).

Each node is formatted so editors can Ctrl‑click:

    func_name @ path/to/file.py:LINE

The leaf marked "<─ target" is the function you asked for.
"""

from __future__ import annotations

import ast
import pathlib
import re
import sys

import networkx as nx

# ─────────────────────────────────────────────────────────────
#  Build directed graph caller ──▶ callee
# ─────────────────────────────────────────────────────────────


def build_call_graph(root: pathlib.Path, rx_exclude: re.Pattern):
    graph = nx.DiGraph()
    defs: dict[str, ast.AST] = {}
    src_map: dict[str, pathlib.Path] = {}
    line_map: dict[str, int] = {}

    for path in root.rglob("*.py"):
        rel = path.relative_to(root).as_posix()
        if rx_exclude.search(rel):
            continue
        try:
            tree = ast.parse(path.read_text(errors="ignore"))
        except SyntaxError:
            continue
        module = ".".join(path.relative_to(root).with_suffix("").parts)

        class Collector(ast.NodeVisitor):
            def __init__(self):
                self.cls: list[str] = []

            def visit_ClassDef(self, node):
                self.cls.append(node.name)
                self.generic_visit(node)
                self.cls.pop()

            def _add(self, node):
                q = module + "." + ".".join(self.cls + [node.name])
                defs[q] = node
                src_map[q] = path
                line_map[q] = node.lineno
                graph.add_node(q)
                self.generic_visit(node)

            visit_FunctionDef = _add
            visit_AsyncFunctionDef = _add

        Collector().visit(tree)

    # add edges (caller → callee)
    for caller, fnode in defs.items():
        caller_prefix = ".".join(caller.split(".")[:-1])
        for n in ast.walk(fnode):
            if not isinstance(n, ast.Call):
                continue
            callee_candidates: list[str] = []
            # foo()
            if isinstance(n.func, ast.Name):
                callee_candidates = [d for d in defs if d.endswith("." + n.func.id)]
            # obj.foo() / self.foo()
            elif isinstance(n.func, ast.Attribute):
                attr = n.func.attr
                if isinstance(n.func.value, ast.Name) and n.func.value.id in {
                    "self",
                    "cls",
                }:
                    same_cls = caller_prefix + "." + attr
                    if same_cls in defs:
                        callee_candidates = [same_cls]
                if not callee_candidates:
                    callee_candidates = [d for d in defs if d.endswith("." + attr)]
            # link: prefer same‑package; otherwise all matches
            if callee_candidates:
                same_pkg = [c for c in callee_candidates if c.startswith(caller_prefix)]
                for callee in same_pkg or callee_candidates:
                    graph.add_edge(caller, callee)

    return graph, src_map, line_map


# ─────────────────────────────────────────────────────────────
#  Label & pretty print caller tree
# ─────────────────────────────────────────────────────────────


def label(node: str, src: dict[str, pathlib.Path], line: dict[str, int]) -> str:
    func = node.split(".")[-1]
    file = src.get(node, pathlib.Path("?"))
    return f"{func} @ {file.as_posix()}:{line.get(node, 1)}"


def print_caller_tree(
    graph: nx.DiGraph, src: dict[str, pathlib.Path], line: dict[str, int], target: str
):
    matches = [n for n in graph if n.endswith("." + target) or n == target]
    if not matches:
        sys.exit(f"✘ function '{target}' not found")
    if len(matches) > 1:
        print("⚠ Ambiguous function name. Matches:")
        for m in matches:
            print("  •", m)
        print(
            "Please specify full path like <module>.<func> or <module>.<Class>.<method>."
        )
        sys.exit(1)
    tgt = matches[0]

    anc = {n for n in graph if nx.has_path(graph, n, tgt)}
    roots = sorted(n for n in anc if not any(p in anc for p in graph.predecessors(n)))

    def walk(node: str, prefix: str = "", last: bool = True):
        branch = "└── " if last else "├── "
        mark = "  <─ target" if node == tgt else ""
        print(prefix + branch + label(node, src, line) + mark)
        kids = sorted(c for c in graph.successors(node) if c in anc)
        for i, k in enumerate(kids):
            walk(k, prefix + ("    " if last else "│   "), i == len(kids) - 1)

    for i, r in enumerate(roots):
        walk(r, "", i == len(roots) - 1)
