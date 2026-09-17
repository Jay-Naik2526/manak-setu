"""Measure every retrieval pipeline on the same queries, and let the table argue.

"Alternative RAG pipelines" is a question about engineering judgement, not an
invitation to add another chatbot. So this runs each registered pipeline over
the same 621 query/standard pairs, against the same 27,687 rows, and reports
what each one costs and what it gets right. The default pipeline is whatever
this table justifies; if a simpler one wins, the simpler one should win.

Every column carries its denominator. Two are worth reading carefully:

  abstention     — only meaningful where the pipeline's score is calibrated.
                   BM25 scores are unbounded and grow with query length; dense
                   cosine barely separates a correct top hit from a wrong one.
                   Both are reported as "no gate" rather than as zero.

  fabrication    — the share of answers naming an IS number the register does
                   not hold. For every retrieval pipeline this is exactly zero,
                   and not because they are careful: they can only return rows
                   that exist. For a model asked to name a standard from memory
                   it is the number that matters, and it is measured, never
                   estimated — with no Ollama running the row reads
                   "not measured".

    python eval_pipelines.py                 # all pipelines, 621 queries
    python eval_pipelines.py --limit 120     # a faster pass
    python eval_pipelines.py --write         # also write the leaderboard JSON
"""

import argparse
import json
import os
import resource
import sys
import time

import pandas as pd

GOLDEN = "data/golden_queries.csv"
OUT = "data/pipeline_leaderboard.json"
RECALL_AT = 10


def _peak_rss_mb() -> float:
    peak = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
    # Linux reports kilobytes, macOS bytes.
    return peak / (1024 * 1024) if sys.platform == "darwin" else peak / 1024


def _same(a: str, b: str) -> bool:
    import engine

    a, b = str(a), str(b)
    if engine._is_base(a).upper() == engine._is_base(b).upper():
        return True
    da, db = engine._is_digits(a), engine._is_digits(b)
    return bool(da) and da == db


def run_pipeline(name: str, rows: list[tuple[str, str]]) -> dict:
    import retrieval

    cfg = retrieval.PIPELINES[name]
    if not cfg.get("retrieval", True):
        return _llm_only(name, cfg, rows)

    hits1 = hitsk = abstained = 0
    latencies = []
    held = _register_numbers()
    outside = 0
    correct_at_1 = []          # per query, for the paired comparison below

    for query, expected in rows:
        t0 = time.perf_counter()
        candidates = retrieval.search(query, pipeline=name)
        latencies.append(time.perf_counter() - t0)

        # The gate has to actually run, or the abstention column is a lie. The
        # first version of this script only counted an empty candidate list,
        # which reported 0 of 621 abstentions for every gated pipeline — as if
        # the system never declines, when in truth it had never been asked to.
        if cfg.get("gate"):
            decision = retrieval._gate(candidates)
            if decision["decision"] == "abstain":
                abstained += 1

        if not candidates:
            correct_at_1.append(0)
            continue
        first = _same(candidates[0]["is_number"], expected)
        correct_at_1.append(1 if first else 0)
        if first:
            hits1 += 1
        if any(_same(c["is_number"], expected) for c in candidates[:RECALL_AT]):
            hitsk += 1
        # Structural, not behavioural: a retriever returns rows, so every answer
        # is in the register by construction. Counted anyway, because a claim
        # nobody checks is a claim nobody should believe.
        if candidates[0]["is_number"] not in held:
            outside += 1

    n = len(rows)
    return {
        "pipeline": name,
        "label": cfg["label"],
        "note": cfg["note"],
        "queries": n,
        "rank_1": hits1,
        "recall_at": RECALL_AT,
        "recall_hits": hitsk,
        "gate": bool(cfg.get("gate")),
        "abstained": abstained if cfg.get("gate") else None,
        "mean_latency_ms": round(1000 * sum(latencies) / max(len(latencies), 1), 1),
        "peak_rss_mb": round(_peak_rss_mb(), 1),
        "answers_outside_the_register": outside,
        "measured": True,
        "_correct_at_1": correct_at_1,
    }


def _register_numbers() -> set:
    import sqlite3

    conn = sqlite3.connect("manak_setu.db")
    try:
        return {r[0] for r in conn.execute('SELECT "IS Number" FROM standards')}
    finally:
        conn.close()


def _llm_only(name: str, cfg: dict, rows: list[tuple[str, str]]) -> dict:
    """The no-retrieval baseline. Only real if a model actually answered."""
    import llm

    status = llm.status()
    blank = {
        "pipeline": name, "label": cfg["label"], "note": cfg["note"],
        "queries": 0, "rank_1": None, "recall_at": RECALL_AT, "recall_hits": None,
        "gate": False, "abstained": None, "mean_latency_ms": None,
        "peak_rss_mb": None, "answers_outside_the_register": None,
        "measured": False,
        "why_not_measured": status.get("detail") or "no local model available",
    }
    if not status.get("available"):
        return blank

    held = _register_numbers()
    import engine

    hits1 = outside = answered = 0
    latencies = []
    for query, expected in rows:
        t0 = time.perf_counter()
        reply = llm.phrase(
            "Name the single Indian Standard that governs this item. "
            "Reply with the IS number alone.\n\n" + query
        )
        latencies.append(time.perf_counter() - t0)
        if not reply:
            continue
        found = engine.extract_citations(str(reply))
        if not found:
            continue
        answered += 1
        top = found[0]
        if _same(top, expected):
            hits1 += 1
        if top not in held and engine._is_base(top) not in held:
            outside += 1

    return {
        **blank,
        "queries": len(rows), "answered": answered, "rank_1": hits1,
        "recall_hits": hits1,
        "mean_latency_ms": round(1000 * sum(latencies) / max(len(latencies), 1), 1),
        "peak_rss_mb": round(_peak_rss_mb(), 1),
        "answers_outside_the_register": outside,
        "measured": True,
        "why_not_measured": None,
    }



def _compare(results: list[dict], default: str) -> None:
    """Paired comparison of every measured pipeline against the default."""
    import math

    base = next((r for r in results
                 if r["pipeline"] == default and r.get("_correct_at_1")), None)
    if base is None:
        return
    others = [r for r in results
              if r.get("_correct_at_1") and r["pipeline"] != default]
    if not others:
        return

    print(f"\nagainst the default ({default}), on the same queries:")
    for r in others:
        a, b = base["_correct_at_1"], r["_correct_at_1"]
        if len(a) != len(b):
            continue
        only_default = sum(1 for x, y in zip(a, b) if x and not y)
        only_other = sum(1 for x, y in zip(a, b) if y and not x)
        n = only_default + only_other
        if n == 0:
            print(f"  {r['pipeline']:<14} identical on every query")
            continue
        # Exact two-sided binomial p at q=0.5 over the discordant pairs.
        k = min(only_default, only_other)
        tail = sum(math.comb(n, i) for i in range(0, k + 1)) / (2 ** n)
        p = min(1.0, 2 * tail)
        verdict = ("the difference is within noise" if p > 0.05
                   else f"{default} wins" if only_default > only_other
                   else f"{r['pipeline']} wins")
        print(f"  {r['pipeline']:<14} {default} alone right on {only_default}, "
              f"{r['pipeline']} alone right on {only_other} "
              f"→ p={p:.3f}, {verdict}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--limit", type=int, default=0, help="use only the first N queries")
    ap.add_argument("--only", nargs="*", help="run only these pipelines")
    ap.add_argument("--write", action="store_true")
    args = ap.parse_args()

    import retrieval

    if not os.path.exists(GOLDEN):
        raise SystemExit(f"no golden set at {GOLDEN}")
    df = pd.read_csv(GOLDEN, encoding="utf-8-sig")
    rows = [(str(q), str(e)) for q, e in zip(df["query"], df["expected_is"])
            if str(e).strip() and str(e).strip().lower() != "nan"]
    if args.limit:
        rows = rows[: args.limit]

    names = args.only or list(retrieval.PIPELINES)
    results = []
    for name in names:
        print(f"running {name} over {len(rows)} queries…", flush=True)
        results.append(run_pipeline(name, rows))

    print(f"\nPipeline leaderboard · {len(rows)} query/standard pairs "
          f"· {len(_register_numbers()):,} standards\n")
    head = (f"{'pipeline':<14}{'rank 1':>12}{'recall@10':>12}{'abstain':>10}"
            f"{'ms/query':>10}{'outside register':>18}")
    print(head)
    print("-" * len(head))
    for r in results:
        if not r["measured"]:
            print(f"{r['pipeline']:<14}{'not measured':>12}"
                  f"{'—':>12}{'—':>10}{'—':>10}{'—':>18}")
            continue
        n = r["queries"]
        r1 = f"{r['rank_1']}/{n}"
        rk = f"{r['recall_hits']}/{n}"
        ab = f"{r['abstained']}/{n}" if r["gate"] else "no gate"
        print(f"{r['pipeline']:<14}{r1:>12}{rk:>12}{ab:>10}"
              f"{r['mean_latency_ms']:>10.0f}{r['answers_outside_the_register']:>18}")

    # Is a seven-query difference over 621 a finding or noise? The pipelines
    # answer the same queries, so the comparison is paired: only the queries
    # where exactly one of them is right carry information. McNemar's test on
    # those, exact under the binomial, says whether to believe the gap.
    _compare(results, retrieval.DEFAULT_PIPELINE)

    print("\nabstain 'no gate' means the pipeline's score is not calibrated enough "
          "to decline on;\nsee retrieval.PIPELINES for which and why. "
          "'outside register' is 0 by construction for\nevery retrieval pipeline — "
          "they can only return rows that exist.")
    for r in results:
        if not r["measured"]:
            print(f"\n{r['pipeline']}: not measured — {r['why_not_measured']}")

    if args.write:
        payload = {
            "generated": __import__("datetime").date.today().isoformat(),
            "queries": len(rows),
            "recall_at": RECALL_AT,
            "default_pipeline": retrieval.DEFAULT_PIPELINE,
            "pipelines": results,
            "note": ("Every pipeline ran the same queries against the same register. "
                     "These measure the retriever alone — raw candidates, before "
                     "the voltage, material, role and status filters and before the "
                     "confidence gate — so they are higher than the end-to-end "
                     "figures eval_retrieval.py reports for the same set. "
                     "Abstention is reported only where the score is calibrated "
                     "enough to decline on. Answers outside the register are zero "
                     "for retrieval pipelines by construction, not by care."),
        }
        # The per-query vector is for the paired test, not for the page.
        for r in payload["pipelines"]:
            r.pop("_correct_at_1", None)
        with open(OUT, "w", encoding="utf-8") as fh:
            json.dump(payload, fh, indent=1)
        print(f"\nwrote {OUT}")


if __name__ == "__main__":
    main()
