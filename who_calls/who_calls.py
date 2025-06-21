#!/usr/bin/env python3
# requirements: networkx
"""Static caller tree explorer.

This module provides the core logic for building a static call graph for a
Python project using :mod:`ast` and :mod:`networkx`.  It can then print every
call path that reaches a requested function.  The printing format is compatible
with most modern editors so that file references can be clicked.
"""

from __future__ import annotations

import ast
import pathlib
import re
import sys
from dataclasses import dataclass


import networkx as nx


@dataclass(slots=True)
class CallGraph:
    """Call graph with source metadata for each discovered function."""

    graph: nx.DiGraph
    src: dict[str, pathlib.Path]
    lines: dict[str, int]

    def filtered(self, pattern: re.Pattern[str]) -> "CallGraph":
        """Return a new graph keeping only nodes matching ``pattern``."""
        nodes = [n for n in self.graph if pattern.search(n)]
        sub = self.graph.subgraph(nodes).copy()
        src = {k: v for k, v in self.src.items() if k in nodes}
        lines = {k: v for k, v in self.lines.items() if k in nodes}
        return CallGraph(graph=sub, src=src, lines=lines)

    def label(self, node: str) -> str:
        """Return ``"func @ file:line"`` for ``node``."""
        func = node.split(".")[-1]
        file = self.src.get(node, pathlib.Path("?"))
        return f"{func} @ {file.as_posix()}:{self.lines.get(node, 1)}"


# ─────────────────────────────────────────────────────────────
#  Build directed graph caller ──▶ callee
# ─────────────────────────────────────────────────────────────


def build_call_graph(root: pathlib.Path, rx_exclude: re.Pattern) -> CallGraph:
    """Scan ``root`` and return a :class:`CallGraph` of all discovered calls."""

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

    return CallGraph(graph=graph, src=src_map, lines=line_map)


# ─────────────────────────────────────────────────────────────
#  Pretty print caller tree
# ─────────────────────────────────────────────────────────────


def print_caller_tree(cgraph: CallGraph, target: str) -> None:
    """Print all call paths in ``cgraph`` that reach ``target``."""

    graph = cgraph.graph
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
        print(prefix + branch + cgraph.label(node))
        kids = sorted(c for c in graph.successors(node) if c in anc)
        for i, k in enumerate(kids):
            walk(k, prefix + ("    " if last else "│   "), i == len(kids) - 1)

    for i, r in enumerate(roots):
        walk(r, "", i == len(roots) - 1)
