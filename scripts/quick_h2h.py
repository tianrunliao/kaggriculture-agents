#!/usr/bin/env python3
"""Quick paired h2h: candidates vs a baseline, both seats, via env.run([path, path])
(Kaggle's own loader => last-callable rule, same as the ladder).

Usage: python3 quick_h2h.py --base strategies/c72/main.py --seeds 0-3 CAND1 [CAND2 ...]
"""
import argparse
import json
import os
import sys
from multiprocessing import Pool

sys.path.insert(0, "/Users/tianrunliao/Documents/Codex/2026-08-24/wo/work/pydeps")
sys.dont_write_bytecode = True


def one(job):
    cand, base, seed, seat = job
    from kaggle_environments import make
    env = make("kaggriculture", configuration={"episodeSteps": 720, "seed": seed}, debug=False)
    pair = [cand, base] if seat == 0 else [base, cand]
    env.run(pair)
    last = env.steps[-1]
    rc, rb = float(last[seat].reward or 0), float(last[1 - seat].reward or 0)
    return {"cand": cand, "base": base, "seed": seed, "seat": seat, "rc": rc, "rb": rb, "margin": rc - rb,
            "status": [last[0].status, last[1].status]}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--base", required=True)
    ap.add_argument("--seeds", default="0-3")
    ap.add_argument("--procs", type=int, default=8)
    ap.add_argument("--out", default=None)
    ap.add_argument("cands", nargs="+")
    a = ap.parse_args()
    lo, hi = map(int, a.seeds.split("-"))
    jobs = [(os.path.abspath(c), os.path.abspath(a.base), s, seat)
            for c in a.cands for s in range(lo, hi + 1) for seat in (0, 1)]
    with Pool(a.procs) as p:
        res = p.map(one, jobs)
    for c in a.cands:
        R = [r for r in res if r["cand"] == os.path.abspath(c)]
        m = [r["margin"] for r in R]
        bad = [r for r in R if r["status"] != ["DONE", "DONE"]]
        print(f"{c}\n  n={len(R)} cand_mean={sum(r['rc'] for r in R)/len(R):.0f} "
              f"base_mean={sum(r['rb'] for r in R)/len(R):.0f} margin_mean={sum(m)/len(m):+.0f} "
              f"wins={sum(x > 0 for x in m)}/{len(m)} non_done={len(bad)}")
        for r in R:
            print(f"    seed {r['seed']} seat {r['seat']} {r['rc']:.0f} vs {r['rb']:.0f} {r['status']}")
    if a.out:
        json.dump(res, open(a.out, "w"), indent=1)


if __name__ == "__main__":
    main()
