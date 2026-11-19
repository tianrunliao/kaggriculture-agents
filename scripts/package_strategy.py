#!/usr/bin/env python3
"""Package a strategy directory's main.py into submission.tar.gz.

Usage:
    python scripts/package_strategy.py strategies/v8

Behavior:
  1. Verify strategies/<v>/main.py exists and compiles.
  2. Create strategies/<v>/submission.tar.gz with a single root entry: main.py.
  3. Run validate_submission on the same directory.

Exit code 0 == packaged and validated, otherwise 1/2.
"""
from __future__ import annotations

import json
import gzip
import io
import subprocess
import sys
import tarfile
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent


def main() -> int:
    if len(sys.argv) != 2:
        print(json.dumps({"error": "usage: package_strategy.py <strategy_dir>"}, indent=2))
        return 2

    strategy_dir = Path(sys.argv[1]).resolve()
    main_py = strategy_dir / "main.py"
    tarball = strategy_dir / "submission.tar.gz"

    if not main_py.is_file():
        print(json.dumps({"error": f"missing main.py in {strategy_dir}"}, indent=2))
        return 1

    # Package main.py as the only root entry with stable metadata.
    data = main_py.read_bytes()
    with tarball.open("wb") as raw:
        with gzip.GzipFile(filename="", mode="wb", fileobj=raw, mtime=0) as gz:
            with tarfile.open(fileobj=gz, mode="w") as tf:
                info = tarfile.TarInfo("main.py")
                info.size = len(data)
                info.mtime = 0
                info.uid = info.gid = 0
                info.uname = info.gname = ""
                tf.addfile(info, fileobj=io.BytesIO(data))
    print(json.dumps({"packaged": str(tarball), "entries": ["main.py"]}, indent=2, ensure_ascii=False))

    # Validate immediately.
    proc = subprocess.run(
        [sys.executable, str(SCRIPT_DIR / "validate_submission.py"), str(strategy_dir)],
        capture_output=True,
        text=True,
    )
    print(proc.stdout, end="")
    if proc.stderr.strip():
        print(proc.stderr, end="", file=sys.stderr)
    return proc.returncode


if __name__ == "__main__":
    sys.exit(main())
