"""Classify allied standards by the role they play.

The problem statement asks for more than "related standards". It asks for

    normative references, test methods, terminology standards, safety
    standards, installation standards, and related product standards

which is a list of *roles*, not a list of numbers. An officer reading a
recommendation needs to know that IS 10810 is how you test the cable, IS 1885 is
what the words mean, and IS 1255 is how you lay it — three different obligations
that belong in three different parts of a tender.

BIS titles state the role plainly, because the catalogue is written that way:
"Methods of test for cables", "Glossary of terms", "Code of practice for
installation and maintenance". So the role is read from the title rather than
guessed. A standard whose title says nothing about its role is reported as a
related product standard, which is the safe default and also the commonest case.

Nothing here infers a relationship. Which standards are allied at all comes from
the co-citation graph — real tenders citing them together. This module only
labels what that relationship is for.
"""

import re

# Order matters: the first matching role wins, most specific first. "Methods of
# test for safety of luminaires" is a test method, not a safety standard.
ROLES = [
    ("test_method", "Test method", [
        r"\bmethods?\s+of\s+test\b", r"\btest\s+methods?\b", r"\btesting\s+of\b",
        r"\bmethods?\s+for\s+(?:sampling|determination|measurement|test)",
        r"\bsampling\b",
    ]),
    ("terminology", "Terminology", [
        r"\bglossary\b", r"\bterminolog", r"\bdefinitions?\b", r"\bvocabulary\b",
        r"\bnomenclature\b", r"\bletter\s+symbols\b",
    ]),
    ("installation", "Installation and practice", [
        r"\bcode\s+of\s+practice\b", r"\binstallation\b", r"\berection\b",
        r"\blaying\b", r"\bmaintenance\b", r"\brecommendations?\s+for\b",
        r"\bguide\s+for\b", r"\bguidelines?\s+for\b",
    ]),
    ("safety", "Safety", [
        r"\bsafety\b", r"\bprotection\s+against\b", r"\bhazard", r"\bfire\s+resist",
        r"\bflammabilit", r"\bexplosive\s+atmospher",
    ]),
    ("dimensions", "Dimensions and ratings", [
        r"\bdimensions?\b", r"\bsizes\b", r"\bcurrent\s+ratings?\b",
        r"\bpreferred\s+numbers\b", r"\btolerances?\b",
    ]),
    ("quality_system", "Quality and conformity", [
        r"\bquality\s+(?:management|assurance|system)", r"\bconformity\s+assessment\b",
        r"\binspection\b", r"\bacceptance\b",
    ]),
]

DEFAULT_ROLE = ("product", "Related product standard")

_COMPILED = [(key, label, [re.compile(p, re.I) for p in pats]) for key, label, pats in ROLES]

# A normative reference is a relationship, not a title pattern: the governing
# standard's own text points at it. We do not hold standard text — BIS sells it —
# so a normative reference cannot be read directly. What the graph can say is how
# consistently two standards are cited together, and a very high confidence edge
# is the observable proxy. It is labelled as a proxy, never as a normative
# reference, because those are not the same claim.
NORMATIVE_PROXY_CONFIDENCE = 0.75


def role_of(title: str) -> tuple[str, str]:
    """The role a standard plays, read from its published title."""
    text = title or ""
    for key, label, patterns in _COMPILED:
        if any(p.search(text) for p in patterns):
            return key, label
    return DEFAULT_ROLE


def classify(related: list[dict], titles: dict[str, str] | None = None) -> dict:
    """Group co-cited standards by role, keeping every field they arrived with."""
    titles = titles or {}
    groups: dict[str, dict] = {}

    for r in related:
        is_number = r.get("target_is") or r.get("is_number")
        title = r.get("title") or titles.get(is_number) or ""
        key, label = role_of(title)
        confidence = r.get("confidence") or 0.0

        entry = dict(r)
        entry["is_number"] = is_number
        entry["title"] = title or None
        entry["role"] = key
        entry["role_label"] = label
        entry["likely_normative"] = bool(confidence >= NORMATIVE_PROXY_CONFIDENCE)
        groups.setdefault(key, {"role": key, "label": label, "standards": []})
        groups[key]["standards"].append(entry)

    order = [k for k, _, _ in _COMPILED] + [DEFAULT_ROLE[0]]
    ordered = [groups[k] for k in order if k in groups]
    for g in ordered:
        g["standards"].sort(key=lambda s: -(s.get("confidence") or 0))
        g["count"] = len(g["standards"])

    normative = [
        s for g in ordered for s in g["standards"] if s["likely_normative"]
    ]
    return {
        "groups": ordered,
        "total": sum(g["count"] for g in ordered),
        "likely_normative": sorted(
            normative, key=lambda s: -(s.get("confidence") or 0)
        )[:6],
        "normative_note": (
            "Standards cited alongside the governing standard in at least "
            f"{NORMATIVE_PROXY_CONFIDENCE:.0%} of comparable tenders. Treat this as a "
            "strong candidate for a normative reference, not a confirmed one: "
            "normative references live in the text of the standard, which BIS sells "
            "and this system does not hold."
        ),
        "role_note": (
            "Roles are read from each standard's published BIS title, so a test "
            "method, a glossary and a code of practice are told apart rather than "
            "listed together as 'related'."
        ),
    }
