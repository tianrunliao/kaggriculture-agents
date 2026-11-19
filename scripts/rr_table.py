#!/usr/bin/env python3
"""Merge quick_h2h.py JSON outputs into one pairwise round-robin table.

Each record has cand/base paths; an agent is named by its parent directory.
Per unordered pair: seed-cluster mean margin (row minus column) + percentile
bootstrap CI (method of ci.py). Per agent: average margin over the opponents
it met, and the minimum CI lower bound across those pairs.
Usage: python3 rr_table.py a.json b.json@<base_dir_name> ... [--boot 20000]
(@<base_dir_name> is only needed for older JSONs written before quick_h2h recorded "base".)
"""
import argparse
import json
import os
import random
from collections import defaultdict


def name(path):
    return os.path.basename(os.path.dirname(path))


def boot_ci(cl, boot, rng):
    n = len(cl)
    bs = sorted(sum(cl[rng.randrange(n)] for _ in range(n)) / n for _ in range(boot))
    return bs[int(0.025 * boot)], bs[int(0.975 * boot) - 1]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("paths", nargs="+")
    ap.add_argument("--boot", type=int, default=20000)
    a = ap.parse_args()
    # (x, y) with x < y -> seed -> list of margins from x's perspective
    pairs = defaultdict(lambda: defaultdict(list))
    bad = 0
    for spec in a.paths:
        p, _, base_override = spec.partition("@")
        for r in json.load(open(p)):
            c = name(r["cand"])
            b = base_override or name(r["base"])
            bad += r["status"] != ["DONE", "DONE"]
            if c < b:
                pairs[(c, b)][r["seed"]].append(r["margin"])
            else:
                pairs[(b, c)][r["seed"]].append(-r["margin"])
    rng = random.Random(20260926)
    res = {}
    for (x, y), seeds in pairs.items():
        cl = [sum(v) / len(v) for v in seeds.values()]
        lo, hi = boot_ci(cl, a.boot, rng)
        res[(x, y)] = (sum(cl) / len(cl), lo, hi, len(cl))
    agents = sorted({n for k in res for n in k})
    rows = []
    for ag in agents:
        vals = []
        for (x, y), (m, lo, hi, n) in res.items():
            if ag == x:
                vals.append((y, m, lo, hi, n))
            elif ag == y:
                vals.append((x, -m, -hi, -lo, n))
        avg = sum(v[1] for v in vals) / len(vals)
        rows.append((avg, ag, min(v[2] for v in vals), vals))
    rows.sort(reverse=True)
    print(f"non-DONE games: {bad}")
    for avg, ag, minlo, vals in rows:
        print(f"{ag[:48]:48s} avg {avg:+8.1f}  min CI-low {minlo:+8.1f}  opponents {len(vals)}")
        for opp, m, lo, hi, n in sorted(vals, key=lambda v: -v[1]):
            print(f"    vs {opp[:44]:44s} {m:+8.1f} CI[{lo:+.1f},{hi:+.1f}] seeds {n}")


if __name__ == "__main__":
    main()
