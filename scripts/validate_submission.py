#!/usr/bin/env python3
"""Validate a strategy directory's submission package.

Usage:
    python scripts/validate_submission.py strategies/v7

Checks:
  1. main.py is byte-compilable (py_compile).
  2. submission.tar.gz has exactly one root entry: main.py.
  3. main.py inside the tarball has the same SHA-256 as strategies/<v>/main.py.

Prints a JSON result. Exit code 0 == valid, 1 == invalid, 2 == usage error.
"""
from __future__ import annotations

import hashlib
import io
import json
import sys
import tarfile
import tempfile
from pathlib import Path

try:
    import py_compile
except ImportError:  # pragma: no cover - always available on CPython
    py_compile = None


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def root_entries(tar_path: Path) -> list[str]:
    """Return the set of top-level names inside a tar file."""
    names: list[str] = []
    with tarfile.open(tar_path, "r:gz") as tf:
        for member in tf.getmembers():
            name = member.name
            if name.startswith("./"):
                name = name[2:]
            root = name.split("/", 1)[0]
            names.append(root)
    return names


def main() -> int:
    if len(sys.argv) != 2:
        print(json.dumps({"error": "usage: validate_submission.py <strategy_dir>"}, indent=2))
        return 2

    strategy_dir = Path(sys.argv[1]).resolve()
    main_py = strategy_dir / "main.py"
    tarball = strategy_dir / "submission.tar.gz"
    result: dict = {
        "strategy_dir": str(strategy_dir),
        "ok": False,
        "checks": {},
    }

    if not main_py.is_file():
        result["error"] = f"missing main.py in {strategy_dir}"
        print(json.dumps(result, indent=2, ensure_ascii=False))
        return 1
    if not tarball.is_file():
        result["error"] = f"missing submission.tar.gz in {strategy_dir}"
        print(json.dumps(result, indent=2, ensure_ascii=False))
        return 1

    # Check 1: py_compile (write .pyc to a temp dir to avoid polluting the repo)
    try:
        with tempfile.TemporaryDirectory() as tmp:
            py_compile.compile(str(main_py), cfile=str(Path(tmp) / "main.cpython.pyc"), doraise=True)
        result["checks"]["py_compile"] = "ok"
    except py_compile.PyCompileError as exc:  # type: ignore[misc]
        result["checks"]["py_compile"] = f"FAIL: {exc}"
        print(json.dumps(result, indent=2, ensure_ascii=False))
        return 1

    # Check 2: tarball root contains only main.py
    try:
        roots = root_entries(tarball)
    except tarfile.TarError as exc:
        result["checks"]["tarball_root"] = f"FAIL: cannot read tarball ({exc})"
        print(json.dumps(result, indent=2, ensure_ascii=False))
        return 1
    result["tarball_root_entries"] = roots
    if roots == ["main.py"]:
        result["checks"]["tarball_root"] = "ok"
    else:
        result["checks"]["tarball_root"] = f"FAIL: root entries = {roots!r}, expected ['main.py']"
        print(json.dumps(result, indent=2, ensure_ascii=False))
        return 1

    # Check 3: sha256 of main.py inside tarball == sha256 of strategies/<v>/main.py
    try:
        with tarfile.open(tarball, "r:gz") as tf:
            member = tf.getmember("main.py")
            payload = tf.extractfile(member).read()
        tar_sha = sha256_bytes(payload)
    except (tarfile.TarError, KeyError) as exc:
        result["checks"]["sha256_match"] = f"FAIL: cannot extract main.py from tarball ({exc})"
        print(json.dumps(result, indent=2, ensure_ascii=False))
        return 1

    dir_sha = sha256_bytes(main_py.read_bytes())
    result["sha256_main_file"] = dir_sha
    result["sha256_main_in_tar"] = tar_sha
    if dir_sha == tar_sha:
        result["checks"]["sha256_match"] = "ok"
    else:
        result["checks"]["sha256_match"] = f"FAIL: strategy main.py {dir_sha} != tar main.py {tar_sha}"
        print(json.dumps(result, indent=2, ensure_ascii=False))
        return 1

    result["ok"] = True
    print(json.dumps(result, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
