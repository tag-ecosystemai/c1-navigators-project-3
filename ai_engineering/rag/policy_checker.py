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

from pydantic import BaseModel, Field, ValidationError

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


class PolicyRule(BaseModel):
    rule_id: str
    requirement: str = Field(description="Plain-English statement of what the applicant must meet")
    chunk_id: str
    clause: str | None = None
    quote: str = Field(default="", description="Short verbatim excerpt from the clause")
    field: str | None = Field(default=None, description="Application field this rule tests, or null")
    operator: Literal["<=", "<", ">=", ">", "==", "!=", "between", "in", "not_in", "qualitative"]
    threshold: float | int | str | bool | list | None = None
    unit: str | None = None
    severity: Literal["requirement", "referral", "risk_indicator"] = "requirement"


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


@dataclass
class PolicyCheckResult:
    results: list[RuleResult] = field(default_factory=list)
    unmatched_fields: list[str] = field(default_factory=list)

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

Rules:
- Express every rule as the condition the applicant should meet. Example: "DTI must not exceed 40%" ->
  operator "<=", threshold 0.40 if the application stores DTI as a fraction (e.g. 0.38), or 40 if it stores percent.
- Match the threshold to the units of the example value for that field.
- A referral band like "40% to 45% is referred, above 45% fails" becomes TWO rules:
  "<= 0.45" severity "requirement" and "<= 0.40" severity "referral".
- A red flag like "two or more returned payments is a red flag" becomes operator "<=", threshold 1,
  severity "risk_indicator" (state the acceptable condition).
- Only extract rules that apply to an individual application. Skip governance, scope and process text.
- Do not evaluate the applicant. Do not invent rules that are not in the excerpts.
"""


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
            {"chunks": sorted(r.chunk.chunk_id for r in clauses), "fields": fields, "llm": getattr(self.llm, "name", "")}
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
                f"APPLICATION FIELDS (name: example value):\n{json.dumps(examples, indent=2, default=str)}\n\n"
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

    # -- step 3: evaluate (deterministic)
    def evaluate(self, rules: list[PolicyRule], application: dict, clauses: list[SearchResult]) -> PolicyCheckResult:
        by_id = {r.chunk.chunk_id: r.chunk for r in clauses}
        out = PolicyCheckResult()
        used_fields = set()
        for rule in rules:
            chunk = by_id[rule.chunk_id]
            quote_ok = bool(rule.quote) and _norm(rule.quote).strip("\"'…. ") in _norm(chunk.text)
            value = application.get(rule.field) if rule.field else None
            if rule.field:
                used_fields.add(rule.field)

            if rule.field is None:
                status: Status = "missing"
                expl = "The application has no field for this requirement; the analyst must obtain or check it."
            elif _is_missing(value):
                status = "missing"
                expl = f"'{rule.field}' is empty in the application."
            elif rule.operator == "qualitative":
                status = "unclear"
                expl = f"Needs analyst judgement: {rule.field} = {value!r}."
            else:
                ok = compare(value, rule.operator, rule.threshold, rule.unit)
                if ok is None:
                    status = "unclear"
                    expl = f"Could not compare {rule.field} = {value!r} with {_describe(rule.operator, rule.threshold, rule.unit)}."
                else:
                    status = "satisfied" if ok else "not_satisfied"
                    verb = "meets" if ok else "does not meet"
                    expl = f"{rule.field} = {value!r} {verb} the condition {_describe(rule.operator, rule.threshold, rule.unit)}."

            out.results.append(
                RuleResult(
                    rule_id=rule.rule_id,
                    requirement=rule.requirement,
                    status=status,
                    severity=rule.severity,
                    field=rule.field,
                    applicant_value=value,
                    operator=rule.operator,
                    threshold=rule.threshold,
                    explanation=expl,
                    citation=chunk.citation if not rule.clause else f"{chunk.title} §{rule.clause}",
                    clause=rule.clause,
                    quote=rule.quote,
                    quote_verified=quote_ok,
                    source=chunk.source,
                    chunk_id=chunk.chunk_id,
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
