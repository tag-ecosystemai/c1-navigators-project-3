"""Compare an application against the lending policy.

Design: the LLM reads the policy, Python applies it.

1. Retrieve the policy clauses relevant to a standard set of topics (RAG).
2. Ask the LLM to turn those clauses into structured rules (field, operator, threshold),
   each pointing at the chunk it came from and quoting it. It does NOT judge the applicant.
3. Evaluate every rule against the application in plain Python, so the numbers are
   reproducible and every result has one of four statuses from the PRD:
   satisfied / not_satisfied / unclear / missing.

Extracted rules are cached per (policy chunks + application fields + model), so the same
case gives the same rules every time and the team can inspect them in
data/processed/policy_index/rules_cache/.
"""

from __future__ import annotations

import hashlib
import json
import re
from dataclasses import asdict, dataclass, field
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, ValidationError

from .llm import JSONLLM
from .retriever import PolicyRetriever
from .stores import SearchResult

Status = Literal["satisfied", "not_satisfied", "unclear", "missing"]

# Aligned to the Navigators policy set: 01 eligibility, 02 affordability/debt service,
# 03 bank statement/transaction investigation, 04 underwriting referral/exception matrix.
# Rule codes referenced in DATA_DICTIONARY.md (POL-ELG-*, POL-DTI-*, POL-LTI-*, POL-SCR-*,
# POL-NDI-*, POL-INC-*, POL-TXN-*) are the citation keys the checker should surface.
DEFAULT_TOPICS = [
    "minimum and maximum applicant age at loan maturity (POL-ELG-001)",
    "minimum verifiable monthly net income (POL-ELG-002)",
    "employment tenure and probation requirement (POL-ELG-003)",
    "credit bureau score tiers and maximum loan amount by tier (POL-SCR-001)",
    "bankruptcy, court judgments and tax lien knockout conditions (POL-SCR-002)",
    "permissible loan amount, term and restricted loan purposes (POL-PRD-001)",
    "debt-to-income ratio threshold tiers (POL-DTI-001)",
    "loan-to-income multiplier cap by credit tier (POL-LTI-001)",
    "net disposable income minimum living buffer (POL-NDI-001)",
    "declared versus verified income variance tolerance (POL-INC-001)",
    "gambling spend and transaction frequency thresholds (POL-TXN-001)",
    "overdraft, NSF fees and returned items (POL-TXN-002)",
    "undisclosed debt, BNPL payments and shadow DTI recalculation (POL-TXN-003)",
    "window dressing large cash deposits before application (POL-TXN-004)",
    "account balance burn rate and payday depletion (POL-TXN-005)",
    "standard approval, referral and decline decision matrix",
]


Operator = Literal["<=", "<", ">=", ">", "==", "!=", "between", "in", "not_in", "qualitative"]


class Condition(BaseModel):
    """One test on an application field that must hold for a rule VARIANT to apply to this applicant
    (e.g. employment_status in [SELF_EMPLOYED], credit_score between [660, 719], dependents_count > 0)."""

    field: str
    operator: Operator
    value: float | int | str | bool | list | None = None


class PolicyRule(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    rule_id: str
    requirement: str = Field(description="Plain-English statement of what the applicant must meet")
    chunk_id: str
    clause: str | None = None
    quote: str = Field(default="", description="Short verbatim excerpt from the clause")
    field: str | None = Field(default=None, description="Application field this rule tests, or null")
    operator: Operator
    threshold: float | int | str | bool | list | None = None
    unit: str | None = None
    severity: Literal["requirement", "referral", "risk_indicator"] = "requirement"
    # None = not stated by the LLM; Python infers it (see repair_polarity).
    # "must_meet": operator/threshold is the condition the applicant must satisfy.
    # "breach_if": operator/threshold is the level at which the policy is BREACHED (e.g. "> 10%" for gambling).
    polarity: Literal["must_meet", "breach_if"] | None = None  # None: inferred (default must_meet)
    # Variant selection: all conditions must hold for the rule to apply to this applicant.
    applies_when: list[Condition] = Field(default_factory=list)
    # A verdict the LLM may volunteer. It is never used; it is only compared with Python's result.
    claimed_status: Status | None = Field(default=None, alias="status")


@dataclass
class RuleResult:
    rule_id: str
    requirement: str
    status: Status
    severity: str
    field: str | None
    applicant_value: Any
    operator: str
    threshold: Any
    explanation: str
    citation: str
    clause: str | None
    quote: str
    quote_verified: bool
    source: str
    chunk_id: str
    polarity: str = "must_meet"
    note: str | None = None  # set when validation repaired or flagged something


@dataclass
class PolicyCheckResult:
    results: list[RuleResult] = field(default_factory=list)
    unmatched_fields: list[str] = field(default_factory=list)
    # rule variants that do not apply to this applicant (e.g. the self-employed clause for a salaried one)
    not_applicable: list[dict] = field(default_factory=list)

    @property
    def counts(self) -> dict[str, int]:
        c = {"satisfied": 0, "not_satisfied": 0, "unclear": 0, "missing": 0}
        for r in self.results:
            c[r.status] += 1
        return c

    @property
    def requires_review(self) -> bool:
        return any(r.status != "satisfied" for r in self.results)

    @property
    def review_reasons(self) -> list[str]:
        return [
            f"[{r.status}] {r.requirement} ({r.citation})" for r in self.results if r.status != "satisfied"
        ]

    def to_dict(self) -> dict:
        return {
            "requires_review": self.requires_review,
            "counts": self.counts,
            "review_reasons": self.review_reasons,
            "results": [asdict(r) for r in self.results],
            "not_applicable": self.not_applicable,
        }


# --------------------------------------------------------------------------- helpers

SYSTEM_PROMPT = """You extract machine-checkable lending rules from bank policy text.

You are given policy excerpts (each with a chunk_id) and the list of fields available
in a loan application, with example values so you can see their units.

Return JSON: {"rules": [ ... ]}. Each rule:
- rule_id: short snake_case id; reuse the rule code lowercased if one is given (e.g. "pol_dti_001"), else something like "max_dti"
- requirement: one plain-English sentence stating the condition the applicant must MEET
- chunk_id: the chunk_id of the excerpt the rule comes from (must be one you were given)
- clause: the clause identifier if visible — a rule code such as "POL-DTI-001" (prefer this
  form when present) or a numbered clause such as "3.1", else null
- quote: a short VERBATIM excerpt (under 25 words) from that excerpt supporting the rule
- field: the application field that tests this rule, chosen ONLY from the given field names; null if none fits
- operator: one of "<=", "<", ">=", ">", "==", "!=", "between", "in", "not_in", "qualitative"
- threshold: number, string, boolean, or [low, high] for "between", or a list for "in"/"not_in"; null for "qualitative"
- unit: e.g. "ratio", "percent", "months", "years", "count", "currency", or null
- severity: "requirement" (failing it means policy is not met), "referral" (failing it means the
  case must be referred to a supervisor) or "risk_indicator" (failing it must be noted)

- polarity: "must_meet" (operator/threshold is the condition the applicant must satisfy; preferred) or
  "breach_if" (operator/threshold is the level at which the policy is BREACHED, used when the text only
  states the breach level). Examples: "gambling above 10% of income is a violation" -> field gambling share,
  operator ">", threshold 10, polarity "breach_if" (equivalently operator "<=", threshold 10, "must_meet");
  "4 or more NSF events is a knockout" -> operator ">=", threshold 4, polarity "breach_if".
  NEVER put a breach level in a must_meet rule: that would fail applicants who are well inside the limit.
  A RISK BAND ("Moderate risk: gambling between 3% and 10% of income", "2 to 3 NSF events", "DTI 43.1% to 50%:
  mandatory referral") is triggered when the applicant's value falls INSIDE the band. Express it as operator
  "between", threshold [low, high], polarity "breach_if", severity "referral" or "risk_indicator". It must
  never be must_meet: an applicant with 0% gambling is not "outside the band and therefore failing".
  For a series of bands that only get worse, prefer one "<=" must_meet rule per boundary instead.
- applies_when: a list of conditions, all of which must hold for this rule to apply to the applicant, each
  {"field": <application field>, "operator": ..., "value": ...}. Use it whenever the policy gives DIFFERENT
  rules for different kinds of applicant, so that each variant becomes its own rule with its own conditions:
  * employment type (employment_status: EMPLOYED_FULL_TIME and PART_TIME are salaried; SELF_EMPLOYED is
    self-employed): the 6-month salaried tenure rule applies_when employment_status in the salaried values; the
    24-month self-employed rule applies_when employment_status == "SELF_EMPLOYED";
  * credit tier (use credit_score ranges from the policy's tier table, e.g. between [660, 719] for Tier 2, or
    credit_score_tier): one rule per tier cap, each with that tier's range;
  * dependents (dependents_count): "single applicant" applies_when dependents_count == 0;
    "applicant with dependents" applies_when dependents_count > 0.
  Use [] when the rule applies to every applicant. Conditions only select the variant; never use them to judge.
- Do NOT include any verdict or status. You never decide whether the applicant passes.

- severity follows the policy's own wording. A threshold whose breach the text calls "Not Satisfied", "Decline",
  "Knockout", "Breach" or "Escalation Required" is severity "requirement". Only thresholds whose breach is merely
  "Flag for Review", "Referral", "Caution" or "Monitor" are "referral" or "risk_indicator". When the text has both
  (e.g. "Flag for Review: under $250 a month ... Not Satisfied: over $250 a month"), extract the not-satisfied
  threshold as a "requirement" rule (<= 250) and, separately, the review condition as a referral/risk_indicator rule
  (e.g. any undisclosed debt at all: <= 0).
Rules:
- Express every rule as the condition the applicant should meet. Example: "DTI must not exceed 40%" ->
  operator "<=", threshold 0.40 if the application stores DTI as a fraction (e.g. 0.38), or 40 if it stores percent.
- Match the threshold to the units of the example value for that field.
- A referral band like "40% to 45% is referred, above 45% fails" becomes TWO rules:
  "<= 0.45" severity "requirement" and "<= 0.40" severity "referral".
- A red flag like "two or more returned payments is a red flag" becomes operator "<=", threshold 1,
  severity "risk_indicator" (state the acceptable condition).
- If one rule states two or more conditions joined by "and" / "or" (e.g. "undisclosed debt must not exceed $250 a
  month AND revised DTI must stay at or below 43%"), output ONE rule per condition, each with its own field,
  operator and threshold. Never keep only one of them.
- Use operator "qualitative" only when the application HAS a field an analyst must interpret. If no field can test
  the condition (e.g. probation status, document verification), set field to null so it is reported as missing
  data; never attach it to an unrelated field.
- Only extract rules that apply to an individual application. Skip governance, scope and process text.
- Do not evaluate the applicant. Do not invent rules that are not in the excerpts.
"""


FIELD_NOTES = '\nFIELD VALUE NOTES (from the data dictionary):\n- employment_status: EMPLOYED_FULL_TIME, PART_TIME, SELF_EMPLOYED\n- credit_score_tier: TIER_1_PRIME, TIER_2_NEAR_PRIME, TIER_3_SUBPRIME, TIER_4_HIGH_RISK\n'


def _norm(s: str) -> str:
    return re.sub(r"\s+", " ", s).strip().lower()


def _flatten(d: dict, prefix: str = "") -> dict:
    out = {}
    for k, v in d.items():
        key = f"{prefix}{k}"
        if isinstance(v, dict):
            out.update(_flatten(v, f"{key}."))
        else:
            out[key] = v
    return out


def _is_missing(v: Any) -> bool:
    return v is None or (isinstance(v, str) and not v.strip()) or (isinstance(v, float) and v != v)


def _to_number(v: Any) -> float | None:
    if isinstance(v, bool):
        return None
    if isinstance(v, (int, float)):
        return float(v)
    if isinstance(v, str):
        s = v.strip().replace(",", "")
        pct = s.endswith("%")
        try:
            n = float(s.rstrip("%"))
        except ValueError:
            return None
        return n / 100 if pct else n
    return None


def _to_bool(v: Any) -> bool | None:
    if isinstance(v, bool):
        return v
    if isinstance(v, str) and v.strip().lower() in {"true", "yes", "y", "1"}:
        return True
    if isinstance(v, str) and v.strip().lower() in {"false", "no", "n", "0"}:
        return False
    if isinstance(v, (int, float)) and v in (0, 1):
        return bool(v)
    return None


def _align_percent(value: float, threshold: float, unit: str | None) -> float:
    """If the policy says 40 (%) but the application stores 0.38, rescale the threshold."""
    if abs(value) <= 1.5 and abs(threshold) > 1.5 and (unit or "").lower() in {"percent", "%", "percentage"}:
        return threshold / 100
    return threshold


def compare(value: Any, op: str, threshold: Any, unit: str | None = None) -> bool | None:
    """True/False if the comparison can be made, None if it cannot (-> 'unclear')."""
    if op in {"<=", "<", ">=", ">"}:
        v, t = _to_number(value), _to_number(threshold)
        if v is None or t is None:
            return None
        t = _align_percent(v, t, unit)
        return {"<=": v <= t, "<": v < t, ">=": v >= t, ">": v > t}[op]
    if op == "between":
        if not isinstance(threshold, (list, tuple)) or len(threshold) != 2:
            return None
        v, lo, hi = _to_number(value), _to_number(threshold[0]), _to_number(threshold[1])
        if v is None or lo is None or hi is None:
            return None
        lo, hi = _align_percent(v, lo, unit), _align_percent(v, hi, unit)
        return lo <= v <= hi
    if op in {"==", "!="}:
        if isinstance(threshold, bool):
            b = _to_bool(value)
            result = None if b is None else (b == threshold)
        elif _to_number(threshold) is not None and _to_number(value) is not None:
            result = _to_number(value) == _to_number(threshold)
        else:
            result = _norm(str(value)) == _norm(str(threshold))
        return None if result is None else (result if op == "==" else not result)
    if op in {"in", "not_in"}:
        if not isinstance(threshold, (list, tuple)):
            return None
        allowed = {_norm(str(x)) for x in threshold}
        inside = _norm(str(value)) in allowed
        return inside if op == "in" else not inside
    return None  # qualitative


def _describe(op: str, threshold: Any, unit: str | None) -> str:
    u = f" {unit}" if unit and unit not in {"ratio", "count", "currency"} else ""
    if op == "between" and isinstance(threshold, (list, tuple)):
        return f"between {threshold[0]} and {threshold[1]}{u}"
    if op in {"in", "not_in"}:
        return f"{'one of' if op == 'in' else 'not one of'} {threshold}"
    return f"{op} {threshold}{u}"


# --------------------------------------------------------------------------- applicability, polarity, validation

# Wording that shows a rule states a BREACH ("... exceeds 10%", "knockout") rather than a condition to meet.
_STRONG_BREACH = re.compile(
    r"\b(knock-?out|decline\w*|breach\w*|violation|prohibited|red flag|severe|critical|high[- ]risk)\b", re.I)
_WEAK_BREACH = re.compile(r"\b(exceed\w*|more than|greater than|above|over|in excess of)\b", re.I)
# "income of $2,000 or more" is a minimum, so "or more/higher" cancels a weak breach cue (not a strong one:
# "4 or more NSF events is a knockout" is a breach).
_OR_MORE = re.compile(r"\bor (higher|more|above|greater)\b", re.I)
# Explicit minimum/maximum wording: the requirement is plainly a condition to meet. Never flipped.
_EXPLICIT_MEET = re.compile(
    r"\b(at least|minimum|no less than|at most|no more than|maximum|up to|must not|may not|cannot|not exceed|within)\b", re.I)


_MEET_UPPER = re.compile(r"\b(must not exceed|may not exceed|cannot exceed|not exceed|at most|no more than|maximum|up to)\b", re.I)
_MEET_LOWER = re.compile(r"\b(at least|minimum|no less than)\b", re.I)
_BAND_CUES = re.compile(r"\b(moderate|monitor|high[- ]risk|caution|conditional|referr\w*|elevated|red flag)\b", re.I)


def repair_polarity(rule: PolicyRule) -> tuple[str, str | None]:
    """(polarity, note). The LLM states polarity; Python backstops two common mistakes that would fail
    applicants who are well inside the limits:
    * a risk BAND ("between 3% and 10%", severity referral / risk_indicator, or band wording) is triggered by
      falling inside it, so it is a breach, never a condition to meet;
    * a breach level ("exceeds 10%", "knockout") extracted as ">" / ">=" must_meet.
    Explicit minimum/maximum wording ("at least", "must not exceed") is never flipped."""
    text = rule.requirement
    declared = rule.polarity or "must_meet"
    if declared == "breach_if":
        # The other direction: "must not exceed $250" with operator "<=" is a condition to MEET. Labelling it
        # breach_if would fail every applicant who is inside the limit.
        if (_MEET_UPPER.search(text) and rule.operator in {"<=", "<"}) or (
                _MEET_LOWER.search(text) and rule.operator in {">=", ">"}):
            return "must_meet", (f"requirement wording and operator '{rule.operator}' state a condition to meet, "
                                 "so the breach_if label was corrected to must_meet")
        return declared, None
    if _EXPLICIT_MEET.search(text):
        return declared, None
    if rule.operator == "between" and (rule.severity in {"referral", "risk_indicator"}
                                       or _BAND_CUES.search(f"{text} {rule.quote}")):
        return "breach_if", "a risk band is triggered by falling inside it, so it was treated as breach_if"
    if (rule.severity == "requirement" and rule.operator in {">", ">="}
            and (_STRONG_BREACH.search(text) or (_WEAK_BREACH.search(text) and not _OR_MORE.search(text)))):
        return "breach_if", (f"extracted '{rule.operator} {rule.threshold}' reads as a breach level, so it was "
                             "treated as breach_if instead of must_meet")
    return declared, None


# The policy's own wording decides severity: breaching a threshold that the text calls "Not Satisfied" / "Decline" /
# "Knockout" is a requirement failure, not just a referral. The LLM sometimes tags such a threshold "referral"
# because it sits next to a "Flag for Review" band (e.g. undisclosed debt under / over $250).
_DECLINE_LABEL = re.compile(r"\b(not satisfied|decline\w*|knock-?out|breach\w*|escalat\w*|critical)\b", re.I)
_BREACH_WORDS = re.compile(r"exceed\w*|\bover\b|above|more than|greater than|below|under|less than|breach\w*|[<>≤≥]", re.I)


def _number_pattern(threshold: Any) -> "re.Pattern | None":
    n = _to_number(threshold)
    if n is None:
        return None
    # the number as its own token: 43 matches "43" and "43.0%" but not "43.1" or "143"
    return re.compile(r"(?<![\d.])" + re.escape(f"{n:g}") + r"(?:\.0+)?(?!\.?\d)")


def repair_severity(rule: PolicyRule, policy_text: str) -> tuple[str, str | None]:
    """(severity, note). Raise a referral / risk_indicator threshold to "requirement" when a line of the policy
    text containing the same number calls breaching it "Not Satisfied", "Decline", "Knockout" or similar."""
    if rule.severity == "requirement" or rule.field is None or rule.operator not in {"<=", "<", ">=", ">"}:
        return rule.severity, None
    pattern = _number_pattern(rule.threshold)
    if pattern is None:
        return rule.severity, None
    for line in policy_text.splitlines():
        if pattern.search(line) and _DECLINE_LABEL.search(line) and _BREACH_WORDS.search(line):
            return "requirement", (f"the policy text calls breaching {rule.threshold} 'not satisfied', so severity "
                                   f"was raised from {rule.severity} to requirement")
    return rule.severity, None


def applies_to(rule: PolicyRule, application: dict) -> tuple[bool | None, str]:
    """Do the rule's applies_when conditions hold for this applicant? (True/False, or None if a condition's
    field is missing so the variant cannot be chosen) and a short reason."""
    for cond in rule.applies_when:
        value = application.get(cond.field)
        if _is_missing(value):
            return None, f"'{cond.field}' is empty, so it is unknown whether this variant applies"
        holds = compare(value, cond.operator, cond.value)
        if holds is None:
            return None, f"could not test {cond.field} = {value!r} against {_describe(cond.operator, cond.value, None)}"
        if not holds:
            return False, f"{cond.field} = {value!r} is not {_describe(cond.operator, cond.value, None)}"
    return True, ""


def _breaches(rule: PolicyRule, value: Any, polarity: str) -> bool | None:
    """True if the applicant value breaches the policy under this rule, None if it cannot be compared."""
    ok = compare(value, rule.operator, rule.threshold, rule.unit)
    if ok is None:
        return None
    return (not ok) if polarity == "must_meet" else ok


def validate_result(rule: PolicyRule, value: Any, status: str, polarity: str | None = None) -> tuple[str, str | None]:
    """Re-derive the status from (applicant value, extracted operator and threshold, polarity) and repair any
    status that contradicts it. In particular "not_satisfied" is invalid when the value does not breach the
    threshold, and "satisfied" is invalid when it does. Returns (status, note)."""
    if status not in {"satisfied", "not_satisfied"}:
        return status, None
    breach = _breaches(rule, value, polarity or rule.polarity or "must_meet")
    if breach is None:
        return "unclear", f"{status} could not be confirmed: {value!r} cannot be compared with the extracted threshold"
    expected = "not_satisfied" if breach else "satisfied"
    if status != expected:
        return expected, (f"status '{status}' contradicted the applicant value {value!r} vs "
                          f"{_describe(rule.operator, rule.threshold, rule.unit)} ({polarity or rule.polarity or 'must_meet'}); corrected to '{expected}'")
    return status, None


# --------------------------------------------------------------------------- checker


class PolicyChecker:
    def __init__(self, retriever: PolicyRetriever, llm: JSONLLM, topics: list[str] | None = None, k_per_topic: int = 3):
        self.retriever = retriever
        self.llm = llm
        self.topics = topics or DEFAULT_TOPICS
        self.k_per_topic = k_per_topic
        self.cache_dir = retriever.settings.index_dir / "rules_cache"

    # -- step 1: retrieve
    def retrieve_clauses(self) -> list[SearchResult]:
        return self.retriever.search_many(self.topics, k=self.k_per_topic)

    # -- step 2: extract rules (LLM, cached)
    def extract_rules(self, clauses: list[SearchResult], application: dict, use_cache: bool = True) -> list[PolicyRule]:
        fields = sorted(application.keys())
        key_src = json.dumps(
            {"chunks": sorted(r.chunk.chunk_id for r in clauses), "fields": fields, "llm": getattr(self.llm, "name", ""),
             "prompt": hashlib.sha1((SYSTEM_PROMPT + FIELD_NOTES).encode()).hexdigest()[:12]}
        )
        cache_file = self.cache_dir / f"{hashlib.sha1(key_src.encode()).hexdigest()[:16]}.json"
        if use_cache and cache_file.exists():
            raw = json.loads(cache_file.read_text())
        else:
            excerpts = "\n\n".join(
                f"=== EXCERPT chunk_id: {r.chunk.chunk_id}\nsource: {r.chunk.citation}\n{r.chunk.text}\n=== END"
                for r in clauses
            )
            examples = {k: application[k] for k in fields}
            user = (
                f"APPLICATION FIELDS (name: example value):\n{json.dumps(examples, indent=2, default=str)}\n{FIELD_NOTES}\n"
                f"POLICY EXCERPTS:\n{excerpts}"
            )
            raw = self.llm.complete_json(SYSTEM_PROMPT, user)
            if use_cache:
                self.cache_dir.mkdir(parents=True, exist_ok=True)
                cache_file.write_text(json.dumps(raw, indent=2))

        valid_ids = {r.chunk.chunk_id for r in clauses}
        rules: list[PolicyRule] = []
        seen: set[tuple] = set()
        for item in raw.get("rules", []):
            try:
                rule = PolicyRule.model_validate(item)
            except ValidationError:
                continue
            if rule.chunk_id not in valid_ids:  # grounding check: must cite a retrieved chunk
                continue
            if rule.field is not None and rule.field not in application:
                rule.field = None  # the LLM named a field that does not exist
            key = (rule.field, rule.operator, json.dumps(rule.threshold, default=str), rule.severity)
            if rule.field is not None and key in seen:
                continue
            seen.add(key)
            rules.append(rule)
        return rules

    # -- step 3: evaluate (deterministic: the LLM never judges the applicant)
    def evaluate(self, rules: list[PolicyRule], application: dict, clauses: list[SearchResult]) -> PolicyCheckResult:
        by_id = {r.chunk.chunk_id: r.chunk for r in clauses}
        out = PolicyCheckResult()
        used_fields = set()
        for rule in rules:
            chunk = by_id[rule.chunk_id]

            # 1. pick the variant that matches the applicant (employment type, credit tier, dependents ...)
            applicable, why = applies_to(rule, application)
            if applicable is False:
                out.not_applicable.append({"rule_id": rule.rule_id, "clause": rule.clause, "reason": why,
                                           "requirement": rule.requirement})
                continue

            quote_ok = bool(rule.quote) and _norm(rule.quote).strip("\"'\u2026. ") in _norm(chunk.text)
            value = application.get(rule.field) if rule.field else None
            if rule.field:
                used_fields.add(rule.field)

            # 2. polarity: is the extracted threshold a condition to meet, or the level that breaches the policy?
            polarity, note = repair_polarity(rule)
            severity, sev_note = repair_severity(rule, chunk.text)
            note = "; ".join(x for x in (note, sev_note) if x) or None

            if applicable is None:
                status: Status = "unclear"
                expl = f"Cannot tell whether this rule variant applies: {why}."
            elif rule.field is None:
                status = "missing"
                expl = "The application has no field for this requirement; the analyst must obtain or check it."
            elif _is_missing(value):
                status = "missing"
                expl = f"'{rule.field}' is empty in the application."
            elif rule.operator == "qualitative":
                status = "unclear"
                expl = f"Needs analyst judgement: {rule.field} = {value!r}."
            else:
                breach = _breaches(rule, value, polarity)
                if breach is None:
                    status = "unclear"
                    expl = f"Could not compare {rule.field} = {value!r} with {_describe(rule.operator, rule.threshold, rule.unit)}."
                else:
                    status = "not_satisfied" if breach else "satisfied"
                    cond = _describe(rule.operator, rule.threshold, rule.unit)
                    if polarity == "must_meet":
                        expl = f"{rule.field} = {value!r} {'does not meet' if breach else 'meets'} the condition {cond}."
                    else:
                        expl = f"{rule.field} = {value!r} {'breaches' if breach else 'does not reach'} the limit ({cond})."

            # 3. validate: no status may contradict the applicant value vs the extracted threshold
            if rule.field and not _is_missing(value) and rule.operator != "qualitative":
                checked, repair = validate_result(rule, value, status, polarity)
                if repair:
                    note, status = "; ".join(x for x in (note, repair) if x), checked  # type: ignore[assignment]
            if rule.claimed_status and rule.claimed_status != status:
                claim = f"the LLM claimed '{rule.claimed_status}'; the Python result '{status}' was used"
                note = "; ".join(x for x in (note, claim) if x)

            out.results.append(
                RuleResult(
                    rule_id=rule.rule_id,
                    requirement=rule.requirement,
                    status=status,
                    severity=severity,
                    field=rule.field,
                    applicant_value=value,
                    operator=rule.operator,
                    threshold=rule.threshold,
                    explanation=expl,
                    citation=chunk.citation if not rule.clause else f"{chunk.title} \u00a7{rule.clause}",
                    clause=rule.clause,
                    quote=rule.quote,
                    quote_verified=quote_ok,
                    source=chunk.source,
                    chunk_id=chunk.chunk_id,
                    polarity=polarity,
                    note=note,
                )
            )
        out.unmatched_fields = sorted(set(application) - used_fields)
        order = {"not_satisfied": 0, "missing": 1, "unclear": 2, "satisfied": 3}
        out.results.sort(key=lambda r: (order[r.status], r.clause or "~"))
        return out

    def check(self, application: dict, use_cache: bool = True) -> PolicyCheckResult:
        app = _flatten(application)
        clauses = self.retrieve_clauses()
        rules = self.extract_rules(clauses, app, use_cache=use_cache)
        return self.evaluate(rules, app, clauses)
