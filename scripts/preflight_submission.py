#!/usr/bin/env python3
"""preflight_submission.py -- MANDATORY pre-submission validation gate.

Any strategy (any lane: v*/nn*/c*/reactive) MUST pass this check with
"ok": true before the user is asked to submit it. Encodes the two historical
online-ERROR lessons:
  L1 (nn1): episode runtime has NO third-party ML frameworks -> import scan
            whitelist (stdlib + numpy only).
  L2 (nn2): runner may load the agent WITHOUT __file__ defined and executes
            module-level code under time pressure -> no __file__ usage,
            exec-without-__file__ load test, import-time budget.

Checks:
  1. main.py exists + py_compile
  2. import whitelist (stdlib + numpy); torch/scipy/sklearn/pandas/etc. FAIL
  3. no '__file__' reference anywhere
  4. module load WITHOUT __file__ (compile+exec) succeeds, timed (< 0.9s)
  5. submission.tar.gz exists and passes scripts/validate_submission.py
  6. file-path smoke vs "starter"/"random"/"pass": all DONE, reward > 3000
  7. agent-call timing (max per-call < 0.45s; actTimeout = 1s online)
  8. size sanity (main.py and tar < 30 MB)

Usage:
    python3 scripts/preflight_submission.py strategies/c1
Exit code 0 == ok.
"""
from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PYDEPS = Path("/Users/tianrunliao/Documents/Codex/2026-08-24/wo/work/pydeps")
if PYDEPS.exists() and str(PYDEPS) not in sys.path:
    sys.path.insert(0, str(PYDEPS))

IMPORT_BUDGET_S = 0.9
CALL_BUDGET_S = 0.45
SIZE_BUDGET_MB = 30

ALLOWED_EXTRA = {"numpy"}


def fail(result, check, msg):
    result["checks"][check] = f"FAIL: {msg}"
    result["ok"] = False
    print(json.dumps(result, indent=2, ensure_ascii=False))
    sys.exit(1)


def scan_imports(src: str):
    import re
    mods = set()
    for m in re.finditer(r"^\s*(?:import|from)\s+([A-Za-z_][\w.]*)", src, re.M):
        mods.add(m.group(1).split(".")[0])
    return mods


def main():
    if len(sys.argv) < 2:
        print(json.dumps({"error": "usage: preflight_submission.py <strategy_dir>"}))
        sys.exit(2)
    sdir = (ROOT / sys.argv[1]).resolve() if not Path(sys.argv[1]).is_absolute() \
        else Path(sys.argv[1]).resolve()
    main_py = sdir / "main.py"
    tar = sdir / "submission.tar.gz"
    result = {"strategy_dir": str(sdir), "ok": True, "checks": {}}

    if not main_py.is_file():
        fail(result, "main_py", f"missing {main_py}")
    src = main_py.read_text(encoding="utf-8", errors="replace")
    nbytes = main_py.stat().st_size

    # 1. compile
    try:
        compile(src, str(main_py), "exec")
        result["checks"]["py_compile"] = "ok"
    except SyntaxError as e:
        fail(result, "py_compile", repr(e))

    # 8. size
    if nbytes > SIZE_BUDGET_MB * 1e6:
        fail(result, "size", f"main.py {nbytes/1e6:.1f}MB > {SIZE_BUDGET_MB}MB")
    if tar.is_file() and tar.stat().st_size > SIZE_BUDGET_MB * 1e6:
        fail(result, "size", f"tar {tar.stat().st_size/1e6:.1f}MB > {SIZE_BUDGET_MB}MB")
    result["checks"]["size"] = f"ok ({nbytes/1e6:.2f}MB)"

    # 2. import whitelist
    import sys as _s
    stdlib = set(_s.stdlib_module_names)
    mods = scan_imports(src)
    bad = sorted(m for m in mods if m not in stdlib and m not in ALLOWED_EXTRA)
    if bad:
        fail(result, "imports", f"non-whitelisted modules: {bad} "
             "(episode runtime only provides stdlib + numpy)")
    result["checks"]["imports"] = f"ok ({sorted(mods)})"

    # 3. __file__
    if "__file__" in src:
        fail(result, "no___file__", "source references __file__ (runner may not define it)")
    result["checks"]["no___file__"] = "ok"

    # 4. load without __file__
    t0 = time.time()
    try:
        code = compile(src, "main.py", "exec")
        g = {"__name__": "agent_preflight"}
        exec(code, g)
        dt = time.time() - t0
    except Exception as e:
        fail(result, "exec_no___file__", f"{type(e).__name__}: {e}")
    if dt > IMPORT_BUDGET_S:
        fail(result, "exec_no___file__", f"module-level exec took {dt:.2f}s > {IMPORT_BUDGET_S}s")
    if not callable(g.get("agent")):
        fail(result, "exec_no___file__", "no callable 'agent' defined")
    result["checks"]["exec_no___file__"] = f"ok ({dt:.2f}s)"

    # 5. package validation
    if not tar.is_file():
        fail(result, "package", "missing submission.tar.gz; run scripts/package_strategy.py first")
    proc = subprocess.run([sys.executable, str(ROOT / "scripts/validate_submission.py"), str(sdir)],
                          capture_output=True, text=True)
    if proc.returncode != 0:
        fail(result, "package", proc.stdout.strip()[-400:] or proc.stderr.strip()[-400:])
    result["checks"]["package"] = "ok"

    # 6+7. functional smoke with timing (module-level load mirrors runner semantics
    # closely enough; file-path smoke follows to catch path-loading specifics)
    from kaggle_environments import make

    spec = importlib.util.spec_from_file_location("preflight_agent", str(main_py))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)

    times = []

    def timed(obs, config=None):
        ta = time.time()
        a = mod.agent(obs, config)
        times.append(time.time() - ta)
        return a

    panels = [("starter", 11), ("random", 11), ("pass", 11), ("pass", 23)]
    for opp, seed in panels:
        env = make("kaggriculture", configuration={"episodeSteps": 720, "seed": seed}, debug=False)
        try:
            env.run([timed, opp])
        except Exception as e:
            fail(result, "smoke", f"vs {opp} seed{seed}: {type(e).__name__}: {e}")
        last = env.steps[-1][0]
        if str(last.status) != "DONE":
            fail(result, "smoke", f"vs {opp} seed{seed}: status {last.status}")
        if opp != "pass" and (last.reward or 0) <= 3000:
            fail(result, "smoke", f"vs {opp} seed{seed}: reward {last.reward} <= 3000 "
                 "(agent effectively inactive; silent import crash?)")
    # file-path load smoke (runner's own loading path)
    env = make("kaggriculture", configuration={"episodeSteps": 720, "seed": 11}, debug=False)
    env.run([str(main_py), "starter"])
    if str(env.steps[-1][0].status) != "DONE":
        fail(result, "smoke_fileload", f"status {env.steps[-1][0].status}")
    if (env.steps[-1][0].reward or 0) <= 3000:
        fail(result, "smoke_fileload", f"reward {env.steps[-1][0].reward} <= 3000")
    result["checks"]["smoke"] = "ok (starter/random/pass DONE, reward > 3000, file-load DONE)"

    mx = max(times) if times else 0.0
    if mx > CALL_BUDGET_S:
        fail(result, "timing", f"max per-call {mx*1000:.0f}ms > {CALL_BUDGET_S*1000:.0f}ms "
             "(online actTimeout=1s)")
    result["checks"]["timing"] = f"ok (max {mx*1000:.0f}ms over starter game)"

    print(json.dumps(result, indent=2, ensure_ascii=False))
    sys.exit(0)


if __name__ == "__main__":
    main()
