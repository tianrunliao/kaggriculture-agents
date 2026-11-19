#!/usr/bin/env python3
"""Seed-cluster bootstrap CI for quick_h2h.py outputs (same method as select_A.md:
average the two seat margins within a seed, then percentile-bootstrap over seeds).

Usage: python3 ci.py <h2h.json> [--boot 200000] [--rng 20260925]
"""
import argparse
import json
import os
import random
from collections import defaultdict


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("path")
    ap.add_argument("--boot", type=int, default=200000)
    ap.add_argument("--rng", type=int, default=20260925)
    a = ap.parse_args()
    res = json.load(open(a.path))
    by = defaultdict(lambda: defaultdict(list))
    for r in res:
        by[r["cand"]][r["seed"]].append(r)
    for cand, seeds in by.items():
        rng = random.Random(a.rng)
        cl = [sum(x["margin"] for x in v) / len(v) for v in seeds.values()]
        n = len(cl)
        boots = sorted(sum(cl[rng.randrange(n)] for _ in range(n)) / n for _ in range(a.boot))
        lo, hi = boots[int(0.025 * a.boot)], boots[int(0.975 * a.boot) - 1]
        games = [x for v in seeds.values() for x in v]
        w = sum(x["margin"] > 0 for x in games)
        l = sum(x["margin"] < 0 for x in games)
        bad = sum(x["status"] != ["DONE", "DONE"] for x in games)
        sw = sum(c > 0 for c in cl)
        sl = sum(c < 0 for c in cl)
        name = os.path.basename(os.path.dirname(cand))
        print(f"{name}: seeds {n} games {len(games)} cand {sum(x['rc'] for x in games)/len(games):.0f} "
              f"base {sum(x['rb'] for x in games)/len(games):.0f} margin {sum(cl)/n:+.1f} "
              f"CI[{lo:+.1f},{hi:+.1f}] W-L-T {w}-{l}-{len(games)-w-l} (seed {sw}-{sl}-{n-sw-sl}) non_done {bad}")


if __name__ == "__main__":
    main()
