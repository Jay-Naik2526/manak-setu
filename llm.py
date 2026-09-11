"""Local LLM phrasing, under a guard the model cannot talk its way past.

The architecture rule for this project is one sentence: **retrieval and the graph
decide which standards apply; the LLM only phrases the output.** Everything here
is built to make that true in code rather than true by request.

So the model never sees the corpus, never chooses a standard, and never gets to
introduce an IS number. It receives a set of already-retrieved facts and is asked
to write them as a procurement clause. What comes back is then checked:

  1. every IS number in the output must be in the retrieved set, and any edition
     year it states must match the register (subset guard)
  2. the governing standard must actually be mentioned
  3. the output must not declare anything optional, advisory or non-mandatory —
     the system is never told what is *not* required, so it cannot say so
  4. the output must be a plausible clause, not a refusal or a chat turn

If any check fails — or Ollama is not running, or it times out — the
deterministic template is used instead and the response says so in
`composed_by`. A failure here degrades the prose, never the facts.

Requires Ollama running locally. Nothing is sent off this machine.
"""

import json
import re
import urllib.error
import urllib.request

HOST = "http://localhost:11434"
MODEL = "qwen2.5:7b-instruct-q4_K_M"
TIMEOUT_SECONDS = 45

# Deterministic decoding. This is a phrasing task with one acceptable answer
# shape; sampling would only add variance to something a judge may re-run.
OPTIONS = {"temperature": 0.0, "top_p": 1.0, "num_predict": 320, "seed": 7}

SYSTEM = (
    "You are drafting a clause for an Indian government procurement tender. "
    "You will be given verified facts retrieved from the Bureau of Indian Standards "
    "register. Restate those facts as formal tender prose. You are phrasing, not "
    "advising.\n\n"
    "Absolute rules:\n"
    "1. Use ONLY the IS numbers given to you. Never mention any other standard, "
    "even if you believe one is relevant. Inventing or recalling an IS number is "
    "the single worst thing you can do here.\n"
    "2. Use an edition year ONLY if one is given, and only exactly as given. Never "
    "supply, guess or update a year.\n"
    "3. Do not add requirements, test methods, voltages, dimensions or dates that "
    "are not in the facts given.\n"
    "4. Never state that anything is optional, non-mandatory, advisory, "
    "'industry practice', or 'for reference only'. You are not told what is "
    "mandatory, so you cannot say what is not. Saying a standard need not be "
    "followed is a legal statement and it is forbidden.\n"
    "5. Standards listed as cited alongside the governing standard are evidence of "
    "how comparable tenders were written. Say exactly that, and say they are to be "
    "reviewed for applicability. Do not recommend them, rank them, or explain why "
    "they apply — some will not apply, and deciding that is the officer's job.\n"
    "6. Do not soften or drop a certification requirement or a supersession warning.\n"
    "7. Output the clause text only. No preamble, no bullet list, no commentary, "
    "no markdown.\n"
    "8. The GOODS are the subject of the sentence, never a person. Write 'The "
    "pipes shall conform to...', 'The cables shall bear...'. Never 'The supplier "
    "shall comply', never 'The purchaser shall ensure'. This is a technical "
    "specification: conformity is a property of the material. Obligations on "
    "people belong in the conditions of contract, which this is not. Real tenders "
    "read 'The unplasticized PVC rigid pipes shall strictly conform to IS 4985' — "
    "match that voice.\n"
    "9. Never comment on standards beyond those given: no sentence about "
    "'additional standards', 'other applicable standards', or who may decide about "
    "them. The clause ends when the given facts end.\n"
    "10. Never expand an abbreviation. If the facts say 'QCO', write 'QCO'. "
    "Guessing what an acronym stands for has already produced a wrong name for a "
    "legal instrument.\n"
    "11. Sentence case throughout. Do not shout words in capitals.\n"
    "12. Two to four sentences. Formal, plain, and specific."
)

_state: dict = {}


def _post(path: str, payload: dict, timeout: int = TIMEOUT_SECONDS) -> dict:
    req = urllib.request.Request(
        HOST + path,
        data=json.dumps(payload).encode(),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return json.loads(resp.read())


def status() -> dict:
    """Is a usable model actually loaded? Reported in /health so a demo machine
    shows the truth rather than a hopeful default."""
    try:
        with urllib.request.urlopen(HOST + "/api/tags", timeout=3) as resp:
            tags = json.loads(resp.read())
    except (urllib.error.URLError, TimeoutError, OSError):
        return {
            "available": False,
            "reason": "ollama_not_running",
            "detail": f"No Ollama server at {HOST}. Clauses are composed from the template.",
            "model": MODEL,
        }

    names = [m.get("name", "") for m in tags.get("models", [])]
    if not any(n == MODEL or n.split(":")[0] == MODEL.split(":")[0] for n in names):
        return {
            "available": False,
            "reason": "model_not_pulled",
            "detail": f"Ollama is running but {MODEL} is not installed. Run: ollama pull {MODEL}",
            "model": MODEL,
            "installed": names,
        }
    return {"available": True, "model": MODEL, "installed": names}


def _facts_block(governing: dict, related: list[dict], cert: dict) -> str:
    """Exactly what the model is allowed to know. Nothing here is prose the model
    can reinterpret — they are retrieved field values."""
    lines = [
        "GOVERNING STANDARD",
        f"  number: {governing['is_number']}",
        f"  title: {governing.get('title')}",
        f"  year: {str(governing.get('year') or '').split('.')[0] or 'not recorded'}",
        f"  status: {governing.get('status')}",
        f"  product family: {governing.get('product_family')}",
    ]
    if related:
        lines.append("")
        lines.append("CO-CITED IN COMPARABLE PUBLISHED TENDERS — PROVENANCE ONLY")
        lines.append(
            "  These appear in the same real tender documents as the governing standard. "
            "That is a fact about how those tenders were written, NOT a finding that each "
            "one governs this item. Several will be unrelated to it. Present them as "
            "observed practice to be reviewed, never as recommendations."
        )
        for r in related[:4]:
            lines.append(f"  {r['target_is']} — {r.get('evidence_statement', '')}")
    lines.append("")
    if cert.get("found") and cert.get("certification_mandatory") == "Yes":
        notif = cert.get("notification_reference")
        lines.append("CERTIFICATION")
        lines.append(
            f"  Mandatory BIS certification applies. Scheme: {cert.get('scheme')}."
        )
        if notif and str(notif) not in ("N/A", "nan", "None"):
            # Handed the bare acronym "QCO", the model expanded it as "Quality
            # Certification Order". It is Quality Control Order. Give it the real
            # instrument name so it never has to guess one.
            lines.append(f"  Instrument, to be quoted exactly if quoted at all: {notif}")
        lines.append("  The clause must require the BIS Standard Mark.")
    else:
        lines.append("CERTIFICATION")
        lines.append("  No mandatory certification rule is on file. Do not claim one applies.")
    if governing.get("status") in ("Superseded", "Withdrawn"):
        lines.append("")
        lines.append("WARNING TO PRESERVE")
        lines.append(
            f"  {governing['is_number']} is recorded as {governing.get('status')} and must be "
            "confirmed against the current BIS listing before publication."
        )
    return "\n".join(lines)


REFUSAL = re.compile(
    r"^\s*(i (cannot|can't|am unable)|as an ai|sorry|here is|here's|certainly|sure[,.])", re.I
)

# The model's first real output invented "although these are not mandatory for
# this tender" — a legal ruling nobody gave it, telling suppliers four standards
# could be ignored. Blocking that phrasing, it produced "at the discretion of the
# purchaser" instead. Prompt rules did not hold either time, so this is checked in
# code. It is a denylist and denylists leak: a generation that gets past it is
# still only prose, and the template below it is always the safe fallback.
PERMISSIVE = re.compile(
    r"\bnot\s+(?:strictly\s+)?(?:mandatory|compulsory|required|obligatory|binding)\b"
    r"|\bnon-?mandatory\b|\bmerely\s+advisory\b|\bfor\s+reference\s+only\b"
    r"|\bdiscretion\b|\boptional\b|\bwhere\s+deemed\s+(?:necessary|appropriate)\b"
    r"|\bfor\s+reference\b|\bguidance\s+only\b|\bwherever\s+applicable\b"
    r"|\bencouraged\s+to\b|\bindustry\s+practice\b|\bneed\s+not\s+(?:be|comply)\b",
    re.I,
)


# Told plainly that no certification rule was on file, the model still wrote "The
# pipes shall bear the certification mark as specified in IS 4985". Inventing a
# statutory duty is as damaging as inventing a standard, so it is checked here
# rather than requested in the prompt.
MARK_CLAIM = re.compile(
    r"\b(?:BIS\s+)?standard\s*mark\b|\bISI\s*mark\b|\bcertification\s+mark\b"
    r"|\bshall\s+be\s+certified\b|\bBIS\s+certifi\w+|\bquality\s+control\s+order\b"
    r"|\bQCO\b|\blicen[cs]e\s+(?:no|number)\b",
    re.I,
)


def phrase(governing: dict, related: list[dict], cert: dict, allowed: list[str],
           years: dict | None = None) -> dict:
    """Ask the model to phrase the retrieved facts. Returns the checked result,
    or a failure the caller falls back on."""
    from retrieval import subset_guard

    prompt = (
        f"{_facts_block(governing, related, cert)}\n\n"
        f"Permitted IS numbers, and no others: {', '.join(allowed)}\n\n"
        "Write the tender clause now."
    )
    try:
        body = _post(
            "/api/generate",
            {
                "model": MODEL,
                "system": SYSTEM,
                "prompt": prompt,
                "stream": False,
                "options": OPTIONS,
            },
        )
    except (urllib.error.URLError, TimeoutError, OSError, json.JSONDecodeError) as exc:
        return {"ok": False, "reason": "call_failed", "detail": f"{type(exc).__name__}: {exc}"}

    model_name = body.get("model") or MODEL
    text = (body.get("response") or "").strip()
    text = re.sub(r"^```[a-z]*\n?|```$", "", text).strip()

    if not text:
        return {"ok": False, "reason": "empty_response", "model": model_name}
    if REFUSAL.match(text):
        return {"ok": False, "reason": "not_a_clause",
            "model": model_name, "detail": text[:120]}

    # Real tender specifications assert conformity of the goods, never of a person:
    # "The unplasticized PVC rigid pipes shall strictly conform to IS 4985/1988."
    # A clause that obliges a party is conditions-of-contract language in the wrong
    # section, whichever party it names.
    party = re.search(
        r"\b(supplier|purchaser|contractor|bidder|tenderer|vendor|department|employer)s?\b"
        r"[^.]{0,60}?\b(?:shall|must|is\s+required\s+to|are\s+required\s+to)\s+"
        # "shall ensure that the products comply" slipped past a narrower pattern,
        # and "the supplier shall review" hands the officer's judgement to the bidder.
        r"(?:also\s+)?(?:comply|conform|adhere|ensure|review|refer|verify|check)",
        text, re.I,
    )
    if party:
        return {
            "ok": False,
            "reason": "obligation_on_person_not_goods",
            "model": model_name,
            "detail": (
                f"clause obliges the {party.group(1).lower()} to comply. A specification "
                "states what the goods shall conform to; duties on parties belong in the "
                "conditions of contract."
            ),
            "rejected_text": text,
        }

    mandatory = cert.get("found") and cert.get("certification_mandatory") == "Yes"
    mark = MARK_CLAIM.search(text)
    if mark and not mandatory:
        return {
            "ok": False,
            "reason": "invented_certification_duty",
            "model": model_name,
            "detail": (
                f"clause demands certification (\u201c{mark.group(0)}\u201d) but no mandatory "
                "BIS certification rule is on file for this standard."
            ),
            "rejected_text": text,
        }
    if mandatory and not mark:
        return {
            "ok": False,
            "reason": "dropped_certification_duty",
            "model": model_name,
            "detail": (
                "mandatory BIS certification applies to this item and the clause does not "
                "require the Standard Mark."
            ),
            "rejected_text": text,
        }

    claim = PERMISSIVE.search(text)
    if claim:
        return {
            "ok": False,
            "reason": "unsupported_permissive_claim",
            "model": model_name,
            "detail": (
                f"output declared something optional or advisory (\u201c{claim.group(0)}\u201d). "
                "Nothing in the retrieved facts establishes what is not mandatory."
            ),
            "rejected_text": text,
        }

    # The guard that makes the architecture claim true rather than aspirational.
    ok, leaked = subset_guard(text, allowed, years)
    if not ok:
        return {
            "ok": False,
            "reason": "subset_guard_failed",
            "model": model_name,
            "detail": f"model introduced {', '.join(leaked)}",
            "leaked": leaked,
            "rejected_text": text,
        }

    # Phrasing that drops the governing standard is not a phrasing of these facts.
    if governing["is_number"].split("(")[0].strip() not in text:
        return {"ok": False, "reason": "governing_standard_missing",
            "model": model_name, "rejected_text": text}

    return {
        "ok": True,
        "text": text,
        "model": MODEL,
        "eval_count": body.get("eval_count"),
        "duration_ms": round((body.get("total_duration") or 0) / 1e6),
    }
