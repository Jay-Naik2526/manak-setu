"""Hybrid retrieval for the forward flow: spec text → governing standard.

Retrieval and the graph decide which standards apply. Nothing downstream may
introduce an IS number that did not come out of this module, and every
recommendation carries the score and the field that produced it.

Pipeline: dense (MiniLM) ∥ BM25 → reciprocal rank fusion → cross-encoder
rerank → confidence gate → graph expansion → deterministic version and
certification lookup → clause composition under a subset guard.

Vectors live in a numpy array rather than pgvector: 405 rows × 384 dims is a
0.6 MB dot product, so a database extension would add infrastructure without
changing the result.
"""

import os
import re
import sqlite3

import numpy as np
import pandas as pd
from rank_bm25 import BM25Okapi
from sentence_transformers import CrossEncoder, SentenceTransformer

DB_PATH = "manak_setu.db"
EMBEDDINGS_PATH = "standards_embeddings.npy"
IS_NUMBERS_PATH = "standards_embeddings_is_numbers.csv"
BI_ENCODER = "all-MiniLM-L6-v2"
CROSS_ENCODER = "cross-encoder/ms-marco-MiniLM-L-6-v2"

RRF_K = 60
FUSE_DEPTH = 20          # per retriever, before fusion
RERANK_DEPTH = 10        # fused candidates handed to the cross-encoder

TOP_SCORE_THRESHOLD = 0.45
MARGIN_THRESHOLD = 0.10
# Above this the cross-encoder is saturated: near-identical scores mean several
# genuinely applicable standards (common within one IS family), not ambiguity.
# Applying the margin rule here abstained on correct #1 hits scoring 0.96-1.00.
HIGH_CONFIDENCE = 0.80

# MiniLM truncates at 256 word-pieces. A 120 KB spec pasted whole is silently
# embedded on its opening fragment and then scores 0.02 against everything, so
# the gate abstains with "no close match" — technically safe, but the officer
# is told the wrong reason. Cap it here and say so instead.
MAX_QUERY_CHARS = 2000

_state = {}


def _conn():
    c = sqlite3.connect(DB_PATH)
    c.row_factory = sqlite3.Row
    return c


def _tokens(text: str) -> list[str]:
    return re.findall(r"[a-z0-9]+", (text or "").lower())


def _load():
    """Corpus, dense vectors and BM25 index. Built once per process."""
    if _state:
        return _state
    conn = _conn()
    try:
        rows = [dict(r) for r in conn.execute("SELECT * FROM standards").fetchall()]
    finally:
        conn.close()

    order = pd.read_csv(IS_NUMBERS_PATH, encoding="utf-8-sig")["IS Number"].tolist()
    by_is = {r["IS Number"]: r for r in rows}
    corpus = [by_is[i] for i in order if i in by_is]

    blobs = [
        f"{r['IS Number']} — {r.get('Full Title') or ''} — {r.get('Product Family') or ''}"
        for r in corpus
    ]
    _state.update(
        corpus=corpus,
        blobs=blobs,
        vectors=np.load(EMBEDDINGS_PATH),
        bm25=BM25Okapi([_tokens(b) for b in blobs]),
        bi=None,
        cross=None,
    )
    return _state


def _bi():
    s = _load()
    if s["bi"] is None:
        s["bi"] = SentenceTransformer(BI_ENCODER)
    return s["bi"]


# A 512 MB host cannot hold both encoders comfortably. With MANAK_LIGHT=1 the
# cross-encoder is skipped and the fused RRF score carries the ranking instead.
# Retrieval is measurably worse without it — that is the trade, and the /health
# response says which mode is running so nobody has to guess.
LIGHT_MODE = os.getenv("MANAK_LIGHT") == "1"


def _cross():
    if LIGHT_MODE:
        return None
    s = _load()
    if s["cross"] is None:
        s["cross"] = CrossEncoder(CROSS_ENCODER)
    return s["cross"]


def _sigmoid(x: float) -> float:
    return float(1 / (1 + np.exp(-x)))


def _matched_field(query: str, row: dict) -> dict:
    """Which stored field actually justifies this candidate. Shown in the UI so
    a recommendation can never be a bare score."""
    q = set(_tokens(query))
    best = {"field": "IS Number", "terms": []}
    if re.search(r"\bIS[:\s]*" + re.escape(str(row["IS Number"]).split()[-1]), query, re.I):
        return {"field": "IS Number", "terms": [row["IS Number"]]}
    for field in ("Full Title", "Product Family"):
        terms = sorted(q & set(_tokens(row.get(field) or "")))
        if len(terms) > len(best["terms"]):
            best = {"field": field, "terms": terms}
    return best


def _rrf(rankings: list[list[int]]) -> dict[int, float]:
    fused: dict[int, float] = {}
    for ranking in rankings:
        for rank, idx in enumerate(ranking):
            fused[idx] = fused.get(idx, 0.0) + 1.0 / (RRF_K + rank + 1)
    return fused


def clip_query(query: str) -> tuple[str, dict]:
    """Trim to the model's usable window, at a sentence boundary where one is
    near, and report what was dropped."""
    text = (query or "").strip()
    if len(text) <= MAX_QUERY_CHARS:
        return text, {"truncated": False, "characters": len(text)}
    head = text[:MAX_QUERY_CHARS]
    cut = max(head.rfind(". "), head.rfind("\n"))
    if cut > MAX_QUERY_CHARS * 0.6:
        head = head[: cut + 1]
    return head.strip(), {
        "truncated": True,
        "characters": len(text),
        "characters_read": len(head.strip()),
        "note": (
            f"Only the first {len(head.strip()):,} of {len(text):,} characters were matched — "
            "the encoder's context window ends there. Run the remaining sections separately, "
            "or paste the single clause you want a standard for."
        ),
    }


def search(query: str, boost: str | None = None) -> list[dict]:
    """Fused, reranked candidates. Highest calibrated relevance first.

    `boost` is the register's own vocabulary for any abbreviation in the query.
    Appending it to the query simply diluted it — "GI" expanded correctly to
    "steel tubes tubulars", but "pipes for water supply" outweighed it and the
    top hit was a GRP pipe standard. Given its own ranking and fused by RRF, the
    expansion gets a vote instead of a whisper."""
    s = _load()
    corpus, vectors = s["corpus"], s["vectors"]

    qv = _bi().encode([query], normalize_embeddings=True)[0]
    dense_scores = vectors @ qv
    dense_rank = list(np.argsort(dense_scores)[::-1][:FUSE_DEPTH])

    bm_scores = s["bm25"].get_scores(_tokens(query))
    bm_rank = list(np.argsort(bm_scores)[::-1][:FUSE_DEPTH])

    rankings = [dense_rank, bm_rank]
    if boost:
        bv = _bi().encode([boost], normalize_embeddings=True)[0]
        rankings.append(list(np.argsort(vectors @ bv)[::-1][:FUSE_DEPTH]))
        rankings.append(list(np.argsort(s["bm25"].get_scores(_tokens(boost)))[::-1][:FUSE_DEPTH]))

    fused = _rrf(rankings)
    shortlist = sorted(fused, key=fused.get, reverse=True)[:RERANK_DEPTH]

    cross = _cross()
    if cross is None:
        # Fused rank stands in for a reranked score, normalised to 0-1 so the
        # confidence gate keeps working on the same scale.
        top = max((fused[i] for i in shortlist), default=1.0) or 1.0
        logits = [np.log(max(fused[i] / top, 1e-6) / max(1 - fused[i] / top, 1e-6))
                  for i in shortlist]
    else:
        pairs = [(query, s["blobs"][i]) for i in shortlist]
        logits = cross.predict(pairs)

    out = []
    for idx, logit in zip(shortlist, logits):
        row = corpus[idx]
        out.append(
            {
                "is_number": row["IS Number"],
                "title": row.get("Full Title"),
                "year": row.get("Year"),
                "status": row.get("Status"),
                "product_family": row.get("Product Family"),
                # BIS's own review date for this edition. Not an amendment — BIS
                # does not publish amendment numbers through this catalogue — but
                # a date in the past means the edition is overdue for revision and
                # the citation is worth confirming before publication.
                "review_due": row.get("Review Due"),
                "review_overdue": row.get("Overdue") == "Yes",
                "score": round(_sigmoid(float(logit)), 4),
                "dense_rank": dense_rank.index(idx) + 1 if idx in dense_rank else None,
                "bm25_rank": bm_rank.index(idx) + 1 if idx in bm_rank else None,
                "rrf": round(fused[idx], 5),
                "matched_on": _matched_field(query, row),
            }
        )
    out.sort(key=lambda c: c["score"], reverse=True)
    out, _ = _apply_voltage_filter(query, out)
    _rank_candidates(out)
    return out


def _gate(candidates: list[dict], stated_voltage: float | None = None) -> dict:
    """Pure logic. Abstaining is a valid, visible outcome — never a blank."""
    if not candidates:
        return {"decision": "abstain", "reason": "no_candidates"}
    top = candidates[0]["score"]
    second = candidates[1]["score"] if len(candidates) > 1 else 0.0
    if top < TOP_SCORE_THRESHOLD:
        return {"decision": "abstain", "reason": "no_close_match"}
    if top < HIGH_CONFIDENCE and (top - second) < MARGIN_THRESHOLD:
        return {"decision": "abstain", "reason": "ambiguous_match"}
    # Only ambiguous when the spec genuinely omits the voltage. Firing this on a
    # query that says "11 kV" told the officer to supply a figure they had
    # already supplied.
    if stated_voltage is None and _parts_tied_on_voltage(candidates):
        return {"decision": "abstain", "reason": "voltage_unspecified"}
    return {"decision": "recommend", "reason": "clear_match"}


def _parts_tied_on_voltage(candidates: list[dict]) -> bool:
    """Two parts of one standard, tied at the top, split only by a voltage the
    spec never states. Picking either is a coin flip presented as an answer;
    asking for the rating is the correct behaviour and takes the officer four
    seconds."""
    if len(candidates) < 2:
        return False
    a, b = candidates[0], candidates[1]
    if abs(a["score"] - b["score"]) >= MARGIN_THRESHOLD:
        return False
    if _base_is(a["is_number"]) != _base_is(b["is_number"]):
        return False
    ra = declared_voltage_range(a.get("title") or "")
    rb = declared_voltage_range(b.get("title") or "")
    return ra is not None and rb is not None and ra != rb


def _base_is(is_number: str) -> str:
    return re.sub(r"\s+", " ", str(is_number).split("(")[0]).strip()


IS_IN_TEXT = re.compile(
    r"\bIS[:\s]*(\d{2,6})(?:\s*\([^)]{0,40}\))?(?:\s*[:\-]\s*((?:19|20)\d{2}))?", re.I
)


def subset_guard(
    text: str, allowed: list[str], years: dict[str, str] | None = None
) -> tuple[bool, list[str]]:
    """Every IS number in composed prose must come from the retrieved set — and
    where the prose states an edition year, that year must be the retrieved one.

    The year matters as much as the number. "IS 4985:2012" reads as authoritative
    and is wrong; a guard that only checked the digits after "IS" would have shown
    a green tick beside a fabricated edition. Enforced in code, because a prompt
    instruction is not a guarantee."""
    allowed_bases = {re.sub(r"[^0-9]", "", a.split("(")[0]) for a in allowed}
    known = {
        re.sub(r"[^0-9]", "", k.split("(")[0]): str(v).split(".")[0]
        for k, v in (years or {}).items()
        if v and str(v).strip() and str(v).lower() != "nan"
    }
    leaked = []
    for base, year in IS_IN_TEXT.findall(text):
        digits = re.sub(r"[^0-9]", "", base)
        if digits and digits not in allowed_bases:
            leaked.append(f"IS {base}")
        elif year and digits in known and year != known[digits]:
            leaked.append(f"IS {base}:{year} (register says {known[digits]})")
    return (not leaked), leaked


def compose_clause(governing: dict, related: list[dict], cert: dict, use_llm: bool = True) -> dict:
    """Deterministic composition, optionally rephrased by a local LLM.

    The template runs first and always. If a model is available its output has to
    survive the subset guard and name the governing standard before it is used;
    otherwise the template stands and `composed_by` says which one you got. The
    facts are identical either way — only the prose differs."""
    cited = [governing["is_number"]] + [r["target_is"] for r in related]
    year = governing.get("year")
    family = governing.get("product_family") or "material"
    # Lower-case the first letter for mid-sentence use, but never an acronym:
    # "LED lighting" must not become "lED lighting".
    if not (len(family) > 1 and family[1].isupper()):
        family = family[0].lower() + family[1:]
    head = (
        f"The {family} supplied under this "
        f"contract shall conform in all respects to {governing['is_number']}"
        f"{f' : {year}' if year and str(year).isdigit() else ''}"
        f" ({governing.get('title')})."
    )
    parts = [head]
    if related:
        listed = ", ".join(r["target_is"] for r in related[:4])
        parts.append(
            f"The following standards are cited alongside {governing['is_number']} in comparable "
            f"published tenders and shall be reviewed for applicability to this procurement: "
            f"{listed}. Their inclusion here records observed procurement practice, not a "
            "determination that each one governs this item."
        )
    if cert.get("found") and cert.get("certification_mandatory") == "Yes":
        parts.append(
            f"The product falls under mandatory BIS certification ({cert.get('scheme')}); "
            "only material bearing a valid BIS Standard Mark shall be accepted."
        )
    if governing.get("status") in ("Superseded", "Withdrawn"):
        parts.append(
            f"Note: {governing['is_number']} is recorded as {governing['status']} and must be "
            "confirmed against the current BIS listing before publication."
        )
    years = {governing["is_number"]: governing.get("year")}
    text = " ".join(parts)
    ok, leaked = subset_guard(text, cited, years)
    result = {
        "text": text,
        "composed_by": "template",
        "cited_standards": cited,
        "subset_guard": {"passed": ok, "leaked": leaked},
    }
    if not use_llm:
        return result

    import llm

    attempt = llm.phrase(governing, related, cert, cited, years)
    if attempt.get("ok"):
        guard_ok, guard_leaked = subset_guard(attempt["text"], cited, years)
        result.update(
            text=attempt["text"],
            composed_by="llm",
            model=attempt.get("model"),
            generation_ms=attempt.get("duration_ms"),
            template_text=text,          # kept, so the two are comparable on screen
            subset_guard={"passed": guard_ok, "leaked": guard_leaked},
        )
    else:
        # A rejected generation is the guard doing its job, so it is shown rather
        # than swallowed: without the text you cannot tell a working model from a
        # dead one, and you cannot tell a real catch from an over-strict rule.
        result["llm"] = {
            "used": False,
            "reason": attempt.get("reason"),
            "detail": attempt.get("detail"),
            "rejected_text": attempt.get("rejected_text"),
            "model": attempt.get("model"),
        }
    return result


def recommend(query: str, ui_language: str | None = None) -> dict:
    """Forward flow end to end."""
    from engine import check_certification, related_standards

    import multilingual
    import normalize

    # Multilingual input: a spec written in an Indian language is translated to
    # English first, because the register is published in English. The original
    # is kept and returned so the officer can see what was actually matched.
    lang = multilingual.translate_query(query, ui_language)
    query = lang["text"]

    query, clipped = clip_query(query)
    # Orchestration: give retrieval the register's own vocabulary before it runs.
    # The officer's words are kept; the register's are appended.
    # Retrieval AND the cross-encoder both see the expanded text. Giving the
    # expansion its own RRF ranking instead was tried and was worse: the reranker
    # still scored against the original wording, so expansion-found candidates
    # were retrieved and then immediately discarded.
    expanded, applied = normalize.expand(query)
    candidates = search(expanded)
    candidates, voltage_filter = _apply_voltage_filter(query, candidates)
    candidates, material_filter = _apply_material_filter(query, candidates)
    candidates, role_filter = _apply_role_filter(query, candidates)
    _rank_candidates(candidates)
    gate = _gate(candidates, stated_voltage=voltage_filter.get("query_voltage_v"))
    result = {
        "query": query,
        "decision": gate["decision"],
        "reason": gate["reason"],
        "thresholds": {
            "top_score": TOP_SCORE_THRESHOLD,
            "margin": MARGIN_THRESHOLD,
            "high_confidence": HIGH_CONFIDENCE,
        },
        "candidates": candidates[:5],
        "voltage_filter": voltage_filter,
        "material_filter": material_filter,
        "role_filter": role_filter,
        "input": clipped,
        "language": lang,
        "normalization": {
            "applied": bool(applied),
            "terms": applied,
            "note": (
                "Trade abbreviations were expanded into the register's own wording before "
                "retrieval. The original text was kept, not replaced."
            ) if applied else None,
        },
    }
    if gate["decision"] == "abstain":
        result["message"] = {
            "no_close_match": "No candidate cleared the relevance threshold. "
            "Shown for reference only — route to a BIS officer.",
            "ambiguous_match": "Top candidates are too close to separate. "
            "A human must choose between them.",
            "no_candidates": "Nothing retrieved for this text.",
            "voltage_unspecified": (
                "Two parts of the same standard cover this product, separated only by working "
                "voltage, and the specification does not state one. Add the voltage rating "
                "(for example \u201c1.1 kV\u201d or \u201c11 kV\u201d) and re-run."
            ),
        }[gate["reason"]]
        return result

    gov = candidates[0]
    related = related_standards(gov["is_number"], limit=12)
    cert = check_certification(gov["is_number"])
    import allied
    from engine import standard_titles

    result.update(
        governing=gov,
        related=related[:6],
        allied=allied.classify(related, standard_titles([r["target_is"] for r in related])),
        certification=cert,
        clause=compose_clause(gov, related, cert),
    )
    return result


# ------------------------------------------------------- role constraints

# A specification describes a product, so it wants a product standard. Retrieval
# does not know that: "galvanized iron pipes for water supply" returned IS 11906,
# "Recommendations for cement mortar lining for ... pipes" — right subject, wrong
# kind of document. Roles are already readable from BIS titles (allied.py), so
# the same reading is used here to keep a code of practice or a test method from
# outranking the product standard the officer actually asked for.
ROLE_SEEKING = {
    "test_method": [r"\bmethod of test\b", r"\btest method\b", r"\btesting\b", r"\bsampling\b"],
    "installation": [r"\bcode of practice\b", r"\binstallation\b", r"\blaying\b",
                     r"\berection\b", r"\bmaintenance\b"],
    "terminology": [r"\bglossary\b", r"\bterminolog", r"\bdefinitions?\b"],
    "safety": [r"\bsafety requirements?\b"],
}
_SEEK_RE = {k: [re.compile(p, re.I) for p in v] for k, v in ROLE_SEEKING.items()}


def _wanted_role(query: str) -> str:
    """What kind of document the spec is asking for. A plain product description
    asks for a product standard, which is the common case."""
    for role, patterns in _SEEK_RE.items():
        if any(p.search(query or "") for p in patterns):
            return role
    return "product"


def _apply_role_filter(query: str, candidates: list[dict]) -> tuple[list[dict], dict]:
    """Demote documents of the wrong kind. Scores untouched, as with the others."""
    import allied

    wanted = _wanted_role(query)
    mismatched = 0
    for c in candidates:
        role, label = allied.role_of(c.get("title") or "")
        agrees = role == wanted or role == "product" and wanted == "product"
        # Only two roles are never the product specification: a glossary and a
        # code of practice. Demoting more than that cost real answers — nine of
        # the seventy-one evaluation targets are titled "safety", "test" or
        # "recommendations" and are still the governing standard for their
        # product ("Leather safety boots and shoes for miners" is classified
        # safety by its own name). Recall fell 92% to 87% and abstention rose to
        # 17% before this was narrowed.
        if wanted == "product" and role not in ("terminology", "installation"):
            agrees = True
        mismatched += 0 if agrees else 1
        c["role"] = {"of_candidate": role, "label": label, "wanted": wanted,
                     "verdict": "match" if agrees else "wrong_kind"}
    return candidates, {
        "applied": True, "wanted": wanted, "demoted": mismatched,
        "note": (
            f"The specification asks for a {wanted.replace('_', ' ')} standard. "
            "Test methods, glossaries and codes of practice were moved below product "
            "standards. Scores are unchanged."
        ) if mismatched else None,
    }


# ------------------------------------------------------- material constraints

# A specification names a material, and the register names it too. Semantic
# similarity does not separate them: "uPVC pipe for drinking water" scored CPVC
# and UPVC identically at 0.995, "GI pipes" returned glass-fibre reinforced
# plastic, and "reinforced cement concrete pipes" returned asbestos-cement. Every
# one of those is the same failure — a near-synonym of the product with the wrong
# substance. Materials are named explicitly in titles, so they can be read.
MATERIALS = {
    "cpvc": [r"\bCPVC\b", r"chlorinated\s+poly"],
    "upvc": [r"\bU-?PVC\b", r"\bPVC-?U\b", r"unplastici[sz]ed"],
    "pvc": [r"\bPVC\b", r"polyvinyl\s+chloride"],
    "xlpe": [r"\bXLPE\b", r"cross-?\s?linked\s+polyethylene"],
    "hdpe": [r"\bHDPE\b", r"high\s+density\s+polyethylene"],
    "ldpe": [r"\bLDPE\b", r"low\s+density\s+polyethylene"],
    "grp": [r"\bGRP\b", r"\bFRP\b", r"glass-?\s?fibre\s+reinforced"],
    "concrete": [r"\bconcrete\b", r"\bcement\s+concrete\b"],
    "asbestos": [r"\basbestos\b"],
    "cast_iron": [r"\bcast\s+iron\b", r"\bCI\b"],
    "ductile_iron": [r"\bductile\s+iron\b"],
    "steel": [r"\bgalvani[sz]ed\b", r"\bsteel\s+tube", r"\bmild\s+steel\b", r"\bGI\b"],
    "elastomer": [r"\belastomer\b", r"\brubber\b"],
}
# Materials that are genuinely compatible: naming the broader one should not
# exclude the narrower. Everything else is treated as a conflict.
COMPATIBLE = {("pvc", "upvc"), ("upvc", "pvc"), ("pvc", "cpvc"), ("cpvc", "pvc")}

_MATERIAL_RE = {k: [re.compile(p, re.I) for p in pats] for k, pats in MATERIALS.items()}


def materials_in(text: str) -> set[str]:
    found = set()
    for name, patterns in _MATERIAL_RE.items():
        if any(p.search(text or "") for p in patterns):
            found.add(name)
    # "unplasticized PVC" is UPVC, not bare PVC; the specific reading wins.
    if "upvc" in found or "cpvc" in found:
        found.discard("pvc")
    return found


def _apply_material_filter(query: str, candidates: list[dict]) -> tuple[list[dict], dict]:
    """Demote candidates whose title names a material the spec did not ask for.

    Scores are untouched, exactly as with the voltage filter: the candidate keeps
    what the cross-encoder gave it and carries a visible verdict, so the reordering
    can be audited rather than taken on trust."""
    wanted = materials_in(query)
    if not wanted:
        return candidates, {"applied": False, "query_materials": []}

    conflicts = 0
    for c in candidates:
        theirs = materials_in(c.get("title") or "")
        if not theirs:
            c["material"] = {"declared": None, "verdict": "not_declared"}
            continue
        agrees = bool(theirs & wanted) or any(
            (w, t) in COMPATIBLE for w in wanted for t in theirs
        )
        conflicts += 0 if agrees else 1
        c["material"] = {
            "declared": sorted(theirs),
            "verdict": "match" if agrees else "different_material",
        }

    return candidates, {
        "applied": True,
        "query_materials": sorted(wanted),
        "demoted": conflicts,
        "note": (
            f"Specification names {', '.join(sorted(wanted))}. Candidates whose title "
            "declares a different material were moved below those that match. Scores "
            "are unchanged."
        ),
    }


# ------------------------------------------------------- numeric constraints

_NUM = r"\d[\d\s]*(?:\.\d+)?"


def _volts(value: str, unit: str) -> float:
    v = float(re.sub(r"\s+", "", value))          # titles write "1 100 V"
    return v * 1000 if unit.lower() == "kv" else v


_RANGE_FROM = re.compile(
    rf"from\s+({_NUM})\s*(kV|V)\b.{{0,40}}?up\s*to\s+and\s+including\s+({_NUM})\s*(kV|V)\b", re.I
)
_RANGE_UPTO = re.compile(
    rf"up\s*to\s+and\s+including\s+({_NUM})\s*(kV|V)\b", re.I
)


def declared_voltage_range(title: str) -> tuple[float, float] | None:
    """The voltage band an IS part declares in its own title.

    IS 1554 Part 1 covers up to 1100 V and Part 2 covers 3.3-11 kV. The
    cross-encoder scores both nearly identically for '1.1 kV cable' because the
    titles differ by a number, and no amount of semantic similarity distinguishes
    numbers. Parsing the band and checking it is the only fix that actually works."""
    if not title:
        return None
    m = _RANGE_FROM.search(title)
    if m:
        return _volts(m.group(1), m.group(2)), _volts(m.group(3), m.group(4))
    m = _RANGE_UPTO.search(title)
    if m:
        return 0.0, _volts(m.group(1), m.group(2))
    return None


_QUERY_VOLT = re.compile(rf"({_NUM})\s*(kV|V)\b")


def query_voltage(query: str) -> float | None:
    """Highest voltage stated in the spec text. '650/1100 V' is a rating pair;
    the upper figure is the one a standard's band is written against."""
    found = [_volts(m.group(1), m.group(2)) for m in _QUERY_VOLT.finditer(query or "")]
    found = [v for v in found if v > 0]
    return max(found) if found else None


V_RANK = {"in_band": 0, "not_declared": 1, "out_of_band": 2}
M_RANK = {"match": 0, "not_declared": 1, "different_material": 2}
R_RANK = {"match": 0, "wrong_kind": 1}
# A live standard outranks a dead one at equal relevance. "PVC insulated heavy
# duty cable" scored IS 4288 (Withdrawn) and IS 1554 identically at 1.000 and
# returned the withdrawn one — this system exists to catch exactly that mistake
# in other people's tenders, so it must not make it in its own recommendation.
S_RANK = {"Current": 0, "Superseded": 1, "Withdrawn": 2}


def _rank_candidates(candidates: list[dict]) -> None:
    """One sort, after every filter has had its say.

    Each filter used to sort on its own key the moment it ran, so whichever ran
    last silently overwrote the others: the material filter promoted an
    out-of-band IS 7098 (Part 3) above the in-band Part 2 purely because it
    scored higher. Constraints have to be combined, not applied in sequence."""
    candidates.sort(key=lambda c: (
        V_RANK.get((c.get("voltage") or {}).get("verdict", "not_declared"), 1),
        M_RANK.get((c.get("material") or {}).get("verdict", "not_declared"), 1),
        R_RANK.get((c.get("role") or {}).get("verdict", "match"), 0),
        S_RANK.get(c.get("status"), 0),
        -c["score"],
    ))


def _apply_voltage_filter(query: str, candidates: list[dict]) -> tuple[list[dict], dict]:
    """Demote candidates whose declared band excludes the stated voltage.

    Scores are left untouched — a silently rewritten score is unauditable. The
    candidate keeps its cross-encoder score and carries a visible verdict, and
    ordering puts out-of-band parts last."""
    qv = query_voltage(query)
    if qv is None:
        return candidates, {"applied": False, "query_voltage_v": None}

    excluded = 0
    for c in candidates:
        band = declared_voltage_range(c.get("title") or "")
        if band is None:
            c["voltage"] = {"declared": None, "verdict": "not_declared"}
            continue
        low, high = band
        inside = low <= qv <= high
        excluded += 0 if inside else 1
        c["voltage"] = {
            "declared": f"{low:g}-{high:g} V" if low else f"up to {high:g} V",
            "low_v": low,
            "high_v": high,
            "verdict": "in_band" if inside else "out_of_band",
        }

    return candidates, {
        "applied": True,
        "query_voltage_v": qv,
        "demoted": excluded,
        "note": (
            f"Spec states {qv:g} V. Candidates whose title declares a voltage band excluding "
            "it were moved below those that cover it. Scores are unchanged."
        ),
    }
