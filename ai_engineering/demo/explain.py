"""Plain-language explanation of a report. In Azure mode an Azure OpenAI deployment writes it from the
report's facts only; on any LLM problem (or offline) a deterministic template is used instead.
Neither path can change the decision: the verdict is passed in, never produced here."""

from __future__ import annotations

import json
import re

VERDICTS = ("ELIGIBLE_FOR_APPROVAL", "FURTHER_REVIEW_REQUIRED", "DECLINE_RECOMMENDED")
TEMPLATE_LABEL = "Generated from rules, not by an LLM"
_CODE = re.compile(r"POL-[A-Z]{2,4}-\d{2,4}")

SYSTEM_PROMPT = (
    "You help a bank credit analyst read an investigation report. Use ONLY the facts in the JSON the "
    "user sends; do not add numbers, rules or facts that are not in it. Cite the policy rule code "
    "(e.g. POL-DTI-001) for every statement about a rule. The verdict in the JSON was produced by "
    "rules and is final for this report: never state, suggest or hint at a different decision, and "
    "never make a decision yourself. A human analyst decides. Mention data gaps if any. "
    "Write 120 to 180 words of plain prose, no headings."
)


def facts_for(view: dict) -> dict:
    cross = view.get("cross_check") or {}
    return {
        "verdict": view["verdict"],
        "primary_driver": view["driver"],
        "rules": [{"code": r["code"], "rule": r["title"], "status": r["status"], "applicant_value": r["value"]}
                  for r in view["rules"]],
        "data_gaps": view["data_gaps"],
        "ml": view["ml"]["text"],
        "policy_text_conflicts": [
            {"code": c, "evaluator": cross["rules"][c]["evaluator"], "rag_outcome": cross["rules"][c].get("rag_outcome"),
             "citation": cross["rules"][c].get("citation")} for c in cross.get("conflicts", [])
        ] if cross.get("available") else [],
    }


def template_explanation(view: dict) -> str:
    flagged = [r for r in view["rules"] if r["status"] not in ("SATISFIED", "CLEAN", "HEALTHY", "Tier 1", "Tier 2", "MISSING_DATA")]
    parts = [f"Verdict: {view['verdict']}."]
    if flagged:
        lead = next((r for r in flagged if r["code"] == view["driver"]), flagged[0])
        parts.append(f"Primary driver: {lead['code']} ({lead['title']}) is {lead['status']} with an applicant value of {lead['value']}.")
        others = [f"{r['code']} ({r['status']})" for r in flagged if r is not lead]
        if others:
            parts.append("Other rules that are not clean: " + ", ".join(others) + ".")
    else:
        parts.append("Every evaluated rule is satisfied.")
    if view["data_gaps"]:
        parts.append("Data gaps: " + "; ".join(f"{g['rule']} lacked {', '.join(g['missing_fields'])}" for g in view["data_gaps"]) + ".")
    parts.append("This is decision support only: a human analyst makes the final decision.")
    return " ".join(parts)


def _check_llm_text(text: str, view: dict) -> str | None:
    """Return a reason to reject the LLM text, or None if it is acceptable."""
    if not text or not text.strip():
        return "empty reply"
    other = [v for v in VERDICTS if v != view["verdict"] and v in text]
    if other:
        return f"mentions a different verdict ({other[0]})"
    known = {r["code"] for r in view["rules"]}
    invented = set(_CODE.findall(text)) - known
    if invented:
        return f"cites rule codes that are not in the report ({', '.join(sorted(invented))})"
    return None


def explain(view: dict, llm=None) -> dict:
    """{"text", "source", "label", "note"}. `llm` is an object with generate(prompt, system=...)."""
    template = {"text": template_explanation(view), "source": "template", "label": TEMPLATE_LABEL, "note": None}
    if llm is None:
        return template
    try:
        text = llm.generate(json.dumps(facts_for(view), indent=2, default=str), system=SYSTEM_PROMPT)
    except Exception as exc:  # noqa: BLE001 - any Azure/network problem: fall back, never fail the demo
        template["note"] = f"Azure explanation unavailable ({exc}); showing the rule-based text instead"
        return template
    problem = _check_llm_text(text, view)
    if problem:
        template["note"] = f"Azure explanation rejected ({problem}); showing the rule-based text instead"
        return template
    return {"text": text.strip(), "source": f"azure:{getattr(llm, 'model', '?')}",
            "label": f"Written by Azure OpenAI ({getattr(llm, 'model', '?')}) from the report facts only; the decision comes from rules and a human",
            "note": None}
