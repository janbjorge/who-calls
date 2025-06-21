import re
from pathlib import Path
import sys
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from who_calls import build_call_graph, print_caller_tree


def write(path: Path, text: str) -> None:
    path.write_text(text)


def test_build_simple_call(tmp_path: Path) -> None:
    f = tmp_path / "mod.py"
    write(
        f,
        """
def a():
    b()


def b():
    pass
""",
    )
    cg = build_call_graph(tmp_path, re.compile("$^"))
    assert "mod.a" in cg.graph
    assert "mod.b" in cg.graph
    assert cg.graph.has_edge("mod.a", "mod.b")


def test_build_method_call(tmp_path: Path) -> None:
    f = tmp_path / "m.py"
    write(
        f,
        """
class Foo:
    def m1(self):
        self.m2()

    def m2(self):
        pass
""",
    )
    cg = build_call_graph(tmp_path, re.compile("$^"))
    assert "m.Foo.m1" in cg.graph
    assert "m.Foo.m2" in cg.graph
    assert cg.graph.has_edge("m.Foo.m1", "m.Foo.m2")


def test_cross_file_call(tmp_path: Path) -> None:
    write(
        tmp_path / "a.py",
        """
from b import bar

def foo():
    bar()
""",
    )
    write(
        tmp_path / "b.py",
        """
def bar():
    pass
""",
    )
    cg = build_call_graph(tmp_path, re.compile("$^"))
    assert cg.graph.has_edge("a.foo", "b.bar")


def test_print_caller_tree_not_found(tmp_path: Path) -> None:
    write(tmp_path / "x.py", "def f():\n    pass\n")
    cg = build_call_graph(tmp_path, re.compile("$^"))
    with pytest.raises(SystemExit):
        print_caller_tree(cg, "missing")


def test_print_caller_tree_ambiguous(tmp_path: Path) -> None:
    write(
        tmp_path / "x.py",
        """
def foo():
    pass
""",
    )
    write(
        tmp_path / "y.py",
        """
def foo():
    pass
""",
    )
    cg = build_call_graph(tmp_path, re.compile("$^"))
    with pytest.raises(SystemExit):
        print_caller_tree(cg, "foo")


def test_filtered(tmp_path: Path) -> None:
    write(tmp_path / "z.py", "def a():\n    pass\n")
    cg = build_call_graph(tmp_path, re.compile("$^"))
    filtered = cg.filtered(re.compile("nomatch"))
    assert len(filtered.graph) == 0


def test_label(tmp_path: Path) -> None:
    f = tmp_path / "lab.py"
    write(f, "def a():\n    pass\n")
    cg = build_call_graph(tmp_path, re.compile("$^"))
    label = cg.label("lab.a")
    assert label.startswith("a @ ") and label.endswith(":1")
