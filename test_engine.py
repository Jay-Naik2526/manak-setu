import json

from engine import check_certification, check_dead_citation, match_spec, related_standards

TEST_IS_NUMBERS = ["IS 5831", "IS 8130", "IS 694"]


def show(label, value):
    print(f"\n--- {label} ---")
    print(json.dumps(value, indent=2, ensure_ascii=False))


def main():
    show("match_spec('PVC insulated cable')", match_spec("PVC insulated cable"))
    show("match_spec('completely made up nonsense product xyz')", match_spec("completely made up nonsense product xyz123"))

    for is_number in TEST_IS_NUMBERS:
        show(f"check_dead_citation({is_number})", check_dead_citation(is_number))
        show(f"check_certification({is_number})", check_certification(is_number))
        show(f"related_standards({is_number})", related_standards(is_number))

    show("check_dead_citation(unknown)", check_dead_citation("IS 999999"))
    show("check_certification(unknown)", check_certification("IS 999999"))


if __name__ == "__main__":
    main()
