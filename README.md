# who-calls

A minimal utility for discovering which functions lead to a given symbol.  It scans Python source code using the standard `ast` module, builds a call graph with `networkx` and prints every path that reaches the target.  Each node is shown as `func @ path.py:LINE` so most editors can jump straight there.

```
├── main @ app/entry.py:28
│   └── orchestrate @ app/tasks/flow.py:71
│       └── do_work @ app/worker.py:42  <─ target
└── cli_entry @ app/cli.py:13
    └── do_work @ app/worker.py:42  <─ target
```

## Features

- Works purely via static analysis, so it is safe for untrusted code.
- Labels are clickable in terminals that support file:line hyperlinks.
- Unwanted files can be skipped with a regular expression (defaults to `.git`, `.venv`, `.cache`, `tests`).
- Knows about `self.method()` and `cls.method()` calls inside classes.
- Warns when a short name is ambiguous and accepts fully qualified targets.

## Requirements

- Python 3.11+
- `networkx` 3.x

## Installation

Using [uv](https://github.com/astral-sh/uv):

```bash
uv pip install who-calls
```

Or with stock tools:

```bash
pip install who-calls
```

For development you can create a virtual environment and install the project in editable mode:

```bash
uv venv .venv && source .venv/bin/activate
uv pip install -e .[dev]
```

## Command line usage

```bash
who-calls <function> [--root DIR] [--exclude REGEX]
```

Examples:

```bash
# all callers of do_work()
who-calls do_work

# specify the fully qualified symbol
who-calls app.worker.do_work

# look only under ./src and ignore build outputs
who-calls process_order --root src --exclude "build|dist"
```

If several symbols match the given name you will see a list of choices and must supply the full dotted path.

## How it works

1. Recursively collect every `*.py` file under `--root`, skipping files that match `--exclude`.
2. Parse the files with `ast.parse` and record every function and method with its module path and line number.
3. Inspect call sites to link callers to callees.  Attribute calls on `self` or `cls` resolve to methods on the same class; other attributes fall back to a global match if unique.
4. Build a directed graph from caller to callee with `networkx`.
5. Reverse the graph and print only the ancestors that can reach the selected function.

## Project layout

```
who-calls/
├── pyproject.toml
└── who_calls/
    ├── who_calls.py
    └── cli.py
```

## License

MIT © 2025 janbjorge
