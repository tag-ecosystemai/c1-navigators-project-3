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
    "never make a decision yourself. A human analyst decides. Mention data gaps if any.\n"
    "Each rule has a 'meaning' that says what its applicant_value measures: use it, and read every "
    "number by it. In particular the income figure for POL-INC-001 is a GAP between the declared "
    "income and the verified bank deposits: a high percentage means the two DIFFER and the declared "
    "income is not supported. Never call that figure alignment, agreement, consistency or a match.\n"
    "'policy_checker' says whether a second reading of the policy text (the policy checker) was run "
    "and whether it disagreed with the rule engine. State it in one sentence: if status is not_run, say "
    "the policy checker was not run and do not say anything about agreement or conflicts; if it ran, say "
    "'the policy checker disagreed with the rule engine on <codes>' for the codes in disagreed_on, or that "
    "it agreed with the rule engine on all the rules it compared if there are none. The checker only compared "
    "'compared' of 'total_rules' rules; the rest were not compared. So never say it agreed on 'all rules' or "
    "'every rule': say 'on all rules it compared' or give the count. "
    "Never call these disagreements 'policy conflicts'.\n"
    "Write 120 to 180 words of plain prose, no headings."
)

# What each rule's applicant_value measures, so the LLM does not guess (e.g. read a 57.3% income gap as alignment).
VALUE_MEANING = {
    "POL-ELG-001": "the applicant's age in years",
    "POL-ELG-002": "declared monthly net income",
    "POL-ELG-003": "months with the current employer",
    "POL-SCR-001": "the credit score; the status is the credit tier (Tier 1 best, Tier 4 worst)",
    "POL-SCR-002": "count of bankruptcies and tax liens on file",
    "POL-DTI-001": "total monthly debt payments including the new loan, as a percentage of monthly income; lower is better",
    "POL-LTI-001": "requested loan divided by annual income; lower is better",
    "POL-NDI-001": "money left each month after all commitments, with the required minimum buffer in brackets; higher is better",
    "POL-INC-001": ("percentage GAP between the declared monthly income and the income verified from bank deposits; "
                    "0% means they agree, a high value means the declared income is NOT supported by the deposits"),
    "POL-TXN-001": "gambling spend as a percentage of monthly income",
    "POL-TXN-002": "number of NSF / overdraft events in the statement window",
    "POL-TXN-003": "monthly payments to lenders found in the bank statement that were not declared",
    "POL-TXN-004": "number of unexplained large non-payroll deposits shortly before applying",
    "POL-TXN-005": "balance pattern between paydays (HEALTHY, VULNERABLE or CRITICAL_DISTRESS)",
}


def checker_status(view: dict) -> dict:
    """Did the policy checker (RAG cross-check) run, and where did it disagree with the rule engine?"""
    cross = view.get("cross_check") or {}
    if not cross.get("available"):
        reason = str(cross.get("error") or "")
        return {"status": "not_run", "reason": "offline mode" if "offline" in reason.lower() else "it was unavailable"}
    codes = list(cross.get("conflicts", []))
    rules = cross.get("rules") or {}
    # evaluator_only / not_compared rules were NOT compared (the checker had nothing to compare them with)
    compared = sum(1 for r in rules.values() if r.get("agreement") in {"agree", "soft_conflict", "hard_conflict", "rag_only"})
    return {"status": "ran", "disagreed_on": codes, "compared": compared, "total_rules": len(rules)}


def facts_for(view: dict) -> dict:
    return {
        "verdict": view["verdict"],
        "primary_driver": view["driver"],
        "rules": [{"code": r["code"], "rule": r["title"], "status": r["status"], "applicant_value": r["value"],
                   "meaning": VALUE_MEANING.get(r["code"], "")} for r in view["rules"]],
        "data_gaps": view["data_gaps"],
        "ml": view["ml"]["text"],
        "policy_checker": checker_status(view),
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
    check = checker_status(view)
    if check["status"] == "not_run":
        parts.append(f"The policy checker was not run ({check['reason']}), so there is no second reading of the policy text.")
    elif check["disagreed_on"]:
        parts.append("The policy checker disagreed with the rule engine on " + ", ".join(check["disagreed_on"])
                     + "; an analyst should read the cited clauses.")
        if check["compared"]:
            parts.append(f"It compared {check['compared']} of {check['total_rules']} rules.")
    elif check["compared"]:
        parts.append(f"The policy checker agreed with the rule engine on all {check['compared']} rules it compared"
                     f" ({check['total_rules'] - check['compared']} others could not be compared).")
    else:
        parts.append("The policy checker agreed with the rule engine on every rule it compared.")
    parts.append("This is decision support only: a human analyst makes the final decision.")
    return " ".join(parts)


_NEGATION = re.compile(r"\b(not|no|never|nor|neither|cannot|without|fail\w*|lack\w*|\w+n't)\b", re.I)
_AGREEMENT_WORDS = re.compile(r"\b(align\w*|match\w*|consistent|in line)\b", re.I)
_INCOME_TOPIC = re.compile(r"variance|income|discrepan|inflow|deposit|declared|POL-INC-001", re.I)
_POLICY_CONFLICT = re.compile(
    r"polic(?:y|ies)[ -](?:text[ -])?conflicts?|conflicts? (?:in|within|with|between) (?:the )?polic|conflicting polic", re.I)
_NOT_RUN = re.compile(
    r"\bnot (?:been )?(?:run|available|performed|executed)\b|\bwas(?:n't| not) run\b|\bdid not run\b|"
    r"\bunavailable\b|\bcould not be run\b", re.I)
_AGREEMENT_CLAIM = re.compile(
    r"\bno (?:policy[ -](?:text[ -])?)?(?:conflicts?|disagreements?)\b|"
    r"(?:policy checker|checker|rag).{0,60}\b(?:agree\w*|consistent|confirm\w*)\b", re.I)
_DISAGREE = re.compile(r"\bdisagree\w*", re.I)
_AGREE_OR_DISAGREE = re.compile(r"\b(?:dis)?agree\w*", re.I)
_UNIVERSAL = re.compile(r"\b(all|every|each)\b", re.I)
_QUALIFIED = re.compile(r"\bcompared\b|\b\d+\s+(?:of\s+\d+\s+)?rules?\b", re.I)


def _negated(sentence: str, start: int) -> bool:
    """Is the word at `start` preceded by a negation within the 5 words before it?"""
    before = sentence[:start].split()[-5:]
    return bool(_NEGATION.search(" ".join(before)))


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

    # the income figure is a GAP: never describe a non-clean variance as alignment or a match
    income = next((r for r in view["rules"] if r["code"] == "POL-INC-001"), None)
    if income and income["status"] not in ("SATISFIED", "MISSING_DATA"):
        for sentence in re.split(r"(?<=[.!?])\s+", text):
            if not _INCOME_TOPIC.search(sentence):
                continue
            for m in _AGREEMENT_WORDS.finditer(sentence):
                if not _negated(sentence, m.start()):
                    return f"describes the income variance as alignment/match ('{m.group(0)}')"

    # the policy checker: say whether it ran, and call its disagreements disagreements, not policy conflicts
    if _POLICY_CONFLICT.search(text):
        return "describes the policy checker's result as policy conflicts"
    check = checker_status(view)
    if check["status"] == "not_run":
        if _AGREEMENT_CLAIM.search(text):
            return "claims the policy checker agreed or found no conflicts although it was not run"
        if not _NOT_RUN.search(text):
            return "does not say that the policy checker was not run"
    if check["status"] == "ran":
        # rules marked evaluator_only / not_compared were not compared: no "agreed on all rules"
        for sentence in re.split(r"(?<=[.!?])\s+", text):
            if _AGREE_OR_DISAGREE.search(sentence) and _UNIVERSAL.search(sentence) and not _QUALIFIED.search(sentence):
                return ("overstates what the policy checker compared: say 'on all rules it compared' "
                        "(or give the count), not 'all rules'")
        if check["disagreed_on"]:
            missing = [c for c in check["disagreed_on"] if c not in text]
            if not _DISAGREE.search(text) or missing:
                return ("does not say the policy checker disagreed with the rule engine on "
                        + ", ".join(check["disagreed_on"]))
        else:
            for m in _DISAGREE.finditer(text):
                if not _negated(text, m.start()):
                    return "claims the policy checker disagreed although it did not"
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
