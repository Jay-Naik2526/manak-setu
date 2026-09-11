import random

import pandas as pd

from engine import check_dead_citation

RANDOM_SEED = 42
SAMPLE_SIZE = 20


def build_eval_set(df: pd.DataFrame) -> pd.DataFrame:
    usable = df[df["Usability"] == "Usable"]
    outdated_yes = usable[usable["Any Outdated"] == "Yes"]
    outdated_no = usable[usable["Any Outdated"] == "No"]

    sample_no = outdated_no.sample(
        n=min(SAMPLE_SIZE, len(outdated_no)), random_state=RANDOM_SEED
    )
    return pd.concat([outdated_yes, sample_no], ignore_index=True)


def predict_any_outdated(is_numbers_cited: str) -> str:
    is_numbers = [s.strip() for s in str(is_numbers_cited).split(";") if s.strip()]
    for is_number in is_numbers:
        result = check_dead_citation(is_number)
        if result.get("found") and result.get("dead"):
            return "Yes"
    return "No"


def main():
    df = pd.read_csv("data/tender_dataset.csv", encoding="utf-8-sig")
    eval_set = build_eval_set(df)

    correct = 0
    mismatches = []

    tp = tn = fp = fn = 0
    for _, row in eval_set.iterrows():
        predicted = predict_any_outdated(row["IS Numbers Cited"])
        actual = row["Any Outdated"]
        is_match = predicted == actual
        correct += int(is_match)
        if actual == "Yes" and predicted == "Yes":
            tp += 1
        elif actual == "No" and predicted == "No":
            tn += 1
        elif actual == "No" and predicted == "Yes":
            fp += 1
        else:
            fn += 1
        if not is_match:
            mismatches.append(
                {
                    "tender_id": row["Tender ID"],
                    "is_numbers_cited": row["IS Numbers Cited"],
                    "actual": actual,
                    "predicted": predicted,
                }
            )

    total = len(eval_set)
    positives = int((eval_set["Any Outdated"] == "Yes").sum())
    negatives = int((eval_set["Any Outdated"] == "No").sum())

    print(f"Evaluation set: n={total} ({positives} outdated + {negatives} clean)")
    print(f"  True positives : {tp}   (outdated, correctly flagged)")
    print(f"  True negatives : {tn}   (clean, correctly passed)")
    print(f"  False positives: {fp}   (clean, wrongly flagged)")
    print(f"  False negatives: {fn}   (outdated, missed)")
    print()
    print(
        f"Honest summary: caught {tp} of {positives} known outdated-citation tenders "
        f"with {fp} false positive(s) across {negatives} sampled clean tenders."
    )
    print(
        "Do NOT report this as a bare accuracy percentage — the positive class is only "
        f"{positives} tenders, far too small to support a general accuracy claim."
    )

    if mismatches:
        print(f"\nMismatches ({len(mismatches)}):")
        for m in mismatches:
            print(f"  Tender {m['tender_id']}: actual={m['actual']} predicted={m['predicted']}")
            print(f"    IS Numbers Cited: {m['is_numbers_cited']}")
    else:
        print("\nNo mismatches.")


if __name__ == "__main__":
    main()
