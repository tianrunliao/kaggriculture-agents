# Kaggriculture Agents

Agents and evaluation tooling from the Kaggle **Kaggriculture** simulation
competition (closed 2026-09-30). In this two-player farm-economy game, each
agent runs a 720-step season: it plants and harvests crops, raises animals,
manages a shed that overflows at night, and trades on a shared market against
the opponent.

## Result

| Final submission | Public score | Private score |
|---|---:|---:|
| `cl18_r2_full` | 1,841.2 | 4,398.2 |
| `cl18_r1_combo` (not included; `cl18_r2_full` is its successor) | 1,799.2 | 4,370.6 |

On the leaderboard downloaded through the Kaggle API on 2026-11-19, the team
ranked **1,026th of 10,148** (score 1,841.2). Over the competition, 91
submissions completed.

## Agents

### `strategies/cl18_r2_full/`: public chassis plus reactive layers (final submission)

This agent is built on public Apache-2.0 Kaggle agents. Its chassis is
tetsutani's public Step1009 agent. The header of `main.py` also credits the
earlier public work it builds on, by thomastschinkel, yhay81, destbreso,
aurax7, prvsiyan, Dmitrii Gluzdov, and Ahmed Berat Ozer. All upstream license
notices are kept verbatim.

On top of the chassis, layers were added one at a time and each was validated
against a fixed opponent panel before being kept:

1. **Adaptive tomato scale:** chooses a planting scale of 10, 15, or 20 from
   the game state.
2. **Replant after weeding.**
3. **Opponent identification:** infers which agent family the rival belongs
   to from its per-turn money changes, then orders sell orders to suit that
   rival. If the family cannot be identified, the agent returns the base
   action unchanged.
4. **Carrot-margin adaptation** against one identified opponent type.
5. **Round two additions:** clear weeds before building, buy wheat first with
   a same-crop guard, and clear weeds earlier.

The development protocol was:

1. Play the current version for 50 seeds in both seats against each of 8
   opponents from the same public family.
2. Classify every non-win by mechanism and replay it exactly to find the
   cause.
3. Make at most four targeted fixes per round.
4. Re-test on fresh seeds. A fix is kept only if the win rate rises and the
   mean score does not fall.

| Version | Fresh-seed panel (8 family opponents) |
|---|---|
| adaptive-tomato base | 612 / 800 wins |
| `cl18_r1_combo` | 776 / 800 wins, 0 regressions |
| `cl18_r2_full` | 2,400 / 2,400 wins across three disjoint seed windows |

Against opponents outside that family, recorded from replays, `cl18_r2_full`
plays almost identically to `cl18_r1_combo` (35–25 over 60 games). The gains
are specific to the panel family.

### `strategies/cc_011m9/`: self-built online production and sales planner

This is an independent agent written from scratch, without the public chassis.
It uses numpy only:

1. A heuristic jointly plans production and sales.
2. Workers are assigned to tasks with a pure-numpy Hungarian algorithm,
   because scipy is not available online.
3. A feed-wheat ring is planted far from the base.
4. Feed-wheat purchases are cut off near the end of the season.
5. Sell orders put produce ahead of surplus inputs, so the nightly shed
   overflow no longer destroys harvested goods.

Local results on held-out seeds 700–719 (both seats): +12,941 per game over
its own earlier baseline (40–0). It improved on the previous version against
every panel opponent. However, it still lost 0–40 to the strongest
fixed-route agents in the local panel, so it was not competitive at the top. Submitted
online, it scored 701.6.

## Evaluation tooling (`scripts/`)

| Script | Purpose |
|---|---|
| `quick_h2h.py` | Paired head-to-head: candidates against a base agent over a seed range, both seats, in parallel, through Kaggle's own loader |
| `ci.py` | Bootstrap confidence intervals for the mean margin in an h2h result file |
| `rr_table.py` | Round-robin summary across several result files |
| `validate_submission.py` | Checks that the tarball contains only `main.py` and that its SHA-256 matches the source |
| `package_strategy.py` | Builds `submission.tar.gz` for a strategy directory |
| `preflight_submission.py` | Checks imports against an allow-list, rejects `__file__` use, times each step, and runs smoke games |
| `compare_similarity.py` | Measures textual similarity between two agents |

```bash
pip install "kaggle-environments==1.32.7" numpy   # version used during the competition

python scripts/quick_h2h.py --base strategies/cc_011m9/main.py --seeds 0-9 --procs 4 \
    --out out.json strategies/cl18_r2_full/main.py
python scripts/ci.py out.json --boot 20000

python scripts/package_strategy.py strategies/cl18_r2_full
python scripts/preflight_submission.py strategies/cl18_r2_full
```

The two `main.py` files are byte-identical to the submitted versions (SHA-256
prefixes `892048e0d1ab` and `5cd473248fcd`).

## License

`strategies/cl18_r2_full/main.py` is a derivative of Apache-2.0 code; its
upstream notices apply.
