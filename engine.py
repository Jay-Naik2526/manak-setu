import sqlite3

import numpy as np
import pandas as pd
from sentence_transformers import SentenceTransformer

DB_PATH = "manak_setu.db"
EMBEDDINGS_PATH = "standards_embeddings.npy"
IS_NUMBERS_PATH = "standards_embeddings_is_numbers.csv"
MODEL_NAME = "all-MiniLM-L6-v2"

_model = None
_embeddings = None
_is_numbers = None


def _get_model():
    global _model
    if _model is None:
        _model = SentenceTransformer(MODEL_NAME)
    return _model


def _get_embeddings():
    global _embeddings, _is_numbers
    if _embeddings is None:
        _embeddings = np.load(EMBEDDINGS_PATH)
        _is_numbers = pd.read_csv(IS_NUMBERS_PATH, encoding="utf-8-sig")["IS Number"].tolist()
    return _embeddings, _is_numbers


def _get_conn():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def _is_base(is_number: str) -> str:
    return is_number.split("(")[0].strip()


def _is_digits(is_number: str) -> str:
    """The bare number, prefix and edition stripped: 'IS/IEC 60947 (Part 1):2020'
    and 'IS 60947' are the same standard and must resolve to the same row."""
    import re as _re

    return _re.sub(r"[^0-9]", "", str(is_number).split("(")[0].split(":")[0])


def _resolve_standard(conn, is_number: str):
    """exact -> base -> bare number. Returns (row, how_it_matched)."""
    row = conn.execute('SELECT * FROM standards WHERE "IS Number" = ?', (is_number,)).fetchone()
    if row is not None:
        return row, "exact"
    row = conn.execute(
        'SELECT * FROM standards WHERE "IS Base" = ?', (_is_base(is_number),)
    ).fetchone()
    if row is not None:
        return row, "is_base_fallback"
    digits = _is_digits(is_number)
    if digits:
        row = conn.execute(
            'SELECT * FROM standards WHERE "IS Digits" = ? ORDER BY "IS Number" LIMIT 1',
            (digits,),
        ).fetchone()
        if row is not None:
            return row, "number_fallback"
    return None, None


def _display(value):
    return value if pd.notna(value) else "N/A"


def _confidence_label(score: float) -> str:
    if score >= 0.65:
        return "High"
    if score >= 0.40:
        return "Medium"
    return "Low - route to BIS office"


def match_spec(query_text: str, top_k: int = 5) -> dict:
    model = _get_model()
    embeddings, is_numbers = _get_embeddings()

    query_vec = model.encode([query_text], normalize_embeddings=True)[0]
    scores = embeddings @ query_vec

    top_idx = np.argsort(scores)[::-1][:top_k]
    matches = [{"is_number": is_numbers[i], "score": round(float(scores[i]), 4)} for i in top_idx]

    top_score = matches[0]["score"] if matches else 0.0
    confidence = _confidence_label(top_score)

    result = {"matches": matches, "confidence": confidence}
    if confidence == "Low - route to BIS office":
        result["message"] = (
            "No confident match found for this spec. Top candidates are shown for "
            "reference only — route to a BIS office for manual verification."
        )
    return result


def check_dead_citation(is_number: str) -> dict:
    conn = _get_conn()
    try:
        row, _ = _resolve_standard(conn, is_number)
        if row is None:
            return {"found": False}

        status = row["Status"]
        if status in ("Superseded", "Withdrawn"):
            replaced_by = row["Replaced By"]
            return {
                "found": True,
                "dead": True,
                "status": status,
                "replaced_by": replaced_by if pd.notna(replaced_by) else "UNKNOWN",
            }
        return {"found": True, "dead": False, "status": status}
    finally:
        conn.close()


def related_standards(is_number: str, limit: int = 5) -> list[dict]:
    """Co-cited standards for this one.

    The graph is keyed on the numbers tenders actually write — "IS 1554" — while
    retrieval returns the register's designation, "IS 1554 (Part 1)". Matching
    only on the exact string returned nothing for every part-suffixed standard,
    so the co-citation panel sat empty on exactly the standards that have parts.
    """
    conn = _get_conn()
    try:
        rows = conn.execute(
            '''SELECT "Target IS", "Confidence", "Lift", "Evidence Statement"
               FROM co_citation
               WHERE "Source IS" = ? OR "Source IS" = ?
               ORDER BY "Confidence" DESC
               LIMIT ?''',
            (is_number, _is_base(is_number), limit),
        ).fetchall()
        if not rows:
            digits = _is_digits(is_number)
            rows = conn.execute(
                '''SELECT "Target IS", "Confidence", "Lift", "Evidence Statement"
                   FROM co_citation
                   WHERE REPLACE(REPLACE(SUBSTR("Source IS", 1,
                         CASE WHEN INSTR("Source IS", '(') > 0
                              THEN INSTR("Source IS", '(') - 1 ELSE LENGTH("Source IS") END),
                         'IS ', ''), ' ', '') = ?
                   ORDER BY "Confidence" DESC LIMIT ?''',
                (digits, limit),
            ).fetchall()
        return [
            {
                "target_is": r["Target IS"],
                "confidence": r["Confidence"],
                "lift": r["Lift"],
                "evidence_statement": r["Evidence Statement"],
            }
            for r in rows
        ]
    finally:
        conn.close()


def check_certification(is_number: str) -> dict:
    conn = _get_conn()
    try:
        row = conn.execute(
            'SELECT * FROM certification_rules WHERE "IS Number" = ?', (is_number,)
        ).fetchone()
        if row is None:
            row = conn.execute(
                'SELECT * FROM certification_rules WHERE "IS Base" = ?', (_is_base(is_number),)
            ).fetchone()
        if row is None:
            return {"found": False}

        return {
            "found": True,
            "certification_mandatory": row["Certification Mandatory"],
            "scheme": row["Scheme"],
            "notification_reference": _display(row["Notification Reference"]),
        }
    finally:
        conn.close()


def full_graph(node_limit: int | None = None, edge_limit: int | None = None) -> dict:
    """Co-citation graph scoped to real data only: the 74 standards that
    actually appear in co_citation_graph.csv, not all 405 standards.
    Each node is enriched with title/status/product family from
    standards_master.csv where a match exists (exact, then IS Base)."""
    conn = _get_conn()
    try:
        rows = conn.execute(
            'SELECT "Source IS", "Target IS", "Confidence", "Lift", "Co-citation Count", '
            '"Evidence Statement" FROM co_citation'
        ).fetchall()

        # A caller that only needs a representative sample (the overview hero)
        # should not download the whole corpus: the full payload is ~600 KB, which
        # dominates page load over anything slower than localhost.
        if node_limit:
            degree: dict[str, int] = {}
            for r in rows:
                degree[r["Source IS"]] = degree.get(r["Source IS"], 0) + 1
                degree[r["Target IS"]] = degree.get(r["Target IS"], 0) + 1
            keep = {
                k for k, _ in sorted(degree.items(), key=lambda kv: -kv[1])[:node_limit]
            }
            rows = [r for r in rows if r["Source IS"] in keep and r["Target IS"] in keep]
        if edge_limit:
            rows = sorted(rows, key=lambda r: -r["Confidence"])[:edge_limit]

        node_ids = sorted({r["Source IS"] for r in rows} | {r["Target IS"] for r in rows})

        nodes = []
        for node_id in node_ids:
            std = conn.execute(
                'SELECT * FROM standards WHERE "IS Number" = ?', (node_id,)
            ).fetchone()
            if std is None:
                std = conn.execute(
                    'SELECT * FROM standards WHERE "IS Base" = ?', (_is_base(node_id),)
                ).fetchone()
            nodes.append(
                {
                    "id": node_id,
                    "title": _display(std["Full Title"]) if std else "N/A",
                    "status": std["Status"] if std else "Unknown",
                    "product_family": _display(std["Product Family"]) if std else "N/A",
                    "in_standards_master": std is not None,
                }
            )

        edges = [
            {
                "source": r["Source IS"],
                "target": r["Target IS"],
                "confidence": r["Confidence"],
                "lift": r["Lift"],
                "co_citation_count": r["Co-citation Count"],
                "evidence_statement": r["Evidence Statement"],
            }
            for r in rows
        ]
        return {
            "nodes": nodes,
            "edges": edges,
            "sampled": bool(node_limit or edge_limit),
        }
    finally:
        conn.close()


def standard_titles(is_numbers: list[str]) -> dict[str, str]:
    """Titles for a set of IS numbers, resolved the same three ways as everything
    else — exact, base, then bare number."""
    out: dict[str, str] = {}
    conn = _get_conn()
    try:
        for n in is_numbers:
            row, _ = _resolve_standard(conn, n)
            if row is not None:
                out[n] = row["Full Title"] or ""
    finally:
        conn.close()
    return out


def list_standards() -> list[dict]:
    conn = _get_conn()
    try:
        rows = conn.execute(
            'SELECT "IS Number", "Full Title", "Year", "Status", "Replaced By", '
            '"Supersedes", "Product Family", "Priority", "Source Link" FROM standards'
        ).fetchall()
        return [{k: _display(row[k]) for k in row.keys()} for row in rows]
    finally:
        conn.close()


def list_certifications() -> list[dict]:
    conn = _get_conn()
    try:
        rows = conn.execute("SELECT * FROM certification_rules").fetchall()
        return [{k: _display(row[k]) for k in row.keys()} for row in rows]
    finally:
        conn.close()


def list_tenders() -> list[dict]:
    """Every tender, with a readable name derived from its filename.

    "Tender ID" stays exactly as collected — it is what links to the source
    document. "Title" is a formatting of it, and "title_derived" says whether the
    filename actually carried words, so the UI never presents an invented subject
    as if it were the document's real title."""
    from tender_titles import display_title

    conn = _get_conn()
    try:
        rows = conn.execute("SELECT * FROM tenders").fetchall()
        out = []
        for row in rows:
            d = {k: _display(row[k]) for k in row.keys()}
            # GeM bids carry their own product line ("Item Category") as the
            # portal prints it. That is the document's real name, so it is used
            # as-is; a filename-derived title is the fallback for the rest.
            category = (row["Item Category"] if "Item Category" in row.keys() else "") or ""
            if str(category).strip() and str(category).strip().lower() != "nan":
                d["Title"] = str(category).strip()
                d["title_derived"] = True
            else:
                name = display_title(row["Tender ID"], row["Product Family"])
                d["Title"] = name["title"]
                d["title_derived"] = name["derived"]
            out.append(d)
        return out
    finally:
        conn.close()


def list_backlog() -> list[dict]:
    conn = _get_conn()
    try:
        rows = conn.execute(
            'SELECT "Tenders Citing", "IS Number" FROM coverage_gap_backlog '
            'ORDER BY "Tenders Citing" DESC'
        ).fetchall()
        return [{"tenders_citing": r["Tenders Citing"], "is_number": r["IS Number"]} for r in rows]
    finally:
        conn.close()


def standard_detail(is_number: str) -> dict:
    conn = _get_conn()
    try:
        row, matched_by = _resolve_standard(conn, is_number)
        if row is None:
            return {"found": False, "is_number": is_number}
        detail = {k: _display(row[k]) for k in row.keys()}
    finally:
        conn.close()

    return {
        "found": True,
        "matched_by": matched_by,
        "standard": detail,
        "certification": check_certification(is_number),
        "related": related_standards(is_number, limit=12),
    }


def _count_by(conn, table: str, column: str) -> list[dict]:
    rows = conn.execute(
        f'SELECT "{column}" AS k, COUNT(*) AS n FROM {table} '
        f'GROUP BY "{column}" ORDER BY n DESC'
    ).fetchall()
    return [{"key": r["k"] if r["k"] is not None else "N/A", "count": r["n"]} for r in rows]


def corpus_stats() -> dict:
    """Every figure here is recomputed from the current database on each call —
    never copied from a previous run or a written report."""
    conn = _get_conn()
    try:
        usable_rows = conn.execute(
            'SELECT "IS Numbers Cited" FROM tenders WHERE "Usability" = ?', ("Usable",)
        ).fetchall()
        cited = set()
        for r in usable_rows:
            if r["IS Numbers Cited"]:
                for part in str(r["IS Numbers Cited"]).split(";"):
                    part = part.strip()
                    if part:
                        cited.add(part)

        std_rows = conn.execute(
            'SELECT "IS Number", "IS Base", "IS Digits" FROM standards'
        ).fetchall()
        exact_set = {r["IS Number"] for r in std_rows}
        base_set = {r["IS Base"] for r in std_rows}
        # Same three-step resolution the lookups and the backlog use. Without the
        # digit fallback here, this figure said 97.1% while the backlog said 99.0%
        # — two numbers for one fact, which is the failure this project is about.
        digit_set = {r["IS Digits"] for r in std_rows if r["IS Digits"]}
        matched = {
            c for c in cited
            if c in exact_set or _is_base(c) in base_set or _is_digits(c) in digit_set
        }

        years = conn.execute(
            'SELECT "Year" AS y, COUNT(*) AS n FROM standards GROUP BY "Year"'
        ).fetchall()
        decades: dict[str, int] = {}
        for r in years:
            try:
                decade = f"{int(r['y']) // 10 * 10}s"
            except (TypeError, ValueError):
                decade = "Unknown"
            decades[decade] = decades.get(decade, 0) + r["n"]

        edges = conn.execute(
            'SELECT "Source IS" AS s, "Target IS" AS t FROM co_citation'
        ).fetchall()
        degree: dict[str, int] = {}
        for e in edges:
            degree[e["s"]] = degree.get(e["s"], 0) + 1
            degree[e["t"]] = degree.get(e["t"], 0) + 1
        top_degree = sorted(degree.items(), key=lambda kv: kv[1], reverse=True)[:10]

        backlog_top = conn.execute(
            'SELECT "Tenders Citing" AS n, "IS Number" AS is_number FROM coverage_gap_backlog '
            'ORDER BY n DESC LIMIT 12'
        ).fetchall()

        return {
            "row_counts": {
                "standards": conn.execute("SELECT COUNT(*) FROM standards").fetchone()[0],
                "tenders": conn.execute("SELECT COUNT(*) FROM tenders").fetchone()[0],
                "co_citation": conn.execute("SELECT COUNT(*) FROM co_citation").fetchone()[0],
                "certification_rules": conn.execute(
                    "SELECT COUNT(*) FROM certification_rules"
                ).fetchone()[0],
                "coverage_gap_backlog": conn.execute(
                    "SELECT COUNT(*) FROM coverage_gap_backlog"
                ).fetchone()[0],
            },
            "standards_by_status": _count_by(conn, "standards", "Status"),
            "standards_by_family": _count_by(conn, "standards", "Product Family"),
            "standards_by_priority": _count_by(conn, "standards", "Priority"),
            "standards_by_decade": sorted(
                [{"key": k, "count": v} for k, v in decades.items()], key=lambda d: d["key"]
            ),
            "tenders_by_usability": _count_by(conn, "tenders", "Usability"),
            "tenders_by_family": _count_by(conn, "tenders", "Product Family"),
            "certs_by_scheme": _count_by(conn, "certification_rules", "Scheme"),
            "certs_by_mandatory": _count_by(conn, "certification_rules", "Certification Mandatory"),
            "coverage": {
                "usable_tenders": len(usable_rows),
                "any_outdated": conn.execute(
                    'SELECT COUNT(*) FROM tenders WHERE "Any Outdated" = ?', ("Yes",)
                ).fetchone()[0],
                "distinct_cited": len(cited),
                "matched": len(matched),
                "unmatched": len(cited) - len(matched),
                "pct": round(100 * len(matched) / len(cited), 1) if cited else 0.0,
                "denominator_note": (
                    "Distinct IS numbers cited across tenders with Usability='Usable' only. "
                    "Tenders marked Multi-scope / Not extractable / Extraction failed are excluded."
                ),
            },
            "graph": {
                "nodes": len(degree),
                "edges": len(edges),
                "top_degree": [{"is_number": k, "degree": v} for k, v in top_degree],
            },
            "backlog_top": [
                {"is_number": r["is_number"], "tenders_citing": r["n"]} for r in backlog_top
            ],
        }
    finally:
        conn.close()


def run_benchmark(sample_size: int = 20, seed: int = 42) -> dict:
    """Re-runs the golden benchmark live. Reports true/false positives and
    negatives explicitly — never a bare accuracy percentage."""
    import random

    conn = _get_conn()
    try:
        rows = conn.execute(
            'SELECT "Tender ID", "IS Numbers Cited", "Any Outdated" FROM tenders '
            "WHERE \"Usability\" = 'Usable' AND \"Any Outdated\" IN ('Yes','No')"
        ).fetchall()
    finally:
        conn.close()

    yes_rows = [r for r in rows if r["Any Outdated"] == "Yes"]
    no_rows = [r for r in rows if r["Any Outdated"] == "No"]
    rng = random.Random(seed)
    sampled_no = rng.sample(no_rows, min(sample_size, len(no_rows)))
    evaluated = yes_rows + sampled_no

    results = []
    tp = tn = fp = fn = 0
    for r in evaluated:
        cited = [s.strip() for s in str(r["IS Numbers Cited"] or "").split(";") if s.strip()]
        predicted = "No"
        hits = []
        for is_number in cited:
            check = check_dead_citation(is_number)
            if check.get("found") and check.get("dead"):
                predicted = "Yes"
                hits.append({"is_number": is_number, **check})
        actual = r["Any Outdated"]
        match = predicted == actual
        if actual == "Yes" and predicted == "Yes":
            tp += 1
        elif actual == "No" and predicted == "No":
            tn += 1
        elif actual == "No" and predicted == "Yes":
            fp += 1
        else:
            fn += 1
        results.append(
            {
                "tender_id": r["Tender ID"],
                "actual": actual,
                "predicted": predicted,
                "match": match,
                "dead_hits": hits,
            }
        )

    return {
        "evaluated": len(evaluated),
        "positives_in_set": len(yes_rows),
        "negatives_sampled": len(sampled_no),
        "true_positives": tp,
        "true_negatives": tn,
        "false_positives": fp,
        "false_negatives": fn,
        "mismatches": [r for r in results if not r["match"]],
        "honest_summary": (
            f"Caught {tp} of {len(yes_rows)} known outdated-citation tenders, with {fp} false "
            f"positives across {len(sampled_no)} sampled clean tenders (n={len(evaluated)}). "
            "Small positive class — not a general accuracy claim."
        ),
        "results": results,
    }


# "as per relevant IS" is tender boilerplate meaning "whichever Indian Standard
# applies" — it names nothing. In a table it is followed by the next row's
# number, and a pattern that reads "conforming to relevant IS 10." as a citation
# of IS 10 invents one. In one real GeM specification 59 of 97 matches were this,
# numbered consecutively 10 through 21: row numbers, not standards. Short IS
# numbers cannot simply be dropped — IS 10 through IS 25 are real BIS standards —
# so the generic phrase itself is what is excluded.
GENERIC_IS_PHRASE = r"(?<!\brelevant )(?<!\bapplicable )(?<!\brespective )(?<!\bappropriate )(?<!\bany other )"
IS_CITATION_PATTERN = GENERIC_IS_PHRASE + r"IS[:\s]*(\d{2,6})(?:\s*\(([^)]{0,40})\))?"


def extract_citations(text: str) -> list[str]:
    """Literal substring extraction of IS-number citations from supplied text.
    Nothing is inferred — a citation only appears if it is written in the text.
    Whitespace is collapsed and spelling variants of the same part reference
    (e.g. "Part-2/ Sec.-1" vs "Part 2/Sec 1") collapse to one entry."""
    import re

    found = []
    seen = set()
    for match in re.finditer(IS_CITATION_PATTERN, text, flags=re.IGNORECASE):
        number = match.group(1)
        raw_part = re.sub(r"\s+", " ", match.group(2)).strip() if match.group(2) else ""
        citation = f"IS {number} ({raw_part})" if raw_part else f"IS {number}"
        key = f"{number}|{re.sub(r'[^a-z0-9]', '', raw_part.lower())}"
        if key not in seen:
            seen.add(key)
            found.append(citation)
    return found


SCANNED_CHARS_PER_PAGE = 200
"""Below this a page is almost certainly a scan: pdfplumber returns the page's
text layer, and a photographed page has none. Tenders from smaller state PSUs are
routinely scans, and silently returning zero citations for one would be the worst
possible failure — it reads as 'this tender is clean'."""

MAX_PAGES = 60


def extract_pdf(file_bytes: bytes) -> dict:
    import io

    import pdfplumber

    pages = []
    with pdfplumber.open(io.BytesIO(file_bytes)) as pdf:
        page_count = len(pdf.pages)
        for page in pdf.pages[:MAX_PAGES]:
            pages.append(page.extract_text() or "")
    text = "\n".join(pages)
    per_page = len(text) / len(pages) if pages else 0.0
    scanned = bool(pages) and per_page < SCANNED_CHARS_PER_PAGE

    return {
        "format": "pdf",
        "page_count": page_count,
        "pages_read": len(pages),
        "characters": len(text),
        "chars_per_page": round(per_page, 1),
        "scanned": scanned,
        "scanned_note": (
            f"Only {per_page:.0f} characters per page were recoverable, below the "
            f"{SCANNED_CHARS_PER_PAGE}-character threshold. This document is very likely a scan "
            "with no text layer. Citations found below are whatever text existed and are almost "
            "certainly incomplete — do not read an empty result as a clean tender. Run OCR, or "
            "paste the specification text directly."
        ) if scanned else None,
        "text": text[:20000],
        "citations": extract_citations(text),
    }


def extract_docx(file_bytes: bytes) -> dict:
    """Tenders arrive as .docx as often as .pdf, and the tables are where the
    citations live — a paragraph-only read misses most of them."""
    import io

    import docx

    document = docx.Document(io.BytesIO(file_bytes))
    parts = [p.text for p in document.paragraphs if p.text.strip()]
    table_count = 0
    for table in document.tables:
        table_count += 1
        for row in table.rows:
            cells = [c.text.strip() for c in row.cells]
            if any(cells):
                parts.append(" | ".join(cells))
    text = "\n".join(parts)

    return {
        "format": "docx",
        "page_count": None,
        "paragraphs": len(document.paragraphs),
        "tables": table_count,
        "characters": len(text),
        "scanned": False,
        "scanned_note": None,
        "text": text[:20000],
        "citations": extract_citations(text),
    }


PDF_MAGIC = b"%PDF"
ZIP_MAGIC = b"PK\x03\x04"  # .docx is a zip container


def extract_document(file_bytes: bytes, filename: str | None = None) -> dict:
    """Sniff the container rather than trusting the extension — a .pdf that is
    really a .docx is a real thing that happens on procurement portals."""
    if file_bytes.startswith(PDF_MAGIC):
        result = extract_pdf(file_bytes)
    elif file_bytes.startswith(ZIP_MAGIC):
        result = extract_docx(file_bytes)
    else:
        raise ValueError(
            "Unrecognised file. Upload a PDF or a .docx, or paste the specification text."
        )
    result["filename"] = filename
    return result
