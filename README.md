# **who‑calls**

> *Who calls my function?* — A tiny static *caller‑tree* explorer for Python.

`who‑calls` scans a project’s source code with the built‑in `ast` module,
builds a directed call‑graph (`caller → callee`), and prints every
call‑path that can reach a target function. Output is an ASCII tree whose
nodes are **clickable file‑and‑line references** in most modern
terminals and IDEs.

```
├── main @ app/entry.py:28
│   └── orchestrate @ app/tasks/flow.py:71
│       └── do_work @ app/worker.py:42  <─ target
└── cli_entry @ app/cli.py:13
    └── do_work @ app/worker.py:42  <─ target
```

---

## ✨ Features

* **Static analysis** only – no code execution, so it’s safe to run on
  untrusted repos or in CI.
* **Clickable labels** – format `func @ path.py:LINE` so VS Code,
  PyCharm, Zed, etc. jump straight to the definition.
* **Regex‑based exclusion** – skip vendored or generated code
  (`.git`, `.venv`, `.cache`, `tests` by default).
* Detects `self.method()` / `cls.method()` calls inside classes.
* Clear error on ambiguous target names; accepts fully‑qualified
  `package.module:Class.method` style.

---

## 🚀 Installation (with UV)

```bash
uv pip install who‑calls
```

> **UV?** [uv](https://github.com/astral‑sh/uv) is a super‑fast drop‑in
> replacement for *pip* + *virtualenv*. If you prefer stock tools, replace
> `uv pip` with `pip`.

### Dev / editable install

```bash
uv venv .venv && source .venv/bin/activate
uv pip install -e .[dev]
```

---

## 🛠️ CLI usage

```bash
who‑calls <function> [OPTIONS]

Options:
  --root DIR         Project root (default: current directory)
  --exclude REGEX    Regex of paths to ignore (default: \\ .git | .venv | .cache | tests)
```

Examples:

```bash
# show who can reach do_work()
who‑calls do_work

# fully‑qualified target
who‑calls app.worker.do_work

# scan ./src and ignore build folder
who‑calls process_order --root src --exclude "build|dist"
```

If the short name matches multiple symbols you’ll get:

```
⚠ Ambiguous function name. Matches:
  • app.utils.filters:create_filter
  • app.api.v1.picking_filters.queries:create_filter
Please specify full path like <module>.<func> or <module>.<Class>.<method>.
```

---

## 🔍 How it works (high‑level)

1. Recursively collect `*.py` files below `--root`, apply `--exclude`.
2. Parse each file with `ast.parse`.
3. Record every `FunctionDef` / `AsyncFunctionDef` with a fully‑qualified
   dotted name (`pkg.mod.Class.func`).
4. Discover call edges:

   * `foo()` → unique match by name.
   * `self.foo()` / `cls.foo()` → method on same class.
   * `obj.foo()` → falls back to unique global match.
5. Build a `networkx.DiGraph`, reverse it, keep only ancestors that can
   reach the target, then pretty‑print.

---

## 📦 Project structure

```
who‑calls/
├── pyproject.toml          # uv build backend
└── who_calls/
    ├── __init__.py         # exposes who_calls.main
    └── cli.py              # core logic (ast + networkx)
```

---

## 🖋️ License

MIT © 2025  *janbjorge*
