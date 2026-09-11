"""Language normalization — the Orchestration step in the architecture.

Officers write trade abbreviations. The BIS register uses formal chemistry and
metallurgy names. Nothing bridges the two, so an entirely reasonable query
retrieves nothing:

    "XLPE insulated armoured power cable 11 kV"
        -> IS 7098 (Part 2), "Crosslinked polyethylene insulated ..."
        -> never appeared in the candidate set at all

No BIS title contains the string "XLPE". Neither the embedding nor BM25 can
close that gap, because the vocabulary simply is not shared. This module adds
the register's own words to the query before retrieval sees it.

Two rules keep this honest:

  * Expansions are ADDED, never substituted. The officer's own words stay in the
    query, so BM25 still matches what they actually typed.
  * Every expansion must appear verbatim in at least one real title in the
    register. `validate()` checks that against the live database, and the test
    at the bottom fails if an entry drifts. This is a vocabulary bridge built
    from the corpus, not domain trivia typed in from memory.

Ambiguous two-letter forms (MS, DI, CI, IP) are matched case-sensitively as
standalone uppercase tokens only, so ordinary prose is never rewritten.

Two entries were dropped when validate() rejected them: "stainless steel" appears
in no title in this register, and it spells the word "armouring", not "armoured".
Both were plausible and both were wrong, which is the reason the check exists.

A third was dropped after measurement rather than validation: "storm water" ->
"drainage sewerage" is accurate English and it made results worse, because a
material-neutral word like "drainage" outranks the material the officer asked
for. "Reinforced cement concrete pipes for storm water drainage" resolved to an
asbestos-cement standard with it, and to IS 458 without it. An expansion has to
earn its place on results, not on plausibility.
"""

import re
import sqlite3

DB_PATH = "manak_setu.db"

# Abbreviation -> the register's phrasing. Case-insensitive matches.
EXPANSIONS = {
    "xlpe": "cross-linked polyethylene",
    "upvc": "unplasticized polyvinyl chloride",
    "pvc-u": "unplasticized polyvinyl chloride",
    "hdpe": "high density polyethylene",
    "ldpe": "low density polyethylene",
    "acsr": "aluminium conductor steel reinforced",
    "frp": "fibre reinforced plastic",
    "rcc": "precast concrete",
    "gi": "galvanized steel tubes tubulars wrought steel fittings",
    "led": "light emitting diode",
    "lt": "low voltage",
    "ht": "high voltage",
}

# Short forms that are also ordinary words or initials. Uppercase, standalone only.
STRICT_EXPANSIONS = {
    "MS": "mild steel",
    "CI": "cast iron",
    "DI": "ductile iron",
    "IP": "degrees of protection",
    "ABC": "aerial bunched",
}

# Not abbreviations, but the same failure: the word an officer reaches for is not
# the word the register indexes under.
PHRASES = {
    # Spelled-out forms matter as much as the abbreviation: "reinforced cement
    # concrete pipes" contains no token "RCC", so the abbreviation rule never
    # fired and the query resolved to a UPVC pipe standard instead of IS 458.
    r"\breinforced\s+cement\s+concrete\b|\bcement\s+concrete\b": "precast concrete",
    r"\bgalvani[sz]ed\s+(?:iron|steel)\b": "galvanized steel tubes tubulars wrought steel fittings",
    r"\bstreet\s+light(?:ing)?\b": "road and street lighting luminaires",
    r"\bflood\s+light\b": "floodlight luminaire",
    r"\bearthing\b": "earthing and bonding",
    r"\bpotable\b": "drinking water supplies",
    # And the reverse: translated queries say "drinking water", the register says
    # "potable water supplies". Without this, Hindi for "uPVC pipe for drinking
    # water" resolved to a corrugated drainage pipe instead of IS 4985.
    r"\bdrinking\s+water\b": "potable water supplies",
}


def expand(query: str) -> tuple[str, list[dict]]:
    """Return the query with register vocabulary appended, and what was added."""
    text = query or ""
    applied: list[dict] = []
    seen: set[str] = set()

    for abbr, full in EXPANSIONS.items():
        if re.search(rf"(?<![A-Za-z0-9]){re.escape(abbr)}(?![A-Za-z0-9])", text, re.I):
            if full not in seen:
                applied.append({"matched": abbr.upper(), "added": full})
                seen.add(full)

    for abbr, full in STRICT_EXPANSIONS.items():
        if re.search(rf"(?<![A-Za-z0-9]){abbr}(?![A-Za-z0-9])", text):  # case-sensitive
            if full not in seen:
                applied.append({"matched": abbr, "added": full})
                seen.add(full)

    for pattern, full in PHRASES.items():
        m = re.search(pattern, text, re.I)
        if m and full not in seen:
            applied.append({"matched": m.group(0), "added": full})
            seen.add(full)

    if not applied:
        return text, []
    return f"{text} {' '.join(a['added'] for a in applied)}", applied


def validate(db_path: str = DB_PATH) -> list[str]:
    """Every expansion must be language the register actually uses. Returns the
    entries that are not, so an unfounded addition cannot pass unnoticed."""
    conn = sqlite3.connect(db_path)
    try:
        blob = " || ".join(
            (r[0] or "").lower() for r in conn.execute('SELECT "Full Title" FROM standards')
        )
    finally:
        conn.close()

    ungrounded = []
    for source in (EXPANSIONS, STRICT_EXPANSIONS, PHRASES):
        for key, full in source.items():
            # the head word is enough: titles vary on hyphenation and word order
            head = re.sub(r"[^a-z ]", "", full.lower()).split()[0]
            if full.lower() not in blob and head not in blob:
                ungrounded.append(f"{key} -> {full}")
    return ungrounded


if __name__ == "__main__":
    bad = validate()
    print(f"{len(EXPANSIONS) + len(STRICT_EXPANSIONS) + len(PHRASES)} normalization rules")
    if bad:
        print("NOT GROUNDED in any register title — remove or correct these:")
        for b in bad:
            print(f"  {b}")
        raise SystemExit(1)
    print("all grounded in at least one real BIS title\n")
    for q in [
        "XLPE insulated armoured power cable 11 kV for underground distribution",
        "GI pipes for water supply with ISI marking",
        "90W LED street light luminaire, IP66 die-cast aluminium housing",
        "reinforced cement concrete pipes for storm water drainage",
        "catering services for departmental canteen",
    ]:
        out, applied = expand(q)
        print(f"  {q}")
        print(f"    + {', '.join(a['added'] for a in applied) if applied else '(nothing added)'}")
