"""Inspect what the local model actually writes, and why each guard fires.

The guards deliberately discard generations, which leaves an awkward question:
if the clause on screen says "template", is the model broken, is Ollama down, or
is a rule too strict? You cannot answer that from the UI alone, so this prints
the raw generation next to the verdict for every case.

  python llm_check.py              # the standard set
  python llm_check.py --raw        # add the full rejected text
  python llm_check.py "spec text"  # one query

A high rejection rate is not automatically good news. Read the rejected text: if
the model was genuinely wrong, the guard earned its keep; if it was fine and a
rule over-fired, that rule needs narrowing. Both outcomes are findings.
"""

import argparse
import sys
import textwrap

# A spread over the three real product families in the corpus, plus the cases
# that have actually caused failures: no certification rule on file, mandatory
# certification, a superseded citation, and a part split only by voltage.
CASES = [
    "Unplasticized PVC rigid pipes for potable water supply",
    "PVC insulated heavy duty electric cable for working voltage 1.1 kV",
    "PVC insulated heavy duty electric cable for working voltage 11 kV",
    "LED street light luminaire 18W for road lighting",
    "Galvanised iron pipes for water supply with ISI marking",
    "XLPE insulated armoured power cable 11 kV for underground distribution",
    "LED flood light fitting with photobiological safety",
    "Reinforced cement concrete pipes for drainage",
]

WIDTH = 94


def wrap(text: str, indent: str = "      ") -> str:
    return textwrap.fill(text, WIDTH, initial_indent=indent, subsequent_indent=indent)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("query", nargs="*", help="a single spec to test")
    ap.add_argument("--raw", action="store_true", help="print rejected generations in full")
    args = ap.parse_args()

    import llm
    from retrieval import recommend

    st = llm.status()
    print(f"model      {st.get('model')}")
    print(f"available  {st.get('available')}"
          + ("" if st.get("available") else f"  — {st.get('detail')}"))
    if not st.get("available"):
        print("\nEvery clause below will come from the template. That is the designed "
              "fallback, not a failure — but it means this run tells you nothing about "
              "the model.")
    print()

    cases = [" ".join(args.query)] if args.query else CASES
    used = rejected = abstained = 0
    reasons: dict[str, int] = {}

    for q in cases:
        print(f"── {q}")
        d = recommend(q)
        if d["decision"] == "abstain":
            abstained += 1
            print(f"      ABSTAINED before composition — {d['reason']}")
            print(wrap(d["message"]))
            print()
            continue

        c = d["clause"]
        info = c.get("llm") or {}
        if c["composed_by"] == "llm":
            used += 1
            print(f"      ACCEPTED  {c.get('model')}  {c.get('generation_ms')} ms")
            print(wrap(c["text"]))
        else:
            rejected += 1
            reason = info.get("reason", "no_model")
            reasons[reason] = reasons.get(reason, 0) + 1
            print(f"      REJECTED  {reason}")
            if info.get("detail"):
                print(wrap(info["detail"], "        · "))
            if args.raw and info.get("rejected_text"):
                print("      what the model wrote:")
                print(wrap(info["rejected_text"], "      | "))
            print("      shown instead (template):")
            print(wrap(c["text"]))
        print()

    total = used + rejected
    print("-" * WIDTH)
    print(f"{used} accepted · {rejected} rejected · {abstained} abstained before composition")
    if total:
        print(f"acceptance rate {100 * used / total:.0f}% of {total} composed clauses")
    for r, n in sorted(reasons.items(), key=lambda kv: -kv[1]):
        print(f"  {n:>2}  {r}")
    print(
        "\nA rejection means the template was shown instead — the facts were never at "
        "risk. Re-run with --raw to read the discarded text and judge whether each "
        "rule fired fairly."
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
