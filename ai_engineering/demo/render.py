"""Console and self-contained HTML renderings of a report view (ASCII only, no external assets)."""

from __future__ import annotations

import html
import json
import textwrap

DISCLAIMER = "Decision support only: a human analyst makes the final decision."


# ----------------------------------------------------------------------------- offline policy text


def retrieve_policy_text(codes: list[str]) -> dict[str, dict]:
    """Offline mode: the policy passage for each rule code, from the local index (auto-ingested)."""
    from ..rag.tools import get_retriever

    out: dict[str, dict] = {}
    try:
        retriever = get_retriever()
        for code in codes:
            hits = retriever.search(code, k=3)
            hit = next((h for h in hits if code in h.chunk.clauses), hits[0] if hits else None)
            out[code] = ({"citation": hit.chunk.citation, "text": hit.chunk.text} if hit
                         else {"error": "no passage found"})
    except Exception as exc:  # noqa: BLE001
        return {code: {"error": f"policy text unavailable: {exc}"} for code in codes}
    return out


# ----------------------------------------------------------------------------- shared helpers


def _short(text: str | None, width: int = 300) -> str:
    return textwrap.shorten(" ".join((text or "").split()), width=width, placeholder=" ...")


def cross_check_rows(view: dict) -> list[dict]:
    cross = view.get("cross_check") or {}
    return [{"code": code, **entry} for code, entry in (cross.get("rules") or {}).items()] if cross.get("available") else []


# ----------------------------------------------------------------------------- console


def _table(headers: list[str], rows: list[list[str]], indent: str = "  ") -> list[str]:
    widths = [max(len(str(r[i])) for r in [headers] + rows) for i in range(len(headers))]
    fmt = lambda r: indent + "  ".join(str(c).ljust(w) for c, w in zip(r, widths)).rstrip()  # noqa: E731
    return [fmt(headers), fmt(["-" * w for w in widths])] + [fmt(r) for r in rows]


def console_report(view: dict, explanation: dict, policy_text: dict[str, dict] | None = None) -> str:
    bar = "=" * 78
    out = [bar, f" {view['banner']}", bar,
           f"Applicant: {view['applicant_id']} ({view['name']})   Loan: {view['loan']}",
           f"VERDICT: {view['verdict']}",
           f"Primary driver: {view['driver']}" + (f" ({view['driver_title']})" if view["driver_title"] else ""),
           DISCLAIMER, "", "Policy rules (rule-based evaluator)"]
    out += _table(["Code", "Rule", "Status", "Applicant value"],
                  [[r["code"], r["title"], r["status"], r["value"]] for r in view["rules"]])

    out += ["", "Data gaps (inputs a rule could not use; a finding, not a failure)"]
    out += [f"  {g['rule']}: missing {', '.join(g['missing_fields'])}" for g in view["data_gaps"]] or ["  none"]

    out += ["", view["ml"]["text"]]

    out += ["", "Evidence"]
    for item in view["evidence"][:8]:
        out.append(f"  [{item['severity']}] {item['title']}: {json.dumps(item['data'], default=str)}")
    if len(view["evidence"]) > 8:
        out.append(f"  ... {len(view['evidence']) - 8} more in the HTML report")
    if not view["evidence"]:
        out.append("  none")

    cross = view.get("cross_check") or {}
    if view["azure_mode"]:
        out += ["", "Policy RAG checker (Azure OpenAI) vs rule evaluator"]
        if cross.get("available"):
            rows = cross_check_rows(view)
            out += _table(["Code", "Evaluator", "RAG", "Agreement", "Cited clause"],
                          [[r["code"], r["evaluator"], r.get("rag_outcome") or "-", r["agreement"], _short(r.get("citation"), 60) or "-"] for r in rows])
            out.append(f"  Conflicts: {', '.join(cross['conflicts']) or 'none'}")
            for code in cross["conflicts"]:
                r = cross["rules"][code]
                out.append(f"    {code}: evaluator={r['evaluator']} vs RAG={r.get('rag_outcome')} - \"{_short(r.get('quote'), 200)}\" ({r.get('citation')})")
        else:
            out.append(f"  RAG checker unavailable: {cross.get('error')}")
    else:
        out += ["", "Policy text by rule code (offline: retrieved from the local index, no RAG checker)"]
        clean = {r["code"] for r in view["rules"] if r["status"] in ("SATISFIED", "CLEAN", "HEALTHY", "Tier 1", "Tier 2")}
        shown = {c: h for c, h in (policy_text or {}).items() if c not in clean}
        if len(shown) < len(policy_text or {}):
            out.append(f"  (showing the {len(shown)} rule(s) that are not clean; all {len(policy_text)} are in the HTML report)")
        for code, hit in shown.items():
            out.append(f"  {code}: " + (hit["error"] if "error" in hit else f"{hit['citation']}"))
            if "text" in hit:
                out += textwrap.wrap(_short(hit["text"], 280), width=74, initial_indent="      ", subsequent_indent="      ")

    out += ["", f"Explanation [{explanation['label']}]"]
    out += textwrap.wrap(explanation["text"], width=76, initial_indent="  ", subsequent_indent="  ")
    if explanation.get("note"):
        out.append(f"  NOTE: {explanation['note']}")
    return "\n".join(out)


# ----------------------------------------------------------------------------- HTML

_CSS = """
body{font-family:Segoe UI,Arial,sans-serif;margin:0;background:#f4f6f8;color:#1b2733}
.wrap{max-width:980px;margin:0 auto;padding:24px}
.banner{padding:10px 16px;font-weight:600;color:#fff}.banner.azure{background:#0b5cad}.banner.offline{background:#8a5a00}
h1{margin:16px 0 4px;font-size:22px}h2{margin:28px 0 8px;font-size:16px;border-bottom:1px solid #cfd8e0;padding-bottom:4px}
.verdict{display:inline-block;padding:6px 14px;border-radius:4px;font-weight:700;color:#fff}
.v-ELIGIBLE_FOR_APPROVAL{background:#1a7f37}.v-FURTHER_REVIEW_REQUIRED{background:#b36b00}.v-DECLINE_RECOMMENDED{background:#b3261e}
table{border-collapse:collapse;width:100%;background:#fff}th,td{border:1px solid #d5dde5;padding:6px 8px;text-align:left;font-size:13px;vertical-align:top}
th{background:#e8eef3}.s-bad{color:#b3261e;font-weight:600}.s-warn{color:#b36b00;font-weight:600}.s-ok{color:#1a7f37}
.note{background:#fff8e1;border-left:4px solid #f0b400;padding:8px 12px;margin:8px 0}
.small{color:#51606e;font-size:12px}blockquote{margin:4px 0;padding:4px 10px;border-left:3px solid #9fb3c4;background:#fff}
"""

_BAD = {"NOT_SATISFIED", "KNOCKOUT", "HIGH_RISK", "Tier 4", "CRITICAL_DISTRESS"}
_OK = {"SATISFIED", "CLEAN", "HEALTHY", "Tier 1", "Tier 2"}


def _e(value) -> str:
    return html.escape(str(value if value is not None else ""))


def _status_cls(status: str) -> str:
    return "s-bad" if status in _BAD else "s-ok" if status in _OK else "s-warn"


def _html_table(headers: list[str], rows: list[list[str]]) -> str:
    head = "".join(f"<th>{_e(h)}</th>" for h in headers)
    body = "".join("<tr>" + "".join(f"<td>{c}</td>" for c in row) + "</tr>" for row in rows)
    return f"<table><tr>{head}</tr>{body}</table>"


def html_report(view: dict, explanation: dict, policy_text: dict[str, dict] | None = None) -> str:
    cross = view.get("cross_check") or {}
    parts = [
        f"<div class='banner {'azure' if view['azure_mode'] else 'offline'}'>{_e(view['banner'])}</div><div class='wrap'>",
        f"<h1>{_e(view['applicant_id'])} &mdash; {_e(view['name'])}</h1><div class='small'>Loan: {_e(view['loan'])}</div>",
        f"<p><span class='verdict v-{_e(view['verdict'])}'>{_e(view['verdict'])}</span> "
        f"&nbsp; Primary driver: <b>{_e(view['driver'])}</b> {_e(view['driver_title'])}</p>",
        f"<div class='small'>{_e(DISCLAIMER)}</div>",
        "<h2>Policy rules (rule-based evaluator)</h2>",
        _html_table(["Code", "Rule", "Status", "Applicant value"],
                    [[_e(r["code"]), _e(r["title"]), f"<span class='{_status_cls(r['status'])}'>{_e(r['status'])}</span>", _e(r["value"])]
                     for r in view["rules"]]),
        "<h2>Data gaps</h2><p class='small'>Inputs a rule could not use. A finding for the analyst, not a system failure.</p>",
        ("<ul>" + "".join(f"<li><b>{_e(g['rule'])}</b>: missing {_e(', '.join(g['missing_fields']))}</li>" for g in view["data_gaps"]) + "</ul>")
        if view["data_gaps"] else "<p>None.</p>",
        f"<h2>ML score</h2><p>{_e(view['ml']['text'])}</p>",
        "<h2>Evidence</h2>",
        _html_table(["Severity", "Title", "Type", "Data"],
                    [[_e(i["severity"]), _e(i["title"]), _e(i["type"]), _e(json.dumps(i["data"], default=str))] for i in view["evidence"]])
        if view["evidence"] else "<p>None.</p>",
    ]
    if view["azure_mode"]:
        parts.append("<h2>Policy RAG checker (Azure OpenAI) vs rule evaluator</h2>")
        if cross.get("available"):
            parts.append(_html_table(
                ["Code", "Evaluator", "RAG", "Agreement", "Cited clause", "Quote"],
                [[_e(r["code"]), _e(r["evaluator"]), _e(r.get("rag_outcome") or "-"), _e(r["agreement"]),
                  _e(r.get("citation") or "-"), _e(_short(r.get("quote"), 240) or "-")] for r in cross_check_rows(view)]))
            parts.append(f"<p>Conflicts: <b>{_e(', '.join(cross['conflicts']) or 'none')}</b></p>")
        else:
            parts.append(f"<div class='note'>RAG checker unavailable: {_e(cross.get('error'))}</div>")
    else:
        parts.append("<h2>Policy text by rule code</h2><p class='small'>Offline: retrieved from the local index; the RAG checker did not run.</p>")
        for code, hit in (policy_text or {}).items():
            body = _e(hit["error"]) if "error" in hit else f"<div class='small'>{_e(hit['citation'])}</div><blockquote>{_e(_short(hit['text'], 700))}</blockquote>"
            parts.append(f"<details><summary><b>{_e(code)}</b></summary>{body}</details>")
    parts.append(f"<h2>Explanation</h2><p class='small'>{_e(explanation['label'])}</p><p>{_e(explanation['text'])}</p>")
    if explanation.get("note"):
        parts.append(f"<div class='note'>{_e(explanation['note'])}</div>")
    parts.append("</div>")
    return ("<!DOCTYPE html><html lang='en'><head><meta charset='utf-8'>"
            f"<title>{_e(view['applicant_id'])} - credit-risk investigation</title><style>{_CSS}</style></head><body>"
            + "".join(parts) + "</body></html>")
