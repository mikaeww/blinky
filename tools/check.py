#!/usr/bin/env python3
"""The one check command: structure limits, Python lint, tests, QML lint. Stops at the first failure.

Not here: a formatter. There is none without adding a dependency (docs/decisions/0001).
"""

import ast
import os
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SKIP_DIRS = {".git", "__pycache__", "node_modules", "build"}
CODE_SUFFIXES = {".py", ".qml", ".js"}
ENTRY_FILES = {"__init__.py", "__main__.py", "qmldir"}
FORBIDDEN_NAMES = {"utils", "util", "helpers", "helper", "misc", "common", "stuff", "shared"}
MAX_FILE_LINES, MAX_CODE_FILES, MAX_DOCS, MAX_FUNC_LINES, MAX_PARAMS = 500, 8, 8, 60, 5
QMLLINT = shutil.which("qmllint") or shutil.which("qmllint6") or "/usr/lib/qt6/bin/qmllint"


def walk():
    for directory, subdirs, files in os.walk(ROOT, followlinks=False):
        subdirs[:] = sorted(d for d in subdirs if d not in SKIP_DIRS)
        yield Path(directory), sorted(files)


def structure_errors() -> tuple[list[str], int]:
    errors, checked = [], 0
    for directory, files in walk():
        code = [f for f in files if Path(f).suffix in CODE_SUFFIXES and f not in ENTRY_FILES and not f.startswith("test_")]
        if len(code) > MAX_CODE_FILES:
            errors.append(f"{directory}: {len(code)} code files > {MAX_CODE_FILES}")
        docs = [f for f in files if f.endswith(".md")]
        if directory.is_relative_to(ROOT / "docs") and len(docs) > MAX_DOCS:
            errors.append(f"{directory}: {len(docs)} markdown files > {MAX_DOCS}")
        for name in files:
            path = directory / name
            if path.is_symlink() or path.suffix not in CODE_SUFFIXES | {".md", ".toml", ""}:
                continue
            checked += 1
            if path.stem in FORBIDDEN_NAMES:
                errors.append(f"{path}: forbidden module name")
            lines = path.read_text(errors="replace").count("\n")
            if lines > MAX_FILE_LINES:
                errors.append(f"{path}: {lines} lines > {MAX_FILE_LINES}")
            if path.suffix == ".py":
                errors += python_errors(path)
    return errors, checked


def python_errors(path: Path) -> list[str]:
    errors = []
    tree = ast.parse(path.read_text(), str(path))
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            length = node.end_lineno - node.lineno + 1
            if length > MAX_FUNC_LINES:
                errors.append(f"{path}:{node.lineno} {node.name}: {length} lines > {MAX_FUNC_LINES}")
            params = [a for a in node.args.args + node.args.kwonlyargs if a.arg not in ("self", "cls")]
            if len(params) > MAX_PARAMS:
                errors.append(f"{path}:{node.lineno} {node.name}: {len(params)} params > {MAX_PARAMS}")
        if isinstance(node, ast.ExceptHandler) and node.type is None:
            errors.append(f"{path}:{node.lineno}: bare except")
    return errors


def run(step: str, command: list[str]) -> None:
    print(f"== {step}", flush=True)
    if subprocess.run(command, cwd=ROOT).returncode != 0:
        sys.exit(f"check failed at: {step}")


def main() -> None:
    os.nice(19)
    print("== structure", flush=True)
    errors, checked = structure_errors()
    for error in errors:
        print(error)
    if errors:
        sys.exit("check failed at: structure")
    print(f"{checked} files checked, symlinks and {sorted(SKIP_DIRS)} skipped")
    run("compile", [sys.executable, "-m", "compileall", "-q", "src", "tools", "tests"])
    run("compile bin/blinky", [sys.executable, "-m", "py_compile", "bin/blinky"])
    run("tests", [sys.executable, "-m", "unittest", "discover", "-s", "tests", "-q"])
    if not Path(QMLLINT).exists():
        sys.exit("check failed: qmllint not found (Qt 6 declarative tools)")
    qml = sorted(str(p.relative_to(ROOT)) for p in (ROOT / "quickshell").rglob("*.qml"))
    run("qmllint", [QMLLINT, "-I", "quickshell", *qml])
    print("all checks passed")


if __name__ == "__main__":
    main()
