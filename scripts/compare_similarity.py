#!/usr/bin/env python3
"""Compare two agent source files for similarity.

Usage:
    python scripts/compare_similarity.py strategies/v7/main.py strategies/v6/main.py

Output (JSON):
  - sha256 of each file
  - byte size of each file
  - raw source similarity (difflib.SequenceMatcher ratio)
  - unique-line Jaccard
"""
from __future__ import annotations

import difflib
import hashlib
import json
import sys
from pathlib import Path


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def unique_line_jaccard(a_text: str, b_text: str) -> float:
    lines_a = {ln.strip() for ln in a_text.splitlines() if ln.strip()}
    lines_b = {ln.strip() for ln in b_text.splitlines() if ln.strip()}
    if not lines_a and not lines_b:
        return 1.0
    inter = len(lines_a & lines_b)
    union = len(lines_a | lines_b)
    return inter / union


def main() -> int:
    if len(sys.argv) != 3:
        print(json.dumps({"error": "usage: compare_similarity.py <file_a> <file_b>"}, indent=2))
        return 2

    pa, pb = Path(sys.argv[1]).resolve(), Path(sys.argv[2]).resolve()
    for p in (pa, pb):
        if not p.is_file():
            print(json.dumps({"error": f"not a file: {p}"}, indent=2))
            return 1

    text_a = pa.read_text(encoding="utf-8", errors="replace")
    text_b = pb.read_text(encoding="utf-8", errors="replace")

    raw_sim = difflib.SequenceMatcher(None, text_a, text_b).ratio()
    jac = unique_line_jaccard(text_a, text_b)

    result = {
        "file_a": str(pa),
        "file_b": str(pb),
        "sha256_a": sha256_file(pa),
        "sha256_b": sha256_file(pb),
        "byte_size_a": pa.stat().st_size,
        "byte_size_b": pb.stat().st_size,
        "raw_source_similarity": round(raw_sim, 6),
        "raw_source_similarity_pct": round(raw_sim * 100, 4),
        "unique_line_jaccard": round(jac, 6),
        "unique_line_jaccard_pct": round(jac * 100, 4),
    }
    print(json.dumps(result, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
